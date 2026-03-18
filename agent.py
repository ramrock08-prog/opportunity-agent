import os
import requests
import json
import smtplib
from datetime import datetime  # THIS FIXES SCREENSHOT 1
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai
from google.genai import errors

# 1. Setup API Keys
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

def check_link(url):
def list_my_models():
    print("--- 🔍 ASKING GOOGLE FOR AVAILABLE MODELS ---")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        return response.status_code == 200
    except Exception:
        return False

def get_history():
    if os.path.exists("history.json"):
        try:
            with open("history.json", "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_history(data):
    with open("history.json", "w") as f:
        json.dump(data, f, indent=4)

def run_scout():
    print(f"--- Starting Drone Scout Run: {datetime.now()} ---")
    
    # 2. KEYWORD EXPANSION
    queries = [
        "Drone UAV hackathons India 2026 registration open",
        "MeitY drone challenge 2026 apply now",
        "Unstop drone competitions India 2026",
    ]
    
    all_search_data = []
    for q in queries:
        url = "https://api.tavily.com/search"
        payload = {"api_key": TAVILY_API_KEY, "query": q, "search_depth": "basic"}
        try:
            res = requests.post(url, json=payload).json()
            all_search_data.extend(res.get('results', []))
        except Exception as e:
            print(f"Search error: {e}")
            continue

    # 3. BULLETPROOF AI FILTERING
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
    Today's Date: {current_date}. 
    Data: {all_search_data}
    RULES: ONLY return active drone hackathons in India for 2026 in EXACT JSON format. 
    Format: [{{"name": "X", "deadline": "YYYY-MM-DD", "location": "Y", "prize": "Z", "url": "URL"}}]
    Return [] if nothing is found.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        found_events = json.loads(clean_text)
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    except errors.ClientError as e:
        # THIS FIXES SCREENSHOT 2 (The 429 Quota Error)
        print(f"🚨 GOOGLE API LIMIT HIT: {e}")
        print("We asked the AI too many questions too fast. The bot will try again on its next scheduled run.")
        return # Gracefully exit without crashing
    except Exception as e:
        print(f"AI Formatting Error: {e}")
        found_events = []

    # 4. MEMORY & VERIFICATION
    history = get_history()
    new_to_report = []
    
    for event in found_events:
        if check_link(event['url']):
            if not any(h['url'] == event['url'] for h in history):
                new_to_report.append(event)

    # 5. REPORTING
    if new_to_report or history:
        updated_history = new_to_report + history
        save_history(updated_history[:15])
        send_email(new_to_report, history)
    else:
        print("No active registration portals found today.")

def send_email(new, old):
    msg = MIMEMultipart()
    msg['Subject'] = f"🚀 [ALERT] {len(new)} New Drone Registrations Open"
    
    html = f"<h2>🔥 NEW DISCOVERIES ({datetime.now().strftime('%d %b %Y')})</h2>"
    if not new:
        html += "<p>No new portals opened recently.</p>"
    else:
        for item in new:
            html += f"<p><b>{item['name']}</b><br>Deadline: {item['deadline']}<br><a href='{item['url']}'>Register</a></p>"
    
    if old:
        html += "<h3>STILL ACTIVE</h3>"
        for item in old[:5]:
            html += f"<p>{item['name']} - <a href='{item['url']}'>Link</a></p>"

    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.environ["SENDER_EMAIL"], os.environ["SENDER_PASSWORD"])
            server.sendmail(os.environ["SENDER_EMAIL"], os.environ["RECEIVER_EMAIL"], msg.as_string())
        print("Email Sent!")
        # This asks Google for every model your key is allowed to use
        models = client.models.list()
        
        print("✅ SUCCESS! Your API Key has access to:")
        for m in models:
            print(f"- {m.name}")
            
    except Exception as e:
        print(f"Email Failed: {e}")
        print(f"🚨 ERROR LISTING MODELS: {e}")

if __name__ == "__main__":
    run_scout()
    list_my_models()
