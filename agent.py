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

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

DATA_FILE = "hackathons.json"

# ==========================================
# 2. MEMORY FUNCTIONS
# ==========================================
def load_memory():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_memory(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def check_link(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except Exception:
        return False

def search_web():
    print("--- 🔍 SEARCHING THE WEB ---")
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": "upcoming UAV drone student hackathons in India 2026 registration dates prize money",
        "search_depth": "advanced",
        "max_results": 10
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return response.json().get('results', [])
    return []

def filter_with_ai(search_data):
    print("--- 🧠 RUNNING AI FILTER ---")
    prompt = f"""
    You are an expert UAV/Drone hackathon scout. Analyze this web search data:
    {json.dumps(search_data)}
    
    RULES:
    1. ONLY include UAV, drone, aerospace, or robotics hackathons happening in India in 2026.
    2. IGNORE results from 2024 or 2025.
    3. Return a clean JSON list of objects. Keys MUST be: 'name', 'registration_date', 'event_date', 'prize_money', 'location', and 'url'.
    """
    try:
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
        return
        
    print("--- 📧 SENDING CUMULATIVE EMAIL ---")
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"🚁 UAV Hackathon Master List - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = f"<h3>You currently have {len(hackathons)} valid UAV hackathons on your radar:</h3><hr>"
    for h in hackathons:
        body += f"<h4><b>{h.get('name', 'Unknown Event')}</b></h4>"
        body += f"<ul>"
        body += f"<li><b>Event Date:</b> {h.get('event_date', 'Not specified')}</li>"
        body += f"<li><b>Registration:</b> {h.get('registration_date', 'Not specified')}</li>"
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
# 4. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print(f"--- Starting Drone Scout Run: {datetime.now()} ---")
    
    # 1. Load memory
    saved_hackathons = load_memory()
    known_urls = {h.get('url') for h in saved_hackathons}
    
    # 2. Find new ones
    raw_data = search_web()
    if raw_data:
        ai_filtered_data = filter_with_ai(raw_data)
        
        new_valid_count = 0
        for event in ai_filtered_data:
            url = event.get('url', '')
            # Only process if it's a NEW link we haven't seen before
            if url and url not in known_urls:
                if check_link(url):
                    saved_hackathons.append(event)
                    known_urls.add(url)
                    new_valid_count += 1
                else:
                    print(f"Dead link ignored: {event.get('name')}")
        
        print(f"Added {new_valid_count} newly discovered hackathons to the master list.")
    
    # 3. Save memory for next time
    save_memory(saved_hackathons)
    
    # 4. Send the master list
    send_email(saved_hackathons)
