"""Build and optionally send an Opportunity Agent email digest.

Preview mode writes an HTML file and never contacts Gmail:

    python notify.py --preview

Sending is opt-in:

    python notify.py --send
"""

import argparse
import html
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from config import RECEIVER_EMAIL, SENDER_EMAIL, SENDER_PASSWORD
from profile import load_profile
from storage import load_opportunities
from validator import validate_opportunity


DISCLAIMER = (
    "Opportunity Agent extracts listings automatically. A listing being "
    "included here does not prove that applications are open, that a "
    "deadline is current, or that you are eligible. Always confirm on "
    "the official page."
)


def _escape(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _deadline_label(value: str | None) -> str:
    if not value:
        return "No deadline published"

    try:
        deadline = datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return value

    remaining = (deadline - date.today()).days

    if remaining < 0:
        return f"{value} (passed)"
    if remaining == 0:
        return f"{value} (today)"

    return f"{value} ({remaining} days away)"


def build_digest(opportunities, profile=None) -> str:
    """Return a self-contained HTML email digest."""
    name = _escape(profile.name) if profile and profile.name else "there"
    generated = datetime.now().strftime("%d %B %Y, %H:%M")

    cards = []

    for item in opportunities:
        apply_url = _escape(
            item.application_url or item.source_url
        )
        cards.append(
            f"""
            <div style="border:1px solid #e5e9f2;border-radius:10px;
                        padding:16px;margin-bottom:14px;">
              <div style="font-size:11px;color:#6a5acd;
                          text-transform:uppercase;font-weight:700;">
                {_escape(item.type)}
              </div>
              <h3 style="margin:7px 0 3px;font-size:16px;color:#1f2d45;">
                {_escape(item.title)}
              </h3>
              <div style="font-size:12px;color:#77849a;">
                {_escape(item.organization or item.source or "Organization not specified")}
              </div>
              <p style="font-size:12px;color:#5f6c81;line-height:1.7;">
                {_escape(item.description[:320])}
              </p>
              <div style="font-size:11px;color:#69768b;line-height:1.9;">
                <strong>Location:</strong> {_escape(item.location)}<br>
                <strong>Deadline:</strong> {_escape(_deadline_label(item.deadline))}
              </div>
              <a href="{apply_url}"
                 style="display:inline-block;margin-top:12px;padding:8px 13px;
                        border-radius:6px;background:#6a54d8;color:#fff;
                        font-size:12px;font-weight:700;text-decoration:none;">
                View opportunity
              </a>
            </div>
            """
        )

    if not cards:
        cards.append(
            "<p style='color:#77849a;font-size:13px;'>"
            "No validated opportunities are stored yet.</p>"
        )

    return f"""<!doctype html>
<html>
  <body style="margin:0;padding:24px;background:#f4f6fb;
               font-family:Arial,Helvetica,sans-serif;color:#1f2d45;">
    <div style="max-width:620px;margin:0 auto;background:#fff;
                border:1px solid #e5e9f2;border-radius:12px;
                overflow:hidden;">
      <div style="padding:22px 24px;background:#10192b;color:#fff;">
        <div style="font-size:11px;letter-spacing:2px;color:#a99aff;">
          OPPORTUNITY AGENT
        </div>
        <h1 style="margin:8px 0 4px;font-size:21px;">
          Hi {name}, here are your opportunities
        </h1>
        <div style="font-size:12px;color:#aab6cb;">
          Generated {generated} · {len(opportunities)} validated record(s)
        </div>
      </div>
      <div style="padding:22px 24px;">
        {''.join(cards)}
        <p style="font-size:10px;color:#98a2b3;line-height:1.7;
                  border-top:1px solid #edf0f5;padding-top:14px;">
          {_escape(DISCLAIMER)}
        </p>
      </div>
    </div>
  </body>
</html>"""


def validated_opportunities():
    """Return currently valid records sorted by nearest deadline."""
    valid = []

    for opportunity in load_opportunities():
        is_valid, _problems = validate_opportunity(opportunity)
        if is_valid:
            valid.append(opportunity)

    return sorted(
        valid,
        key=lambda item: item.deadline or "9999-12-31",
    )


def send_digest(html_body: str, subject: str | None = None) -> bool:
    """Send the digest through Gmail SMTP.

    Returns False when email settings are not configured. Credentials
    are never printed or returned in error messages.
    """
    if not (SENDER_EMAIL and SENDER_PASSWORD and RECEIVER_EMAIL):
        print(
            "Email is not configured. Set SENDER_EMAIL, "
            "SENDER_PASSWORD, and RECEIVER_EMAIL in .env."
        )
        return False

    message = MIMEMultipart("alternative")
    message["From"] = SENDER_EMAIL
    message["To"] = RECEIVER_EMAIL
    message["Subject"] = subject or "Opportunity Agent digest"
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        print(
            "Email could not be sent. Check the Gmail app password "
            f"and network connection ({type(error).__name__})."
        )
        return False

    print("Email digest sent.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview or send the Opportunity Agent digest."
    )
    parser.add_argument(
        "--preview",
        nargs="?",
        const="email_preview.html",
        default=None,
        help="Write an HTML preview (optionally choose a path).",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the digest using the configured Gmail account.",
    )
    args = parser.parse_args()

    opportunities = validated_opportunities()
    body = build_digest(opportunities, load_profile())

    if args.send:
        sent = send_digest(
            body,
            subject=(
                f"Opportunity Agent: {len(opportunities)} "
                "validated opportunities"
            ),
        )
        if not sent:
            return 0

    if args.preview or not args.send:
        path = Path(args.preview or "email_preview.html")
        path.write_text(body, encoding="utf-8")
        print(f"Preview written to {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())