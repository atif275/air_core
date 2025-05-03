import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch email and app password from .env
sender_email = os.getenv("EMAIL")
app_password = os.getenv("APP_PASSWORD")

def send_email(recipient_email, subject, body, attachments=None):
    # Create a multipart message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = subject

    # Add body to email
    message.attach(MIMEText(body, "plain"))

    # Process attachments if any
    if attachments:
        for attachment_path in attachments:
            try:
                with open(attachment_path, "rb") as attachment:
                    # Get the file name from path
                    filename = os.path.basename(attachment_path)
                    
                    # Determine the content type based on file extension
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                        # Handle images
                        img_data = attachment.read()
                        image = MIMEImage(img_data, name=filename)
                        message.attach(image)
                    else:
                        # Handle other file types
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                        
                        # Encode the attachment
                        encoders.encode_base64(part)
                        
                        # Add header
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {filename}",
                        )
                        message.attach(part)
                        
            except Exception as e:
                print(f"Error processing attachment {attachment_path}: {e}")
                continue

    # Set up the SSL context for a secure connection
    context = ssl.create_default_context()

    # Connect to Gmail's SMTP server and send the email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, app_password)
            server.send_message(message)
        print("\033[92mEmail sent successfully!\033[0m")
    except Exception as e:
        print(f"Error: {e}")
