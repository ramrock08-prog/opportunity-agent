import sqlite3
from urllib.parse import urlparse

from database import LEGACY_BOOKMARKS_FILE, get_connection, utc_now


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


def load_bookmarks() -> list[str]:
    """Load bookmarked opportunity URLs from SQLite."""
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT url FROM bookmarks
                ORDER BY created_at ASC, url ASC
                """
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


def add_bookmark(url: str) -> list[str]:
    """Add a URL to the saved shortlist."""
    if not _valid_url(url):
        raise ValueError("A valid HTTP or HTTPS URL is required.")

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO bookmarks(url, created_at)
                VALUES(?, ?)
                """,
                (url.strip(), utc_now()),
            )
    except sqlite3.Error as error:
        raise RuntimeError("Could not save the bookmark.") from error

    return load_bookmarks()


def remove_bookmark(url: str) -> list[str]:
    """Remove a URL from the saved shortlist."""
    try:
        with get_connection() as connection:
            connection.execute(
                "DELETE FROM bookmarks WHERE url = ?",
                (url.strip(),),
            )
    except sqlite3.Error as error:
        raise RuntimeError("Could not remove the bookmark.") from error

    return load_bookmarks()


def is_bookmarked(url: str) -> bool:
    """Return True when a URL is currently bookmarked."""
    return url.strip() in load_bookmarks()