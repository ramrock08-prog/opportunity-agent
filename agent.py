import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai # <-- THE NEW 2026 LIBRARY

# 1. Setup API Keys
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

def check_link(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=12)
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
        "DGCA India drone events 2026 registration",
        "IIT drone racing hackathon 2026 india"
    ]
    
    all_search_data = []
    for q in queries:
        url = "https://api.tavily.com/search"
        payload = {"api_key": TAVILY_API_KEY, "query": q, "search_depth": "advanced"}
        try:
            res = requests.post(url, json=payload).json()
            all_search_data.extend(res.get('results', []))
        except Exception as e:
            print(f"Search error for {q}: {e}")
            continue

    # 3. RUTHLESS AI FILTERING (Using the new Client structure)
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    Today's Date: {current_date}
    Context: India Drone/UAV Sector
    Data to Audit: {all_search_data}
    
    STRICT RUTHLESS INSTRUCTIONS:
    1. DELETE any 'News' or 'Scholarship' articles that do not have a functional 'Apply' or 'Register' portal.
    2. ONLY include events in INDIA.
    3. ONLY include events with deadlines AFTER {current_date}. 
    4. IGNORE results from 2024 or 2025. 
    5. Prioritize: Unstop, Devpost, MeitY.gov.in, and Official IIT/NIT/University sites.

    Output format (JSON ONLY):
    [
      {{"name": "Event Name", "deadline": "YYYY-MM-DD", "location": "City", "prize": "INR/Details", "url": "Direct Link"}}
    ]
    Return [] if no high-quality registration portals exist.
    """
    
    # NEW 2026 API CALL (Using the correct hyphens!)
    response = client.models.generate_content(
        model='gemini-2.0-flash', # Upgraded to the faster model
        contents=prompt
    )
    
    try:
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        found_events = json.loads(clean_text)
    except Exception:
        found_events = []

    # 4. LINK VERIFICATION & MEMORY COMPARISON
    history = get_history()
    new_to_report = []
    
    for event in found_events:
        if check_link(event['url']):
            already_exists = any(h['url'] == event['url'] for h in history)
            if not already_exists:
                new_to_report.append(event)

    # 5. FINAL REPORTING
    if new_to_report or history:
        updated_history = new_to_report + history
        save_history(updated_history[:20])
        send_email(new_to_report, history)
    else:
        print("No active registration portals found today.")

def send_email(new, old):
    msg = MIMEMultipart()
    msg['Subject'] = f"🚀 [ALERT] {len(new)} New Drone Registrations Open"
    
    html = f"""
    <body style="font-family: Arial, sans-serif; background-color: #f8f9fa; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
            <h1 style="color: #1b5e20; text-align: center;">Drone Scout Report</h1>
            <p style="text-align: center; color: #666;">Generated on {datetime.now().strftime('%d %b %Y')}</p>
            <hr>
            <h2 style="color: #d32f2f;">🔥 NEW DISCOVERIES</h2>
    """
    
    if not new:
        html += "<p style='color: #888;'>No new registration portals opened in the last 5 hours.</p>"
    else:
        for item in new:
            html += f"""
            <div style="background: #e8f5e9; border-left: 5px solid #2e7d32; padding: 15px; margin-bottom: 15px;">
                <h3 style="margin: 0 0 10px 0;">{item['name']}</h3>
                <p style="margin: 5px 0;"><b>📍 Location:</b> {item['location']}</p>
                <p style="margin: 5px 0;"><b>⏰ Deadline:</b> {item['deadline']}</p>
                <p style="margin: 5px 0;"><b>💰 Prize:</b> {item['prize']}</p>
                <a href="{item['url']}" style="display: inline-block; margin-top: 10px; background: #2e7d32; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Register Now &rarr;</a>
            </div>
            """
    
    if old:
        html += "<h2 style='margin-top: 30px; color: #555;'>STILL ACTIVE (Previously Sent)</h2>"
        for item in old[:10]:
            html += f"<p style='margin: 5px 0;'>• <b>{item['name']}</b> ({item['location']}) - <a href='{item['url']}'>Link</a></p>"

    html += """
            <hr>
            <p style="font-size: 12px; color: #999; text-align: center;">This is an automated drone intelligence report.</p>
        </div>
    </body>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.environ["SENDER_EMAIL"], os.environ["SENDER_PASSWORD"])
            server.sendmail(os.environ["SENDER_EMAIL"], os.environ["RECEIVER_EMAIL"], msg.as_string())
        print("Email Sent Successfully.")
    except Exception as e:
        print(f"Email Failed: {e}")

if __name__ == "__main__":
    run_scout()
