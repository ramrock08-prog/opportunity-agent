import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from database import (
    DEMO_USER_ID,
    LEGACY_PROFILE_FILE,
    DatabaseError,
    get_connection,
    utc_now,
)

# Legacy JSON location, retained for migration and tooling.
PROFILE_FILE = LEGACY_PROFILE_FILE

SUPPORTED_TYPES = {
    "hackathon",
    "internship",
    "job",
    "scholarship",
    "fellowship",
    "competition",
    "research",
    "other",
}


@dataclass
class UserProfile:
    """Preferences used to personalize opportunity recommendations."""

    name: str = ""
    degree: str = ""
    branch: str = ""
    year_of_study: int | None = None

    # Contact details used to pre-fill applications.
    phone: str = ""
    college: str = ""
    graduation_year: int | None = None
    github: str = ""
    linkedin: str = ""
    portfolio: str = ""

    skills: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)

    preferred_locations: list[str] = field(
        default_factory=lambda: ["India"]
    )

    remote_preferred: bool = True

    opportunity_types: list[str] = field(
        default_factory=lambda: [
            "hackathon",
            "internship",
            "scholarship",
            "job",
            "fellowship",
            "competition",
            "research",
        ]
    )

    def __post_init__(self):
        self.name = self.name.strip()[:100]
        self.degree = self.degree.strip()[:100]
        self.branch = self.branch.strip()[:100]
        self.phone = self.phone.strip()[:30]
        self.college = self.college.strip()[:150]
        self.github = self.github.strip()[:300]
        self.linkedin = self.linkedin.strip()[:300]
        self.portfolio = self.portfolio.strip()[:300]

        if self.graduation_year is not None:
            if (
                isinstance(self.graduation_year, bool)
                or not isinstance(self.graduation_year, int)
                or not 2000 <= self.graduation_year <= 2100
            ):
                raise ValueError(
                    "graduation_year must be between 2000 and 2100."
                )

        if self.year_of_study is not None:
            if (
                isinstance(self.year_of_study, bool)
                or not isinstance(self.year_of_study, int)
                or not 1 <= self.year_of_study <= 8
            ):
                raise ValueError(
                    "year_of_study must be an integer from 1 to 8."
                )

        for field_name in (
            "skills",
            "interests",
            "preferred_locations",
        ):
            values = getattr(self, field_name)

            if not isinstance(values, list):
                raise ValueError(
                    f"{field_name} must be a list of strings."
                )

            if not all(isinstance(item, str) for item in values):
                raise ValueError(
                    f"{field_name} must contain only strings."
                )

            setattr(
                self,
                field_name,
                [item.strip() for item in values if item.strip()],
            )

        if not isinstance(self.opportunity_types, list):
            raise ValueError("opportunity_types must be a list.")

        normalized_types = [
            item.strip().lower()
            for item in self.opportunity_types
            if isinstance(item, str) and item.strip()
        ]

        unsupported = set(normalized_types) - SUPPORTED_TYPES

        if unsupported:
            raise ValueError(
                f"Unsupported opportunity types: {sorted(unsupported)}"
            )

        self.opportunity_types = list(dict.fromkeys(normalized_types))

        if not isinstance(self.remote_preferred, bool):
            raise ValueError("remote_preferred must be true or false.")

    def to_dict(self) -> dict:
        """Convert this profile to a JSON-compatible dictionary."""
        return asdict(self)


def load_profile(
    user_id: int = DEMO_USER_ID,
) -> UserProfile:
    """Load one user's profile, or defaults if none exists yet."""
    try:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT payload FROM user_profiles
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
    except DatabaseError as error:
        raise RuntimeError("Could not read the profile.") from error

    if row is None:
        return UserProfile()

    try:
        data = json.loads(row["payload"])
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "The stored profile contains invalid JSON."
        ) from error

    if not isinstance(data, dict):
        raise ValueError("Profile must contain a JSON object.")

    allowed_fields = UserProfile.__dataclass_fields__.keys()
    clean_data = {
        key: value
        for key, value in data.items()
        if key in allowed_fields
    }

    return UserProfile(**clean_data)


def save_profile(
    profile: UserProfile,
    user_id: int = DEMO_USER_ID,
) -> None:
    """Validate and save one user's profile in SQLite."""
    if not isinstance(profile, UserProfile):
        raise TypeError("profile must be a UserProfile instance.")

    try:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO user_profiles(user_id, payload, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    json.dumps(
                        profile.to_dict(), ensure_ascii=False
                    ),
                    utc_now(),
                ),
            )
    except DatabaseError as error:
        raise RuntimeError("Could not save the profile.") from error


def profile_file_path() -> Path:
    """Return the legacy profile file path for diagnostics only."""
    return PROFILE_FILE
