import json
import os
from pathlib import Path
from urllib.parse import urlparse


BOOKMARKS_FILE = Path(__file__).with_name("bookmarks.json")


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
    """Load bookmarked opportunity URLs."""
    if not BOOKMARKS_FILE.exists():
        return []

    try:
        with BOOKMARKS_FILE.open(
            "r", encoding="utf-8-sig"
        ) as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "bookmarks.json contains invalid JSON."
        ) from error

    if not isinstance(data, list):
        raise RuntimeError(
            "bookmarks.json must contain a JSON list."
        )

    return list(dict.fromkeys(
        url.strip()
        for url in data
        if isinstance(url, str) and _valid_url(url)
    ))


def _save_bookmarks(urls: list[str]) -> None:
    """Write bookmarks using an atomic replacement."""
    temporary_file = BOOKMARKS_FILE.with_suffix(".json.tmp")

    try:
        with temporary_file.open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(urls, file, indent=2)
            file.write("\n")

        os.replace(temporary_file, BOOKMARKS_FILE)

    finally:
        if temporary_file.exists():
            temporary_file.unlink()


def add_bookmark(url: str) -> list[str]:
    """Add a URL to the saved shortlist."""
    if not _valid_url(url):
        raise ValueError("A valid HTTP or HTTPS URL is required.")

    urls = load_bookmarks()
    url = url.strip()

    if url not in urls:
        urls.append(url)
        _save_bookmarks(urls)

    return urls


def remove_bookmark(url: str) -> list[str]:
    """Remove a URL from the saved shortlist."""
    urls = load_bookmarks()
    remaining = [item for item in urls if item != url.strip()]

    if remaining != urls:
        _save_bookmarks(remaining)

    return remaining
