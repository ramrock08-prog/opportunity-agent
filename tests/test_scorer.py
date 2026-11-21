from profile import UserProfile

from opportunity import Opportunity
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

    relevant_result = score_opportunity(relevant, profile)
    unrelated_result = score_opportunity(unrelated, profile)

    assert relevant_result["score"] > unrelated_result["score"]
    assert relevant_result["components"]["confidence"] == 9.0
    assert any(
        "extraction confidence" in reason.lower()
        for reason in relevant_result["reasons"]
    )


def test_ai_ml_interest_matches_machine_learning_title():
    profile = UserProfile(
        interests=["AI/ML"],
        opportunity_types=["internship"],
    )
    opportunity = Opportunity(
        title="Machine Learning Intern",
        type="internship",
        description="Work on artificial intelligence models.",
        source_url="https://example.com/ml",
        application_url="https://example.com/ml/apply",
        confidence=0.9,
    )

    result = score_opportunity(opportunity, profile)

    assert result["components"]["interests"] == 35.0


def test_skills_match_listing_text_when_source_lists_none():
    profile = UserProfile(
        skills=["Python", "FastAPI", "Docker"],
        interests=["software development"],
        opportunity_types=["job"],
    )
    opportunity = Opportunity(
        title="Forward Deployed Engineer",
        type="job",
        description=(
            "Build Python APIs with FastAPI and deploy them with "
            "Docker for customer-facing systems."
        ),
        source_url="https://example.com/fde",
        application_url="https://example.com/fde/apply",
        confidence=0.9,
    )

    result = score_opportunity(opportunity, profile)

    assert result["components"]["skills"] >= 8
    assert any("skills" in reason.lower() for reason in result["reasons"])


def test_india_preference_matches_indian_city():
    profile = UserProfile(
        preferred_locations=["India"],
        opportunity_types=["internship"],
    )
    opportunity = Opportunity(
        title="Software Intern",
        type="internship",
        location="Bengaluru, India",
        source_url="https://example.com/in",
        application_url="https://example.com/in/apply",
        confidence=0.9,
    )

    result = score_opportunity(opportunity, profile)

    assert result["components"]["location"] == 15.0


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