import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai

# ==========================================
# 1. SETUP API KEYS
# ==========================================
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]
EMAIL_USER = os.environ.get("EMAIL_USER") # Make sure this matches your GitHub Secret name
EMAIL_PASS = os.environ.get("EMAIL_PASS") # Make sure this matches your GitHub Secret name

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def check_link(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except Exception:
        return False

def search_web():
    print("--- 🔍 SEARCHING THE WEB (TAVILY) ---")
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": "upcoming student hackathons in India 2026 registration open",
        "search_depth": "advanced",
        "max_results": 10
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json().get('results', [])
    print("🚨 Tavily Search Failed")
    return []

def filter_with_ai(search_data):
    print("--- 🧠 RUNNING AI FILTER (2.5-FLASH-LITE) ---")
    prompt = f"""
    You are an expert hackathon scout. Analyze this web search data:
    {json.dumps(search_data)}
    
    RULES:
    1. ONLY include hackathons happening in India in 2026.
    2. IGNORE results from 2024 or 2025.
    3. IGNORE news articles or empty pages.
    4. Return a clean JSON list of objects with 'name', 'date', and 'url'. If none match, return an empty list [].
    """
    try:
        # USING THE CORRECT, ACTIVE FREE-TIER MODEL
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"🚨 AI Filter Error: {e}")
        return []

def send_email(hackathons):
    if not hackathons:
        print("No active registration portals found today.")
        return
        
    print("--- 📧 SENDING EMAIL ---")
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER
    msg['Subject'] = f"🚀 Daily Hackathon Report - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = "<h3>Here are your verified Hackathons:</h3><ul>"
    for h in hackathons:
        body += f"<li><b>{h.get('name', 'Unknown')}</b> ({h.get('date', 'TBD')}) - <a href='{h.get('url', '#')}'>Link</a></li>"
    body += "</ul>"
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print("✅ Email Sent Successfully!")
    except Exception as e:
        print(f"🚨 Email Failed: {e}")

# ==========================================
# 3. MAIN EXECUTION (DRONE SCOUT)
# ==========================================
if __name__ == "__main__":
    print(f"--- Starting Drone Scout Run: {datetime.now()} ---")
    
    raw_data = search_web()
    
    if raw_data:
        ai_filtered_data = filter_with_ai(raw_data)
        
        # Check if the links actually work
        valid_hackathons = []
        for event in ai_filtered_data:
            if check_link(event.get('url', '')):
                valid_hackathons.append(event)
            else:
                print(f"Dead link removed: {event.get('name')}")
                
        send_email(valid_hackathons)
    else:
        print("No active registration portals found today.")
