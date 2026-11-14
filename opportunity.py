from dataclasses import asdict, dataclass, field
from typing import Optional

from text_utils import clean_list, clean_text


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

    # Short, verbatim snippets from the source that support the
    # extracted facts. Empty when the source did not provide enough
    # evidence. These are not proof that applications are open.
    evidence: list[str] = field(default_factory=list)
    deadline_evidence: Optional[str] = None

    def __post_init__(self):
        self.title = clean_text(self.title)
        self.type = self.type.strip().lower()

        self.organization = clean_text(self.organization)
        self.description = clean_text(self.description)
        self.location = clean_text(self.location) or "Not specified"
        self.stipend = clean_text(self.stipend) or None
        self.prize_money = clean_text(self.prize_money) or None
        self.source = clean_text(self.source)
        self.deadline_evidence = (
            clean_text(self.deadline_evidence) or None
        )

        # URLs must keep their exact structure, so only strip them.
        self.source_url = (self.source_url or "").strip()
        self.application_url = (self.application_url or "").strip()

        for field_name in (
            "eligibility",
            "required_skills",
            "fields",
            "degree_requirements",
            "year_requirements",
            "evidence",
        ):
            setattr(
                self,
                field_name,
                clean_list(getattr(self, field_name)),
            )

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
