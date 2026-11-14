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
