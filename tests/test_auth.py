import pytest

from auth import (
    authenticate_user,
    create_user,
    decode_token,
    hash_password,
    issue_token,
    verify_password,
)


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("correct horse battery")
    second = hash_password("correct horse battery")

    assert first != second
    assert verify_password("correct horse battery", first)
    assert not verify_password("wrong password", first)
    assert not verify_password("anything", "not-a-hash")


def test_create_and_authenticate_user(isolated_db):
    user = create_user(
        "Student@Example.com",
        "strong-password",
        "Student",
    )

    assert user["email"] == "student@example.com"
    assert authenticate_user(
        "student@example.com", "strong-password"
    )["id"] == user["id"]
    assert authenticate_user(
        "student@example.com", "wrong-password"
    ) is None


def test_duplicate_email_is_rejected(isolated_db):
    create_user("student@example.com", "strong-password")

    with pytest.raises(ValueError, match="already exists"):
        create_user("STUDENT@example.com", "another-password")


def test_weak_credentials_are_rejected(isolated_db):
    with pytest.raises(ValueError, match="valid email"):
        create_user("not-an-email", "strong-password")

    with pytest.raises(ValueError, match="8-128"):
        create_user("student@example.com", "short")


def test_token_round_trip(isolated_db):
    user = create_user("student@example.com", "strong-password")
    token = issue_token(user)

    claims = decode_token(token)

    assert claims["sub"] == str(user["id"])
    assert claims["email"] == "student@example.com"
    assert decode_token("not-a-token") is None


def test_demo_account_cannot_sign_in(isolated_db):
    assert authenticate_user(
        "demo@opportunity.local", ""
    ) is None