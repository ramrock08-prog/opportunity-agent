import re
from profile import UserProfile

from opportunity import Opportunity


def contains_term(term: str, text: str) -> bool:
    """Match a complete word or phrase, avoiding simple substring matches."""
    term = term.strip().casefold()

    if not term:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(term).replace(r"\ ", r"\s+")
        + r"(?!\w)"
    )

    return re.search(pattern, text.casefold()) is not None


def score_opportunity(
    opportunity: Opportunity,
    profile: UserProfile,
) -> dict:
    """
    Calculate a transparent relevance score from 0 to 100.

    This score measures relevance, not verified eligibility,
    source authenticity, or whether applications are still open.
    """

    if opportunity.type not in profile.opportunity_types:
        return {
            "score": 0,
            "matched": False,
            "reasons": ["Opportunity type is not selected in the profile."],
            "components": {},
        }

    earned = 20.0
    possible = 20.0

    components = {
        "opportunity_type": 20.0,
    }
    reasons = ["Opportunity type matches your preferences."]

    # 1. Interest matching: up to 35 points.
    interests = profile.interests

    searchable_text = " ".join([
        opportunity.title,
        opportunity.description,
        opportunity.organization,
        " ".join(opportunity.fields),
    ])

    if interests:
        matched_interests = [
            item for item in interests
            if contains_term(item, searchable_text)
        ]

        interest_points = 35.0 * len(matched_interests) / len(interests)

        earned += interest_points
        possible += 35.0

        components["interests"] = round(interest_points, 2)

        if matched_interests:
            reasons.append(
                "Matching interests: " + ", ".join(matched_interests)
            )

    # 2. Skill matching: up to 20 points, when both sides provide data.
    if profile.skills and opportunity.required_skills:
        matched_skills = [
            skill for skill in opportunity.required_skills
            if any(
                contains_term(user_skill, skill)
                for user_skill in profile.skills
            )
        ]

        skill_points = (
            20.0 * len(matched_skills)
            / len(opportunity.required_skills)
        )

        earned += skill_points
        possible += 20.0

        components["skills"] = round(skill_points, 2)

        if matched_skills:
            reasons.append(
                "Matching skills: " + ", ".join(matched_skills)
            )

    # 3. Location matching: up to 15 points when location is known.
    location = (opportunity.location or "").strip()
    unknown_locations = {"", "not specified", "unknown", "n/a"}

    if profile.preferred_locations and (
        location.casefold() not in unknown_locations
    ):
        location_match = any(
            contains_term(preferred, location)
            for preferred in profile.preferred_locations
        )

        location_points = 15.0 if location_match else 0.0

        earned += location_points
        possible += 15.0

        components["location"] = location_points

        if location_match:
            reasons.append("Location matches your preferences.")

    # 4. Remote preference: up to 10 points when explicitly known.
    if profile.remote_preferred and opportunity.remote is not None:
        remote_points = 10.0 if opportunity.remote else 0.0

        earned += remote_points
        possible += 10.0

        components["remote"] = remote_points

        if opportunity.remote:
            reasons.append("Remote work is available.")

    final_score = round(100 * earned / possible)

    return {
        "score": max(0, min(100, final_score)),
        "matched": True,
        "reasons": reasons,
        "components": components,
    }


def rank_opportunities(
    opportunities: list[Opportunity],
    profile: UserProfile,
) -> list[dict]:
    """Return opportunities sorted by relevance, highest first."""

    ranked = []

    for opportunity in opportunities:
        result = score_opportunity(opportunity, profile)

        if result["matched"]:
            ranked.append({
                "opportunity": opportunity,
                **result,
            })

    return sorted(
        ranked,
        key=lambda item: item["score"],
        reverse=True,
    )
