"""Per-user application tracking for saved opportunities."""

from database import (
    DEMO_USER_ID,
    DatabaseError,
    get_connection,
    utc_now,
)
from validator import valid_http_url

ALLOWED_STATUSES = {
    "interested",
    "applied",
    "interview",
    "offer",
    "rejected",
}


def _clean_status(status: str) -> str:
    normalized = (status or "").strip().lower()

    if normalized not in ALLOWED_STATUSES:
        raise ValueError(
            "Status must be one of: "
            + ", ".join(sorted(ALLOWED_STATUSES))
        )

    return normalized


def load_applications(
    user_id: int = DEMO_USER_ID,
) -> list[dict]:
    """Load this user's tracked application rows."""
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT opportunity_url, status, note, updated_at
                FROM application_status
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
    except DatabaseError as error:
        raise RuntimeError(
            "Could not load applications."
        ) from error

    return [
        {
            "source_url": row["opportunity_url"],
            "status": row["status"],
            "note": row["note"] or "",
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def set_application_status(
    source_url: str,
    status: str,
    note: str = "",
    user_id: int = DEMO_USER_ID,
) -> dict:
    """Create or update one tracked application."""
    if not valid_http_url(source_url):
        raise ValueError("A valid opportunity URL is required.")

    status = _clean_status(status)
    note = (note or "").strip()[:500]

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO application_status(
                    user_id, opportunity_url, status, note, updated_at
                ) VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(user_id, opportunity_url) DO UPDATE SET
                    status = excluded.status,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    source_url.strip(),
                    status,
                    note,
                    utc_now(),
                ),
            )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not save the application status."
        ) from error

    return {
        "source_url": source_url.strip(),
        "status": status,
        "note": note,
    }


def remove_application(
    source_url: str,
    user_id: int = DEMO_USER_ID,
) -> list[dict]:
    """Stop tracking one opportunity."""
    try:
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM application_status
                WHERE user_id = ? AND opportunity_url = ?
                """,
                (user_id, source_url.strip()),
            )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not remove the application."
        ) from error

    return load_applications(user_id)


def application_summary(
    user_id: int = DEMO_USER_ID,
) -> dict:
    """Return counts per status plus the total."""
    summary = {status: 0 for status in sorted(ALLOWED_STATUSES)}
    applications = load_applications(user_id)

    for item in applications:
        summary[item["status"]] = (
            summary.get(item["status"], 0) + 1
        )

    summary["total"] = len(applications)
    return summary