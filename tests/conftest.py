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
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import api
    import auth
    import database
    import rate_limit

    database._initialized_targets.clear()
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_ENABLED", False)
    monkeypatch.setattr(auth, "AUTH_REQUIRE_VERIFIED", False)
    monkeypatch.setattr(api, "AUTH_REQUIRE_VERIFIED", False)
    monkeypatch.setattr(api, "AUTH_DEV_SHOW_TOKENS", False)

    yield database_file