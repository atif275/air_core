"""Email chatbot module for handling email-related queries."""
import os
import time
import asyncio
import faiss
import numpy as np
from dotenv import load_dotenv
from openai import AsyncOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import OpenAI
from sentence_transformers import SentenceTransformer

# Handle imports differently when run as main vs imported
if __name__ == "__main__":
    from email_sender import send_email
else:
    from email_sender import send_email

# Load environment variables
load_dotenv()
# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize LangChain memory for conversation context and vector model
memory = ConversationBufferMemory(return_messages=True)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize FAISS index for vector storage
d = 384  # Dimension for 'all-MiniLM-L6-v2' embeddings
index = faiss.IndexFlatL2(d)
email_data = []

# Track the last email draft
last_email_draft = None

# System prompt to guide the chatbot's tone and structure
system_prompt = (
    "You are an AI email assistant named EmailBot. Your tone should be friendly, helpful, and professional.\n\n"
    "Guidelines:\n"
    "1. For new email requests:\n"
    "   - NEVER create an email without getting ALL required information first\n"
    "   - NEVER make assumptions about any details, especially recipients\n"
    "   - NEVER use any placeholders, brackets, or template text\n"
    "   - NEVER use [Your Name], [Name], or any other placeholder text\n"
    "   - NEVER create an email with just 'Hi' and 'How are you?'\n"
    "   - If user says 'write an email' without details:\n"
    "     * First ask: 'Who would you like to send the email to?'\n"
    "     * Then ask: 'What would you like to write about?'\n"
    "   - If user provides multiple pieces of information at once, extract and use them\n"
    "   - If any information is missing, ask for it in a natural way\n"
    "   - Keep track of what information you have and what you still need\n"
    "   - Write complete, ready-to-send emails without any placeholders\n"
    "   - NEVER assume recipient names or email addresses\n"
    "   - NEVER add decorative elements like '---' or other separators\n"
    "   - ALWAYS end emails with 'Maaz Asghar' without any brackets or placeholders\n"
    "   - NEVER use redundant closings like 'Best regards,' before the signature\n"
    "   - NEVER use multiple signature lines\n"
    "   - NEVER use any kind of placeholder text in ANY part of the email\n"
    "   - NEVER use template text or placeholders in ANY part of the email\n\n"
    "2. For unread emails, follow this structure:\n"
    "   name: <name>, email: <email>, subject: <subject>, body: <body>\n\n"
    "3. For email responses, follow this structure:\n"
    "   recipient: <recipient's email address>\n"
    "   subject: <appropriate subject>\n"
    "   body: <appropriate body text>\n\n"
    "   Always end emails with the name: Maaz Asghar\n\n"
    "4. For email confirmations and modifications:\n"
    "   - If user confirms (yes/send), send the email\n"
    "   - If user declines or gives negative feedback:\n"
    "     * Ask: 'What would you like to change in the email?'\n"
    "     * Wait for specific feedback before making changes\n"
    "     * NEVER include user's feedback in the email body\n"
    "     * NEVER modify the email without clear instructions\n"
    "   - If user wants changes, ask what needs to be modified\n"
    "   - NEVER include user's feedback or comments in the email\n\n"
    "5. Important formatting rules:\n"
    "   - Strictly avoid adding any extra symbols or formatting before or after 'recipient:', 'subject:', or 'body:'\n"
    "   - Keep responses conversational and natural\n"
    "   - Ask clarifying questions when needed\n"
    "   - NEVER use placeholder text or brackets in the email content\n"
    "   - NEVER add decorative elements or separators\n"
    "   - NEVER use template text or placeholders\n"
    "   - NEVER use redundant closings or multiple signature lines\n"
    "   - NEVER include user's feedback or comments in the email\n"
    "   - NEVER use any kind of placeholder text in ANY part of the email\n"
    "   - NEVER use template text or placeholders in ANY part of the email\n\n"
    "6. For general queries:\n"
    "   - Respond in a helpful, conversational manner\n"
    "   - Provide clear, concise information\n"
    "   - Ask follow-up questions if more information is needed"
)

