"""Verification and password-reset email content."""

import html

from auth import create_auth_token
from config import PUBLIC_APP_URL
from mailer import send_email


def _link(query_key: str, token: str) -> str:
    return f"{PUBLIC_APP_URL}/?{query_key}={token}"


def send_verification_email(user: dict) -> tuple[bool, str]:
    token = create_auth_token(
        user["id"], "verify_email", ttl_minutes=24 * 60
    )
    link = _link("verify_token", token)
    safe_name = html.escape(user.get("name") or "there")

    text = (
        f"Hi {user.get('name') or 'there'},\n\n"
        "Verify your Opportunity Agent email address:\n"
        f"{link}\n\n"
        "This link expires in 24 hours. If you did not register, "
        "you can ignore this message."
    )

    body = f"""<!doctype html>
<html><body style="font-family:Arial,sans-serif;background:#f4f6fb;
padding:24px;color:#1f2d45;">
  <div style="max-width:560px;margin:auto;background:#fff;
  border:1px solid #e5e9f2;border-radius:12px;padding:26px;">
    <h2 style="margin-top:0;">Verify your email</h2>
    <p>Hi {safe_name},</p>
    <p>Confirm your email address to activate your Opportunity Agent
    account.</p>
    <p style="margin:24px 0;">
      <a href="{html.escape(link)}"
         style="background:#6a54d8;color:#fff;padding:11px 16px;
         border-radius:7px;text-decoration:none;font-weight:700;">
        Verify email
      </a>
    </p>
    <p style="font-size:12px;color:#77849a;">This link expires in 24
    hours. If you did not register, ignore this email.</p>
  </div>
</body></html>"""

    sent = send_email(
        user["email"],
        "Verify your Opportunity Agent email",
        text,
        body,
    )
    return sent, token


def send_password_reset_email(user: dict) -> tuple[bool, str]:
    token = create_auth_token(
        user["id"], "reset_password", ttl_minutes=30
    )
    link = _link("reset_token", token)
    safe_name = html.escape(user.get("name") or "there")

    text = (
        f"Hi {user.get('name') or 'there'},\n\n"
        "Reset your Opportunity Agent password:\n"
        f"{link}\n\n"
        "This link expires in 30 minutes. If you did not request a "
        "reset, you can ignore this message."
    )

    body = f"""<!doctype html>
<html><body style="font-family:Arial,sans-serif;background:#f4f6fb;
padding:24px;color:#1f2d45;">
  <div style="max-width:560px;margin:auto;background:#fff;
  border:1px solid #e5e9f2;border-radius:12px;padding:26px;">
    <h2 style="margin-top:0;">Reset your password</h2>
    <p>Hi {safe_name},</p>
    <p>Use the button below to choose a new password.</p>
    <p style="margin:24px 0;">
      <a href="{html.escape(link)}"
         style="background:#6a54d8;color:#fff;padding:11px 16px;
         border-radius:7px;text-decoration:none;font-weight:700;">
        Reset password
      </a>
    </p>
    <p style="font-size:12px;color:#77849a;">This link expires in 30
    minutes. If you did not request it, ignore this email.</p>
  </div>
</body></html>"""

    sent = send_email(
        user["email"],
        "Reset your Opportunity Agent password",
        text,
        body,
    )
    return sent, token