"""Cross-process discovery lock stored in the database."""

import uuid
from datetime import datetime, timedelta, timezone

from database import (
    DatabaseError,
    get_connection,
    utc_now,
)


def acquire_lock(
    name: str,
    ttl_seconds: int = 20 * 60,
) -> str | None:
    """Return an owner token, or None when the lock is held."""
    owner = uuid.uuid4().hex
    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(seconds=ttl_seconds)
    ).isoformat(timespec="seconds")

    try:
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM discovery_locks
                WHERE name = ? AND expires_at <= ?
                """,
                (name, utc_now()),
            )

            row = connection.execute(
                """
                INSERT INTO discovery_locks(
                    name, owner, acquired_at, expires_at
                ) VALUES(?, ?, ?, ?)
                ON CONFLICT(name) DO NOTHING
                RETURNING name
                """,
                (name, owner, utc_now(), expires_at),
            ).fetchone()
    except DatabaseError as error:
        raise RuntimeError(
            "Could not acquire the discovery lock."
        ) from error

    return owner if row is not None else None


def release_lock(name: str, owner: str) -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM discovery_locks
                WHERE name = ? AND owner = ?
                """,
                (name, owner),
            )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not release the discovery lock."
        ) from error