# Function to embed and store email data in vector database
def add_email_to_vector_db(sender, subject, body):
    email_summary = f"From: {sender}, Subject: {subject}, Snippet: {body[:100]}..."
    vector = model.encode([email_summary])[0]
    index.add(np.array([vector]))
    email_data.append({"sender": sender, "subject": subject, "body": body, "vector": vector})

# Function to load emails from "emails.txt" and add them to the vector database
def load_emails_to_vector_db():
    global email_data
    email_data.clear()
    index.reset()

    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    emails_file = os.path.join(script_dir, "emails.txt")

    try:
        with open(emails_file, "r", encoding="utf-8") as file:
            emails = file.read().split("----- New Email -----")
            for email_entry in emails:
                if email_entry.strip():
                    lines = email_entry.strip().split("\n")
                    sender = lines[0].split(": ")[1]
                    subject = lines[1].split(": ")[1]
                    body = "\n".join(lines[2:])
                    add_email_to_vector_db(sender, subject, body)
        print(f"Loaded emails from: {emails_file}")
    except FileNotFoundError:
        print(f"No 'emails.txt' file found at: {emails_file}")
        # Create an empty file if it doesn't exist
        with open(emails_file, "w", encoding="utf-8") as f:
            pass
        print(f"Created empty emails.txt file at: {emails_file}")
    except Exception as e:
        print(f"Error loading emails: {e}")

# Function to find relevant emails from vector database based on query
def query_vector_db(query, k=5):
    if not email_data:  # If no emails exist
        return []
        
    query_vector = model.encode([query])[0]
    # Only search for as many emails as we actually have
    k = min(k, len(email_data))
    distances, indices = index.search(np.array([query_vector]), k)
    # Only return unique emails
    seen = set()
    unique_emails = []
    for i in indices[0]:
        if i < len(email_data):
            email = email_data[i]
            email_key = (email['sender'], email['subject'], email['body'])
            if email_key not in seen:
                seen.add(email_key)
                unique_emails.append(email)
    return unique_emails

