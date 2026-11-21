import re
from profile import UserProfile

from opportunity import Opportunity

TERM_SYNONYMS = {
    "ai": [
        "artificial intelligence",
        "machine learning",
        "ml",
    ],
    "ai/ml": [
        "ai",
        "artificial intelligence",
        "machine learning",
        "ml",
    ],
    "ml": ["machine learning", "artificial intelligence"],
    "software development": [
        "software engineering",
        "software engineer",
        "developer",
        "programming",
        "swe",
    ],
    "software engineering": [
        "software development",
        "software engineer",
        "developer",
        "swe",
    ],
    "data science": [
        "data scientist",
        "data analytics",
        "analytics",
        "data engineer",
    ],
    "cloud": [
        "aws",
        "gcp",
        "azure",
        "cloud computing",
        "cloud platform",
    ],
    "computer vision": [
        "cv",
        "opencv",
        "image processing",
        "vision",
    ],
    "embedded": [
        "embedded systems",
        "firmware",
        "microcontroller",
        "iot",
        "electronics",
    ],
    "backend": [
        "back-end",
        "back end",
        "server side",
        "api",
        "apis",
        "microservices",
    ],
    "frontend": ["front-end", "front end", "ui", "react"],
    "full stack": ["full-stack", "fullstack", "frontend", "backend"],
    "fde": [
        "forward deployed engineer",
        "forward-deployed engineer",
        "forward deployed",
        "forward-deployed",
    ],
    "india": [
        "bangalore",
        "bengaluru",
        "hyderabad",
        "pune",
        "mumbai",
        "chennai",
        "delhi",
        "noida",
        "gurgaon",
        "gurugram",
        "kolkata",
        "ahmedabad",
        "ind",
    ],
    "remote": ["work from home", "wfh", "hybrid"],
}


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


def _variants(term: str) -> list[str]:
    base = term.strip().casefold()

    if not base:
        return []

    variants = set()
    parts = re.split(r"[/,&]|\band\b", base)

    for part in [base, *parts]:
        part = part.strip()

        if not part:
            continue

        variants.add(part)
        variants.update(TERM_SYNONYMS.get(part, []))

        if part.endswith("s") and len(part) > 3:
            variants.add(part[:-1])
        else:
            variants.add(part + "s")

    return [item for item in variants if item]


def term_matches(term: str, text: str) -> bool:
    """Match a term or any of its known synonyms against text."""
    return any(
        contains_term(variant, text)
        for variant in _variants(term)
    )


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

    searchable_text = " ".join([
        opportunity.title,
        opportunity.description,
        opportunity.organization,
        " ".join(opportunity.fields),
        " ".join(opportunity.required_skills),
    ])

    # 1. Interest matching: up to 35 points.
    interests = profile.interests

    if interests:
        matched_interests = [
            item for item in interests
            if term_matches(item, searchable_text)
        ]

        interest_points = 35.0 * len(matched_interests) / len(interests)

        earned += interest_points
        possible += 35.0

        components["interests"] = round(interest_points, 2)

        if matched_interests:
            reasons.append(
                "Matching interests: " + ", ".join(matched_interests)
            )

    # 2. Skill matching: up to 20 points.
    #
    # Some sources publish required skills; structured listings often do
    # not. Match against the listing text in that case so a strong
    # profile is not penalised by missing upstream data.
    if profile.skills:
        if opportunity.required_skills:
            matched_skills = [
                skill for skill in opportunity.required_skills
                if any(
                    term_matches(user_skill, skill)
                    for user_skill in profile.skills
                )
            ]

            skill_points = (
                20.0 * len(matched_skills)
                / len(opportunity.required_skills)
            )
            skill_reason = "Matching required skills: "
        else:
            matched_skills = [
                skill for skill in profile.skills
                if term_matches(skill, searchable_text)
            ]

            skill_points = min(20.0, 4.0 * len(matched_skills))
            skill_reason = "Matching your skills in the listing: "

        earned += skill_points
        possible += 20.0
        components["skills"] = round(skill_points, 2)

        if matched_skills:
            reasons.append(
                skill_reason + ", ".join(matched_skills[:6])
            )

    # 3. Location matching: up to 15 points when location is known.
    location = (opportunity.location or "").strip()
    unknown_locations = {"", "not specified", "unknown", "n/a"}

    if profile.preferred_locations and (
        location.casefold() not in unknown_locations
    ):
        location_match = any(
            term_matches(preferred, location)
            for preferred in profile.preferred_locations
        )

        if (
            not location_match
            and opportunity.remote is True
            and any(
                "remote" in preferred.casefold()
                for preferred in profile.preferred_locations
            )
        ):
            location_match = True

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

    # 5. Extraction confidence: up to 10 points.
    confidence = max(0.0, min(1.0, opportunity.confidence))
    confidence_points = 10.0 * confidence

    earned += confidence_points
    possible += 10.0
    components["confidence"] = round(confidence_points, 2)

    if confidence >= 0.8:
        reasons.append(
            "High extraction confidence (not independent verification)."
        )
    elif confidence < 0.65:
        reasons.append(
            "Lower extraction confidence; verify the source carefully."
        )

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