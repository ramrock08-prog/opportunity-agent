from datetime import date, timedelta

import notify
from opportunity import Opportunity


def make_opportunity(**overrides):
    data = {
        "title": "AI Internship",
        "type": "internship",
        "organization": "Example Labs",
        "description": "Work on machine learning.",
        "source_url": "https://example.com/job",
        "application_url": "https://example.com/apply",
        "location": "India",
        "deadline": (date.today() + timedelta(days=5)).isoformat(),
        "confidence": 0.9,
    }
    data.update(overrides)
    return Opportunity(**data)


def test_digest_escapes_untrusted_content():
    body = notify.build_digest([
        make_opportunity(
            title="<script>alert(1)</script>",
            description="<img src=x onerror=alert(1)>",
        )
    ])

    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "<img src=x" not in body
    assert "does not prove" in body


def test_digest_handles_empty_collection():
    body = notify.build_digest([])

    assert "No validated opportunities" in body


def test_send_without_configuration_is_skipped(monkeypatch):
    monkeypatch.setattr(notify, "SENDER_EMAIL", None)
    monkeypatch.setattr(notify, "SENDER_PASSWORD", None)
    monkeypatch.setattr(notify, "RECEIVER_EMAIL", None)

    assert notify.send_digest("<p>hi</p>") is False


def test_deadline_label_marks_passed_dates():
    past = (date.today() - timedelta(days=2)).isoformat()

    assert "passed" in notify._deadline_label(past)
    assert "No deadline" in notify._deadline_label(None)