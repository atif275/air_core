import openai
from openai import OpenAI
import os
import time
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from datetime import datetime
import re
import warnings

# Suppress LangChain Deprecation Warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Load environment variables
load_dotenv()
# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get the absolute path to the whatsapp_module directory
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
WHATSAPP_RECV_PATH = os.path.join(MODULE_DIR, "whatsapp_recv.txt")
WHATSAPP_SEND_PATH = os.path.join(MODULE_DIR, "send_whatsapp.txt")
CONTACTS_PATH = os.path.join(MODULE_DIR, "contacts.txt")

# Dictionary to store messages in memory
unread_messages_memory = {}
last_active_contact = None
contacts_list = []  # Store the list of contacts
contacts_last_modified = None  # Track last modified time of contacts.txt

# Initialize LangChain memory for conversation context
memory = ConversationBufferMemory()
last_modified_time = None  # Variable to store the last modified time of the file

# Base prompt without unread messages (we'll add them dynamically)
base_prompt = """
You are my personal WhatsApp assistant. I will provide you with unread messages in the following format:

Contact Name/Phone Number: [Contact Name]
Received Time: [Time]
Unread Messages Count: [Count]
Message: [Message Content]
---------

### Instructions:
1. **Answer my questions**: I may ask about specific contacts, times, or message details. Answer accurately, concisely, and to the point. Keep track of the conversation context, especially if I'm referring to a specific contact or message. If anything is unclear, ask for clarification.

2. **Generate replies**: I might ask you to draft a reply to a contact. Compose an appropriate response and ask for my confirmation before finalizing. If I provide a specific reply, use it directly. Format your responses as follows:
---------
Contact Name/Phone Number: [Contact Name]
Sent Time: current time
Message: [your reply text]
---------

3. **Simulate message sending**: When I confirm a reply to be "sent," provide the formatted response, followed by the exact phrase: "Message Sent Successfully to XYZ (Contact Name/Phone Number)."

4. **Message Type Understanding**: 
   - If a message starts with "Voice Message", it's a voice message
   - If a message starts with "Audio", it's an audio file
   - If a message is "Photo", it's an image
   - If a message is "Video", it's a video file
   - If a message is "Sticker", it's a sticker
   - If a message is "GIF", it's a GIF
   - If a message starts with 'File "', it's a document
   - If a message is "Location", it's a location share
   - If a message starts with 'Poll "', it's a poll
   - If a message starts with 'Contact Sharing "', it's a contact card
   - If a message starts with 'Event "', it's an event invitation
   - If a message is "Missed voice call" or "Missed video call", it's a missed call
   - Any other message is considered a text message

5. **Message Display**: When showing messages to the user:
   - For media messages (voice, audio, photo, video, etc.), show: "You received a [message type] from [contact]"
   - For text messages, show the actual message content
   - For missed calls, show: "You missed a [call type] from [contact]"

6. **Contact Name Handling**:
   - When a user mentions a partial contact name (e.g., "sabhee"), use the full contact name from contacts.txt
   - If multiple contacts match the partial name, ask the user to specify which contact they mean
   - Always use the exact full contact name from contacts.txt in the response
   - When asked about contacts, list all available contacts from the contacts list
   - When asked about a specific contact, check if they exist in the contacts list and provide information accordingly

Now, I will share my unread messages and contacts list with you, and you can assist accordingly.
"""

# Function to load unread messages from "whatsapp_recv.txt" into memory
def load_unread_messages():
    global unread_messages_memory
    unread_messages_memory.clear()  # Clear existing messages to reload fresh data

    try:
        with open(WHATSAPP_RECV_PATH, "r", encoding="utf-8") as file:
            messages = file.read().split("---------\n")
            for message in messages:
                if message.strip():
                    lines = message.strip().split("\n")
                    contact_name = lines[0].split(": ")[1]
                    received_time = lines[1].split(": ")[1]
                    unread_count = int(lines[2].split(": ")[1])
                    message_text = lines[3].split(": ", 1)[1]
                    unread_messages_memory[contact_name] = {
                        "received_time": received_time,
                        "unread_count": unread_count,
                        "message_text": message_text,
                        "referenced": False
                    }
    except FileNotFoundError:
        print(f"No '{WHATSAPP_RECV_PATH}' file found.")
    except Exception as e:
        print(f"Error loading messages: {e}")

