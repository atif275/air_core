import openai
import os
import time
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import OpenAI
from datetime import datetime

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Dictionary to store messages in memory
unread_messages_memory = {}
last_active_contact = None
confirmation_pending = False  # Track whether a send confirmation is pending
confirmed_message = None  # Store the confirmed message for saving

# Initialize LangChain memory for conversation context
memory = ConversationBufferMemory()
last_modified_time = None  # Variable to store the last modified time of the file

# Function to load unread messages from "whatsapp_recv.txt" into memory
def load_unread_messages():
    global unread_messages_memory
    unread_messages_memory.clear()

    try:
        with open("whatsapp_recv.txt", "r", encoding="utf-8") as file:
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
        print("No 'whatsapp_recv.txt' file found.")
    except Exception as e:
        print(f"Error loading messages: {e}")

# Function to monitor the file and reload messages if the file has changed
def check_and_reload_messages():
    global last_modified_time
    try:
        current_modified_time = os.path.getmtime("whatsapp_recv.txt")
        if last_modified_time is None or current_modified_time > last_modified_time:
            load_unread_messages()
            last_modified_time = current_modified_time
    except FileNotFoundError:
        print("No 'whatsapp_recv.txt' file found.")

# Function to create a refined prompt for the AI, with send functionality
def create_refined_prompt(query):
    if confirmation_pending:
        return "Please confirm if you would like to proceed with sending this message."

    # Prompt includes formatted structure for the AI response
    message_summary = "\n".join([
        f"{contact} sent: '{details['message_text']}' at {details['received_time']}."
        for contact, details in unread_messages_memory.items()
    ])
    
    refined_prompt = (
        f"As a WhatsApp AI assistant, here is a summary of unread messages:\n"
        f"{message_summary}\n\n"
        f"Please interpret the user's query and respond accurately. For queries about unread messages, provide a detailed list. "
        f"For requests to reply, craft a direct response for the user. If any clarification is needed—such as confirming a contact when multiple are involved—please ask.\n\n"
        f"Additionally, when the user requests to send a message, generate the message in the following structured format (not to be sent directly):\n"
        f"----------\n"
        f"Contact Name/Phone Number: (e.g., Maaz Umt W1)\n"
        f"Sent Time: (current time, dynamically set)\n"
        f"Message: (AI-generated message confirmed by the user)\n"
        f"----------\n\n"
        f"When the user confirms, echo back the contact’s name or the last 4 digits of their phone number for verification.\n\n"
        f"User query: '{query}'"
    )
    
    return refined_prompt

# Function to interact with AI for answering queries about unread messages with memory and send functionality
def ai_query_unread_messages(query):
    global last_active_contact, confirmation_pending, confirmed_message

    # Directly handle confirmation mode without further AI processing
    if confirmation_pending:
        if query.lower() in ["yes", "confirm", "confirmed"]:
            # Ensure contact and message are defined before saving
            if last_active_contact and confirmed_message:
                # Save the confirmed message and reset confirmation flags
                save_message_to_file(last_active_contact, confirmed_message)
                confirmation_pending = False
                confirmed_message = None
                return f"Message sent to {last_active_contact} successfully."
            else:
                confirmation_pending = False
                return "Unable to send message: contact name or message format is missing."

        elif query.lower() in ["no", "cancel"]:
            confirmation_pending = False
            confirmed_message = None
            return "Message sending canceled."

        else:
            return "Please respond with 'yes' to confirm, or 'no' to cancel."

    # Generate a general response if not in confirmation mode
    prompt = create_refined_prompt(query)

    try:
        # Use AI to interpret the query if no confirmation mode is active
        messages = [
            {"role": "user" if message.type == "human" else "assistant", "content": message.content}
            for message in memory.chat_memory.messages
        ]
        messages.append({"role": "user", "content": prompt})

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=messages,
            max_tokens=100
        )
        ai_response = response.choices[0].message['content'].strip()

        # Check if AI response indicates a "send" intent, then enter confirmation mode
        if "send" in query.lower() or "confirm send" in ai_response.lower():
            confirmation_pending = True
            confirmed_message = ai_response  # Store the formatted message
            if last_active_contact:
                # If contact is known, confirm sending
                return f"Are you sure you want to send this message to {last_active_contact}? (yes/no):"
            else:
                # If contact is unknown, ask for the contact name before confirming
                contact_name = input("Specify the contact name or number: ")
                last_active_contact = contact_name
                return f"Are you sure you want to send this message to {last_active_contact}? (yes/no):"

        # Update memory and last active contact context
        memory.save_context({"content": query}, {"content": ai_response})
        for contact in unread_messages_memory.keys():
            if contact in ai_response:
                last_active_contact = contact
                break

        return ai_response

    except Exception as e:
        print(f"Error with AI query: {e}")
        return "I'm here to help, but it seems there was an issue processing that request. Could you try again."

# Function to save only the actual message content to a file in the specified format
def save_message_to_file(contact_name, message_content):
    # Extract the actual message content without the AI's additional instructions
    actual_message = extract_actual_message(message_content)
    with open("send_whatsapp.txt", "a") as file:
        file.write("----------\n")
        file.write(f"Contact Name/Phone Number: {contact_name}\n")
        file.write(f"Sent Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        file.write(f"Message: {actual_message}\n")
        file.write("----------\n")
    print("Message saved to send_whatsapp.txt.")

# Helper function to extract the actual message content from AI response
def extract_actual_message(ai_response):
    # Assume message starts after "Message:" line in formatted response
    start_idx = ai_response.find("Message:") + len("Message:")
    return ai_response[start_idx:].strip() if start_idx > 0 else ai_response.strip()

# Main AI Agent function to respond to queries
def ai_agent_interact():
    print("AI Agent ready. Type queries about unread messages or 'exit' to quit.")
    
    while True:
        check_and_reload_messages()
        user_query = input("Your query: ").strip()
        if user_query.lower() == "exit":
            print("Exiting AI agent.")
            break
        elif user_query:
            answer = ai_query_unread_messages(user_query)
            print("AI Response:", answer)
        time.sleep(1)

# Main execution
if __name__ == "__main__":
    ai_agent_interact()
