from profile import load_profile

from scorer import rank_opportunities
from storage import load_opportunities
from validator import validate_opportunity


def main():
    profile = load_profile()
    opportunities = load_opportunities()

    valid_opportunities = []

    for opportunity in opportunities:
        is_valid, problems = validate_opportunity(opportunity)

        if is_valid:
            valid_opportunities.append(opportunity)
        else:
            print(f"Skipping: {opportunity.title}")
            for problem in problems:
                print(f"  - {problem}")

    ranked = rank_opportunities(valid_opportunities, profile)

    print("\nOPPORTUNITY AGENT — RECOMMENDATIONS")
    print("=" * 55)
    print(f"Profile: {profile.degree} {profile.branch}")
    print(f"Interests: {', '.join(profile.interests)}")
    print(f"Opportunities considered: {len(valid_opportunities)}")

    if not ranked:
        print("\nNo valid matching opportunities are currently saved.")
        print("Run the discovery agent to search for more.")
        return

    for index, item in enumerate(ranked, start=1):
        opportunity = item["opportunity"]

        print(f"\n{index}. {opportunity.title}")
        print(f"   Type: {opportunity.type}")
        print(f"   Organization: {opportunity.organization or 'Not specified'}")
        print(f"   Relevance score: {item['score']}/100")
        print(f"   Location: {opportunity.location}")
        print(f"   Deadline: {opportunity.deadline or 'Not specified'}")
        print(f"   Application: {opportunity.application_url}")

        print("   Reasons:")
        for reason in item["reasons"]:
            print(f"     - {reason}")

    print("\nNote: Relevance scores do not prove eligibility")
    print("or confirm that applications are currently open.")


if __name__ == "__main__":
    main()