# Function to monitor the file and reload messages if the file has changed
def check_and_reload_messages():
    global last_modified_time
    try:
        current_modified_time = os.path.getmtime(WHATSAPP_RECV_PATH)
        # Reload only if file modification time has changed
        if last_modified_time is None or current_modified_time > last_modified_time:
            print("File updated. Reloading messages...")
            load_unread_messages()
            last_modified_time = current_modified_time
            return True  # Return True if messages were reloaded
        else:
            print("No new updates detected in 'whatsapp_recv.txt'.")
            return False  # Return False if no updates
    except FileNotFoundError:
        print(f"No '{WHATSAPP_RECV_PATH}' file found.")
        return False

# Function to build a dynamic prompt including the current unread messages and contacts
def build_dynamic_prompt():
    # Build the contacts section
    contacts_section = "\n### Current Contacts List:\n"
    if contacts_list:
        contacts_section += "\n".join([f"- {contact}" for contact in contacts_list])
    else:
        contacts_section += "No contacts available at the moment."
    
    # Build the messages section
    if not unread_messages_memory:
        messages_section = "\n### Current Unread Messages:\nNo unread messages at the moment."
    else:
        message_summary = "\n".join([
            f"Contact Name/Phone Number: {contact}\nReceived Time: {details['received_time']}\nUnread Messages Count: {details['unread_count']}\nMessage: {details['message_text']}\n---------"
            for contact, details in unread_messages_memory.items()
        ])
        messages_section = f"\n### Current Unread Messages:\n{message_summary}"
    
    # Add conversation context
    context_section = "\n### Conversation Context:\n"
    if last_active_contact:
        context_section += f"Last active contact: {last_active_contact}\n"
    
    return f"{base_prompt}\n{contacts_section}\n{messages_section}\n{context_section}"

# Function to detect message type
def detect_message_type(message_text):
    if message_text.startswith("Voice Message"):
        return "voice message"
    elif message_text == "Audio":
        return "audio file"
    elif message_text == "Photo":
        return "photo"
    elif message_text == "Video":
        return "video"
    elif message_text == "Sticker":
        return "sticker"
    elif message_text == "GIF":
        return "GIF"
    elif message_text.startswith('File "'):
        return "document"
    elif message_text == "Location":
        return "location"
    elif message_text.startswith('Poll "'):
        return "poll"
    elif message_text.startswith('Contact Sharing "'):
        return "contact card"
    elif message_text.startswith('Event "'):
        return "event invitation"
    elif message_text in ["Missed voice call", "Missed video call"]:
        return "missed call"
    else:
        return "text message"

# Function to format message for display
def format_message_for_display(contact, message_text):
    message_type = detect_message_type(message_text)
    
    if message_type == "text message":
        return f"From {contact}: {message_text}"
    elif message_type == "missed call":
        call_type = "voice" if "voice" in message_text else "video"
        return f"You missed a {call_type} call from {contact}"
    else:
        return f"You received a {message_type} from {contact}"

# Function to load contacts from contacts.txt
def load_contacts():
    global contacts_list, contacts_last_modified
    try:
        current_modified_time = os.path.getmtime(CONTACTS_PATH)
        
        # Only reload if the file has been modified
        if contacts_last_modified is None or current_modified_time > contacts_last_modified:
            with open(CONTACTS_PATH, "r", encoding="utf-8") as file:
                content = file.read().split("---------\n")
                contacts_list = [contact.strip() for contact in content if contact.strip()]
            contacts_last_modified = current_modified_time
            print(f"Loaded {len(contacts_list)} contacts from contacts.txt")
    except FileNotFoundError:
        print(f"No '{CONTACTS_PATH}' file found.")
        contacts_list = []
        contacts_last_modified = None
    except Exception as e:
        print(f"Error loading contacts: {e}")
        contacts_list = []
        contacts_last_modified = None

# Function to find matching contacts
def find_matching_contacts(query_name):
    query_name = query_name.lower()
    matches = []
    for contact in contacts_list:
        if query_name in contact.lower():
            matches.append(contact)
    return matches

