from dataclasses import asdict, dataclass, field
from typing import Optional


ALLOWED_TYPES = {
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
class Opportunity:
    """Standard representation of any discovered opportunity."""

    title: str
    type: str

    organization: str = ""
    description: str = ""

    source_url: str = ""
    application_url: str = ""

    deadline: Optional[str] = None
    start_date: Optional[str] = None

    location: str = "Not specified"
    remote: Optional[bool] = None

    eligibility: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    degree_requirements: list[str] = field(default_factory=list)
    year_requirements: list[str] = field(default_factory=list)

    stipend: Optional[str] = None
    prize_money: Optional[str] = None

    source: str = ""
    confidence: float = 0.0

    def __post_init__(self):
        self.title = self.title.strip()
        self.type = self.type.strip().lower()

        if not self.title:
            raise ValueError("Opportunity title cannot be empty.")

        if self.type not in ALLOWED_TYPES:
            raise ValueError(
                f"Unsupported opportunity type: {self.type}"
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1.")

    def to_dict(self) -> dict:
        """Convert the opportunity into a JSON-compatible dictionary."""
        return asdict(self)
