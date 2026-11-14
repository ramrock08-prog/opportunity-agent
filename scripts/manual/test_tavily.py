import requests

from config import TAVILY_API_KEY

if not TAVILY_API_KEY:
    print("ERROR: Tavily API key was not loaded from .env")
    raise SystemExit(1)

print("Tavily API key loaded: Yes")

try:
    response = requests.post(
        "https://api.tavily.com/search",
        headers={
            "Authorization": f"Bearer {TAVILY_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "query": "AI internship opportunities for students in India",
            "max_results": 1,
            "search_depth": "basic",
        },
        timeout=30,
    )

    print("HTTP status:", response.status_code)

    if response.ok:
        data = response.json()
        print("Connection successful!")
        print("Results returned:", len(data.get("results", [])))
        for item in data.get("results", [])[:1]:
            print("Sample title:", item.get("title", "No title"))
    else:
        print("API request was not successful.")
        print("Response:", response.text[:300])

except requests.RequestException as error:
    print("Connection error:", str(error))
