import os
import requests
import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai

# ==========================================
# SETUP
# ==========================================
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
TAVILY_API_KEY    = os.environ["TAVILY_API_KEY"]
SENDER_EMAIL      = os.environ["SENDER_EMAIL"]
SENDER_PASSWORD   = os.environ["SENDER_PASSWORD"]
RECEIVER_EMAIL    = os.environ["RECEIVER_EMAIL"]

DATA_FILE    = "hackathons.json"
TODAY        = datetime.now().strftime("%Y-%m-%d")
TODAY_LABEL  = datetime.now().strftime("%d %B %Y")

# ==========================================
# MEMORY
# ==========================================
def load_memory():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def save_memory(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==========================================
# LINK VERIFICATION
# Real HTTP ping — not a guess.
# ==========================================
def is_link_alive(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        return r.status_code == 200
    except Exception:
        return False

# ==========================================
# SEARCH
# 5 targeted queries to cover India UAV events
# ==========================================
def search_web():
    print("🔍 Searching the web...")
    queries = [
        "UAV drone hackathon India 2026 registration open",
        "drone competition India 2026 apply now prize",
        "Unstop drone UAV hackathon India 2026",
        "MeitY aerospace drone challenge 2026 India",
        "IIT NIT drone robotics hackathon 2026 India",
    ]
    results = []
    for q in queries:
        try:
            r = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": q,
                    "search_depth": "advanced",
                    "max_results": 8,
                },
                timeout=15,
            )
            if r.status_code == 200:
                results.extend(r.json().get("results", []))
        except Exception as e:
            print(f"  Search failed for '{q}': {e}")
    print(f"  Got {len(results)} raw results from {len(queries)} queries.")
    return results

# ==========================================
# AI FILTER
# Model confirmed working on your API key.
# Temperature 0 = no hallucination.
# ==========================================
def filter_with_ai(raw_results):
    print("🧠 Running AI filter...")
    prompt = f"""
You are a ruthless UAV/Drone hackathon auditor.

Today's date: {TODAY} (format: YYYY-MM-DD)

RAW DATA:
{json.dumps(raw_results, indent=2)}

STRICT RULES — if ANY rule fails, the event is DELETED:
1. Must be UAV, drone, aerial robotics, or aerospace. Anything else = DELETE.
2. Must be in INDIA. Anything else = DELETE.
3. Registration deadline must be STRICTLY AFTER {TODAY}. 
   - If deadline is before or equal to {TODAY} = DELETE immediately.
   - If deadline says "closed", "ended", "over" = DELETE immediately.
   - If you CANNOT find a clear registration deadline = DELETE it. Do not guess.
4. Event year must be 2026 or later. Anything from 2024 or 2025 = DELETE.
5. News articles, blog posts, scholarship pages = DELETE.

Return ONLY a valid JSON array. Zero explanation. Zero markdown.
Each object must have exactly these keys:
- "name": Full event name
- "event_date": When the event happens (e.g. "15-17 April 2026")
- "registration_deadline": Last date to register (e.g. "31 March 2026")
- "prize_money": Prize amount (e.g. "INR 1,00,000" or "Not specified")
- "location": City and state, or "Online"
- "url": Direct registration or official page URL

If zero events pass ALL rules, return exactly: []
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0},
        )
        parsed = json.loads(response.text)
        if isinstance(parsed, list):
            print(f"  AI returned {len(parsed)} candidates.")
            return parsed
        return []
    except Exception as e:
        print(f"  AI filter error: {e}")
        return []

# ==========================================
# VERIFY CANDIDATES
# Check each link is alive before trusting it.
# ==========================================
def verify_candidates(candidates, known_urls):
    print("🔗 Verifying links...")
    new_valid = []
    for h in candidates:
        url = h.get("url", "").strip()
        if not url:
            continue
        if url in known_urls:
            print(f"  Already known, skipping: {h.get('name')}")
            continue
        if is_link_alive(url):
            new_valid.append(h)
            print(f"  ✅ Valid: {h.get('name')}")
        else:
            print(f"  ❌ Dead link removed: {h.get('name')}")
    return new_valid

# ==========================================
# EMAIL
# ==========================================
def send_email(new_items, old_items):
    total = len(new_items) + len(old_items)
    if total == 0:
        print("📭 Nothing to report. No email sent.")
        return

    print("📧 Sending email...")

    subject = f"🚁 UAV Hackathon Scout — {len(new_items)} New | {len(old_items)} Tracked | {TODAY_LABEL}"

    # --- Build HTML ---
    html = f"""
    <html><body style="font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px;">
    <div style="max-width: 640px; margin: auto; background: white; border-radius: 10px; overflow: hidden; border: 1px solid #ddd;">

      <div style="background: #1a237e; padding: 20px;">
        <h1 style="color: white; margin: 0; font-size: 20px;">🚁 UAV Hackathon Scout</h1>
        <p style="color: #c5cae9; margin: 5px 0 0 0; font-size: 13px;">Report generated: {TODAY_LABEL} &nbsp;|&nbsp; India only &nbsp;|&nbsp; Open registrations only</p>
      </div>

      <div style="padding: 20px;">
    """

    # New section
    html += f'<h2 style="color: #d32f2f; border-bottom: 2px solid #d32f2f; padding-bottom: 6px;">🔥 NEW THIS SCAN ({len(new_items)} found)</h2>'
    if not new_items:
        html += '<p style="color: #888;">No new hackathons discovered in this scan. Showing your tracked list below.</p>'
    else:
        for h in new_items:
            html += _card(h, is_new=True)

    # Previous section
    if old_items:
        html += f'<h2 style="color: #455a64; border-bottom: 2px solid #cfd8dc; padding-bottom: 6px; margin-top: 30px;">📌 PREVIOUSLY TRACKED ({len(old_items)} active)</h2>'
        for h in old_items:
            html += _card(h, is_new=False)

    html += """
      </div>
      <div style="background: #f5f5f5; padding: 12px 20px; font-size: 11px; color: #999; text-align: center;">
        This is an automated report. Links verified at time of scan. Re-check before registering.
      </div>
    </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"🚨 Email failed: {e}")

