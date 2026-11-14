import argparse

from ai import extract_opportunity
from dedup import deduplicate_opportunities
from search import SEARCH_QUERIES, search_category
from storage import load_opportunities, save_opportunities
from validator import validate_opportunity


def run_agent(category: str, limit: int) -> int:
    """Discover, validate, deduplicate, and save opportunities."""

    print("\nOpportunity Agent")
    print(f"Category: {category}")
    print(f"Maximum Gemini extractions this run: {limit}")
    print("-" * 55)

    try:
        # 1. Search the web.
        results = search_category(
            category,
            max_results_per_query=5,
        )
        results = results[:limit]

        print(f"\nSearch results selected: {len(results)}")

        # 2. Extract opportunities using Gemini.
        discovered = []

        for index, result in enumerate(results, start=1):
            print(
                f"\n[{index}/{len(results)}] "
                f"Analyzing: {result.get('title', 'Untitled')}"
            )

            opportunity = extract_opportunity(result)

            if opportunity is None:
                print("Skipped: no usable opportunity extracted.")
                continue

            discovered.append(opportunity)
            print(
                f"Extracted: {opportunity.title} "
                f"({opportunity.type})"
            )

        # 3. Load existing records and merge with new discoveries.
        existing = load_opportunities()
        combined = deduplicate_opportunities(existing + discovered)

        # 4. Revalidate all records, including previously saved ones.
        valid_records = []

        for opportunity in combined:
            is_valid, problems = validate_opportunity(opportunity)

            if is_valid:
                valid_records.append(opportunity)
            else:
                print(f"\nFiltered out: {opportunity.title}")

                for problem in problems:
                    print(f" - {problem}")

        # 5. Save only records that pass validation.
        save_opportunities(valid_records)

        print("\n" + "-" * 55)
        print(f"Extracted this run: {len(discovered)}")
        print(f"Records saved in total: {len(valid_records)}")
        print(
            "Records filtered as invalid: "
            f"{len(combined) - len(valid_records)}"
        )
        print("Storage file: opportunities.json")

        return 0

    except (RuntimeError, OSError, ValueError) as error:
        print(f"\nAgent stopped: {error}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover and save student opportunities."
    )

    parser.add_argument(
        "--category",
        choices=sorted(SEARCH_QUERIES.keys()),
        default="internship",
        help="Opportunity category to search.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum search results sent to Gemini (1–10).",
    )

    args = parser.parse_args()

    if not 1 <= args.limit <= 10:
        parser.error("--limit must be between 1 and 10.")

    return run_agent(args.category, args.limit)


if __name__ == "__main__":
    raise SystemExit(main())
