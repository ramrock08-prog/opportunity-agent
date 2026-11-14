from dedup import deduplicate_opportunities, normalize_url
from opportunity import Opportunity


def test_normalize_url_removes_tracking_and_www():
    assert normalize_url(
        "https://www.example.com/internship/?utm_source=a#top"
    ) == "https://example.com/internship"


def test_duplicate_urls_keep_higher_confidence():
    items = [
        Opportunity(
            title="AI Internship",
            type="internship",
            source_url="https://example.com/internship?utm_source=a",
            confidence=0.6,
        ),
        Opportunity(
            title="AI Internship",
            type="internship",
            source_url="https://www.example.com/internship/?utm_source=b",
            confidence=0.9,
        ),
    ]

    unique = deduplicate_opportunities(items)

    assert len(unique) == 1
    assert unique[0].confidence == 0.9


def test_same_title_and_organization_is_duplicate():
    items = [
        Opportunity(
            title="Software Intern",
            type="internship",
            organization="Example Corp",
            source_url="https://example.com/a",
            confidence=0.8,
        ),
        Opportunity(
            title="  software   intern ",
            type="internship",
            organization="example corp",
            source_url="https://example.org/b",
            confidence=0.85,
        ),
    ]

    assert len(deduplicate_opportunities(items)) == 1


def test_distinct_opportunities_are_kept():
    items = [
        Opportunity(
            title="AI Internship",
            type="internship",
            source_url="https://example.com/ai",
            confidence=0.8,
        ),
        Opportunity(
            title="Data Hackathon",
            type="hackathon",
            source_url="https://example.org/hack",
            confidence=0.8,
        ),
    ]

    assert len(deduplicate_opportunities(items)) == 2