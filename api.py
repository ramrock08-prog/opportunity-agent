import threading
from pathlib import Path
from profile import UserProfile, load_profile, save_profile

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from auth import (
    auth_configuration_warning,
    auth_mode_label,
    authenticate_user,
    create_user,
    decode_token,
    get_user_by_id,
    issue_token,
)
from bookmarks import add_bookmark, load_bookmarks, remove_bookmark
from config import ALLOWED_ORIGINS, AUTH_REQUIRED, SERVE_FRONTEND
from database import DEMO_USER_EMAIL, DEMO_USER_ID
from database import healthcheck as database_healthcheck
from opportunity import ALLOWED_TYPES
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


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=100)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


DEMO_USER = {
    "id": DEMO_USER_ID,
    "email": DEMO_USER_EMAIL,
    "name": "Demo Student",
    "created_at": "",
    "demo": True,
}


def current_user(request: Request) -> dict:
    """Resolve the caller: demo user locally, JWT in auth mode."""
    if not AUTH_REQUIRED:
        return DEMO_USER

    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")

    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=401,
            detail="Sign in to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = decode_token(token.strip())

    if not claims:
        raise HTTPException(
            status_code=401,
            detail="Your session is invalid or has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = get_user_by_id(int(claims.get("sub", "0")))
    except (TypeError, ValueError, RuntimeError) as error:
        raise HTTPException(
            status_code=401,
            detail="Your session is invalid or has expired.",
        ) from error

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Your session is invalid or has expired.",
        )

    user["demo"] = False
    return user


# Only one discovery job may write at a time in this process. This avoids
# two requests replacing the opportunity collection simultaneously.
_discovery_lock = threading.Lock()


app = FastAPI(
    title="Opportunity Agent API",
    description="Discover, validate, and recommend opportunities for students.",
    version="2.0.0",
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


FRONTEND_DIST = Path(__file__).with_name("frontend") / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"


@app.get("/")
def home():
    if SERVE_FRONTEND and FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)

    return {
        "app": "Opportunity Agent",
        "message": "Backend is running.",
        "docs": "/docs",
        "frontend": "run the Vite dev server on port 5173",
    }


@app.get("/api")
def api_home():
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
        "auth": auth_mode_label(),
        "auth_warning": auth_configuration_warning(),
    }


@app.get("/api/auth/status")
def auth_status():
    """Let the frontend discover whether sign-in is required."""
    return {
        "auth_required": AUTH_REQUIRED,
        "mode": auth_mode_label(),
        "warning": auth_configuration_warning(),
    }


@app.post("/api/auth/register")
def register(request: RegisterRequest):
    """Create an account and return a bearer token."""
    try:
        user = create_user(
            request.email,
            request.password,
            request.name,
        )
    except ValueError as error:
        status_code = (
            409
            if "already exists" in str(error)
            else 422
        )
        raise HTTPException(
            status_code=status_code,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail="The account could not be created.",
        ) from error

    return {
        "status": "registered",
        "token": issue_token(user),
        "user": user,
    }


@app.post("/api/auth/login")
def login(request: LoginRequest):
    """Exchange email and password for a bearer token."""
    try:
        user = authenticate_user(
            request.email, request.password
        )
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail="Sign-in could not be completed.",
        ) from error

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Email or password is incorrect.",
        )

    return {
        "status": "authenticated",
        "token": issue_token(user),
        "user": user,
    }


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    """Return the signed-in user's public profile."""
    return {"user": user}


@app.get("/api/bookmarks")
def get_bookmarks(user: dict = Depends(current_user)):
    """Return the current user's saved bookmark URLs."""
    try:
        bookmarks = load_bookmarks(user["id"])
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
def create_bookmark(
    request: BookmarkRequest,
    user: dict = Depends(current_user),
):
    """Save an opportunity URL for the current user."""
    try:
        bookmarks = add_bookmark(request.url, user["id"])
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
def delete_bookmark(
    url: str,
    user: dict = Depends(current_user),
):
    """Remove an opportunity URL from the current user's bookmarks."""
    try:
        bookmarks = remove_bookmark(url, user["id"])
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
def get_profile(user: dict = Depends(current_user)):
    """Return the current user's profile."""

    try:
        return load_profile(user["id"]).to_dict()
    except (RuntimeError, OSError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to load the user profile.",
        ) from error


@app.put("/api/profile")
def update_profile(
    request: ProfileUpdate,
    user: dict = Depends(current_user),
):
    """Validate and save the current user's profile."""

    try:
        profile = UserProfile(**request.model_dump())
        save_profile(profile, user["id"])
        return {
            "status": "saved",
            "profile": profile.to_dict(),
        }
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except (RuntimeError, OSError) as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to save the user profile.",
        ) from error


@app.post("/api/discover")
def discover(
    request: DiscoveryRequest,
    user: dict = Depends(current_user),
):
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
def get_recommendations(user: dict = Depends(current_user)):
    """Rank saved opportunities against the current user's profile."""

    try:
        profile = load_profile(user["id"])
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

# Serve the production React build when explicitly enabled. API routes
# are declared first, so they take precedence over the static mount.
if SERVE_FRONTEND and FRONTEND_DIST.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIST, html=True),
        name="frontend",
    )
