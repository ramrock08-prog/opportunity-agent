import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


PROFILE_FILE = Path(__file__).with_name("profile.json")

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
        self.name = self.name.strip()
        self.degree = self.degree.strip()
        self.branch = self.branch.strip()

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


def load_profile() -> UserProfile:
    """Load the profile, or return defaults if none exists yet."""

    if not PROFILE_FILE.exists():
        return UserProfile()

    try:
        with PROFILE_FILE.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Profile file must contain a JSON object.")

        allowed_fields = UserProfile.__dataclass_fields__.keys()
        clean_data = {
            key: value
            for key, value in data.items()
            if key in allowed_fields
        }

        return UserProfile(**clean_data)

    except (json.JSONDecodeError, TypeError) as error:
        raise RuntimeError(
            "Could not read profile.json. Check its contents."
        ) from error


def save_profile(profile: UserProfile) -> None:
    """Save a profile safely using a temporary file."""

    if not isinstance(profile, UserProfile):
        raise TypeError("profile must be a UserProfile instance.")

    temporary_file = PROFILE_FILE.with_suffix(".json.tmp")

    try:
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(profile.to_dict(), file, indent=2)
            file.write("\n")

        os.replace(temporary_file, PROFILE_FILE)

    finally:
        if temporary_file.exists():
            temporary_file.unlink()
