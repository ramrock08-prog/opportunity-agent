from datetime import datetime, timedelta, timezone

import pytest

import auth
from auth import (
    EmailNotVerifiedError,
    authenticate_user,
    create_auth_token,
    create_session,
    create_user,
    reset_password,
    revoke_all_user_sessions,
    revoke_session,
    session_is_active,
    verify_email_token,
)


def test_session_can_be_revoked(isolated_db):
    user = create_user(
        "session@example.com",
        "strong-password",
        email_verified=True,
    )
    token = create_session(user)
    claims = auth.decode_token(token)

    assert session_is_active(claims["jti"])

    revoke_session(claims["jti"], user["id"])

    assert not session_is_active(claims["jti"])


def test_revoke_all_sessions(isolated_db):
    user = create_user(
        "session@example.com",
        "strong-password",
        email_verified=True,
    )
    first = auth.decode_token(create_session(user))
    second = auth.decode_token(create_session(user))

    revoke_all_user_sessions(user["id"])

    assert not session_is_active(first["jti"])
    assert not session_is_active(second["jti"])


def test_email_verification_token_is_single_use(isolated_db):
    user = create_user(
        "verify@example.com",
        "strong-password",
        email_verified=False,
    )
    token = create_auth_token(user["id"], "verify_email", 60)

    verified = verify_email_token(token)

    assert verified["email_verified"] is True
    assert verify_email_token(token) is None


def test_unverified_login_raises_when_required(
    isolated_db, monkeypatch
):
    user = create_user(
        "verify@example.com",
        "strong-password",
        email_verified=False,
    )
    monkeypatch.setattr(auth, "AUTH_REQUIRE_VERIFIED", True)

    with pytest.raises(EmailNotVerifiedError):
        authenticate_user(user["email"], "strong-password")


def test_account_locks_after_failed_attempts(isolated_db):
    user = create_user(
        "lock@example.com",
        "strong-password",
        email_verified=True,
    )

    for _ in range(5):
        assert (
            authenticate_user(user["email"], "wrong-password")
            is None
        )

    # Even the correct password is rejected while locked.
    assert (
        authenticate_user(user["email"], "strong-password")
        is None
    )


def test_password_reset_revokes_sessions(isolated_db):
    user = create_user(
        "reset@example.com",
        "strong-password",
        email_verified=True,
    )
    session = auth.decode_token(create_session(user))
    token = create_auth_token(user["id"], "reset_password", 30)

    updated = reset_password(token, "brand-new-password")

    assert updated["email"] == user["email"]
    assert not session_is_active(session["jti"])
    assert authenticate_user(
        user["email"], "brand-new-password"
    )["id"] == user["id"]


def test_expired_verification_token_is_rejected(isolated_db):
    user = create_user(
        "expired@example.com",
        "strong-password",
        email_verified=False,
    )
    token = create_auth_token(user["id"], "verify_email", 60)

    from database import get_connection

    expired = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat(timespec="seconds")

    with get_connection() as connection:
        connection.execute(
            "UPDATE auth_tokens SET expires_at = ?",
            (expired,),
        )

    assert verify_email_token(token) is None