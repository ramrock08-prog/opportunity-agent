"""Password, session, and account-token helpers."""

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from config import (
    AUTH_REQUIRE_VERIFIED,
    AUTH_REQUIRED,
    AUTH_SECRET,
    AUTH_TOKEN_MINUTES,
)
from database import (
    DatabaseError,
    DatabaseIntegrityError,
    get_connection,
    utc_now,
)

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)

PASSWORD_ITERATIONS = 260_000
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

JWT_ALGORITHM = "HS256"
_DEFAULT_SECRET = "opportunity-agent-development-secret-change-me"
_DUMMY_HASH = None


class EmailNotVerifiedError(RuntimeError):
    """Raised after a correct password when email verification is required."""

    def __init__(self, user: dict):
        super().__init__("Email verification is required.")
        self.user = user


def _secret() -> str:
    return AUTH_SECRET or _DEFAULT_SECRET


def using_insecure_default_secret() -> bool:
    """True when no production AUTH_SECRET has been configured."""
    return not bool(AUTH_SECRET)


def _dummy_hash() -> str:
    global _DUMMY_HASH

    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("not-a-real-password")

    return _DUMMY_HASH


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_password(password: str) -> None:
    if not isinstance(password, str):
        raise ValueError("Password must be text.")

    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must be {PASSWORD_MIN_LENGTH}-"
            f"{PASSWORD_MAX_LENGTH} characters."
        )


def validate_credentials(email: str, password: str) -> None:
    """Raise ValueError with a safe message for invalid credentials."""
    if not EMAIL_PATTERN.match(normalize_email(email)):
        raise ValueError("Enter a valid email address.")

    validate_password(password)


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


def _public_user(row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["display_name"] or "",
        "email_verified": bool(row["email_verified"]),
        "created_at": row["created_at"],
    }


def get_user_by_id(user_id: int) -> dict | None:
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id, email, display_name, email_verified,
                       created_at
                FROM users WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
    except DatabaseError as error:
        raise RuntimeError(
            "Could not read the user account."
        ) from error

    return _public_user(row) if row else None


def create_user(
    email: str,
    password: str,
    display_name: str = "",
    email_verified: bool = False,
) -> dict:
    """Create an account and return its public representation."""
    email = normalize_email(email)
    display_name = (display_name or "").strip()[:100]
    validate_credentials(email, password)

    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                INSERT INTO users(
                    email, password_hash, display_name,
                    email_verified, created_at
                ) VALUES(?, ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    email,
                    hash_password(password),
                    display_name,
                    1 if email_verified else 0,
                    utc_now(),
                ),
            ).fetchone()
    except DatabaseIntegrityError as error:
        raise ValueError(
            "An account with this email already exists."
        ) from error
    except DatabaseError as error:
        raise RuntimeError(
            "Could not create the account."
        ) from error

    if row is None:
        raise RuntimeError("The new account could not be loaded.")

    user = get_user_by_id(row["id"])

    if user is None:
        raise RuntimeError("The new account could not be loaded.")

    return user


def _is_locked(locked_until: str | None) -> bool:
    if not locked_until:
        return False

    return locked_until > utc_now()


def _record_failed_login(user_id: int) -> None:
    locked_until = (
        datetime.now(timezone.utc)
        + timedelta(minutes=LOCKOUT_MINUTES)
    ).isoformat(timespec="seconds")

    try:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE users
                SET failed_login_attempts = failed_login_attempts + 1,
                    locked_until = CASE
                        WHEN failed_login_attempts + 1 >= ?
                        THEN ?
                        ELSE locked_until
                    END
                WHERE id = ?
                """,
                (MAX_FAILED_LOGINS, locked_until, user_id),
            )
    except DatabaseError:
        pass


def _clear_login_failures(user_id: int) -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE users
                SET failed_login_attempts = 0, locked_until = NULL
                WHERE id = ?
                """,
                (user_id,),
            )
    except DatabaseError:
        pass


def authenticate_user(email: str, password: str) -> dict | None:
    """Return the user when the email/password pair is correct.

    Raises EmailNotVerifiedError after a correct password when the
    account still needs verification.
    """
    email = normalize_email(email)

    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id, email, display_name, email_verified,
                       created_at, password_hash, failed_login_attempts,
                       locked_until
                FROM users WHERE email = ?
                """,
                (email,),
            ).fetchone()
    except DatabaseError as error:
        raise RuntimeError(
            "Could not read the user account."
        ) from error

    # Do comparable work for unknown accounts to reduce timing leaks.
    if row is None:
        verify_password(password, _dummy_hash())
        return None

    if _is_locked(row["locked_until"]):
        verify_password(password, _dummy_hash())
        return None

    if not row["password_hash"]:
        return None

    if not verify_password(password, row["password_hash"]):
        _record_failed_login(row["id"])
        return None

    _clear_login_failures(row["id"])
    user = _public_user(row)

    if AUTH_REQUIRE_VERIFIED and not user["email_verified"]:
        raise EmailNotVerifiedError(user)

    return user


def issue_token(user: dict, jti: str | None = None) -> str:
    """Create a signed bearer token. Sessions are created separately."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "jti": jti or uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=AUTH_TOKEN_MINUTES),
    }

    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_session(
    user: dict,
    minutes: int | None = None,
) -> str:
    """Create a revocable server-side session and return its JWT."""
    jti = uuid.uuid4().hex
    lifetime = minutes or AUTH_TOKEN_MINUTES
    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=lifetime)
    ).isoformat(timespec="seconds")

    try:
        with get_connection() as connection:
            # Opportunistic cleanup of expired sessions.
            connection.execute(
                "DELETE FROM sessions WHERE expires_at < ?",
                (utc_now(),),
            )
            connection.execute(
                """
                INSERT INTO sessions(
                    jti, user_id, created_at, expires_at
                ) VALUES(?, ?, ?, ?)
                """,
                (jti, user["id"], utc_now(), expires_at),
            )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not create a user session."
        ) from error

    return issue_token(user, jti)


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


