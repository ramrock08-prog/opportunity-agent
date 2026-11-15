import os
from profile import UserProfile, load_profile, save_profile

import pytest
from fastapi.testclient import TestClient

import api
import auth
import rate_limit
from auth import (
    create_session,
    create_user,
    session_is_active,
)
from bookmarks import add_bookmark, load_bookmarks
from database import get_connection
from locks import acquire_lock, release_lock
from opportunity import Opportunity
from rate_limit import hit
from storage import load_opportunities, save_opportunities

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES_URL"),
    reason="Set TEST_POSTGRES_URL to run PostgreSQL integration tests.",
)

TABLES = (
    "sessions",
    "auth_tokens",
    "rate_limits",
    "discovery_locks",
    "discovery_candidates",
    "application_status",
    "user_bookmarks",
    "user_profiles",
    "users",
    "opportunities",
    "schema_meta",
)


def _drop_everything():
    import database

    with get_connection() as connection:
        for table in TABLES:
            connection.execute(
                f"DROP TABLE IF EXISTS {table} CASCADE"
            )

    database._initialized_targets.clear()


@pytest.fixture
def postgres_db(monkeypatch):
    import database

    monkeypatch.setenv(
        "DATABASE_URL", os.environ["TEST_POSTGRES_URL"]
    )
    monkeypatch.setenv("OPPORTUNITY_SKIP_IMPORT", "1")
    database._initialized_targets.clear()
    _drop_everything()

    assert database.initialize_database() == "postgresql"

    yield

    _drop_everything()


def test_postgres_storage_round_trip(postgres_db):
    save_opportunities([
        Opportunity(
            title="Postgres Intern",
            type="internship",
            organization="Example",
            source_url="https://example.com/pg",
            application_url="https://example.com/pg/apply",
            confidence=0.9,
        )
    ])

    loaded = load_opportunities()

    assert len(loaded) == 1
    assert loaded[0].title == "Postgres Intern"


def test_postgres_user_data_round_trip(postgres_db):
    user = create_user(
        "postgres@example.com",
        "strong-password",
        email_verified=True,
    )

    assert add_bookmark("https://example.com/saved", user["id"]) == [
        "https://example.com/saved"
    ]
    assert load_bookmarks(user["id"]) == [
        "https://example.com/saved"
    ]

    profile = UserProfile(name="PG User", opportunity_types=["internship"])
    save_profile(profile, user["id"])
    assert load_profile(user["id"]).name == "PG User"

    token = create_session(user)
    from auth import decode_token

    assert session_is_active(decode_token(token)["jti"])


def test_postgres_api_flow(postgres_db, monkeypatch):
    monkeypatch.setattr(api, "AUTH_REQUIRED", True)
    monkeypatch.setattr(api, "AUTH_REQUIRE_VERIFIED", False)
    monkeypatch.setattr(auth, "AUTH_REQUIRE_VERIFIED", False)
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_ENABLED", False)

    client = TestClient(api.app)

    registered = client.post(
        "/api/auth/register",
        json={
            "email": "pg-api@example.com",
            "password": "strong-password",
            "name": "PG API",
        },
    )
    assert registered.status_code == 200, registered.text
    token = registered.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    saved = client.post(
        "/api/bookmarks",
        json={"url": "https://example.com/pg-api"},
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["count"] == 1

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "pg-api@example.com"


def test_postgres_rate_limit_and_lock(postgres_db):
    assert hit("pg:test", 1, 60)[0] is True
    assert hit("pg:test", 1, 60)[0] is False

    owner = acquire_lock("discovery")
    assert owner
    assert acquire_lock("discovery") is None

    release_lock("discovery", owner)
    assert acquire_lock("discovery")