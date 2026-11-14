import requests

from config import TAVILY_API_KEY

SEARCH_QUERIES = {
    "hackathon": [
        "student hackathons India registration open 2026 2027",
        "online coding hackathons students apply",
        "AI ML robotics hackathon students India",
    ],
    "internship": [
        "software engineering internship India 2027 official careers -site:indeed.com -site:naukri.com -site:linkedin.com",
        "AI machine learning internship India undergraduate 2027 apply -site:indeed.com -site:naukri.com",
        "embedded systems VLSI internship India students 2027 apply",
        "site:careers.google.com internship India 2027",
        "site:amazon.jobs intern India 2027 software",
        "site:jobs.microsoft.com internship India 2027",
        "site:careers.qualcomm.com internship India 2027",
        "site:jobs.nvidia.com internship India 2027",
        "site:careers.intel.com internship India 2027",
        "site:careers.ti.com internship India 2027",
    ],
    "job": [
        "software engineer fresher India 2027 official careers -site:indeed.com -site:naukri.com",
        "graduate engineer trainee India electronics computer science 2027",
        "AI ML engineer fresher India 2027 apply",
        "site:careers.google.com university graduate India 2027",
        "site:amazon.jobs software development engineer India 2027",
        "site:jobs.microsoft.com university graduate India 2027",
    ],
    "scholarship": [
        "undergraduate engineering scholarships India 2026 2027",
        "merit based scholarships BTech students India",
        "technology student financial aid scholarship India",
    ],
    "fellowship": [
        "student technology fellowship India 2026 2027",
        "AI research fellowship undergraduate students",
        "engineering research fellowships students India",
    ],
    "competition": [
        "technology competitions for college students India",
        "AI ML coding competitions students 2026 2027",
        "engineering innovation competitions students India",
    ],
    "research": [
        "undergraduate research opportunities AI ML India",
        "engineering research assistant opportunities students India",
        "summer research programs undergraduate students India",
    ],
}

NEGATIVE_TITLE_TERMS = {
    "phd",
    "mba",
    "sales",
    "business analyst",
    "strategy",
    "operations",
    "product manager",
    "marketing",
    "finance",
    "human resources",
    "guide",
    "how to",
    "open now",
    "step-by-step",
    "companies & skills",
}

LOW_QUALITY_HOSTS = {
    "facebook.com",
    "instagram.com",
    "reddit.com",
    "quora.com",
    "x.com",
    "twitter.com",
    "linkedin.com",
    "naukri.com",
    "indeed.com",
    "glassdoor.co.in",
    "ambitionbox.com",
    "thejobcompany.co.in",
    "myinternships.in",
    "techfreshers.com",
    "careersat.tech",
    "productbased.in",
    "elitmus.com",
    "internshala.com",
    "campustodrive.com",
    "hiredoor.in",
    "unstop.com",
    "wellfound.com",
    "chipxpert.in",
    "vectorindia.org",
    "github.com",
    "fastweb.com",
    "extern.com",
    "prosple.com",
    "mhcognition.com",
    "internshipwala.com",
    "nareshit.com",
    "pmaccelerator.io",
}


def _host(url: str) -> str:
    from urllib.parse import urlparse

    try:
        return (urlparse(url).hostname or "").lower().removeprefix(
            "www."
        )
    except ValueError:
        return ""


def _is_low_quality(url: str) -> bool:
    from urllib.parse import urlparse

    host = _host(url)

    if any(
        host == blocked or host.endswith("." + blocked)
        for blocked in LOW_QUALITY_HOSTS
    ):
        return True

    parsed = urlparse(url)
    path = parsed.path.rstrip("/").lower()
    last_segment = path.split("/")[-1] if path else ""

    # Search-results pages are directories, not one specific opening.
    if parsed.query and last_segment in {
        "jobs",
        "results",
        "search",
        "careers",
        "internships",
    }:
        return True

    if "sitemap" in path or "talentcommunity" in path:
        return True

    return False


def _is_undergraduate_profile(profile) -> bool:
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


def _title_is_relevant(item: dict, profile) -> bool:
    if not _is_undergraduate_profile(profile):
        return True

    title = item.get("title", "").lower()

    if any(term in title for term in NEGATIVE_TITLE_TERMS):
        return False

    # Summer 2026 has passed at the time this project is maintained.
    if "summer 2026" in title or "spring 2026" in title:
        return False

    return True


