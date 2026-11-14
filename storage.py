import json
from pathlib import Path

from database import (
    LEGACY_OPPORTUNITIES_FILE,
    DatabaseError,
    get_connection,
    source_key,
    utc_now,
)
from dedup import normalize_url
from opportunity import ALLOWED_TYPES, Opportunity

# Kept as the legacy JSON snapshot location. Runtime storage is SQLite.
DATA_FILE = LEGACY_OPPORTUNITIES_FILE


def _parse_record(payload: str, index: int) -> Opportunity | None:
    """Parse one stored JSON payload into an Opportunity."""
    try:
        record = json.loads(payload)
    except json.JSONDecodeError:
        print(f"Skipping invalid stored record {index}: invalid JSON")
        return None

    if not isinstance(record, dict):
        print(f"Skipping invalid stored record {index}: not an object")
        return None

    try:
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
            "evidence",
        ):
            value = getattr(opportunity, field_name)
            if not isinstance(value, list) or not all(
                isinstance(item, str) for item in value
            ):
                raise ValueError(f"Invalid {field_name} field")

        return opportunity

    except (TypeError, ValueError) as error:
        print(f"Skipping invalid stored record {index}: {error}")
        return None


def load_opportunities() -> list[Opportunity]:
    """Load saved opportunity records from SQLite."""
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT payload FROM opportunities
                ORDER BY id ASC
                """
            ).fetchall()
    except DatabaseError as error:
        raise RuntimeError(
            "Could not read opportunities from the database."
        ) from error

    opportunities = []

    for index, row in enumerate(rows):
        opportunity = _parse_record(row["payload"], index)
        if opportunity is not None:
            opportunities.append(opportunity)

    return opportunities


def save_opportunities(
    opportunities: list[Opportunity],
) -> None:
    """Replace the opportunity collection in one transaction."""
    rows = []
    seen_keys = set()

    for opportunity in opportunities:
        if not isinstance(opportunity, Opportunity):
            raise TypeError("All records must be Opportunity objects.")

        if opportunity.type not in ALLOWED_TYPES:
            raise ValueError(f"Unsupported type: {opportunity.type}")

        key = source_key(
            opportunity.source_url,
            opportunity.title,
            opportunity.organization,
        )

        # Defensive guard: the database key is unique, so never let a
        # caller-supplied duplicate abort the whole transaction.
        if key in seen_keys:
            continue

        seen_keys.add(key)

        rows.append((
            key,
            opportunity.source_url,
            opportunity.title,
            opportunity.type,
            json.dumps(opportunity.to_dict(), ensure_ascii=False),
        ))

    now = utc_now()

    try:
        with get_connection() as connection:
            existing = {
                row["source_key"]: row["created_at"]
                for row in connection.execute(
                    "SELECT source_key, created_at FROM opportunities"
                ).fetchall()
            }

            connection.execute("DELETE FROM opportunities")

            connection.executemany(
                """
                INSERT INTO opportunities(
                    source_key, source_url, title, type,
                    payload, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        key,
                        source_url,
                        title,
                        record_type,
                        payload,
                        existing.get(key, now),
                        now,
                    )
                    for (
                        key,
                        source_url,
                        title,
                        record_type,
                        payload,
                    ) in rows
                ],
            )
    except DatabaseError as error:
        raise RuntimeError(
            "Could not save opportunities to the database."
        ) from error


def find_opportunity(source_url: str) -> Opportunity | None:
    """Find a stored opportunity by exact or normalized source URL."""
    if not isinstance(source_url, str) or not source_url.strip():
        return None

    target = source_url.strip()
    target_key = normalize_url(target)

    for opportunity in load_opportunities():
        if opportunity.source_url.strip() == target:
            return opportunity

        if target_key and normalize_url(
            opportunity.source_url
        ) == target_key:
            return opportunity

    return None


def export_opportunities_json(path: str | Path) -> Path:
    """Write a JSON snapshot of the database for backups or exports."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")

    records = [
        opportunity.to_dict()
        for opportunity in load_opportunities()
    ]

    try:
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(records, file, indent=2, ensure_ascii=False)
            file.write("\n")

        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    return destination
