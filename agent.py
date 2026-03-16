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
    print("Performing specialized multi-query search...")
    url = "https://api.tavily.com/search"
    
    # We use two separate queries to ensure NIDAR doesn't get lost!
    queries = [
        "\"NIDAR hackathon\" 2026 2027 registration status official website updates",
        "upcoming drone UAV robotics hackathons 2026 registration open prizes dates"
    ]
    
    all_results = []
    for q in queries:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": q,
            "search_depth": "advanced",
            "max_results": 10 # 10 for each query = 20 total high-quality results
        }
        response = requests.post(url, json=payload)
        all_results.append(response.json())
    
    return all_results

def process_with_ai(search_results):
    print("AI is synthesizing deep data from multiple sources...")
    prompt = f"""
    You are a professional Hackathon Scout. Analyze these search results: {search_results}
    
    1. 🚨 NIDAR WATCH 🚨: 
       Identify if NIDAR registration for late 2026 or 2027 has any news. If the current status is 'Closed', look for 'Registration Opening Soon' dates.
    
    2. DRONE HACKATHONS (2026+): 
       Extract every drone/UAV hackathon where registration is currently OPEN. 
    
    3. DATA EXTRACTION RULES (MANDATORY):
       For each event, you MUST find and list:
       - Event Name
       - Exact Dates (e.g., March 26-28, 2026)
       - Location (City, Country OR 'Virtual')
       - Problem Statement/Theme (What is the hackathon about?)
       - Prize Money/Rewards (e.g., INR 6 Lakhs, EUR 20,000)
       - Registration Link & Deadline
    
    4. QUALITY CHECK: If a result is just an Instagram link and lacks details, mention that "Further details are on the official social media page."
    
    Format as clean, professional HTML. No markdown.
    """
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    # Temperature 0.0 ensures the AI doesn't 'guess' missing prizes or dates.
    response = model.generate_content(prompt, generation_config={"temperature": 0.0})
    return response.text

def send_email(html_content):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "🚁 NIDAR & Drone Hackathon Deep Report"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg.attach(MIMEText(html_content, 'html'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    print("Deep Report sent!")

if __name__ == "__main__":
    data = search_hackathons()
    email_body = process_with_ai(data)
    send_email(email_body)
