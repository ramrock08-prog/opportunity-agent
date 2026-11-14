import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Point the application at a disposable SQLite database."""
    database_file = tmp_path / "test.db"

    monkeypatch.setenv(
        "OPPORTUNITY_DB_PATH", str(database_file)
    )
    monkeypatch.setenv("OPPORTUNITY_SKIP_IMPORT", "1")

    import database

    database._initialized_paths.discard(
        str(database_file.resolve())
    )

    yield database_file