from datetime import date, timedelta

from opportunity import Opportunity
from validator import validate_opportunity


def make_opportunity(**overrides):
    data = {
        "title": "Valid Internship",
        "type": "internship",
        "source_url": "https://example.com/internship",
        "application_url": "https://example.com/internship/apply",
        "confidence": 0.9,
    }
    data.update(overrides)
    return Opportunity(**data)


def test_valid_opportunity_passes():
    future = (date.today() + timedelta(days=40)).isoformat()
    is_valid, problems = validate_opportunity(
        make_opportunity(deadline=future)
    )

    assert is_valid, problems


def test_social_media_application_is_rejected():
    is_valid, problems = validate_opportunity(
        make_opportunity(
            application_url="https://instagram.com/p/example"
        )
    )

    assert not is_valid
    assert any("social-media" in problem for problem in problems)


def test_past_deadline_is_rejected():
    past = (date.today() - timedelta(days=1)).isoformat()
    is_valid, problems = validate_opportunity(
        make_opportunity(deadline=past)
    )

    assert not is_valid
    assert "Deadline has passed" in problems


def test_low_confidence_is_rejected():
    is_valid, problems = validate_opportunity(
        make_opportunity(confidence=0.2)
    )

    assert not is_valid
    assert any("Confidence" in problem for problem in problems)


def test_invalid_urls_and_dates_are_rejected():
    is_valid, problems = validate_opportunity(
        make_opportunity(
            source_url="ftp://example.com",
            application_url="not a url",
            deadline="2026/01/01",
            start_date="soon",
        )
    )

    assert not is_valid
    assert "Invalid source URL" in problems
    assert "Invalid application URL" in problems
    assert "Deadline must use YYYY-MM-DD format" in problems
    assert "Start date must use YYYY-MM-DD format" in problems