async def ai_query_with_email_context(query):
    global last_email_draft
    memory.save_context({"content": query}, {"content": ""})

    try:
        # Check if this is a confirmation response
        if last_email_draft:
            # Use OpenAI to determine the user's intent
            intent_prompt = (
                f"User response: '{query}'\n\n"
                "Determine the user's intent. Choose exactly one of these options:\n"
                "1. 'confirm' - if they want to send the email (yes, sure, go ahead, etc.)\n"
                "2. 'modify' - if they want to change something (make shorter, change subject, etc.)\n"
                "3. 'cancel' - if they want to cancel the email (no, don't send, cancel, etc.)\n"
                "Respond with exactly one word: 'confirm', 'modify', or 'cancel'."
            )
            
            intent_response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": intent_prompt}],
                max_tokens=10
            )
            
            intent = intent_response.choices[0].message.content.strip().lower()
            
            if intent == "confirm":
                # Extract email details from the draft
                recipient = last_email_draft.split("recipient: ")[1].split("\n")[0].strip()
                subject = last_email_draft.split("subject: ")[1].split("\n")[0].strip()
                body_start_index = last_email_draft.find("body:") + len("body:")
                body = last_email_draft[body_start_index:].strip()
                
                # Send the email
                send_email(recipient, subject, body)
                response = "Email sent successfully!"
                last_email_draft = None  # Clear the draft
                return response
            elif intent == "modify":
                # Generate a modified version of the email
                modification_prompt = (
                    f"Original email draft:\n{last_email_draft}\n\n"
                    f"User's modification request: '{query}'\n\n"
                    "Generate a modified version of the email following the same structure:\n"
                    "recipient: <email>\nsubject: <subject>\nbody: <body>\n\n"
                    "End with 'Maaz Asghar'"
                )
                
                modified_response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": modification_prompt}],
                    max_tokens=200
                )
                
                last_email_draft = modified_response.choices[0].message.content.strip()
                return f"{last_email_draft}\n\nWould you like to send this email?"
            else:  # cancel
                response = "Email draft cancelled."
                last_email_draft = None  # Clear the draft
                return response

        relevant_emails = query_vector_db(query)
        if relevant_emails:
            email_context = "\n".join([
                f"name: {email['sender']}, email: <{email['sender']}>, "
                f"subject: {email['subject']}, body: {email['body']}"
                for email in relevant_emails
            ])
        else:
            email_context = "No related emails found in memory."

        if "respond to" in query.lower():
            recipient_email = relevant_emails[0]["sender"] if relevant_emails else None
            if recipient_email:
                prompt = (
                    f"You are an email assistant. The user wants to respond to an email from {recipient_email}.\n"
                    f"Generate a professional and contextually relevant subject and body for this email, "
                    f"following this structure:\n\n"
                    f"recipient: {recipient_email}\nsubject: <appropriate subject>\n"
                    f"body: <appropriate body text>\n\nEnd with 'Maaz Asghar'."
                )
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200
                )
                ai_response = response.choices[0].message.content.strip()
                last_email_draft = ai_response  # Store the draft
                return f"{ai_response}\n\nWould you like to send this email?"
            else:
                return "No suitable email found to respond to."

        prompt = (
            f"User query: '{query}'\n\n"
            f"Relevant email information:\n{email_context}\n\n"
            f"Provide a response based on the user's query and email context above."
        )

        messages = [{"role": "system", "content": system_prompt}]

        messages.extend(
            {"role": "user" if message.type == "human" else "assistant", "content": message.content}
            for message in memory.chat_memory.messages
        )

        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200
        )
        ai_response = response.choices[0].message.content.strip()
        
        # If the response contains email fields, store it as a draft and ask for confirmation
        if all(field in ai_response.lower() for field in ["recipient:", "subject:", "body:"]):
            last_email_draft = ai_response
            ai_response = f"{ai_response}\n\nWould you like to send this email?"
        
        memory.save_context({"content": query}, {"content": ai_response})
        return ai_response

    except Exception as e:
        print(f"Error with AI query: {e}")
        return "I'm here to help, but it seems there was an issue processing that request. Could you try again."

def email_bot(message: str = "", **kwargs) -> str:
    """
    Process email-related queries from the main chatbot.
    
    Args:
        message: The user's query about emails
        **kwargs: Additional context from the chatbot
        
    Returns:
        str: Response to the user's query
    """
    # Initialize on first run or reload emails
    load_emails_to_vector_db()
    
    # Process the query and return the response
    try:
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(ai_query_with_email_context(message))
        loop.close()
        
        return response
        
    except Exception as e:
        print(f"Error in email_bot: {str(e)}")
        return "I had trouble processing your email request. Please try again."

# Main execution - only used when running directly
if __name__ == "__main__":
    print("Email chatbot loaded and running continuously.")
    print("Initialize email system...")
    load_emails_to_vector_db()
    
    # Start the email monitor in a separate process
    import subprocess
    import sys
    from pathlib import Path

    # Get the directory of the current script
    current_dir = Path(__file__).parent
    monitor_script = current_dir / "email_monitor.py"
    
    # Start email monitor in a separate process
    try:
        monitor_process = subprocess.Popen([sys.executable, str(monitor_script)], 
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        print("Email monitor started in background")
    except Exception as e:
        print(f"Warning: Could not start email monitor: {e}")

    # Main chatbot loop
    while True:
        try:
            # Check for new emails every minute
            load_emails_to_vector_db()
            time.sleep(60)  # Wait for 60 seconds before checking again
        except KeyboardInterrupt:
            print("\nStopping email system...")
            if 'monitor_process' in locals():
                monitor_process.terminate()
                print("Email monitor stopped")
            break
        except Exception as e:
            print(f"Error in email system: {str(e)}")
            time.sleep(60)  # Wait before retrying
