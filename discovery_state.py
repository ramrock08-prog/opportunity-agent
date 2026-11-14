"""Track web-result URLs already sent to Gemini."""

from datetime import datetime, timedelta, timezone

from database import DatabaseError, get_connection, utc_now

DEFAULT_COOLDOWN_DAYS = 14


def filter_unseen(
    results: list[dict],
    category: str,
    cooldown_days: int = DEFAULT_COOLDOWN_DAYS,
) -> list[dict]:
    """Drop URLs attempted recently for this category.

    This lets repeated discovery runs move deeper into search results
    instead of sending the same first few pages to Gemini forever.
    """
    if not results:
        return []

    cutoff = (
        datetime.now(timezone.utc)
        - timedelta(days=cooldown_days)
    ).isoformat(timespec="seconds")

    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT url FROM discovery_candidates
                WHERE category = ? AND last_attempted > ?
                """,
                (category, cutoff),
            ).fetchall()
    except DatabaseError as error:
        raise RuntimeError(
            "Could not load discovery candidate history."
        ) from error

    recent = {row["url"] for row in rows}
    return [
        item for item in results
        if item.get("url") and item["url"] not in recent
    ]


def mark_attempts(
    results: list[dict],
    category: str,
    outcomes: dict[str, str],
) -> None:
    """Record that these URLs were sent to Gemini."""
    if not results:
        return

    now = utc_now()

    try:
        with get_connection() as connection:
            for item in results:
                url = item.get("url")

                if not url:
                    continue

                connection.execute(
                    """
                    INSERT INTO discovery_candidates(
                        url, category, attempts,
                        last_attempted, outcome
                    ) VALUES(?, ?, 1, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        category = excluded.category,
                        attempts = discovery_candidates.attempts + 1,
                        last_attempted = excluded.last_attempted,
                        outcome = excluded.outcome
                    """,
                    (
                        url,
                        category,
                        now,
                        outcomes.get(url, "rejected"),
                    ),
                )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not update discovery candidate history."
        ) from error


def reset_candidates() -> None:
    """Clear candidate history. Intended for local maintenance."""
    try:
        with get_connection() as connection:
            connection.execute("DELETE FROM discovery_candidates")
    except DatabaseError as error:
        raise RuntimeError(
            "Could not reset discovery candidates."
        ) from error