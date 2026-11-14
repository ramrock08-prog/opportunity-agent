from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_resume_import_returns_prefilled_profile(
    isolated_db, monkeypatch
):
    monkeypatch.setattr(
        api,
        "extract_resume_text",
        lambda filename, data: "B.Tech ECE student skilled in Python.",
    )
    monkeypatch.setattr(
        api,
        "extract_profile_from_resume",
        lambda text: {
            "name": "Resume Student",
            "degree": "B.Tech",
            "branch": "ECE",
            "year_of_study": 3,
            "skills": ["Python"],
            "interests": ["AI"],
            "preferred_locations": ["India"],
            "remote_preferred": True,
            "opportunity_types": ["internship", "job"],
        },
    )

    response = client.post(
        "/api/profile/import-resume",
        files={
            "file": (
                "resume.txt",
                b"B.Tech ECE student skilled in Python.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200, response.text
    profile = response.json()["profile"]

    assert profile["name"] == "Resume Student"
    assert profile["degree"] == "B.Tech"
    assert profile["skills"] == ["Python"]
    assert profile["opportunity_types"] == ["internship", "job"]


def test_resume_import_rejects_unsupported_type(isolated_db):
    response = client.post(
        "/api/profile/import-resume",
        files={
            "file": (
                "resume.exe",
                b"MZ" * 100,
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 422


def test_resume_import_reports_missing_ai_key(
    isolated_db, monkeypatch
):
    monkeypatch.setattr(
        api,
        "extract_resume_text",
        lambda filename, data: "A valid resume with enough text.",
    )

    def fail(text):
        raise RuntimeError("GEMINI_API_KEY is missing.")

    monkeypatch.setattr(api, "extract_profile_from_resume", fail)

    response = client.post(
        "/api/profile/import-resume",
        files={
            "file": (
                "resume.txt",
                b"A valid resume with enough text.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]