import os
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import google.generativeai as genai

# Load Secret Keys from GitHub
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD") 
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL") 

genai.configure(api_key=GEMINI_API_KEY)

def search_hackathons():
    print("Searching the web for NIDAR and drone hackathons...")
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        # We added NIDAR to the exact search query!
        "query": "NIDAR hackathon 2026 registration status OR upcoming open drone UAV robotics hackathons", 
        "search_depth": "advanced",
        "time_range": "month"
    }
    response = requests.post(url, json=payload)
    return response.json()

def process_with_ai(search_results):
    print("AI is analyzing and formatting the data...")
    prompt = f"""
    You are an AI assistant tracking hackathons. 
    Review the following raw search results: {search_results}
    
    1. 🚨 NIDAR WATCH (CRITICAL) 🚨: Look specifically for ANY mention of the "NIDAR hackathon". 
       - If you find information about NIDAR, create a special bolded section at the very top of the email titled "🚨 NIDAR HACKATHON STATUS 🚨". State clearly if registration is open, announced, or if there is no news yet. Include the link if available.
       - Even if registration is closed or not open yet for NIDAR, tell me its current status.
    
    2. OTHER DRONE HACKATHONS: 
       - After the NIDAR section, list any other drone, UAV, or aerial robotics hackathons.
       - ONLY include these other hackathons if their registration is currently OPEN. 
    
    3. Format the entire email as a clean, professional HTML. Use bullet points and bold text.
    Do not include any markdown formatting like ```html. Just output raw HTML.
    """
    
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model = genai.GenerativeModel(available_models[0])
    
    response = model.generate_content(prompt)
    return response.text

def send_email(html_content):
    print("Sending the email...")
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "🚁 NIDAR Watch & Drone Hackathon Report" 
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    part = MIMEText(html_content, 'html')
    msg.attach(part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    print("Email sent successfully!")

if __name__ == "__main__":
    raw_data = search_hackathons()
    email_body = process_with_ai(raw_data)
    send_email(email_body)
