"""Import structured internship listings from open-source datasets.

This is what closes the volume gap with platforms like Unstop and
Internshala: instead of only parsing web-search snippets, we read
maintained listing datasets that contain thousands of internships with
direct apply links.
"""

from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

from dedup import deduplicate_opportunities
from opportunity import Opportunity
from storage import load_opportunities, save_opportunities
from text_utils import clean_list, clean_text

SOURCES = [
    {
        "name": "SimplifyJobs",
        "url": (
            "https://raw.githubusercontent.com/SimplifyJobs/"
            "Summer2027-Internships/dev/.github/scripts/listings.json"
        ),
    },
    {
        "name": "vanshb03",
        "url": (
            "https://raw.githubusercontent.com/vanshb03/"
            "Summer2027-Internships/dev/.github/scripts/listings.json"
        ),
    },
]

COUNTRY_TOKENS = {
    "india": [
        "india",
        "bangalore",
        "bengaluru",
        "hyderabad",
        "pune",
        "mumbai",
        "chennai",
        "delhi",
        "noida",
        "gurgaon",
        "gurugram",
        "kolkata",
        "ahmedabad",
        "remote",
    ],
    "remote": ["remote"],
}

NEGATIVE_TITLE_TERMS = {
    "mba",
    "phd",
    "doctorate",
    "sales",
    "marketing",
    "human resources",
}

STALE_TERMS = {
    "summer 2026",
    "spring 2026",
    "fall 2025",
    "winter 2025",
    "summer 2025",
}

RELEVANT_CATEGORIES = {
    "software",
    "software engineering",
    "ai/ml/data",
    "data science, ai & machine learning",
    "data science",
    "hardware",
    "quant",
    "product",
}