# Function to handle contact disambiguation
def handle_contact_disambiguation(matches, query):
    if len(matches) == 0:
        return None, "No matching contacts found."
    elif len(matches) == 1:
        return matches[0], None
    else:
        # Ask user to choose from multiple matches
        response = f"I found multiple contacts matching '{query}':\n"
        for i, contact in enumerate(matches, 1):
            response += f"{i}. {contact}\n"
        response += "Please specify which contact you want to send the message to by number or name."
        return None, response

# Function to interact with AI, checking for send confirmation directly in AI's response
def ai_query_unread_messages(query):
    global last_active_contact

    try:
        # Check for contacts.txt updates before processing the query
        load_contacts()
        
        # Check if this is a message sending request
        if "send" in query.lower() or "reply" in query.lower() or "text" in query.lower():
            # Extract the contact name from the query
            contact_match = re.search(r"(?:send|reply|text).*to\s+(\w+)", query.lower())
            if contact_match:
                contact_query = contact_match.group(1)
                # Check if the query is a phone number
                if re.match(r'^\+?[\d\s-]+$', contact_query):
                    # If it's a phone number, use it directly
                    selected_contact = contact_query
                else:
                    # Otherwise, try to find matching contacts
                    matches = find_matching_contacts(contact_query)
                    selected_contact, disambiguation_message = handle_contact_disambiguation(matches, contact_query)
                    
                    if disambiguation_message:
                        return disambiguation_message
                
                # Replace the contact name in the query with the full contact name
                query = query.replace(contact_query, selected_contact)
                last_active_contact = selected_contact

        # Build the dynamic prompt with current unread messages
        dynamic_prompt = build_dynamic_prompt()

        # Manually build the messages list for context
        messages = [{"role": "system", "content": dynamic_prompt}]
        for message in memory.chat_memory.messages:
            messages.append({
                "role": "user" if message.type == "human" else "assistant",
                "content": message.content
            })
        messages.append({"role": "user", "content": query})

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150
        )
        ai_response = response.choices[0].message.content.strip()

        # Check if AI response contains confirmation text (case-insensitive)
        if "message sent successfully to" in ai_response.lower():
            # Extract the message content from the response
            contact_match = re.search(r"Contact Name/Phone Number:\s*(.+)", ai_response)
            message_match = re.search(r"Message:\s*(.+)", ai_response)
            
            if contact_match and message_match:
                contact = contact_match.group(1)
                message = message_match.group(1)
                # Format the message properly
                formatted_message = (
                    f"Contact Name/Phone Number: {contact}\n"
                    f"Sent Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Message: {message}\n"
                )
                # Save to file
                with open(WHATSAPP_SEND_PATH, "a") as file:
                    file.write("---------\n")
                    file.write(formatted_message)
                    file.write("---------\n")
                print("Message saved to send_whatsapp.txt in the correct format.")
            else:
                print("Error: Could not find all required fields in the message content.")
                return ai_response

        # Update memory and track context for last active contact
        memory.save_context({"content": query}, {"content": ai_response})
        for contact in unread_messages_memory.keys():
            if contact in ai_response:
                last_active_contact = contact
                break

        return ai_response

    except Exception as e:
        print(f"Error with AI query: {e}")
        return "I'm here to help, but there was an issue processing that request. Could you try again."

# Main AI Agent function for user interaction
def whatsapp_bot(user_query: str = "", **kwargs) -> str:
    """
    Process WhatsApp related queries from the main chatbot.
    
    Args:
        user_query: The user's query about WhatsApp messages
        **kwargs: Additional context from the chatbot
        
    Returns:
        str: Response to the user's query
    """
    # Initialize on first run
    if not memory.chat_memory.messages:
        load_unread_messages()
        load_contacts()  # Load contacts on first run
    
    # Check for new messages and contact updates
    messages_updated = check_and_reload_messages()
    load_contacts()  # Check for contact updates
    
    # If messages were updated, force a reload of the context
    #if messages_updated:
        # Clear the conversation memory to ensure fresh context
        #memory.clear()
    
    # Process the query and return the response
    return ai_query_unread_messages(user_query)

# Main execution (only for standalone testing)
if __name__ == "__main__":
    # Load contacts on startup
    load_contacts()
    
    while True:
        user_input = input("Your query (or 'exit' to quit): ").strip()
        if user_input.lower() == "exit":
            print("Exiting AI agent.")
            break
        response = whatsapp_bot(user_input)
        print("AI Response:", response)
