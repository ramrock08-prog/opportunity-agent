import requests

from config import TAVILY_API_KEY

SEARCH_QUERIES = {
    "hackathon": [
        "student hackathons India registration open 2026 2027",
        "online coding hackathons students apply",
        "AI ML robotics hackathon students India",
    ],
    "internship": [
    "software engineering intern 2027 India official careers application apply -site:indeed.com -site:thejobcompany.co.in",
    "machine learning research internship undergraduate India apply directly -site:indeed.com",
    "software developer intern India students official company careers apply -site:thejobcompany.co.in",
],
    "job": [
        "software engineering jobs freshers India 2026 2027",
        "entry level AI ML jobs India",
        "graduate engineer jobs electronics computer science India",
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


def search_category(
    category: str,
    max_results_per_query: int = 5,
) -> list[dict]:
    """Search the web for opportunities in one category."""

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

    for query in SEARCH_QUERIES[category]:
        print(f"Searching: {query}")

        try:
            response = requests.post(
                "https://api.tavily.com/search",
                headers=headers,
                json={
                    "query": query,
                    "search_depth": "basic",
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

            if not url or url in seen_urls:
                continue

            seen_urls.add(url)

            results.append({
                "title": item.get("title", ""),
                "url": url,
                "content": item.get("content", ""),
                "score": item.get("score", 0.0),
                "category": category,
                "search_query": query,
            })

    return results


def search_all_categories() -> list[dict]:
    """Search every supported opportunity category."""

    all_results = []

    for category in SEARCH_QUERIES:
        try:
            results = search_category(category)
            all_results.extend(results)

            print(
                f"{category}: {len(results)} unique results"
            )

        except RuntimeError as error:
            print(f"Warning: {error}")

    return all_results
