from urllib.parse import parse_qs, urlparse

import auth_emails
from auth import create_user


def test_verification_email_contains_single_use_link(
    isolated_db, monkeypatch
):
    captured = {}

    def fake_send(to_email, subject, text, html_body):
        captured.update(
            {
                "to": to_email,
                "subject": subject,
                "text": text,
                "html": html_body,
            }
        )
        return True

    monkeypatch.setattr(auth_emails, "send_email", fake_send)
    monkeypatch.setattr(
        auth_emails, "PUBLIC_APP_URL", "https://example.test"
    )

    user = create_user(
        "mail@example.com",
        "strong-password",
        "Mail <User>",
        email_verified=False,
    )

    sent, token = auth_emails.send_verification_email(user)

    assert sent is True
    assert token
    assert captured["to"] == "mail@example.com"
    assert "verify_token=" in captured["text"]
    assert "&lt;User&gt;" in captured["html"]

    link = next(
        line
        for line in captured["text"].splitlines()
        if "verify_token=" in line
    )
    parsed = urlparse(link)
    assert parsed.netloc == "example.test"
    assert parse_qs(parsed.query)["verify_token"] == [token]


def test_reset_email_uses_reset_parameter(isolated_db, monkeypatch):
    captured = {}

    def fake_send(to_email, subject, text, html_body):
        captured["text"] = text
        return True

    monkeypatch.setattr(auth_emails, "send_email", fake_send)

    user = create_user(
        "reset-mail@example.com",
        "strong-password",
        email_verified=True,
    )

    sent, token = auth_emails.send_password_reset_email(user)

    assert sent is True
    assert "reset_token=" in captured["text"]
    assert token in captured["text"]