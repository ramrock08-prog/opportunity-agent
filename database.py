"""Database persistence for Opportunity Agent.

Runtime storage is SQLite by default, or PostgreSQL when DATABASE_URL is
set. A small adapter keeps the repository code portable: it normalizes
placeholders, rows, transactions, and integrity errors.

Legacy JSON files are imported once, so existing data is preserved.
Set OPPORTUNITY_SKIP_IMPORT=1 to disable that import (tests).
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # SQLite-only installs still work.
    psycopg = None
    dict_row = None


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "opportunity_agent.db"

LEGACY_OPPORTUNITIES_FILE = BASE_DIR / "opportunities.json"
LEGACY_BOOKMARKS_FILE = BASE_DIR / "bookmarks.json"
LEGACY_PROFILE_FILE = BASE_DIR / "profile.json"

SCHEMA_VERSION = "3"
DEMO_USER_ID = 1
DEMO_USER_EMAIL = "demo@opportunity.local"

_initialized_targets: set[str] = set()


class DatabaseError(RuntimeError):
    """A safe, user-facing database failure."""


class DatabaseIntegrityError(DatabaseError):
    """A unique or foreign-key constraint was violated."""


def utc_now() -> str:
    """Return a timezone-aware ISO timestamp for database rows."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def database_url() -> str:
    return os.getenv("DATABASE_URL", "").strip()


def is_postgres() -> bool:
    return database_url().startswith(
        ("postgres://", "postgresql://")
    )


def database_label() -> str:
    return "postgresql" if is_postgres() else "sqlite"


def database_path() -> Path:
    """Resolve the configured SQLite file."""
    configured = os.getenv("OPPORTUNITY_DB_PATH", "").strip()

    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = BASE_DIR / path
        return path

    return DEFAULT_DB_PATH


def _target_key() -> str:
    if is_postgres():
        return f"postgres:{database_url()}"

    return f"sqlite:{database_path().resolve()}"


class _CursorWrapper:
    def __init__(self, cursor, postgres: bool):
        self._cursor = cursor
        self._postgres = postgres

    def execute(self, sql: str, params=()):
        if self._postgres:
            sql = sql.replace("?", "%s")

        try:
            self._cursor.execute(sql, params)
        except Exception as error:
            _translate_database_error(error)

        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        self._cursor.close()

    @property
    def lastrowid(self):
        return getattr(self._cursor, "lastrowid", None)

    @property
    def rowcount(self):
        return getattr(self._cursor, "rowcount", -1)


class _ConnectionWrapper:
    def __init__(self, connection, postgres: bool):
        self._connection = connection
        self._postgres = postgres

    def execute(self, sql: str, params=()):
        cursor = self._connection.cursor()
        return _CursorWrapper(cursor, self._postgres).execute(
            sql, params
        )

    def executemany(self, sql: str, parameter_rows):
        if self._postgres:
            sql = sql.replace("?", "%s")

        cursor = self._connection.cursor()

        try:
            cursor.executemany(sql, list(parameter_rows))
        except Exception as error:
            _translate_database_error(error)

        return _CursorWrapper(cursor, self._postgres)

    def executescript(self, script: str):
        if self._postgres:
            for statement in script.split(";"):
                if statement.strip():
                    self.execute(statement)
            return

        self._connection.executescript(script)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


def _translate_database_error(error: Exception) -> None:
    integrity = isinstance(error, sqlite3.IntegrityError)

    if psycopg is not None and isinstance(
        error, psycopg.errors.IntegrityError
    ):
        integrity = True

    if integrity:
        raise DatabaseIntegrityError(
            "A database uniqueness constraint was violated."
        ) from error

    raise DatabaseError("The database operation failed.") from error


def _open_raw():
    if is_postgres():
        if psycopg is None:
            raise DatabaseError(
                "PostgreSQL support requires the psycopg package."
            )

        try:
            return psycopg.connect(
                database_url(),
                row_factory=dict_row,
                connect_timeout=10,
            )
        except psycopg.Error as error:
            raise DatabaseError(
                "Could not connect to the configured database."
            ) from error

    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


@contextmanager
def get_connection() -> Iterator[_ConnectionWrapper]:
    """Open a transactional connection to SQLite or PostgreSQL."""
    _ensure_schema()

    try:
        raw = _open_raw()
    except DatabaseError:
        raise
    except Exception as error:
        raise DatabaseError(
            "Could not open the configured database."
        ) from error

    connection = _ConnectionWrapper(raw, is_postgres())

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _schema_sql() -> str:
    serial = (
        "BIGSERIAL PRIMARY KEY"
        if is_postgres()
        else "INTEGER PRIMARY KEY AUTOINCREMENT"
    )

    return f"""
    CREATE TABLE IF NOT EXISTS schema_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS opportunities (
        id {serial},
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

    CREATE TABLE IF NOT EXISTS users (
        id {serial},
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL DEFAULT '',
        display_name TEXT NOT NULL DEFAULT '',
        email_verified INTEGER NOT NULL DEFAULT 0,
        failed_login_attempts INTEGER NOT NULL DEFAULT 0,
        locked_until TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INTEGER PRIMARY KEY,
        payload TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS user_bookmarks (
        user_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (user_id, url),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_user_bookmarks_user
        ON user_bookmarks(user_id);

    CREATE TABLE IF NOT EXISTS sessions (
        jti TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        revoked_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_sessions_user
        ON sessions(user_id);

    CREATE TABLE IF NOT EXISTS auth_tokens (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        purpose TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_auth_tokens_user
        ON auth_tokens(user_id, purpose);

    CREATE TABLE IF NOT EXISTS rate_limits (
        limit_key TEXT PRIMARY KEY,
        window_start REAL NOT NULL,
        count INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS discovery_locks (
        name TEXT PRIMARY KEY,
        owner TEXT NOT NULL,
        acquired_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    );
    """


