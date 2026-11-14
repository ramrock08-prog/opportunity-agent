from urllib.parse import urlparse, urlunparse

from opportunity import Opportunity


def normalize_url(url: str) -> str:
    """Normalize URLs to help identify duplicate opportunities."""
    if not isinstance(url, str) or not url.strip():
        return ""

    try:
        parsed = urlparse(url.strip())

        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""

        host = parsed.hostname.lower().removeprefix("www.")
        path = parsed.path.rstrip("/")

        # Remove common tracking parameters.
        query_items = []
        if parsed.query:
            from urllib.parse import parse_qsl, urlencode

            query_items = [
                (key, value)
                for key, value in parse_qsl(
                    parsed.query, keep_blank_values=True
                )
                if not key.lower().startswith("utm_")
                and key.lower() not in {"gclid", "fbclid"}
            ]

        query = ""
        if query_items:
            from urllib.parse import urlencode
            query = urlencode(query_items)

        return urlunparse((
            "https",
            host,
            path,
            "",
            query,
            "",
        ))

    except (ValueError, TypeError):
        return ""


def normalize_text(value: str) -> str:
    """Normalize text for basic title and organization matching."""
    return " ".join((value or "").casefold().split())


def _same_opportunity(first: Opportunity, second: Opportunity) -> bool:
    """Compare two opportunities using source URL or title and organization."""
    first_url = normalize_url(first.source_url)
    second_url = normalize_url(second.source_url)

    if first_url and second_url and first_url == second_url:
        return True

    first_title = normalize_text(first.title)
    second_title = normalize_text(second.title)

    first_org = normalize_text(first.organization)
    second_org = normalize_text(second.organization)

    return (
        bool(first_title)
        and first_title == second_title
        and bool(first_org)
        and first_org == second_org
    )


def deduplicate_opportunities(
    opportunities: list[Opportunity],
) -> list[Opportunity]:
    """
    Remove duplicate opportunities.

    If duplicates have different extraction confidence scores,
    keep the record with the higher score.
    """
    unique = []

    for candidate in opportunities:
        duplicate_index = next(
            (
                index
                for index, existing in enumerate(unique)
                if _same_opportunity(candidate, existing)
            ),
            None,
        )

        if duplicate_index is None:
            unique.append(candidate)
        elif (
            candidate.confidence
            > unique[duplicate_index].confidence
        ):
            unique[duplicate_index] = candidate

    return unique