def _title_key(title: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _profile_terms(profile) -> list[str]:
    if profile is None:
        return []

    terms = []

    for field_name in (
        "skills",
        "interests",
        "preferred_locations",
    ):
        value = getattr(profile, field_name, []) or []
        terms.extend(
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        )

    for field_name in ("degree", "branch"):
        value = getattr(profile, field_name, "") or ""
        if isinstance(value, str) and value.strip():
            terms.append(value.strip())

    return list(dict.fromkeys(terms))


def _build_queries(category: str, profile) -> list[str]:
    queries = list(SEARCH_QUERIES[category])

    if category in {"internship", "job"}:
        terms = _profile_terms(profile)

        for term in terms[:5]:
            queries.append(
                f"{term} internship India 2027 students apply"
            )

    seen = set()
    unique = []

    for query in queries:
        key = query.casefold()

        if key not in seen:
            seen.add(key)
            unique.append(query)

    return unique[:12]


def _relevance_score(item: dict, terms: list[str]) -> float:
    text = f"{item.get('title', '')} {item.get('content', '')}".lower()
    keyword_hits = sum(
        1 for term in terms if term.casefold() in text
    )
    host = _host(item.get("url", ""))
    official_hint = 1.0 if (
        "career" in host or "job" in host
    ) else 0.0

    return (
        keyword_hits * 4.0
        + official_hint
        + float(item.get("score", 0.0))
    )


def search_category(
    category: str,
    max_results_per_query: int = 8,
    profile=None,
) -> list[dict]:
    """Search the web for opportunities in one category.

    Profile terms add targeted queries, and known directory/social
    hosts are skipped before they consume Gemini extractions.
    """

    category = category.strip().lower()

    if category not in SEARCH_QUERIES:
        raise ValueError(
            f"Unknown category: {category}. "
            f"Available categories: {', '.join(SEARCH_QUERIES)}"
        )

    if not TAVILY_API_KEY:
        raise RuntimeError(
            "TAVILY_API_KEY is missing. "
            "Configure it in your local .env file."
        )

    headers = {
        "Authorization": f"Bearer {TAVILY_API_KEY}",
        "Content-Type": "application/json",
    }

    results = []
    seen_urls = set()
    seen_titles = set()
    queries = _build_queries(category, profile)
    depth = (
        "advanced"
        if category in {"internship", "job"}
        else "basic"
    )

    for query in queries:
        print(f"Searching: {query}")

        try:
            response = requests.post(
                "https://api.tavily.com/search",
                headers=headers,
                json={
                    "query": query,
                    "search_depth": depth,
                    "max_results": max_results_per_query,
                },
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

        except requests.RequestException as error:
            raise RuntimeError(
                f"Tavily search failed for category '{category}'. "
                "Check your API key, connection, and usage limits."
            ) from error

        for item in data.get("results", []):
            url = item.get("url", "").strip()

            normalized_url = url.rstrip("/").lower()
            title_key = _title_key(item.get("title", ""))

            if (
                not url
                or normalized_url in seen_urls
                or title_key in seen_titles
                or _is_low_quality(url)
            ):
                continue

            candidate = {
                "title": item.get("title", ""),
                "url": url,
                "content": item.get("content", ""),
                "score": item.get("score", 0.0),
                "category": category,
                "search_query": query,
            }

            if (
                category in {"internship", "job"}
                and not _title_is_relevant(candidate, profile)
            ):
                continue

            seen_urls.add(normalized_url)
            seen_titles.add(title_key)
            results.append(candidate)

    terms = _profile_terms(profile)

    if terms:
        results.sort(
            key=lambda item: _relevance_score(item, terms),
            reverse=True,
        )

    return results


def search_all_categories(
    profile=None,
) -> list[dict]:
    """Search every supported opportunity category."""

    all_results = []

    for category in SEARCH_QUERIES:
        try:
            results = search_category(
                category, profile=profile
            )
            all_results.extend(results)

            print(
                f"{category}: {len(results)} unique results"
            )

        except RuntimeError as error:
            print(f"Warning: {error}")

    return all_results