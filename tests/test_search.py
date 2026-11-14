import pytest

import search


class FakeResponse:
    def __init__(self, results):
        self._results = results

    def raise_for_status(self):
        return None

    def json(self):
        return {"results": self._results}


def test_profile_queries_and_quality_filter(monkeypatch):
    monkeypatch.setattr(search, "TAVILY_API_KEY", "test-key")
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append(json)

        return FakeResponse([
            {
                "title": "Facebook internship post",
                "url": "https://facebook.com/post",
                "content": "social post",
                "score": 0.9,
            },
            {
                "title": "Python Machine Learning Internship",
                "url": "https://careers.example.com/python-intern",
                "content": "Python and machine learning internship.",
                "score": 0.8,
            },
            {
                "title": "Naukri internship directory",
                "url": "https://naukri.com/jobs",
                "content": "directory",
                "score": 0.7,
            },
        ])

    monkeypatch.setattr(search.requests, "post", fake_post)

    class Profile:
        skills = ["Python"]
        interests = ["Machine Learning"]
        preferred_locations = ["India"]
        degree = "B.Tech"
        branch = "ECE"

    results = search.search_category(
        "internship", max_results_per_query=3, profile=Profile()
    )

    assert [item["url"] for item in results] == [
        "https://careers.example.com/python-intern"
    ]
    assert any(
        "Python internship India" in call["query"]
        for call in calls
    )
    assert all(
        call["search_depth"] == "advanced" for call in calls
    )


def test_search_requires_tavily_key(monkeypatch):
    monkeypatch.setattr(search, "TAVILY_API_KEY", "")

    with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
        search.search_category("internship")


def test_unknown_category_is_rejected(monkeypatch):
    monkeypatch.setattr(search, "TAVILY_API_KEY", "test-key")

    with pytest.raises(ValueError, match="Unknown category"):
        search.search_category("not-real")