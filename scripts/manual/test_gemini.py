from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL

if not GEMINI_API_KEY:
    print("ERROR: Gemini API key was not loaded from .env")
    raise SystemExit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

print("Gemini API key loaded: Yes")
print("Testing model:", GEMINI_MODEL)

try:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Reply with exactly: Gemini connection OK",
    )

    print("Gemini response:", response.text.strip())

except Exception as error:
    print("Gemini request failed.")
    print("Error type:", type(error).__name__)
    print("Details:", str(error)[:500])
