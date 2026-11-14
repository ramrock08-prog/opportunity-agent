import shutil

from storage import DATA_FILE, load_opportunities, save_opportunities
from validator import validate_opportunity


if not DATA_FILE.exists():
    print("No saved opportunity database exists yet.")
    raise SystemExit(0)

backup_file = DATA_FILE.with_name("opportunities.backup.json")

# Preserve the original database before changing it.
shutil.copy2(DATA_FILE, backup_file)
print(f"Backup created: {backup_file.name}")

records = load_opportunities()
valid_records = []

for opportunity in records:
    is_valid, problems = validate_opportunity(opportunity)

    if is_valid:
        valid_records.append(opportunity)
    else:
        print(f"\nRemoving invalid record: {opportunity.title}")
        for problem in problems:
            print(f" - {problem}")

save_opportunities(valid_records)

print("\nCleanup complete.")
print(f"Original records: {len(records)}")
print(f"Valid records retained: {len(valid_records)}")
print(f"Invalid records removed: {len(records) - len(valid_records)}")
