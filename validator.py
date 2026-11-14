from datetime import date, datetime
from urllib.parse import urlparse

from opportunity import ALLOWED_TYPES, Opportunity

TRAINING_LISTING_TERMS = {
    "training program",
    "training course",
    "online internship on",
    "bootcamp",
    "certification course",
    "course with certificate",
}

SOCIAL_MEDIA_HOSTS = {
    "instagram.com",
    "facebook.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
    "threads.net",
}


def valid_http_url(value: str) -> bool:
    """Check that a URL uses HTTP or HTTPS and has a hostname."""
    if not isinstance(value, str) or not value.strip():
        return False

    try:
        parsed = urlparse(value.strip())
        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.hostname)
            and " " not in value
        )
    except ValueError:
        return False


def _hostname(value: str) -> str:
    """Extract a normalized hostname from a URL."""
    try:
        parsed = urlparse(value.strip())
        return (parsed.hostname or "").lower().removeprefix("www.")
    except (AttributeError, ValueError):
        return ""


def _valid_date(value) -> bool:
    """Accept an unknown date or a valid YYYY-MM-DD date."""
    if value is None:
        return True

    if not isinstance(value, str):
        return False

    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_opportunity(
    opportunity: Opportunity,
    minimum_confidence: float = 0.55,
) -> tuple[bool, list[str]]:
    """
    Validate basic data quality, URL type, and deadline.

    Passing these checks does not prove that an opportunity is
    genuine, open, or suitable for a particular user.
    """
    problems = []

    if not opportunity.title.strip():
        problems.append("Missing title")

    if opportunity.type not in ALLOWED_TYPES:
        problems.append("Unsupported opportunity type")

    title_lower = opportunity.title.casefold()

    if opportunity.type in {"internship", "job"} and any(
        term in title_lower for term in TRAINING_LISTING_TERMS
    ):
        problems.append(
            "Title looks like a training/course listing, not a job"
        )

    if not valid_http_url(opportunity.source_url):
        problems.append("Invalid source URL")

    if not valid_http_url(opportunity.application_url):
        problems.append("Invalid application URL")
    else:
        host = _hostname(opportunity.application_url)

        if any(
            host == domain or host.endswith("." + domain)
            for domain in SOCIAL_MEDIA_HOSTS
        ):
            problems.append(
                "Application URL points to a social-media page, "
                "not a verified application page"
            )

    if not 0.0 <= opportunity.confidence <= 1.0:
        problems.append("Confidence must be between 0 and 1")
    elif opportunity.confidence < minimum_confidence:
        problems.append(
            "Confidence is below the minimum threshold"
        )

    if not _valid_date(opportunity.deadline):
        problems.append("Deadline must use YYYY-MM-DD format")
    elif opportunity.deadline:
        deadline = datetime.strptime(
            opportunity.deadline, "%Y-%m-%d"
        ).date()

        if deadline < date.today():
            problems.append("Deadline has passed")

    if not _valid_date(opportunity.start_date):
        problems.append("Start date must use YYYY-MM-DD format")

    return (len(problems) == 0, problems)
