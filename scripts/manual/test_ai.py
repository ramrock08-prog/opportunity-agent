from ai import extract_opportunity
from search import search_category

print("Searching for an internship...")
results = search_category("internship", max_results_per_query=1)

if not results:
    print("No search results returned. Check the Tavily connection.")
    raise SystemExit(1)

result = next(
    (item for item in results if item.get("title") and item.get("content")),
    None,
)

if result is None:
    print("Search results did not contain usable content.")
    raise SystemExit(1)

print("\nSearch result:", result["title"])
print("Sending one result to Gemini...\n")

opportunity = extract_opportunity(result)

if opportunity is None:
    print("Gemini did not extract a usable opportunity from this result.")
    print("This can happen if the page lacks sufficient evidence.")
else:
    print("EXTRACTION SUCCESSFUL")
    print(opportunity.to_dict())
