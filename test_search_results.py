from search import search_category

results = search_category(
    "internship",
    max_results_per_query=5,
)

print("\nSEARCH RESULTS")
print("=" * 70)

for index, item in enumerate(results, start=1):
    print(f"\n{index}. {item.get('title', 'No title')}")
    print("URL:", item.get("url", ""))
    print("Preview:", item.get("content", "")[:200])

print("\nTotal unique results:", len(results))
