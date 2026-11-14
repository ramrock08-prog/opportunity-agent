"""Password hashing and JWT helpers for optional user accounts."""

import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import jwt

from config import AUTH_REQUIRED, AUTH_SECRET, AUTH_TOKEN_MINUTES
from database import get_connection, utc_now

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)

PASSWORD_ITERATIONS = 260_000
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

JWT_ALGORITHM = "HS256"

# A development fallback keeps local demo mode working. Public
# deployments must set AUTH_SECRET.
_DEFAULT_SECRET = "opportunity-agent-development-secret-change-me"


def _secret() -> str:
    return AUTH_SECRET or _DEFAULT_SECRET


def using_insecure_default_secret() -> bool:
    """True when no production AUTH_SECRET has been configured."""
    return not bool(AUTH_SECRET)


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_credentials(email: str, password: str) -> None:
    """Raise ValueError with a safe message for invalid credentials."""
    if not EMAIL_PATTERN.match(normalize_email(email)):
        raise ValueError("Enter a valid email address.")

    if not isinstance(password, str):
        raise ValueError("Password must be text.")

    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must be {PASSWORD_MIN_LENGTH}-"
            f"{PASSWORD_MAX_LENGTH} characters."
        )


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 and a random salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )

    return (
        f"pbkdf2_sha256${PASSWORD_ITERATIONS}$"
        f"{salt.hex()}${digest.hex()}"
    )


def verify_password(password: str, stored: str) -> bool:
    """Compare a password against a stored PBKDF2 hash."""
    if not stored:
        return False

    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(digest.hex(), digest_hex)


def _public_user(row: sqlite3.Row | dict) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["display_name"] or "",
        "created_at": row["created_at"],
    }


def get_user_by_id(user_id: int) -> dict | None:
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id, email, display_name, created_at
                FROM users WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
    except sqlite3.Error as error:
        raise RuntimeError("Could not read the user account.") from error

    return _public_user(row) if row else None


def create_user(
    email: str,
    password: str,
    display_name: str = "",
) -> dict:
    """Create an account and return its public representation."""
    email = normalize_email(email)
    display_name = (display_name or "").strip()[:100]
    validate_credentials(email, password)

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users(
                    email, password_hash, display_name, created_at
                ) VALUES(?, ?, ?, ?)
                """,
                (
                    email,
                    hash_password(password),
                    display_name,
                    utc_now(),
                ),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError as error:
        raise ValueError(
            "An account with this email already exists."
        ) from error
    except sqlite3.Error as error:
        raise RuntimeError("Could not create the account.") from error

    user = get_user_by_id(user_id)

    if user is None:
        raise RuntimeError("The new account could not be loaded.")

    return user


def authenticate_user(email: str, password: str) -> dict | None:
    """Return the user when the email/password pair is correct."""
    email = normalize_email(email)

    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id, email, display_name, created_at,
                       password_hash
                FROM users WHERE email = ?
                """,
                (email,),
            ).fetchone()
    except sqlite3.Error as error:
        raise RuntimeError("Could not read the user account.") from error

    if row is None or not row["password_hash"]:
        return None

    if not verify_password(password, row["password_hash"]):
        return None

    return _public_user(row)


def issue_token(user: dict) -> str:
    """Create a signed bearer token for a user."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "iat": now,
        "exp": now + timedelta(minutes=AUTH_TOKEN_MINUTES),
    }

    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Return token claims, or None when invalid or expired."""
    try:
        return jwt.decode(
            token,
            _secret(),
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.PyJWTError:
        return None


def auth_mode_label() -> str:
    return "required" if AUTH_REQUIRED else "demo"


def auth_configuration_warning() -> str:
    if AUTH_REQUIRED and using_insecure_default_secret():
        return (
            "AUTH_REQUIRED is enabled but AUTH_SECRET is missing. "
            "Set a long random AUTH_SECRET before deployment."
        )

    return ""