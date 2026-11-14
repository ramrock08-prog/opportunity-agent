from rate_limit import clear_rate_limits, hit


def test_fixed_window_counter(isolated_db):
    assert hit("bucket:test", 2, 60) == (True, 61)
    assert hit("bucket:test", 2, 60)[0] is True

    allowed, retry_after = hit("bucket:test", 2, 60)

    assert allowed is False
    assert retry_after > 0


def test_clear_resets_counter(isolated_db):
    hit("bucket:test", 1, 60)
    clear_rate_limits()

    assert hit("bucket:test", 1, 60)[0] is True


def test_login_rate_limit(isolated_db, monkeypatch):
    from fastapi.testclient import TestClient

    import rate_limit
    from api import app

    monkeypatch.setattr(rate_limit, "RATE_LIMIT_ENABLED", True)
    clear_rate_limits()
    client = TestClient(app)

    statuses = [
        client.post(
            "/api/auth/login",
            json={
                "email": "missing@example.com",
                "password": "wrong-password",
            },
        ).status_code
        for _ in range(11)
    ]

    assert statuses[0] == 401
    assert statuses[-1] == 429