def _fetch(source: dict) -> list[dict]:
    try:
        response = requests.get(
            source["url"],
            timeout=120,
            headers={"User-Agent": "OpportunityAgent/1.0"},
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    if not isinstance(data, list):
        return []

    normalized = []

    for item in data:
        if not isinstance(item, dict):
            continue

        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        company = str(item.get("company_name") or "").strip()

        if not url or not title or not company:
            continue

        if item.get("active") is False:
            continue

        if item.get("is_visible") is False:
            continue

        terms = item.get("terms")

        if not isinstance(terms, list):
            season = item.get("season")
            terms = [season] if season else []

        locations = item.get("locations")

        if not isinstance(locations, list):
            locations = [locations] if locations else []

        degrees = item.get("degrees")

        if not isinstance(degrees, list):
            degrees = [degrees] if degrees else []

        category = str(item.get("category") or "Software").strip()

        normalized.append({
            "title": title,
            "company": company,
            "url": url,
            "locations": [str(x) for x in locations if x],
            "terms": [str(x) for x in terms if x],
            "degrees": [str(x) for x in degrees if x],
            "category": category,
            "sponsorship": str(item.get("sponsorship") or ""),
            "date_posted": int(item.get("date_posted") or 0),
            "source": source["name"],
        })

    return normalized


def _is_fresh(terms: list[str]) -> bool:
    lowered = {term.lower() for term in terms}

    if not lowered:
        return True

    return not any(term in STALE_TERMS for term in lowered)


def _location_matches(locations: list[str], country: str) -> bool:
    tokens = COUNTRY_TOKENS.get(country.lower(), [country.lower()])
    text = " ".join(locations).lower()

    return any(token in text for token in tokens)


def _is_undergraduate(profile) -> bool:
    if profile is None:
        return False

    degree = str(getattr(profile, "degree", "") or "").lower()
    year = getattr(profile, "year_of_study", None)

    return (
        "b.tech" in degree
        or "b.e" in degree
        or "bachelor" in degree
        or (isinstance(year, int) and 1 <= year <= 4)
    )


def _student_level_matches(item: dict, profile) -> bool:
    """Keep roles a 3rd-year Bachelor's student can apply to."""
    if not _is_undergraduate(profile):
        return True

    title = item["title"].lower()

    if any(term in title for term in NEGATIVE_TITLE_TERMS):
        return False

    degrees = [degree.lower() for degree in item["degrees"]]

    if not degrees:
        return True

    if any(
        "bachelor" in degree
        or "undergrad" in degree
        or "associate" in degree
        or "b.tech" in degree
        for degree in degrees
    ):
        return True

    return False


def _term_priority(terms: list[str]) -> int:
    """Rank the internship cycle for a 2028 graduate."""
    text = " ".join(terms).lower()

    if "summer 2027" in text:
        return 3

    if any(
        cycle in text
        for cycle in ("fall 2026", "winter 2027", "spring 2027")
    ):
        return 2

    if "summer" in text:
        return 1

    return 0


def _profile_terms(profile) -> list[str]:
    if profile is None:
        return []

    terms = []

    for field_name in ("skills", "interests", "preferred_locations"):
        values = getattr(profile, field_name, []) or []
        terms.extend(str(value) for value in values if value)

    return terms


def _relevance(item: dict, terms: list[str]) -> int:
    text = f"{item['title']} {item['category']} {item['company']}".lower()
    return sum(1 for term in terms if term.lower() in text)


def select_listings(
    listings: list[dict],
    profile=None,
    country: str = "India",
    limit: int = 200,
) -> list[dict]:
    """Filter and rank curated listings for a student."""
    terms = _profile_terms(profile)

    selected = [
        item for item in listings
        if _is_fresh(item["terms"])
        and _location_matches(item["locations"], country)
        and _student_level_matches(item, profile)
    ]

    selected.sort(
        key=lambda item: (
            _term_priority(item["terms"]),
            _relevance(item, terms),
            item["category"].lower() in RELEVANT_CATEGORIES,
            item["date_posted"],
        ),
        reverse=True,
    )

    seen = set()
    unique = []

    for item in selected:
        key = item["url"].rstrip("/").lower()

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

        if len(unique) >= limit:
            break

    return unique


def build_opportunity(item: dict) -> Opportunity:
    """Convert one curated listing into an Opportunity."""
    locations = item["locations"][:3]
    location = ", ".join(locations) or "Not specified"
    terms = item["terms"]
    category = item["category"]

    description = (
        f"{item['title']} at {item['company']}. "
        f"Category: {category}. "
        f"Term: {', '.join(terms) or 'Not specified'}. "
        f"Locations: {location}."
    )

    eligibility = [f"Term: {term}" for term in terms]

    if item["sponsorship"] and item["sponsorship"].lower() not in {
        "other",
        "n/a",
    }:
        eligibility.append(
            f"Sponsorship: {item['sponsorship']}"
        )

    remote = "remote" in location.lower()

    try:
        source = urlparse(item["url"]).hostname or item["source"]
    except ValueError:
        source = item["source"]

    return Opportunity(
        title=clean_text(item["title"]),
        type="internship",
        organization=clean_text(item["company"]),
        description=clean_text(description),
        source_url=item["url"],
        application_url=item["url"],
        location=clean_text(location),
        remote=remote or None,
        eligibility=clean_list(eligibility),
        fields=clean_list([category]),
        degree_requirements=clean_list(item["degrees"]),
        source=str(source).removeprefix("www."),
        confidence=0.8,
        evidence=[
            f"Structured listing from the {item['source']} "
            "open-source internship dataset."
        ],
    )


def import_curated(
    profile=None,
    country: str = "India",
    limit: int = 200,
) -> dict:
    """Fetch curated datasets and merge them into storage."""
    listings = []

    for source in SOURCES:
        listings.extend(_fetch(source))

    if not listings:
        raise RuntimeError(
            "Curated internship sources could not be reached."
        )

    selected = select_listings(
        listings,
        profile=profile,
        country=country,
        limit=limit,
    )

    if not selected:
        return {
            "fetched": len(listings),
            "selected": 0,
            "added": 0,
            "total": len(load_opportunities()),
        }

    opportunities = [
        build_opportunity(item) for item in selected
    ]

    existing = load_opportunities()
    before = len(existing)
    combined = deduplicate_opportunities(
        existing + opportunities
    )
    save_opportunities(combined)

    return {
        "fetched": len(listings),
        "selected": len(selected),
        "added": len(combined) - before,
        "total": len(combined),
        "synced_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ),
        "sources": [source["name"] for source in SOURCES],
    }