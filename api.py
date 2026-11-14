from bookmarks import add_bookmark, load_bookmarks, remove_bookmark
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from opportunity import ALLOWED_TYPES
from profile import UserProfile, load_profile, save_profile
from run_agent import run_agent as execute_discovery
from scorer import rank_opportunities
from search import SEARCH_QUERIES
from storage import load_opportunities
from validator import validate_opportunity


class DiscoveryRequest(BaseModel):
    category: str = "internship"
    limit: int = Field(default=3, ge=1, le=3)


class ProfileUpdate(BaseModel):
    name: str = ""
    degree: str = ""
    branch: str = ""
    year_of_study: int | None = Field(default=None, ge=1, le=8)

    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)

    preferred_locations: list[str] = Field(
        default_factory=lambda: ["India"]
    )
    remote_preferred: bool = True

    opportunity_types: list[str] = Field(
        default_factory=lambda: [
            "hackathon",
            "internship",
            "job",
            "scholarship",
            "fellowship",
            "competition",
            "research",
        ]
    )
class BookmarkRequest(BaseModel):
    url: str

app = FastAPI(
    title="Opportunity Agent API",
    description="Discover, validate, and recommend opportunities for students.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_valid_opportunities():
    """Load opportunities and filter out records failing validation."""

    try:
        opportunities = load_opportunities()
    except (RuntimeError, OSError) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to load the opportunity database.",
        ) from error

    valid = []

    for opportunity in opportunities:
        is_valid, _problems = validate_opportunity(opportunity)
        if is_valid:
            valid.append(opportunity)

    return valid


@app.get("/")
def home():
    return {
        "app": "Opportunity Agent",
        "message": "Backend is running.",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Opportunity Agent"}

@app.get("/api/bookmarks")
def get_bookmarks():
    """Return saved bookmark URLs."""
    try:
        bookmarks = load_bookmarks()
        return {
            "count": len(bookmarks),
            "bookmarks": bookmarks,
        }
    except (RuntimeError, OSError) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to load bookmarks.",
        ) from error


@app.post("/api/bookmarks")
def create_bookmark(request: BookmarkRequest):
    """Save an opportunity URL."""
    try:
        bookmarks = add_bookmark(request.url)
        return {
            "status": "saved",
            "count": len(bookmarks),
            "bookmarks": bookmarks,
        }
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except (RuntimeError, OSError) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to save bookmark.",
        ) from error


@app.delete("/api/bookmarks")
def delete_bookmark(url: str):
    """Remove an opportunity URL from bookmarks."""
    try:
        bookmarks = remove_bookmark(url)
        return {
            "status": "removed",
            "count": len(bookmarks),
            "bookmarks": bookmarks,
        }
    except (RuntimeError, OSError) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to remove bookmark.",
        ) from error

@app.get("/api/profile")
def get_profile():
    """Return the currently configured user profile."""

    try:
        return load_profile().to_dict()
    except (RuntimeError, OSError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to load the user profile.",
        ) from error


@app.put("/api/profile")
def update_profile(request: ProfileUpdate):
    """Validate and save an updated user profile."""

    try:
        profile = UserProfile(**request.model_dump())
        save_profile(profile)
        return {
            "status": "saved",
            "profile": profile.to_dict(),
        }
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to save the user profile.",
        ) from error


@app.post("/api/discover")
def discover(request: DiscoveryRequest):
    """Run a limited discovery job from the website."""

    category = request.category.strip().lower()

    if category not in SEARCH_QUERIES:
        raise HTTPException(
            status_code=422,
            detail="Unsupported opportunity category.",
        )

    result = execute_discovery(category, request.limit)

    if result != 0:
        raise HTTPException(
            status_code=502,
            detail="Discovery failed. Check the backend terminal logs.",
        )

    opportunities = get_valid_opportunities()

    return {
        "status": "completed",
        "category": category,
        "count": len(opportunities),
        "opportunities": [
            item.to_dict() for item in opportunities
        ],
    }


@app.get("/api/opportunities")
def get_opportunities(category: str | None = None):
    """Return saved, validated opportunities."""

    if category:
        category = category.strip().lower()

        if category not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=422,
                detail="Unsupported opportunity category.",
            )

    opportunities = get_valid_opportunities()

    if category:
        opportunities = [
            item for item in opportunities
            if item.type == category
        ]

    return {
        "count": len(opportunities),
        "opportunities": [
            item.to_dict() for item in opportunities
        ],
    }


@app.get("/api/recommendations")
def get_recommendations():
    """Rank saved opportunities against the user profile."""

    try:
        profile = load_profile()
        opportunities = get_valid_opportunities()
        ranked = rank_opportunities(opportunities, profile)
    except (RuntimeError, OSError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate recommendations.",
        ) from error

    return {
        "count": len(ranked),
        "profile": {
            "degree": profile.degree,
            "branch": profile.branch,
            "year_of_study": profile.year_of_study,
            "interests": profile.interests,
        },
        "recommendations": [
            {
                "score": item["score"],
                "reasons": item["reasons"],
                "components": item["components"],
                "opportunity": item["opportunity"].to_dict(),
            }
            for item in ranked
        ],
    }
