"""Import structured internships from open-source listing datasets.

Usage:
    python scripts/import_curated.py --country India --limit 200
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile import load_profile  # noqa: E402

from curated import import_curated  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import curated internship listings."
    )
    parser.add_argument("--country", default="India")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    stats = import_curated(
        profile=load_profile(),
        country=args.country,
        limit=args.limit,
    )

    print("Curated import complete")
    for key, value in stats.items():
        print(f"{key}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())