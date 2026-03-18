import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai

# ==========================================
# 1. SETUP API KEYS & SECRETS
# ==========================================
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

# Matching your exact GitHub Actions YAML names
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

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
        # UPDATED: Specifically asking for UAV and Drone events
        "query": "upcoming UAV drone student hackathons in India 2026 registration dates prize money",
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
    You are an expert UAV/Drone hackathon scout. Analyze this web search data:
    {json.dumps(search_data)}
    
    RULES:
    1. ONLY include UAV, drone, aerospace, or robotics hackathons happening in India in 2026.
    2. IGNORE results from 2024 or 2025.
    3. IGNORE news articles or empty pages.
    4. Return a clean JSON list of objects. Each object MUST have these exact keys: 
       'name', 'registration_date', 'event_date', 'prize_money', 'location', and 'url'.
    5. If a specific detail (like prize money) is not found in the text, put "Not specified".
    6. If no hackathons match the criteria, return an empty list [].
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
        print("No active UAV registration portals found today.")
        return
        
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("🚨 ERROR: Email credentials are missing! Check your GitHub Secrets.")
        return

    print("--- 📧 SENDING EMAIL ---")
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"🚁 Daily UAV Hackathon Scout - {datetime.now().strftime('%Y-%m-%d')}"
    
    # UPDATED: Better email formatting for the new details
    body = "<h3>Here are your verified UAV/Drone Hackathons:</h3><hr>"
    for h in hackathons:
        body += f"<h4><b>{h.get('name', 'Unknown Event')}</b></h4>"
        body += f"<ul>"
        body += f"<li><b>Event Date:</b> {h.get('event_date', 'Not specified')}</li>"
        body += f"<li><b>Registration Deadline:</b> {h.get('registration_date', 'Not specified')}</li>"
        body += f"<li><b>Prize Money:</b> {h.get('prize_money', 'Not specified')}</li>"
        body += f"<li><b>Location:</b> {h.get('location', 'Not specified')}</li>"
        body += f"<li><b>Link:</b> <a href='{h.get('url', '#')}'>Register Here</a></li>"
        body += f"</ul><br>"
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
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
        print("No active UAV registration portals found today.")
