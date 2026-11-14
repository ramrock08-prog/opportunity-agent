"""Revalidate stored opportunities and export a JSON backup.

The database is the source of truth. This script keeps the useful
cleanup behaviour of the original project while writing a portable
snapshot that can be committed or inspected.
"""

from pathlib import Path

from storage import (
    export_opportunities_json,
    load_opportunities,
    save_opportunities,
)
from validator import validate_opportunity

BACKUP_FILE = Path(__file__).with_name("opportunities.backup.json")

records = load_opportunities()

if not records:
    print("No saved opportunities exist yet.")
    raise SystemExit(0)

valid_records = []
invalid_records = []

for opportunity in records:
    is_valid, problems = validate_opportunity(opportunity)

    if is_valid:
        valid_records.append(opportunity)
    else:
        invalid_records.append((opportunity, problems))
        print(f"\nRemoving invalid record: {opportunity.title}")
        for problem in problems:
            print(f" - {problem}")

# Preserve the pre-cleanup state before deleting rows.
export_opportunities_json(BACKUP_FILE)
print(f"\nBackup created: {BACKUP_FILE.name}")

save_opportunities(valid_records)

print("\nCleanup complete.")
print(f"Original records: {len(records)}")
print(f"Valid records retained: {len(valid_records)}")
print(f"Invalid records removed: {len(invalid_records)}")