"""SQLite persistence for Opportunity Agent.

The application used JSON files in its first iteration. This module
adds a transactional SQLite store and imports the legacy JSON files
once, so existing data is preserved without any manual migration step.

Set OPPORTUNITY_DB_PATH to use a different database file (tests and
deployments use this). Set OPPORTUNITY_SKIP_IMPORT=1 to disable the
one-time legacy JSON import.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "opportunity_agent.db"

LEGACY_OPPORTUNITIES_FILE = BASE_DIR / "opportunities.json"
LEGACY_BOOKMARKS_FILE = BASE_DIR / "bookmarks.json"
LEGACY_PROFILE_FILE = BASE_DIR / "profile.json"

SCHEMA_VERSION = "1"

_initialized_paths: set[str] = set()


def utc_now() -> str:
    """Return a timezone-aware ISO timestamp for database rows."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def database_path() -> Path:
    """Resolve the configured SQLite file."""
    configured = os.getenv("OPPORTUNITY_DB_PATH", "").strip()

    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = BASE_DIR / path
        return path

    return DEFAULT_DB_PATH


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Open a transactional SQLite connection with safe defaults."""
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    _ensure_schema(path)

    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _ensure_schema(path: Path) -> None:
    """Create tables and run the one-time JSON import if needed."""
    key = str(path.resolve())

    if key in _initialized_paths:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_key TEXT NOT NULL UNIQUE,
                source_url TEXT NOT NULL,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_opportunities_type
                ON opportunities(type);

            CREATE TABLE IF NOT EXISTS bookmarks (
                url TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        connection.execute(
            """
            INSERT INTO schema_meta(key, value)
            VALUES('schema_version', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (SCHEMA_VERSION,),
        )

        imported = connection.execute(
            "SELECT value FROM schema_meta WHERE key = 'legacy_imported'"
        ).fetchone()

        if imported is None:
            _import_legacy_json(connection)
            connection.execute(
                """
                INSERT INTO schema_meta(key, value)
                VALUES('legacy_imported', '1')
                ON CONFLICT(key) DO UPDATE SET value = '1'
                """
            )

        connection.commit()
    finally:
        connection.close()

    _initialized_paths.add(key)


def _import_legacy_json(connection: sqlite3.Connection) -> None:
    """Import the old JSON stores without overwriting newer data."""
    if os.getenv("OPPORTUNITY_SKIP_IMPORT") == "1":
        return

    now = utc_now()

    if LEGACY_OPPORTUNITIES_FILE.exists():
        try:
            records = json.loads(
                LEGACY_OPPORTUNITIES_FILE.read_text(
                    encoding="utf-8-sig"
                )
            )
        except (json.JSONDecodeError, OSError):
            records = []

        if isinstance(records, list):
            for record in records:
                if not isinstance(record, dict):
                    continue

                source_url = str(
                    record.get("source_url") or ""
                ).strip()
                title = str(record.get("title") or "").strip()
                record_type = str(record.get("type") or "").strip()

                if not source_url or not title or not record_type:
                    continue

                connection.execute(
                    """
                    INSERT OR IGNORE INTO opportunities(
                        source_key, source_url, title, type,
                        payload, created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_key(source_url, title, record.get(
                            "organization", ""
                        )),
                        source_url,
                        title,
                        record_type,
                        json.dumps(record, ensure_ascii=False),
                        now,
                        now,
                    ),
                )

    if LEGACY_PROFILE_FILE.exists():
        try:
            profile = json.loads(
                LEGACY_PROFILE_FILE.read_text(encoding="utf-8-sig")
            )
        except (json.JSONDecodeError, OSError):
            profile = None

        if isinstance(profile, dict):
            connection.execute(
                """
                INSERT OR IGNORE INTO profile(id, payload, updated_at)
                VALUES(1, ?, ?)
                """,
                (json.dumps(profile, ensure_ascii=False), now),
            )

    if LEGACY_BOOKMARKS_FILE.exists():
        try:
            urls = json.loads(
                LEGACY_BOOKMARKS_FILE.read_text(encoding="utf-8-sig")
            )
        except (json.JSONDecodeError, OSError):
            urls = []

        if isinstance(urls, list):
            for url in urls:
                if isinstance(url, str) and url.strip():
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO bookmarks(url, created_at)
                        VALUES(?, ?)
                        """,
                        (url.strip(), now),
                    )


def source_key(source_url: str, title: str, organization: str) -> str:
    """Build a stable unique key for an opportunity row."""
    normalized = (source_url or "").strip().lower().rstrip("/")

    if normalized:
        return normalized

    return " | ".join(
        [
            " ".join((title or "").lower().split()),
            " ".join((organization or "").lower().split()),
        ]
    )


def initialize_database() -> Path:
    """Create the schema and import legacy JSON when necessary."""
    path = database_path()
    _ensure_schema(path)
    return path


def healthcheck() -> bool:
    """Return True when the database can execute a simple query."""
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False