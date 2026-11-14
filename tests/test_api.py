from fastapi.testclient import TestClient

import api
from opportunity import Opportunity
from storage import save_opportunities


client = TestClient(api.app)


def test_health_reports_sqlite(isolated_db):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["storage"] == "sqlite"


def test_opportunities_endpoint_reads_database(isolated_db):
    save_opportunities([
        Opportunity(
            title="Backend Intern",
            type="internship",
            organization="Example",
            source_url="https://example.com/backend",
            application_url="https://example.com/backend/apply",
            confidence=0.9,
        )
    ])

    response = client.get("/api/opportunities")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["opportunities"][0]["title"] == (
        "Backend Intern"
    )


def test_bookmark_endpoints(isolated_db):
    url = "https://example.com/bookmark-test"

    created = client.post("/api/bookmarks", json={"url": url})
    assert created.status_code == 200
    assert url in created.json()["bookmarks"]

    listed = client.get("/api/bookmarks")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    removed = client.delete(
        "/api/bookmarks", params={"url": url}
    )
    assert removed.status_code == 200
    assert removed.json()["count"] == 0


def test_bookmark_rejects_invalid_url(isolated_db):
    response = client.post(
        "/api/bookmarks", json={"url": "not-a-url"}
    )

    assert response.status_code == 422


def test_profile_endpoints(isolated_db):
    payload = {
        "name": "Student",
        "degree": "B.Tech",
        "branch": "CSE",
        "year_of_study": 2,
        "skills": ["Python"],
        "interests": ["AI"],
        "preferred_locations": ["India"],
        "remote_preferred": True,
        "opportunity_types": ["internship", "hackathon"],
    }

    saved = client.put("/api/profile", json=payload)
    assert saved.status_code == 200

    loaded = client.get("/api/profile")
    assert loaded.status_code == 200
    assert loaded.json()["name"] == "Student"
    assert loaded.json()["opportunity_types"] == [
        "internship",
        "hackathon",
    ]


def test_verify_unknown_opportunity_returns_404(isolated_db):
    response = client.post(
        "/api/opportunities/verify",
        json={"source_url": "https://example.com/missing"},
    )

    assert response.status_code == 404


def test_verify_endpoint_uses_stored_record(
    isolated_db, monkeypatch
):
    source_url = "https://example.com/verify-me"

    save_opportunities([
        Opportunity(
            title="Verify Me",
            type="internship",
            source_url=source_url,
            application_url=source_url,
            confidence=0.9,
        )
    ])

    monkeypatch.setattr(
        "api.verify_opportunity",
        lambda opportunity: {
            "checked_at": "now",
            "application": {"status": "reachable"},
            "source": {"status": "reachable"},
            "deadline": {"status": "missing"},
            "disclaimer": "A link is not proof.",
        },
    )

    response = client.post(
        "/api/opportunities/verify",
        json={"source_url": source_url},
    )

    assert response.status_code == 200
    assert response.json()["verification"]["application"][
        "status"
    ] == "reachable"


def test_discovery_rejects_unknown_category(isolated_db):
    response = client.post(
        "/api/discover",
        json={"category": "not-real", "limit": 1},
    )

    assert response.status_code == 422


def test_discovery_returns_conflict_while_locked(isolated_db):
    acquired = api._discovery_lock.acquire(blocking=False)
    assert acquired

    try:
        response = client.post(
            "/api/discover",
            json={"category": "internship", "limit": 1},
        )
    finally:
        api._discovery_lock.release()

    assert response.status_code == 409