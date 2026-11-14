from pathlib import Path
from profile import UserProfile, load_profile, save_profile

from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ai import extract_profile_from_resume
from auth import (
    EmailNotVerifiedError,
    auth_configuration_warning,
    auth_mode_label,
    authenticate_user,
    create_session,
    create_user,
    decode_token,
    get_user_by_id,
    get_user_for_password_reset,
    reset_password,
    revoke_session,
    session_is_active,
    verify_email_token,
)
from auth_emails import (
    send_password_reset_email,
    send_verification_email,
)
from bookmarks import add_bookmark, load_bookmarks, remove_bookmark
from config import (
    ALLOWED_ORIGINS,
    AUTH_DEV_SHOW_TOKENS,
    AUTH_REQUIRE_VERIFIED,
    AUTH_REQUIRED,
    SERVE_FRONTEND,
)
from database import DEMO_USER_EMAIL, DEMO_USER_ID, database_label
from database import healthcheck as database_healthcheck
from locks import acquire_lock, release_lock
from mailer import email_configured
from opportunity import ALLOWED_TYPES
from rate_limit import enforce as enforce_rate_limit
from resume import MAX_UPLOAD_BYTES, extract_resume_text
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


class EmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class TokenRequest(BaseModel):
    token: str = Field(min_length=10, max_length=500)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=500)
    password: str = Field(min_length=8, max_length=128)


DEMO_USER = {
    "id": DEMO_USER_ID,
    "email": DEMO_USER_EMAIL,
    "name": "Demo Student",
    "email_verified": True,
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

    jti = claims.get("jti", "")

    if not session_is_active(jti):
        raise HTTPException(
            status_code=401,
            detail="Your session has been signed out or expired.",
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

    if AUTH_REQUIRE_VERIFIED and not user["email_verified"]:
        raise HTTPException(
            status_code=403,
            detail="Email verification required.",
        )

    user["demo"] = False
    user["jti"] = jti
    return user


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
        "storage": (
            database_label() if database_ready else "unavailable"
        ),
        "auth": auth_mode_label(),
        "auth_warning": auth_configuration_warning(),
    }


@app.get("/api/auth/status")
def auth_status():
    """Let the frontend discover the authentication requirements."""
    return {
        "auth_required": AUTH_REQUIRED,
        "verification_required": (
            AUTH_REQUIRED and AUTH_REQUIRE_VERIFIED
        ),
        "email_configured": email_configured(),
        "dev_tokens": AUTH_DEV_SHOW_TOKENS,
        "mode": auth_mode_label(),
        "warning": auth_configuration_warning(),
    }


@app.post("/api/auth/register")
def register(payload: RegisterRequest, http_request: Request):
    """Create an account, verify email when required, or sign in."""
    enforce_rate_limit(http_request, "register", 5, 3600)

    require_verification = AUTH_REQUIRED and AUTH_REQUIRE_VERIFIED

    if (
        require_verification
        and not email_configured()
        and not AUTH_DEV_SHOW_TOKENS
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "Email delivery is not configured. Ask the operator "
                "to set SENDER_EMAIL/SENDER_PASSWORD before sign-up."
            ),
        )

    try:
        user = create_user(
            payload.email,
            payload.password,
            payload.name,
            email_verified=not require_verification,
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

    if require_verification:
        sent, token = send_verification_email(user)
        response = {
            "status": "verification_sent",
            "verification_required": True,
            "email": user["email"],
            "email_sent": sent,
            "user": user,
        }

        if AUTH_DEV_SHOW_TOKENS:
            response["dev_verification_token"] = token

        if not sent and not AUTH_DEV_SHOW_TOKENS:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Account created, but the verification email "
                    "could not be sent. Try resending it later."
                ),
            )

        return response

    return {
        "status": "registered",
        "token": create_session(user),
        "user": user,
    }


@app.post("/api/auth/login")
def login(payload: LoginRequest, http_request: Request):
    """Exchange email and password for a revocable session token."""
    enforce_rate_limit(http_request, "login", 10, 300)

    try:
        user = authenticate_user(
            payload.email, payload.password
        )
    except EmailNotVerifiedError as error:
        raise HTTPException(
            status_code=403,
            detail="Email verification required.",
        ) from error
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
        "token": create_session(user),
        "user": user,
    }


@app.post("/api/auth/verify-email")
def verify_email(payload: TokenRequest, http_request: Request):
    """Consume a verification token and start a session."""
    enforce_rate_limit(http_request, "verify_email", 10, 3600)

    user = verify_email_token(payload.token)

    if user is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token.",
        )

    return {
        "status": "verified",
        "token": create_session(user),
        "user": user,
    }


