from datetime import datetime, timedelta, timezone

from database import get_connection
from discovery_state import (
    filter_unseen,
    mark_attempts,
    reset_candidates,
)

RESULTS = [
    {"url": "https://example.com/a"},
    {"url": "https://example.com/b"},
]


def test_attempted_urls_are_filtered(isolated_db):
    mark_attempts(
        RESULTS[:1],
        "internship",
        {"https://example.com/a": "extracted"},
    )

    unseen = filter_unseen(RESULTS, "internship")

    assert [item["url"] for item in unseen] == [
        "https://example.com/b"
    ]


def test_other_categories_do_not_hide_results(isolated_db):
    mark_attempts(
        RESULTS[:1],
        "internship",
        {"https://example.com/a": "rejected"},
    )

    unseen = filter_unseen(RESULTS, "job")

    assert len(unseen) == 2


def test_old_attempts_become_visible_again(isolated_db):
    mark_attempts(
        RESULTS[:1],
        "internship",
        {"https://example.com/a": "rejected"},
    )

    old = (
        datetime.now(timezone.utc) - timedelta(days=40)
    ).isoformat(timespec="seconds")

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE discovery_candidates
            SET last_attempted = ?
            """,
            (old,),
        )

    unseen = filter_unseen(
        RESULTS, "internship", cooldown_days=14
    )

    assert len(unseen) == 2


def test_reset_candidates(isolated_db):
    mark_attempts(
        RESULTS,
        "internship",
        {
            "https://example.com/a": "extracted",
            "https://example.com/b": "rejected",
        },
    )
    reset_candidates()

    assert len(filter_unseen(RESULTS, "internship")) == 2