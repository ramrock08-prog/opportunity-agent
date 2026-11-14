"""Minimal SMTP delivery used by digests and account emails."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import RECEIVER_EMAIL, SENDER_EMAIL, SENDER_PASSWORD


def email_configured() -> bool:
    """True when outgoing Gmail SMTP credentials are present.

    RECEIVER_EMAIL is only needed for the digest, not for verification
    or password-reset messages sent to a user's own address.
    """
    return bool(SENDER_EMAIL and SENDER_PASSWORD)


def digest_configured() -> bool:
    return bool(email_configured() and RECEIVER_EMAIL)


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> bool:
    """Send an email without ever logging credentials.

    Returns False when SMTP is not configured or delivery fails.
    """
    if not email_configured():
        print(
            "Email is not configured. Set SENDER_EMAIL, "
            "SENDER_PASSWORD, and RECEIVER_EMAIL in .env."
        )
        return False

    if not to_email:
        print("No email recipient was provided.")
        return False

    message = MIMEMultipart("alternative")
    message["From"] = SENDER_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(text_body, "plain", "utf-8"))

    if html_body:
        message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(
            "smtp.gmail.com", 587, timeout=30
        ) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        print(
            "Email could not be sent. Check the Gmail app password "
            f"and network connection ({type(error).__name__})."
        )
        return False

    return True