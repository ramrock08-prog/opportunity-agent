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


def test_required_email_verification_flow(
    isolated_db, monkeypatch
):
    import auth
    import auth_emails

    monkeypatch.setattr(api, "AUTH_REQUIRED", True)
    monkeypatch.setattr(api, "AUTH_REQUIRE_VERIFIED", True)
    monkeypatch.setattr(auth, "AUTH_REQUIRE_VERIFIED", True)
    monkeypatch.setattr(api, "AUTH_DEV_SHOW_TOKENS", True)
    monkeypatch.setattr(api, "email_configured", lambda: False)
    monkeypatch.setattr(
        auth_emails, "send_email", lambda *args, **kwargs: False
    )

    registered = client.post(
        "/api/auth/register",
        json={
            "email": "verify@example.com",
            "password": "strong-password",
            "name": "Verify Me",
        },
    )

    assert registered.status_code == 200, registered.text
    body = registered.json()
    assert body["verification_required"] is True
    assert "token" not in body
    assert body["dev_verification_token"]

    blocked = client.post(
        "/api/auth/login",
        json={
            "email": "verify@example.com",
            "password": "strong-password",
        },
    )
    assert blocked.status_code == 403

    verified = client.post(
        "/api/auth/verify-email",
        json={"token": body["dev_verification_token"]},
    )
    assert verified.status_code == 200
    token = verified.json()["token"]

    me = client.get("/api/auth/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["user"]["email_verified"] is True

    logout = client.post(
        "/api/auth/logout", headers=auth_header(token)
    )
    assert logout.status_code == 200

    # Revoked sessions cannot be reused.
    assert client.get(
        "/api/auth/me", headers=auth_header(token)
    ).status_code == 401


def test_password_reset_flow(isolated_db, monkeypatch):
    import auth_emails

    monkeypatch.setattr(api, "AUTH_REQUIRED", True)
    monkeypatch.setattr(api, "AUTH_DEV_SHOW_TOKENS", True)
    monkeypatch.setattr(
        auth_emails, "send_email", lambda *args, **kwargs: False
    )

    token = register("reset@example.com", "Reset User")

    forgot = client.post(
        "/api/auth/forgot-password",
        json={"email": "reset@example.com"},
    )
    assert forgot.status_code == 200
    reset_token = forgot.json()["dev_reset_token"]

    reset = client.post(
        "/api/auth/reset-password",
        json={
            "token": reset_token,
            "password": "new-strong-password",
        },
    )
    assert reset.status_code == 200

    # Existing sessions are revoked.
    assert client.get(
        "/api/auth/me", headers=auth_header(token)
    ).status_code == 401

    login = client.post(
        "/api/auth/login",
        json={
            "email": "reset@example.com",
            "password": "new-strong-password",
        },
    )
    assert login.status_code == 200


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