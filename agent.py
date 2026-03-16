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
        # A broad, stable search query that won't confuse the AI
        "query": "\"NIDAR hackathon\" future registration OR upcoming open drone UAV hackathons 2026 2027", 
        "search_depth": "advanced",
        "time_range": "month"
    }
    response = requests.post(url, json=payload)
    return response.json()

def process_with_ai(search_results):
    print("AI is analyzing and formatting the data...")
    prompt = f"""
    You are a strict, data-extracting AI assistant tracking hackathons. Do NOT invent or make up information.
    Review the following raw search results: {search_results}
    
    1. 🚨 NIDAR WATCH (CRITICAL) 🚨: 
       - Search the text for "NIDAR hackathon". We know 2026 registration is closed. 
       - Check if there is ANY news about registration opening currently or for future years (like late 2026 or 2027). 
       - Create a bolded section at the top titled "🚨 NIDAR HACKATHON STATUS 🚨" and report exactly what the search results say about its future status. If there is no news, say "No new updates for future registrations."

    2. OTHER DRONE HACKATHONS: 
       - After NIDAR, list any other drone, UAV, or aerial robotics hackathons happening in 2026 or upcoming years.
       - ONLY include them if registration is currently OPEN. Do not include closed events.
    
    3. Format the entire email as a clean, professional HTML. Use bullet points and bold text. Do not use markdown formatting like ```html.
   
    4. MANDATORY DETAILS TO EXTRACT:
       - For every single hackathon you find, you MUST list: The Event Name, The Exact Dates, problem statement, prize money, The Location (or state if it is Virtual), and the Registration date and Link. """
    
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model = genai.GenerativeModel(available_models[0])
    
    # CRITICAL FIX: Setting temperature to 0.0 makes the AI 100% strict and factual. It will not hallucinate or make things up.
    response = model.generate_content(prompt, generation_config={"temperature": 0.0})
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
