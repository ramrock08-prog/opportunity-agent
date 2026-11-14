import sqlite3
from urllib.parse import urlparse

from database import (
    DEMO_USER_ID,
    LEGACY_BOOKMARKS_FILE,
    get_connection,
    utc_now,
)

# Legacy JSON location, retained for migration and tooling.
BOOKMARKS_FILE = LEGACY_BOOKMARKS_FILE


def _valid_url(url: str) -> bool:
    """Accept only HTTP or HTTPS URLs with a hostname."""
    if not isinstance(url, str) or not url.strip():
        return False

    try:
        parsed = urlparse(url.strip())
        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.hostname)
        )
    except ValueError:
        return False


def load_bookmarks(user_id: int = DEMO_USER_ID) -> list[str]:
    """Load one user's bookmarked opportunity URLs."""
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT url FROM user_bookmarks
                WHERE user_id = ?
                ORDER BY created_at ASC, url ASC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error as error:
        raise RuntimeError("Could not load bookmarks.") from error

    urls = []
    seen = set()

    for row in rows:
        url = row["url"].strip()

        if url not in seen and _valid_url(url):
            seen.add(url)
            urls.append(url)

    return urls


def add_bookmark(
    url: str, user_id: int = DEMO_USER_ID
) -> list[str]:
    """Add a URL to one user's saved shortlist."""
    if not _valid_url(url):
        raise ValueError("A valid HTTP or HTTPS URL is required.")

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO user_bookmarks(
                    user_id, url, created_at
                ) VALUES(?, ?, ?)
                """,
                (user_id, url.strip(), utc_now()),
            )
    except sqlite3.Error as error:
        raise RuntimeError("Could not save the bookmark.") from error

    return load_bookmarks(user_id)


def remove_bookmark(
    url: str, user_id: int = DEMO_USER_ID
) -> list[str]:
    """Remove a URL from one user's saved shortlist."""
    try:
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM user_bookmarks
                WHERE user_id = ? AND url = ?
                """,
                (user_id, url.strip()),
            )
    except sqlite3.Error as error:
        raise RuntimeError("Could not remove the bookmark.") from error

    return load_bookmarks(user_id)


def is_bookmarked(
    url: str, user_id: int = DEMO_USER_ID
) -> bool:
    """Return True when a URL is bookmarked by this user."""
    return url.strip() in load_bookmarks(user_id)