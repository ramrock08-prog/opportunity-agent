from application_tracker import (
    ALLOWED_STATUSES,
    application_summary,
    load_applications,
    remove_application,
    set_application_status,
)
from auth import create_user

URL = "https://example.com/internship"


def test_status_round_trip(isolated_db):
    user = create_user(
        "apps@example.com", "strong-password", email_verified=True
    )

    saved = set_application_status(
        URL, "applied", "Applied on the careers page", user["id"]
    )

    assert saved["status"] == "applied"
    assert load_applications(user["id"])[0]["note"].startswith(
        "Applied"
    )

    set_application_status(URL, "interview", user_id=user["id"])
    assert load_applications(user["id"])[0]["status"] == "interview"

    summary = application_summary(user["id"])
    assert summary["interview"] == 1
    assert summary["total"] == 1

    assert remove_application(URL, user["id"]) == []
    assert summary["total"] == 1


def test_invalid_status_is_rejected(isolated_db):
    user = create_user(
        "apps@example.com", "strong-password", email_verified=True
    )

    try:
        set_application_status(URL, "not-a-status", user_id=user["id"])
    except ValueError as error:
        assert "Status must be one of" in str(error)
    else:
        raise AssertionError("Invalid status was accepted.")

    assert "applied" in ALLOWED_STATUSES