def session_is_active(jti: str) -> bool:
    """Return True for a non-revoked, non-expired session."""
    if not jti:
        return False

    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT jti, expires_at, revoked_at
                FROM sessions WHERE jti = ?
                """,
                (jti,),
            ).fetchone()
    except DatabaseError:
        return False

    if row is None or row["revoked_at"]:
        return False

    return row["expires_at"] > utc_now()


def revoke_session(jti: str, user_id: int | None = None) -> None:
    try:
        with get_connection() as connection:
            if user_id is None:
                connection.execute(
                    """
                    UPDATE sessions SET revoked_at = ?
                    WHERE jti = ? AND revoked_at IS NULL
                    """,
                    (utc_now(), jti),
                )
            else:
                connection.execute(
                    """
                    UPDATE sessions SET revoked_at = ?
                    WHERE jti = ? AND user_id = ?
                      AND revoked_at IS NULL
                    """,
                    (utc_now(), jti, user_id),
                )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not revoke the user session."
        ) from error


def revoke_all_user_sessions(user_id: int) -> None:
    try:
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE sessions SET revoked_at = ?
                WHERE user_id = ? AND revoked_at IS NULL
                """,
                (utc_now(), user_id),
            )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not revoke user sessions."
        ) from error


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_auth_token(
    user_id: int,
    purpose: str,
    ttl_minutes: int,
) -> str:
    """Create a single-use verification/reset token."""
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=ttl_minutes)
    ).isoformat(timespec="seconds")

    try:
        with get_connection() as connection:
            connection.execute(
                "DELETE FROM auth_tokens WHERE expires_at < ?",
                (utc_now(),),
            )
            connection.execute(
                """
                DELETE FROM auth_tokens
                WHERE user_id = ? AND purpose = ? AND used_at IS NULL
                """,
                (user_id, purpose),
            )
            connection.execute(
                """
                INSERT INTO auth_tokens(
                    token_hash, user_id, purpose, created_at,
                    expires_at, used_at
                ) VALUES(?, ?, ?, ?, ?, NULL)
                """,
                (
                    _hash_token(token),
                    user_id,
                    purpose,
                    utc_now(),
                    expires_at,
                ),
            )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not create the account token."
        ) from error

    return token


def _active_token(
    connection, token: str, purpose: str
):
    return connection.execute(
        """
        SELECT token_hash, user_id, expires_at, used_at
        FROM auth_tokens
        WHERE token_hash = ? AND purpose = ?
        """,
        (_hash_token(token), purpose),
    ).fetchone()


def verify_email_token(token: str) -> dict | None:
    """Consume a verification token and mark the account verified."""
    try:
        with get_connection() as connection:
            row = _active_token(
                connection, token, "verify_email"
            )

            if (
                row is None
                or row["used_at"]
                or row["expires_at"] <= utc_now()
            ):
                return None

            connection.execute(
                "UPDATE auth_tokens SET used_at = ? WHERE token_hash = ?",
                (utc_now(), row["token_hash"]),
            )
            connection.execute(
                """
                UPDATE users SET email_verified = 1,
                    failed_login_attempts = 0, locked_until = NULL
                WHERE id = ?
                """,
                (row["user_id"],),
            )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not verify the email address."
        ) from error

    return get_user_by_id(row["user_id"])


def get_user_for_password_reset(email: str) -> dict | None:
    """Return a user for reset-email delivery without revealing existence."""
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id, email, display_name, email_verified,
                       created_at
                FROM users WHERE email = ?
                """,
                (normalize_email(email),),
            ).fetchone()
    except DatabaseError as error:
        raise RuntimeError(
            "Could not read the user account."
        ) from error

    return _public_user(row) if row else None


def reset_password(token: str, new_password: str) -> dict | None:
    """Consume a reset token, change the password, revoke sessions."""
    validate_password(new_password)

    try:
        with get_connection() as connection:
            row = _active_token(
                connection, token, "reset_password"
            )

            if (
                row is None
                or row["used_at"]
                or row["expires_at"] <= utc_now()
            ):
                return None

            connection.execute(
                "UPDATE auth_tokens SET used_at = ? WHERE token_hash = ?",
                (utc_now(), row["token_hash"]),
            )
            connection.execute(
                """
                UPDATE users
                SET password_hash = ?, failed_login_attempts = 0,
                    locked_until = NULL
                WHERE id = ?
                """,
                (hash_password(new_password), row["user_id"]),
            )
            connection.execute(
                """
                UPDATE sessions SET revoked_at = ?
                WHERE user_id = ? AND revoked_at IS NULL
                """,
                (utc_now(), row["user_id"]),
            )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not reset the password."
        ) from error

    return get_user_by_id(row["user_id"])


def auth_mode_label() -> str:
    return "required" if AUTH_REQUIRED else "demo"


def auth_configuration_warning() -> str:
    if AUTH_REQUIRED and using_insecure_default_secret():
        return (
            "AUTH_REQUIRED is enabled but AUTH_SECRET is missing. "
            "Set a long random AUTH_SECRET before deployment."
        )

    return ""