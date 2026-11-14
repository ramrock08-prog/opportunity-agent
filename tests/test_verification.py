from datetime import date, timedelta

from opportunity import Opportunity
from verification import (
    check_url,
    deadline_status,
    verify_opportunity,
)


class FakeResponse:
    def __init__(
        self,
        status_code,
        url="https://example.com/final",
        headers=None,
    ):
        self.status_code = status_code
        self.url = url
        self.headers = headers or {}

    def iter_content(self, size):
        return iter([b"ok"])

    def close(self):
        pass


def test_deadline_status_branches():
    assert deadline_status(None)["status"] == "missing"
    assert deadline_status("not-a-date")["status"] == "invalid"

    past = (date.today() - timedelta(days=2)).isoformat()
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=9)).isoformat()

    assert deadline_status(past)["status"] == "passed"
    assert deadline_status(today)["status"] == "closes_today"
    assert deadline_status(future)["status"] == "future"
    assert deadline_status(future)["days_remaining"] == 9


def test_invalid_url_is_not_fetched():
    result = check_url("not-a-url")

    assert result["status"] == "invalid"
    assert result["status_code"] is None


def test_private_host_is_blocked():
    result = check_url("http://127.0.0.1:8000/api/health")

    assert result["status"] == "blocked"
    assert "not a public" in result["message"]


def test_reachable_page(monkeypatch):
    monkeypatch.setattr(
        "verification._is_public_hostname", lambda host: True
    )
    monkeypatch.setattr(
        "verification.requests.get",
        lambda *args, **kwargs: FakeResponse(200),
    )

    result = check_url("https://example.com/job")

    assert result["status"] == "reachable"
    assert result["status_code"] == 200
    assert "does not confirm" in result["message"]


def test_blocked_page(monkeypatch):
    monkeypatch.setattr(
        "verification._is_public_hostname", lambda host: True
    )
    monkeypatch.setattr(
        "verification.requests.get",
        lambda *args, **kwargs: FakeResponse(403),
    )

    result = check_url("https://example.com/job")

    assert result["status"] == "blocked"
    assert "normal browser" in result["message"]


def test_redirect_to_private_host_is_blocked(monkeypatch):
    monkeypatch.setattr(
        "verification._is_public_hostname",
        lambda host: host != "127.0.0.1",
    )
    monkeypatch.setattr(
        "verification.requests.get",
        lambda *args, **kwargs: FakeResponse(
            302, headers={"Location": "http://127.0.0.1/secret"}
        ),
    )

    result = check_url("https://example.com/job")

    assert result["status"] == "blocked"
    assert "non-public host" in result["message"]


def test_public_redirect_is_followed(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return FakeResponse(
                302, headers={"Location": "/final"}
            )
        return FakeResponse(200)

    monkeypatch.setattr(
        "verification._is_public_hostname", lambda host: True
    )
    monkeypatch.setattr("verification.requests.get", fake_get)

    result = check_url("https://example.com/job")

    assert result["status"] == "reachable"
    assert result["final_url"] == "https://example.com/final"
    assert calls == [
        "https://example.com/job",
        "https://example.com/final",
    ]


def test_verify_opportunity_reports_both_links(monkeypatch):
    calls = []

    def fake_check(url, timeout=12):
        calls.append(url)
        return {
            "url": url,
            "status": "reachable",
            "status_code": 200,
            "final_url": url,
            "checked_at": "now",
            "message": "ok",
        }

    monkeypatch.setattr("verification.check_url", fake_check)

    opportunity = Opportunity(
        title="Internship",
        type="internship",
        source_url="https://news.example.com/listing",
        application_url="https://careers.example.org/apply",
        deadline="2099-01-01",
        confidence=0.9,
    )

    result = verify_opportunity(opportunity)

    assert calls == [
        "https://careers.example.org/apply",
        "https://news.example.com/listing",
    ]
    assert result["same_host"] is False
    assert result["application_on_social_media"] is False
    assert result["deadline"]["status"] == "future"
    assert "does not confirm" in result["disclaimer"]


def test_verify_opportunity_reuses_same_page(monkeypatch):
    calls = []

    def fake_check(url, timeout=12):
        calls.append(url)
        return {
            "url": url,
            "status": "reachable",
            "status_code": 200,
            "final_url": url,
            "checked_at": "now",
            "message": "ok",
        }

    monkeypatch.setattr("verification.check_url", fake_check)

    opportunity = Opportunity(
        title="Internship",
        type="internship",
        source_url="https://example.com/job",
        application_url="https://example.com/job",
        confidence=0.9,
    )

    result = verify_opportunity(opportunity)

    assert calls == ["https://example.com/job"]
    assert result["source"]["same_as_application"] is True
    assert result["same_host"] is True