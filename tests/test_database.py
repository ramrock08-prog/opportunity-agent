import json
import sqlite3
from profile import UserProfile, load_profile, save_profile

import database
from bookmarks import add_bookmark, load_bookmarks, remove_bookmark
from opportunity import Opportunity
from storage import (
    export_opportunities_json,
    load_opportunities,
    save_opportunities,
)


def make_opportunity(**overrides):
    data = {
        "title": "AI Research Intern",
        "type": "internship",
        "organization": "Example Labs",
        "source_url": "https://example.com/ai-intern",
        "application_url": "https://example.com/ai-intern/apply",
        "confidence": 0.9,
        "required_skills": ["Python"],
    }
    data.update(overrides)
    return Opportunity(**data)


def test_opportunities_round_trip(isolated_db):
    save_opportunities([
        make_opportunity(),
        make_opportunity(
            title="ML Hackathon",
            type="hackathon",
            source_url="https://example.com/ml-hack",
        ),
    ])

    loaded = load_opportunities()

    assert [item.title for item in loaded] == [
        "AI Research Intern",
        "ML Hackathon",
    ]
    assert loaded[0].required_skills == ["Python"]


def test_saving_duplicate_keys_does_not_abort(isolated_db):
    save_opportunities([
        make_opportunity(),
        make_opportunity(title="Same URL, different title"),
    ])

    loaded = load_opportunities()
    assert len(loaded) == 1
    assert loaded[0].title == "AI Research Intern"


def test_saving_replaces_collection_and_export_works(
    isolated_db, tmp_path
):
    save_opportunities([make_opportunity()])
    save_opportunities([
        make_opportunity(title="Second Intern")
    ])

    loaded = load_opportunities()
    assert len(loaded) == 1
    assert loaded[0].title == "Second Intern"

    export_file = tmp_path / "snapshot.json"
    export_opportunities_json(export_file)

    records = json.loads(export_file.read_text(encoding="utf-8"))
    assert records[0]["title"] == "Second Intern"


def test_bookmarks_round_trip(isolated_db):
    url = "https://example.com/opportunity"

    assert add_bookmark(url) == [url]
    assert add_bookmark(url) == [url]
    assert load_bookmarks() == [url]
    assert remove_bookmark(url) == []
    assert load_bookmarks() == []


def test_legacy_bookmarks_are_not_reimported_after_removal(
    isolated_db,
):
    # Initialize the schema (one-time migration flag is written).
    assert load_bookmarks() == []

    # Simulate a leftover v1 bookmark table arriving after migration.
    with sqlite3.connect(isolated_db) as connection:
        connection.execute(
            """
            CREATE TABLE bookmarks(
                url TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO bookmarks(url, created_at)
            VALUES('https://example.com/legacy', 'now')
            """
        )

    # Force the schema hook to run again, as it would on a restart.
    database._initialized_paths.discard(
        str(isolated_db.resolve())
    )

    assert load_bookmarks() == []


def test_profile_round_trip(isolated_db):
    profile = UserProfile(
        name="Test Student",
        degree="B.Tech",
        branch="ECE",
        year_of_study=3,
        skills=["Python"],
        interests=["AI"],
        preferred_locations=["India"],
        opportunity_types=["internship"],
    )

    save_profile(profile)
    loaded = load_profile()

    assert loaded.name == "Test Student"
    assert loaded.skills == ["Python"]
    assert loaded.opportunity_types == ["internship"]