import threading

from bookmarks import add_bookmark, load_bookmarks, remove_bookmark
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import ALLOWED_ORIGINS
from database import healthcheck as database_healthcheck
from opportunity import ALLOWED_TYPES
from profile import UserProfile, load_profile, save_profile
from run_agent import run_agent as execute_discovery
from scorer import rank_opportunities
from search import SEARCH_QUERIES
from storage import find_opportunity, load_opportunities
from validator import validate_opportunity
from verification import verify_opportunity


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


class VerifyRequest(BaseModel):
    source_url: str


# Only one discovery job may write at a time in this process. This avoids
# two requests replacing the opportunity collection simultaneously.
_discovery_lock = threading.Lock()


app = FastAPI(
    title="Opportunity Agent API",
    description="Discover, validate, and recommend opportunities for students.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
    database_ready = database_healthcheck()

    return {
        "status": "ok" if database_ready else "degraded",
        "app": "Opportunity Agent",
        "storage": "sqlite" if database_ready else "unavailable",
    }

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

    if not _discovery_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="A discovery run is already in progress. Try again shortly.",
        )

    try:
        result = execute_discovery(category, request.limit)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Discovery stopped unexpectedly. Check the backend logs.",
        ) from error
    finally:
        _discovery_lock.release()

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


@app.post("/api/opportunities/verify")
def verify_stored_opportunity(request: VerifyRequest):
    """Check links for a stored opportunity, on demand.

    Only URLs already present in storage are fetched. Accepting
    arbitrary URLs here would create a server-side request forgery
    risk.
    """
    opportunity = find_opportunity(request.source_url)

    if opportunity is None:
        raise HTTPException(
            status_code=404,
            detail="No stored opportunity matches that source URL.",
        )

    try:
        verification = verify_opportunity(opportunity)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="The link check could not be completed.",
        ) from error

    return {
        "status": "checked",
        "source_url": opportunity.source_url,
        "verification": verification,
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