def _ensure_schema() -> None:
    """Create tables, run migrations, and import legacy JSON once."""
    key = _target_key()

    if key in _initialized_targets:
        return

    raw = _open_raw()
    connection = _ConnectionWrapper(raw, is_postgres())

    try:
        connection.executescript(_schema_sql())
        _migrate_user_columns(connection)

        # The demo user owns pre-authentication local data. It cannot
        # sign in because its password hash is empty.
        connection.execute(
            """
            INSERT INTO users(
                id, email, password_hash, display_name,
                email_verified, created_at
            ) VALUES(?, ?, '', 'Demo Student', 1, ?)
            ON CONFLICT DO NOTHING
            """,
            (DEMO_USER_ID, DEMO_USER_EMAIL, utc_now()),
        )

        if is_postgres():
            connection.execute(
                """
                SELECT setval(
                    pg_get_serial_sequence('users', 'id'),
                    GREATEST(
                        (SELECT COALESCE(MAX(id), 1) FROM users),
                        1
                    ),
                    true
                )
                """
            )

        v1_user_data_migrated = connection.execute(
            """
            SELECT value FROM schema_meta
            WHERE key = 'v1_user_data_migrated'
            """
        ).fetchone()

        if v1_user_data_migrated is None:
            _migrate_v1_user_data(connection)
            connection.execute(
                """
                INSERT INTO schema_meta(key, value)
                VALUES('v1_user_data_migrated', '1')
                ON CONFLICT(key) DO UPDATE SET value = '1'
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
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    _initialized_targets.add(key)


def _column_exists(
    connection: _ConnectionWrapper, table: str, column: str
) -> bool:
    if is_postgres():
        row = connection.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = ? AND column_name = ?
            """,
            (table, column),
        ).fetchone()
        return row is not None

    rows = connection.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()
    return any(row["name"] == column for row in rows)


def _migrate_user_columns(connection: _ConnectionWrapper) -> None:
    additions = (
        ("email_verified", "INTEGER NOT NULL DEFAULT 0"),
        ("failed_login_attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("locked_until", "TEXT"),
    )

    for column, definition in additions:
        if not _column_exists(connection, "users", column):
            connection.execute(
                f"ALTER TABLE users ADD COLUMN {column} {definition}"
            )


def _table_exists(
    connection: _ConnectionWrapper, name: str
) -> bool:
    if is_postgres():
        row = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name = ?
            """,
            (name,),
        ).fetchone()
        return row is not None

    row = connection.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (name,),
    ).fetchone()
    return row is not None


def _migrate_v1_user_data(
    connection: _ConnectionWrapper,
) -> None:
    """Copy single-user profile/bookmarks into the demo account."""
    if _table_exists(connection, "profile"):
        row = connection.execute(
            "SELECT payload FROM profile WHERE id = 1"
        ).fetchone()

        if row is not None:
            connection.execute(
                """
                INSERT INTO user_profiles(
                    user_id, payload, updated_at
                ) VALUES(?, ?, ?)
                ON CONFLICT(user_id) DO NOTHING
                """,
                (DEMO_USER_ID, row["payload"], utc_now()),
            )

    if _table_exists(connection, "bookmarks"):
        for row in connection.execute(
            "SELECT url, created_at FROM bookmarks"
        ).fetchall():
            connection.execute(
                """
                INSERT INTO user_bookmarks(
                    user_id, url, created_at
                ) VALUES(?, ?, ?)
                ON CONFLICT(user_id, url) DO NOTHING
                """,
                (DEMO_USER_ID, row["url"], row["created_at"]),
            )


def _import_legacy_json(
    connection: _ConnectionWrapper,
) -> None:
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
                    INSERT INTO opportunities(
                        source_key, source_url, title, type,
                        payload, created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_key) DO NOTHING
                    """,
                    (
                        source_key(
                            source_url,
                            title,
                            record.get("organization", ""),
                        ),
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
                INSERT INTO user_profiles(
                    user_id, payload, updated_at
                ) VALUES(?, ?, ?)
                ON CONFLICT(user_id) DO NOTHING
                """,
                (
                    DEMO_USER_ID,
                    json.dumps(profile, ensure_ascii=False),
                    now,
                ),
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
                        INSERT INTO user_bookmarks(
                            user_id, url, created_at
                        ) VALUES(?, ?, ?)
                        ON CONFLICT(user_id, url) DO NOTHING
                        """,
                        (DEMO_USER_ID, url.strip(), now),
                    )


def source_key(
    source_url: str, title: str, organization: str
) -> str:
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


def initialize_database() -> str:
    """Create the schema and return a safe database descriptor."""
    _ensure_schema()
    return database_label()


def healthcheck() -> bool:
    """Return True when the database can execute a simple query."""
    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()
        return True
    except (DatabaseError, OSError):
        return False