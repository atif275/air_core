import imaplib
import email
from email.header import decode_header
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch email and app password from .env
username = os.getenv("EMAIL")
app_password = os.getenv("APP_PASSWORD")

# Connect to Gmail's IMAP server
mail = imaplib.IMAP4_SSL("imap.gmail.com")

# Login to the account
mail.login(username, app_password)

# Function to fetch and save new emails in a single file
def check_new_emails():
    # Select the mailbox you want to monitor (inbox)
    mail.select("inbox")

    # Search for all unseen (new) emails
    status, messages = mail.search(None, "UNSEEN")

    # Get the list of email IDs of new emails
    email_ids = messages[0].split()

    # Process each new email
    for email_id in email_ids:
        try:
            # Fetch the email by ID
            status, msg_data = mail.fetch(email_id, "(RFC822)")

            # Extract the email message
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    # Parse the email content
                    msg = email.message_from_bytes(response_part[1])

                    # Decode email subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    subject = subject.strip()  # Strip whitespace from subject

                    # Decode sender's email
                    from_ = msg.get("From").strip()  # Strip whitespace from sender's email

                    # Initialize the email body
                    body = ""

                    # If the email message is multipart
                    if msg.is_multipart():
                        # Walk through each part of the email
                        for part in msg.walk():
                            # If part is text/plain or text/html
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))

                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    # Decode and strip the body content
                                    body = part.get_payload(decode=True).decode().strip()

                                    # Remove excessive blank lines
                                    body = "\n".join([line for line in body.splitlines() if line.strip()])
                                except Exception as e:
                                    print(f"Error decoding body: {e}")
                                    body = "(Error decoding body)"
                    else:
                        # If the message is not multipart, the payload is the body
                        try:
                            # Decode and strip the body content
                            body = msg.get_payload(decode=True).decode().strip()

                            # Remove excessive blank lines
                            body = "\n".join([line for line in body.splitlines() if line.strip()])
                        except Exception as e:
                            print(f"Error decoding body: {e}")
                            body = "(Error decoding body)"


                    # Append email details to emails.txt in UTF-8
                    with open("emails.txt", "a", encoding="utf-8") as f:
                        f.write("----- New Email -----\n")
                        f.write(f"From: {from_}\n")
                        f.write(f"Subject: {subject}\n")
                        f.write("Body:\n")
                        f.write(body)
                        f.write("\n\n")  # Add some spacing between emails

                    print("New email appended to emails.txt")

        except Exception as e:
            print(f"Error processing email ID {email_id.decode()}: {e}")

# Monitor for new emails every 60 seconds
try:
    while True:
        check_new_emails()
        time.sleep(60)  # Wait for 60 seconds before checking again
except KeyboardInterrupt:
    print("Monitoring stopped.")
finally:
    mail.logout()