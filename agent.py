import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import google.generativeai as genai

# Setup
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
TAVILY_API_KEY = os.environ["TAVILY_API_KEY"]

def check_link(url):
    """Verifies if the official website is live and accessible."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        # We only want links that return a 'success' code
        return response.status_code == 200
    except:
        return False

def get_history():
    """Loads the history.json from the GitHub repo."""
    if os.path.exists("history.json"):
        try:
            with open("history.json", "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(data):
    """Saves the current state to history.json."""
    with open("history.json", "w") as f:
        json.dump(data, f, indent=4)

def run_scout():
    # 1. SEARCH: Broad but focused on India and 2026
    search_queries = [
        "Drone UAV hackathons India 2026 registration open",
        "MeitY drone competition 2026 apply now",
        "Unstop drone hackathon india",
        "IIT NIT drone challenges 2026",
        "DGCA India drone news registration"
    ]
    
    raw_results = []
    for q in search_queries:
        url = "https://api.tavily.com/search"
        payload = {"api_key": TAVILY_API_KEY, "query": q, "search_depth": "advanced"}
        try:
            res = requests.post(url, json=payload).json()
            raw_results.extend(res.get('results', []))
        except:
            continue

    # 2. THE RUTHLESS AI FILTER
    model = genai.GenerativeModel('gemini-1.5-flash')
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # YOUR NEW RULES APPLIED HERE:
    prompt = f"""
    Current Date: {current_date}
    Raw Search Data: {raw_results}
    
    STRICT FILTERING RULES:
    1. DELETE any result from 'Scholarship' or 'News' websites (like Times of India, News18) that do NOT have a direct 'Register' or 'Apply' button.
    2. ONLY include hackathons in INDIA.
    3. IGNORE everything from 2025 or older.
    4. Registration MUST be open as of {current_date}.
    5. Prioritize portals: Unstop, MeitY.gov.in, Devpost, IIT/NIT websites.

    Output format (JSON ONLY):
    [
      {{"name": "Name", "reg_date": "Deadline", "location": "City", "prize": "INR", "url": "URL"}}
    ]
    Return [] if no high-quality registration portals are found.
    """
    
    response = model.generate_content(prompt)
    try:
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        new_findings = json.loads(clean_json)
    except:
        new_findings = []

    # 3. VERIFICATION & HISTORY
    history = get_history()
    to_report = []
    
    for item in new_findings:
        # Step A: Is the link actually alive?
        if check_link(item['url']):
            # Step B: Have we seen this URL before?
            is_duplicate = any(h['url'] == item['url'] for h in history)
            if not is_duplicate:
                to_report.append(item)

    # 4. REPORTING
    if to_report or history:
        # Update memory with new items
        updated_history = to_report + history
        save_history(updated_history[:20]) # Keep top 20 active events
        send_email(to_report, history)
    else:
        print("No active registration portals found in this run.")

def send_email(new, old):
    msg = MIMEMultipart()
    msg['Subject'] = f"🚀 [ALERT] {len(new)} New Drone Registrations Open"
    
    html = f"""
    <body style="font-family: sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="background: white; padding: 20px; border-radius: 10px;">
            <h1 style="color: #d32f2f;">New Active Hackathons</h1>
    """
    
    if not new:
        html += "<p style='color: #666;'>No new portals opened in the last 5 hours.</p>"
    else:
        for item in new:
            html += f"""
            <div style="border-bottom: 2px solid #eee; padding: 10px 0;">
                <h2 style="margin:0;">{item['name']}</h2>
                <p><b>Location:</b> {item['location']} | <b>Deadline:</b> {item['reg_date']}</p>
                <p><b>Prize:</b> {item['prize']}</p>
                <a href="{item['url']}" style="background: #2e7d32; color: white; padding: 10px; text-decoration: none; border-radius: 5px;">Go to Registration</a>
            </div>
            """
    
    if old:
        html += "<h2 style='margin-top:40px; color: #555;'>Tracked & Still Active</h2>"
        for item in old[:5]:
            html += f"<p>• {item['name']} - <a href='{item['url']}'>Link</a></p>"

    html += "</div></body>"
    msg.attach(MIMEText(html, 'html'))
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["SENDER_EMAIL"], os.environ["SENDER_PASSWORD"])
        server.sendmail(os.environ["SENDER_EMAIL"], os.environ["RECEIVER_EMAIL"], msg.as_string())
    print("Report Delivered.")

if __name__ == "__main__":
    run_scout()