@app.post("/api/auth/resend-verification")
def resend_verification(
    payload: EmailRequest,
    http_request: Request,
):
    """Resend a verification email without revealing account existence."""
    enforce_rate_limit(
        http_request, "resend_verification", 3, 3600
    )

    response = {
        "status": "sent",
        "email_sent": False,
    }

    user = get_user_for_password_reset(payload.email)

    if user is not None and not user["email_verified"]:
        sent, token = send_verification_email(user)
        response["email_sent"] = sent

        if AUTH_DEV_SHOW_TOKENS:
            response["dev_verification_token"] = token

    return response


@app.post("/api/auth/forgot-password")
def forgot_password(
    payload: EmailRequest,
    http_request: Request,
):
    """Send a reset link without revealing account existence."""
    enforce_rate_limit(http_request, "forgot_password", 5, 3600)

    response = {
        "status": "sent",
        "email_sent": False,
    }

    user = get_user_for_password_reset(payload.email)

    if user is not None:
        sent, token = send_password_reset_email(user)
        response["email_sent"] = sent

        if AUTH_DEV_SHOW_TOKENS:
            response["dev_reset_token"] = token

    return response


@app.post("/api/auth/reset-password")
def reset_password_endpoint(
    payload: ResetPasswordRequest,
    http_request: Request,
):
    """Consume a reset token, change the password, revoke sessions."""
    enforce_rate_limit(
        http_request, "reset_password", 5, 3600
    )

    try:
        user = reset_password(payload.token, payload.password)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail="The password could not be reset.",
        ) from error

    if user is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token.",
        )

    return {
        "status": "reset",
        "email": user["email"],
    }


@app.post("/api/auth/logout")
def logout(user: dict = Depends(current_user)):
    """Revoke the current server-side session."""
    if not user.get("demo") and user.get("jti"):
        try:
            revoke_session(user["jti"], user["id"])
        except RuntimeError as error:
            raise HTTPException(
                status_code=500,
                detail="The session could not be revoked.",
            ) from error

    return {"status": "logged_out"}


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


@app.post("/api/profile/import-resume")
async def import_resume(
    http_request: Request,
    file: UploadFile = File(...),
    user: dict = Depends(current_user),
):
    """Parse a resume and return a pre-filled, unsaved profile."""
    enforce_rate_limit(
        http_request, "resume_import", 5, 3600, user_id=user["id"]
    )

    data = await file.read(MAX_UPLOAD_BYTES + 1)

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="The resume is larger than the 5 MB limit.",
        )

    try:
        text = extract_resume_text(
            file.filename or "resume", data
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    try:
        extracted = extract_profile_from_resume(text)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        message = str(error)

        if "GEMINI_API_KEY" in message:
            raise HTTPException(
                status_code=503,
                detail=(
                    "AI resume extraction is not configured. "
                    "Fill the profile manually or ask the operator "
                    "to set GEMINI_API_KEY."
                ),
            ) from error

        raise HTTPException(
            status_code=502,
            detail=message,
        ) from error

    current = load_profile(user["id"]).to_dict()
    merged = dict(current)

    for key, value in extracted.items():
        if value is not None and value != "" and value != []:
            merged[key] = value

    try:
        profile = UserProfile(**merged)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail="The resume information could not be validated.",
        ) from error

    return {
        "status": "parsed",
        "filename": Path(file.filename or "resume").name,
        "characters": len(text),
        "profile": profile.to_dict(),
    }


@app.post("/api/discover")
def discover(
    request: DiscoveryRequest,
    http_request: Request,
    user: dict = Depends(current_user),
):
    """Run a limited discovery job from the website."""

    enforce_rate_limit(
        http_request, "discover", 5, 3600, user_id=user["id"]
    )

    category = request.category.strip().lower()

    if category not in SEARCH_QUERIES:
        raise HTTPException(
            status_code=422,
            detail="Unsupported opportunity category.",
        )

    owner = acquire_lock("discovery")

    if owner is None:
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
        try:
            release_lock("discovery", owner)
        except RuntimeError:
            pass

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
def verify_stored_opportunity(
    request: VerifyRequest,
    http_request: Request,
    user: dict = Depends(current_user),
):
    """Check links for a stored opportunity, on demand.

    Rate limiting also prevents repeated outbound requests.

    Only URLs already present in storage are fetched. Accepting
    arbitrary URLs here would create a server-side request forgery
    risk.
    """
    enforce_rate_limit(
        http_request, "verify_links", 30, 3600, user_id=user["id"]
    )

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
            "name": profile.name,
            "degree": profile.degree,
            "branch": profile.branch,
            "year_of_study": profile.year_of_study,
            "skills": profile.skills,
            "interests": profile.interests,
            "preferred_locations": profile.preferred_locations,
            "remote_preferred": profile.remote_preferred,
            "opportunity_types": profile.opportunity_types,
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
