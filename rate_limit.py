"""Database-backed fixed-window rate limiting."""

import secrets
import time

from fastapi import HTTPException, Request

from config import RATE_LIMIT_ENABLED, TRUST_PROXY
from database import DatabaseError, get_connection


def clear_rate_limits() -> None:
    """Remove all counters. Intended for tests and local resets."""
    with get_connection() as connection:
        connection.execute("DELETE FROM rate_limits")


def _client_identity(request: Request | None, user_id: int | None):
    if user_id is not None:
        return f"user:{user_id}"

    if request is None:
        return "unknown"

    if TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

    return f"ip:{request.client.host if request.client else 'unknown'}"


def hit(
    key: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """Increment a fixed-window counter.

    Returns (allowed, retry_after_seconds). The atomic upsert works on
    both SQLite and PostgreSQL, so limits are shared across processes
    using the same database.
    """
    now = time.time()
    window_start_cutoff = now - window_seconds

    with get_connection() as connection:
        row = connection.execute(
            """
            INSERT INTO rate_limits(
                limit_key, window_start, count
            ) VALUES(?, ?, 1)
            ON CONFLICT(limit_key) DO UPDATE SET
                count = CASE
                    WHEN rate_limits.window_start < ?
                    THEN 1
                    ELSE rate_limits.count + 1
                END,
                window_start = CASE
                    WHEN rate_limits.window_start < ?
                    THEN ?
                    ELSE rate_limits.window_start
                END
            RETURNING count, window_start
            """,
            (
                key,
                now,
                window_start_cutoff,
                window_start_cutoff,
                now,
            ),
        ).fetchone()

        # Opportunistic cleanup keeps the table small.
        if secrets.randbelow(100) == 0:
            connection.execute(
                """
                DELETE FROM rate_limits
                WHERE window_start < ?
                """,
                (now - 86_400,),
            )

    if row is None:
        raise DatabaseError("Could not update the rate limiter.")

    retry_after = max(
        1, int(row["window_start"] + window_seconds - now) + 1
    )

    return row["count"] <= limit, retry_after


def enforce(
    request: Request | None,
    bucket: str,
    limit: int,
    window_seconds: int,
    user_id: int | None = None,
) -> None:
    """Raise HTTP 429 when a caller exceeds the bucket limit."""
    if not RATE_LIMIT_ENABLED:
        return

    key = f"{bucket}:{_client_identity(request, user_id)}"
    allowed, retry_after = hit(key, limit, window_seconds)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )