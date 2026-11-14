"""Run the PostgreSQL integration tests against a temporary local server.

Usage:
    python scripts/test_postgres.py

Requires the development dependency pgserver. Data is stored under
F:\Tools\pgdata by default; override with PGSERVER_DATA.
"""

import os
from pathlib import Path

import pgserver
import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(
    os.getenv("PGSERVER_DATA", r"F:\Tools\pgdata")
)

server = pgserver.get_server(DATA_DIR, cleanup_mode="stop")
os.environ["TEST_POSTGRES_URL"] = server.get_uri()

raise SystemExit(
    pytest.main([str(ROOT / "tests" / "test_postgres.py"), "-q"])
)