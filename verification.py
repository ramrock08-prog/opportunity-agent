"""Honest, on-demand verification of stored opportunity links.

A successful HTTP response proves only that a page responded. It does
not prove that a role is open, that a deadline is correct, or that a
student is eligible. The wording in this module deliberately reflects
that limitation.
"""

import ipaddress
import socket
from datetime import date, datetime, timezone
from urllib.parse import urlparse

import requests

from opportunity import Opportunity
from validator import SOCIAL_MEDIA_HOSTS, valid_http_url


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 OpportunityAgent/1.0"
)

BLOCKED_STATUS_CODES = {401, 403, 405, 429, 999}

DISCLAIMER = (
    "A reachable link does not confirm that applications are open, "
    "that the deadline is current, or that you are eligible. "
    "Always check the official page."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hostname(value: str) -> str:
    try:
        return (urlparse(value).hostname or "").lower().removeprefix(
            "www."
        )
    except (AttributeError, ValueError):
        return ""


def _is_social_media(host: str) -> bool:
    return any(
        host == domain or host.endswith("." + domain)
        for domain in SOCIAL_MEDIA_HOSTS
    )


def _is_public_hostname(host: str) -> bool:
    """Reject localhost and private network targets (basic SSRF guard)."""
    if not host:
        return False

    try:
        addresses = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False

    for address in addresses:
        raw_ip = address[4][0]

        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            return False

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return False

    return True


def check_url(url: str, timeout: int = 12) -> dict:
    """Fetch a URL and report reachability without claiming it is open."""
    result = {
        "url": (url or "").strip(),
        "status": "invalid",
        "status_code": None,
        "final_url": None,
        "checked_at": _now(),
        "message": "A valid HTTP or HTTPS URL is required.",
    }

    if not valid_http_url(url):
        return result

    host = _hostname(url)

    if not _is_public_hostname(host):
        result.update(
            status="blocked",
            message=(
                "The host could not be resolved or is not a public "
                "internet address, so the link was not fetched."
            ),
        )
        return result

    try:
        response = requests.get(
            url.strip(),
            headers={"User-Agent": USER_AGENT},
            timeout=(5, timeout),
            allow_redirects=True,
            stream=True,
        )

        status_code = response.status_code
        final_url = response.url

        # Read only a small prefix so we never download a large file.
        next(response.iter_content(1024), None)
        response.close()

    except requests.Timeout:
        result.update(
            status="timeout",
            message="The page did not respond before the timeout.",
        )
        return result

    except requests.TooManyRedirects:
        result.update(
            status="unreachable",
            message="The page redirected too many times.",
        )
        return result

    except requests.RequestException:
        result.update(
            status="unreachable",
            message="The page could not be reached from the backend.",
        )
        return result

    result.update(status_code=status_code, final_url=final_url)

    if 200 <= status_code < 400:
        result.update(
            status="reachable",
            message=(
                f"The page returned HTTP {status_code}. This does not "
                "confirm that applications are open."
            ),
        )
    elif status_code in BLOCKED_STATUS_CODES:
        result.update(
            status="blocked",
            message=(
                f"The site returned HTTP {status_code}, which usually "
                "means automated checks are blocked. The link may still "
                "work in a normal browser."
            ),
        )
    else:
        result.update(
            status="unreachable",
            message=(
                f"The page returned HTTP {status_code} and may be "
                "unavailable."
            ),
        )

    return result


def deadline_status(value: str | None) -> dict:
    """Describe a stored deadline without guessing a missing one."""
    if not value:
        return {
            "value": None,
            "status": "missing",
            "days_remaining": None,
            "message": "No deadline was published in the extracted data.",
        }

    try:
        deadline = datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return {
            "value": value,
            "status": "invalid",
            "days_remaining": None,
            "message": "The stored deadline could not be parsed.",
        }

    remaining = (deadline - date.today()).days

    if remaining < 0:
        status = "passed"
        message = "The stored deadline has passed."
    elif remaining == 0:
        status = "closes_today"
        message = "The stored deadline is today."
    else:
        status = "future"
        message = f"The stored deadline is {remaining} day(s) away."

    return {
        "value": value,
        "status": status,
        "days_remaining": remaining,
        "message": message,
    }


def verify_opportunity(opportunity: Opportunity) -> dict:
    """Verify both sides of a stored opportunity's links."""
    application_url = opportunity.application_url.strip()
    source_url = opportunity.source_url.strip()

    application = check_url(application_url)
    application_host = _hostname(application_url)

    if application_url and application_url == source_url:
        source = {
            **application,
            "same_as_application": True,
        }
    else:
        source = check_url(source_url)
        source["same_as_application"] = False

    source_host = _hostname(source_url)

    return {
        "checked_at": _now(),
        "application": application,
        "source": source,
        "application_host": application_host,
        "source_host": source_host,
        "same_host": bool(
            application_host
            and source_host
            and application_host == source_host
        ),
        "application_on_social_media": _is_social_media(
            application_host
        ),
        "deadline": deadline_status(opportunity.deadline),
        "disclaimer": DISCLAIMER,
    }
