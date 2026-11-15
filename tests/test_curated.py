import curated

SAMPLE = [
    {
        "title": "Software Engineering Intern",
        "company": "Google",
        "url": "https://example.com/google-intern",
        "locations": ["Bangalore, India"],
        "terms": ["Summer 2027"],
        "degrees": ["Bachelor's"],
        "category": "Software",
        "sponsorship": "Other",
        "date_posted": 200,
        "source": "TestSource",
    },
    {
        "title": "Machine Learning Intern",
        "company": "Example AI",
        "url": "https://example.com/ml-intern",
        "locations": ["Remote"],
        "terms": ["Fall 2026"],
        "degrees": ["Master's"],
        "category": "AI/ML/Data",
        "sponsorship": "Offers Sponsorship",
        "date_posted": 100,
        "source": "TestSource",
    },
    {
        "title": "Old Internship",
        "company": "Old Corp",
        "url": "https://example.com/old",
        "locations": ["Bangalore, India"],
        "terms": ["Summer 2026"],
        "degrees": [],
        "category": "Software",
        "sponsorship": "",
        "date_posted": 300,
        "source": "TestSource",
    },
    {
        "title": "US Only Intern",
        "company": "US Corp",
        "url": "https://example.com/us",
        "locations": ["New York, NY"],
        "terms": ["Summer 2027"],
        "degrees": [],
        "category": "Software",
        "sponsorship": "",
        "date_posted": 400,
        "source": "TestSource",
    },
]


class Profile:
    skills = ["Python", "Machine Learning"]
    interests = ["Software Engineering"]
    preferred_locations = ["India"]


def test_select_listings_filters_and_orders():
    selected = curated.select_listings(
        SAMPLE, profile=Profile(), country="India", limit=10
    )

    titles = [item["title"] for item in selected]

    assert "Old Internship" not in titles
    assert "US Only Intern" not in titles
    assert "Software Engineering Intern" in titles
    assert "Machine Learning Intern" in titles
    # Both match profile terms; the software role is newer.
    assert titles[0] == "Software Engineering Intern"


def test_build_opportunity_maps_fields():
    opportunity = curated.build_opportunity(SAMPLE[1])

    assert opportunity.type == "internship"
    assert opportunity.organization == "Example AI"
    assert opportunity.remote is True
    assert opportunity.confidence == 0.8
    assert "AI/ML/Data" in opportunity.fields


def test_import_curated_merges_into_storage(
    isolated_db, monkeypatch
):
    monkeypatch.setattr(curated, "_fetch", lambda source: SAMPLE)

    stats = curated.import_curated(
        profile=Profile(), country="India", limit=10
    )

    assert stats["added"] == 2
    assert stats["total"] == 2

    # A second import must not duplicate records.
    stats = curated.import_curated(
        profile=Profile(), country="India", limit=10
    )

    assert stats["added"] == 0
    assert stats["total"] == 2