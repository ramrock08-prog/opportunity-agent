from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def register(email, name):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "strong-password",
            "name": name,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_auth_mode_requires_token(isolated_db, monkeypatch):
    monkeypatch.setattr(api, "AUTH_REQUIRED", True)

    assert client.get("/api/profile").status_code == 401
    assert client.get("/api/bookmarks").status_code == 401
    assert client.get("/api/recommendations").status_code == 401


def test_register_login_and_me(isolated_db, monkeypatch):
    monkeypatch.setattr(api, "AUTH_REQUIRED", True)

    token = register("alice@example.com", "Alice")

    me = client.get("/api/auth/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "alice@example.com"

    login = client.post(
        "/api/auth/login",
        json={
            "email": "alice@example.com",
            "password": "strong-password",
        },
    )
    assert login.status_code == 200
    assert login.json()["token"]


def test_bad_login_is_generic(isolated_db, monkeypatch):
    monkeypatch.setattr(api, "AUTH_REQUIRED", True)
    register("alice@example.com", "Alice")

    response = client.post(
        "/api/auth/login",
        json={
            "email": "alice@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Email or password is incorrect."
    )


def test_users_cannot_read_each_others_bookmarks(
    isolated_db, monkeypatch
):
    monkeypatch.setattr(api, "AUTH_REQUIRED", True)

    alice = auth_header(register("alice@example.com", "Alice"))
    bob = auth_header(register("bob@example.com", "Bob"))

    url = "https://example.com/alice-only"

    saved = client.post(
        "/api/bookmarks", json={"url": url}, headers=alice
    )
    assert saved.status_code == 200
    assert saved.json()["bookmarks"] == [url]

    assert client.get(
        "/api/bookmarks", headers=bob
    ).json()["bookmarks"] == []

    assert client.delete(
        "/api/bookmarks", params={"url": url}, headers=bob
    ).json()["bookmarks"] == []

    assert client.get(
        "/api/bookmarks", headers=alice
    ).json()["bookmarks"] == [url]


def test_users_cannot_read_each_others_profiles(
    isolated_db, monkeypatch
):
    monkeypatch.setattr(api, "AUTH_REQUIRED", True)

    alice = auth_header(register("alice@example.com", "Alice"))
    bob = auth_header(register("bob@example.com", "Bob"))

    payload = {
        "name": "Alice",
        "degree": "B.Tech",
        "branch": "CSE",
        "year_of_study": 3,
        "skills": ["Python"],
        "interests": ["AI"],
        "preferred_locations": ["India"],
        "remote_preferred": True,
        "opportunity_types": ["internship"],
    }

    assert client.put(
        "/api/profile", json=payload, headers=alice
    ).status_code == 200

    bob_profile = client.get("/api/profile", headers=bob)
    assert bob_profile.status_code == 200
    assert bob_profile.json()["name"] == ""
    assert bob_profile.json()["opportunity_types"] != ["internship"]