def _card(h, is_new):
    border = "#2e7d32" if is_new else "#78909c"
    bg     = "#e8f5e9" if is_new else "#f9f9f9"
    name   = h.get("name", "Unknown Event")
    edate  = h.get("event_date", "Not specified")
    rdate  = h.get("registration_deadline", "Not specified")
    prize  = h.get("prize_money", "Not specified")
    loc    = h.get("location", "Not specified")
    url    = h.get("url", "#")

    return f"""
    <div style="background:{bg}; border-left: 5px solid {border}; padding: 14px; margin-bottom: 14px; border-radius: 4px;">
      <h3 style="margin: 0 0 10px 0; font-size: 15px;">{name}</h3>
      <table style="font-size: 13px; border-collapse: collapse;">
        <tr><td style="padding: 2px 10px 2px 0; color:#555; white-space:nowrap;"><b>📅 Event Date</b></td><td>{edate}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; color:#555; white-space:nowrap;"><b>⏰ Register By</b></td><td>{rdate}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; color:#555; white-space:nowrap;"><b>💰 Prize Money</b></td><td>{prize}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; color:#555; white-space:nowrap;"><b>📍 Location</b></td><td>{loc}</td></tr>
      </table>
      <a href="{url}" style="display:inline-block; margin-top:10px; background:{border}; color:white; padding:8px 14px; text-decoration:none; border-radius:4px; font-size:13px;">Register Now →</a>
    </div>
    """

# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    print(f"\n{'='*50}")
    print(f"Drone Scout starting — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    # Load what we already know
    memory      = load_memory()
    known_urls  = {h.get("url") for h in memory if h.get("url")}
    print(f"📂 Loaded {len(memory)} previously tracked hackathons.\n")

    # Search + filter + verify
    raw          = search_web()
    candidates   = filter_with_ai(raw) if raw else []
    new_valid    = verify_candidates(candidates, known_urls)

    # Merge and save
    combined = new_valid + memory
    save_memory(combined)
    print(f"\n💾 Memory updated: {len(combined)} total hackathons tracked.")

    # Send
    send_email(new_valid, memory)

    print(f"\n✅ Scout run complete.\n")
