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
    print("Searching the web for hackathons...")
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": "upcoming software hackathons online or in India registration links dates",
        "search_depth": "advanced",
        "time_range": "month"
    }
    response = requests.post(url, json=payload)
    return response.json()

def process_with_ai(search_results):
    print("AI is analyzing and formatting the data...")
    prompt = f"""
    You are an AI assistant tasked with finding hackathons. 
    Review the following raw search results: {search_results}
    
    1. Filter out any past events.
    2. Extract the Name, Dates, Location (or Virtual), and Registration Link.
    3. Format the results as a clean, professional HTML email. Use bullet points and bold text.
    Do not include any markdown formatting like ```html. Just output raw HTML.
    """
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return response.text

def send_email(html_content):
    print("Sending the email...")
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "🤖 Your Daily Hackathon Report"
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
