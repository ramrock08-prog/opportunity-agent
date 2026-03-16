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
    
    # Separate queries ensure we get both NIDAR and other drone events
    queries = [
        "\"NIDAR hackathon\" 2026 2027 registration status updates",
        "upcoming drone UAV robotics hackathons 2026 registration open"
    ]
    
    all_results = []
    for q in queries:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": q,
            "search_depth": "advanced",
            "max_results": 10
        }
        response = requests.post(url, json=payload)
        all_results.append(response.json())
    
    return all_results

def process_with_ai(search_results):
    print("AI is synthesizing deep data...")
    # This prompt is wrapped in triple quotes to prevent syntax errors
    prompt = f"""
    You are a strict, data-extracting AI assistant. Use the following results: {search_results}
    
    1. 🚨 NIDAR WATCH 🚨: 
       Identify if NIDAR registration for late 2026 or 2027 has news. If closed, look for 'Opening Soon' dates.
    
    2. OTHER DRONE HACKATHONS: 
       List any other drone/UAV hackathons where registration is currently OPEN.
       
    3. MANDATORY DETAILS TO EXTRACT:
       For every event, you MUST list:
       - Event Name
       - Exact Dates
       - Location (or 'Virtual')
       - Prize Money/Rewards
       - Registration Link
    
    4. Format the entire email as clean, professional HTML. Use bullet points and bold text. No markdown.
    """
    
    # FIX: Robust model selection to avoid the 'NotFound' error
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model = genai.GenerativeModel(available_models[0])
    
    # Temperature 0.0 prevents hallucinations
    response = model.generate_content(prompt, generation_config={"temperature": 0.0})
    return response.text

def send_email(html_content):
    print("Sending the deep report...")
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "🚁 NIDAR & Drone Hackathon Deep Report"
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
