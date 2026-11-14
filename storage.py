import json
import os
from pathlib import Path

from opportunity import Opportunity, ALLOWED_TYPES


DATA_FILE = Path(__file__).with_name("opportunities.json")


def load_opportunities() -> list[Opportunity]:
    """Load saved opportunity records from the JSON file."""

    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            records = json.load(file)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"{DATA_FILE.name} contains invalid JSON. "
            "Repair the file before saving new data."
        ) from error

    if not isinstance(records, list):
        raise RuntimeError(
            f"{DATA_FILE.name} must contain a JSON list."
        )

    opportunities = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            print(f"Skipping invalid record at index {index}.")
            continue

        try:
            # Ignore unexpected fields from older schema versions.
            allowed_fields = Opportunity.__dataclass_fields__.keys()
            clean_record = {
                key: value
                for key, value in record.items()
                if key in allowed_fields
            }

            opportunity = Opportunity(**clean_record)

            if not isinstance(opportunity.confidence, (int, float)):
                raise ValueError("Invalid confidence value")

            if not 0 <= opportunity.confidence <= 1:
                raise ValueError("Confidence must be between 0 and 1")

            for field_name in (
                "eligibility",
                "required_skills",
                "fields",
                "degree_requirements",
                "year_requirements",
            ):
                value = getattr(opportunity, field_name)
                if not isinstance(value, list) or not all(
                    isinstance(item, str) for item in value
                ):
                    raise ValueError(
                        f"Invalid {field_name} field"
                    )

            opportunities.append(opportunity)

        except (TypeError, ValueError) as error:
            print(f"Skipping invalid record {index}: {error}")

    return opportunities


def save_opportunities(
    opportunities: list[Opportunity],
) -> None:
    """Save all opportunities using an atomic file replacement."""

    for opportunity in opportunities:
        if not isinstance(opportunity, Opportunity):
            raise TypeError(
                "All records must be Opportunity objects."
            )

        if opportunity.type not in ALLOWED_TYPES:
            raise ValueError(
                f"Unsupported type: {opportunity.type}"
            )

    records = [
        opportunity.to_dict()
        for opportunity in opportunities
    ]

    temporary_file = DATA_FILE.with_suffix(".json.tmp")

    try:
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(
                records,
                file,
                indent=2,
                ensure_ascii=False,
            )
            file.write("\n")

        os.replace(temporary_file, DATA_FILE)

    finally:
        if temporary_file.exists():
            temporary_file.unlink()
