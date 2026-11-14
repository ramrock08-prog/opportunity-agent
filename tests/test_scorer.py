from opportunity import Opportunity
from profile import UserProfile
from scorer import rank_opportunities, score_opportunity


def test_relevant_opportunity_scores_higher():
    profile = UserProfile(
        interests=["AI", "Machine Learning"],
        skills=["Python"],
        preferred_locations=["India"],
        remote_preferred=True,
        opportunity_types=["internship"],
    )

    relevant = Opportunity(
        title="AI Research Internship",
        type="internship",
        description="Build machine learning models with Python.",
        location="Bangalore, India",
        remote=True,
        required_skills=["Python"],
        source_url="https://example.com/ai",
        application_url="https://example.com/ai/apply",
        confidence=0.9,
    )

    unrelated = Opportunity(
        title="Mechanical Design Internship",
        type="internship",
        description="CAD and manufacturing support.",
        location="Pune, India",
        remote=False,
        required_skills=["AutoCAD"],
        source_url="https://example.com/mech",
        application_url="https://example.com/mech/apply",
        confidence=0.9,
    )

    assert score_opportunity(
        relevant, profile
    )["score"] > score_opportunity(unrelated, profile)["score"]


def test_unselected_type_returns_zero():
    profile = UserProfile(opportunity_types=["internship"])
    opportunity = Opportunity(
        title="Hackathon",
        type="hackathon",
        source_url="https://example.com/hack",
        application_url="https://example.com/hack/apply",
        confidence=0.9,
    )

    result = score_opportunity(opportunity, profile)

    assert result["matched"] is False
    assert result["score"] == 0


def test_rank_ignores_unselected_types():
    profile = UserProfile(opportunity_types=["internship"])
    opportunities = [
        Opportunity(
            title="Internship",
            type="internship",
            source_url="https://example.com/i",
            application_url="https://example.com/i/apply",
            confidence=0.9,
        ),
        Opportunity(
            title="Hackathon",
            type="hackathon",
            source_url="https://example.com/h",
            application_url="https://example.com/h/apply",
            confidence=0.9,
        ),
    ]

    ranked = rank_opportunities(opportunities, profile)

    assert len(ranked) == 1
    assert ranked[0]["opportunity"].type == "internship"