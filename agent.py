import os
from google import genai

def list_my_models():
    print("--- 🔍 ASKING GOOGLE FOR AVAILABLE MODELS ---")
    try:
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        
        # This asks Google for every model your key is allowed to use
        models = client.models.list()
        
        print("✅ SUCCESS! Your API Key has access to:")
        for m in models:
            print(f"- {m.name}")
            
    except Exception as e:
        print(f"🚨 ERROR LISTING MODELS: {e}")

if __name__ == "__main__":
    list_my_models()
