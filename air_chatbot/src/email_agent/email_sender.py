import smtplib
import ssl
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch email and app password from .env
sender_email = os.getenv("EMAIL")
app_password = os.getenv("APP_PASSWORD")

# Function to send email
def send_email(recipient_email, subject, body):
    # Combine subject and body into a message
    message = f"Subject: {subject}\n\n{body}"

    # Set up the SSL context for a secure connection
    context = ssl.create_default_context()

    # Connect to Gmail's SMTP server and send the email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, message)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")
