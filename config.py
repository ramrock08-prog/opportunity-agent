import os

from dotenv import load_dotenv

# Load settings from the local .env file, if present.
load_dotenv()

APP_NAME = "Opportunity Agent"
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()


def _parse_origins(value: str) -> list[str]:
    """Parse a comma-separated CORS allow-list."""
    origins = [
        item.strip().rstrip("/")
        for item in value.split(",")
        if item.strip()
    ]

    return list(dict.fromkeys(origins))


ALLOWED_ORIGINS = _parse_origins(
    os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
)

# Authentication is opt-in for local development. Set AUTH_REQUIRED=1
# and provide a long random AUTH_SECRET before a public deployment.
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

AUTH_SECRET = os.getenv("AUTH_SECRET", "").strip()
AUTH_TOKEN_MINUTES = int(
    os.getenv("AUTH_TOKEN_MINUTES", "10080")
)

# Require a verified email before user-scoped API access. Local demos
# can disable this, and AUTH_DEV_SHOW_TOKENS exposes verification links
# in API responses during development only.
AUTH_REQUIRE_VERIFIED = os.getenv(
    "AUTH_REQUIRE_VERIFIED", "1"
).strip().lower() in {"1", "true", "yes", "on"}

AUTH_DEV_SHOW_TOKENS = os.getenv(
    "AUTH_DEV_SHOW_TOKENS", "0"
).strip().lower() in {"1", "true", "yes", "on"}

PUBLIC_APP_URL = os.getenv(
    "PUBLIC_APP_URL", "http://localhost:5173"
).strip().rstrip("/")

RATE_LIMIT_ENABLED = os.getenv(
    "RATE_LIMIT_ENABLED", "1"
).strip().lower() in {"1", "true", "yes", "on"}

TRUST_PROXY = os.getenv(
    "TRUST_PROXY", "0"
).strip().lower() in {"1", "true", "yes", "on"}

# When enabled, FastAPI serves frontend/dist at the site root. Docker
# images set this to 1 after building the React app.
SERVE_FRONTEND = os.getenv("SERVE_FRONTEND", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# AI configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite",
)

# Web-search configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Email configuration
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")


def require_setting(name: str) -> str:
    """Return a required setting without exposing its value in errors."""
    value = os.getenv(name)

    if not value:
        raise RuntimeError(
            f"Missing required setting: {name}. "
            "Check your local .env file."
        )

    return value
