import openai
import os
import time
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from datetime import datetime
import re


# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Dictionary to store messages in memory
unread_messages_memory = {}
last_active_contact = None

# Initialize LangChain memory for conversation context
memory = ConversationBufferMemory()
last_modified_time = None  # Variable to store the last modified time of the file

# Define the specific assistant prompt
base_prompt = """
You are my personal WhatsApp assistant. I will provide you with unread messages in the following format:

Contact Name/Phone Number: Maaz Umt W1
Received Time: Yesterday
Unread Messages Count: 2
Message: Where are you?
---------
Contact Name/Phone Number: Sabhee Ahmad Yazdan Umt
Received Time: 10:21 pm
Unread Messages Count: 1
Message: Aoa
---------

### Instructions:
1. **Answer my questions**: I may ask about specific contacts, times, or message details (e.g., "Did XYZ send any messages?", "What time did XYZ send a message?", or "List all unread messages."). Answer accurately, concisely, and to the point. Keep track of the conversation context, especially if I’m referring to a specific contact or message, to respond appropriately. If anything is unclear, ask for clarification.

2. **Generate replies**: I might ask you to draft a reply to a contact. Compose an appropriate response and ask for my confirmation before finalizing. If I provide a specific reply, use it directly. Format your responses as follows:
---------
Contact Name/Phone Number: (eg:Sabhee Ahmad Yazdan Umt)
Sent Time: current time
Message: (your reply text)
---------

3. **Simulate message sending**: When I confirm a reply to be “sent,” provide the formatted response, followed by the exact phrase: "Message Sent Successfully to XYZ (Contact Name/Phone Number)." This is a simulation; you are not required to actually send messages on WhatsApp, just to respond with the formatted message.

4. **General Assistance**: You should also be prepared to answer any other relevant questions I may ask, beyond managing unread messages.

### Key Notes:
- Retain prior context for continuity in responses.
- Be concise, clear, and relevant in all replies.
- When confirming a "sent" message, remember that this is only an exercise, so provide only the formatted message and confirmation text as specified.

Now, I will share my unread messages with you, and you can assist accordingly.
"""

# Function to load unread messages from "whatsapp_recv.txt" into memory
def load_unread_messages():
    global unread_messages_memory
    unread_messages_memory.clear()  # Clear existing messages to reload fresh data

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
            # print("Updated unread_messages_memory:", unread_messages_memory)  # Debugging output to confirm reloading
    except FileNotFoundError:
        print("No 'whatsapp_recv.txt' file found.")
    except Exception as e:
        print(f"Error loading messages: {e}")

# Function to monitor the file and reload messages if the file has changed
def check_and_reload_messages():
    global last_modified_time
    try:
        current_modified_time = os.path.getmtime("whatsapp_recv.txt")
        # Reload only if file modification time has changed
        if last_modified_time is None or current_modified_time > last_modified_time:
            print("File updated. Reloading messages...")
            load_unread_messages()
            last_modified_time = current_modified_time
        else:
            print("No new updates detected in 'whatsapp_recv.txt'.")  # Debugging output for unchanged file
    except FileNotFoundError:
        print("No 'whatsapp_recv.txt' file found.")

# Function to build a dynamic prompt including the current unread messages
def build_dynamic_prompt():
    message_summary = "\n".join([
        f"Contact Name/Phone Number: {contact}\nReceived Time: {details['received_time']}\nUnread Messages Count: {details['unread_count']}\nMessage: {details['message_text']}\n---------"
        for contact, details in unread_messages_memory.items()
    ])
    return f"{base_prompt}\n\n### Current Unread Messages:\n{message_summary}"


# Function to interact with AI, checking for send confirmation directly in AI's response
def ai_query_unread_messages(query):
    global last_active_contact

    try:
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

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=messages,
            max_tokens=150
        )
        ai_response = response.choices[0].message['content'].strip()

        # Check if AI response contains confirmation text, then save message
        if "message sent successfully " in ai_response.lower():
            try:
                contact_line = ai_response.splitlines()[1]
                contact_name = contact_line.split(": ")[1].strip()
                save_message_to_file(contact_name, ai_response)
            except IndexError:
                print("Error: Expected response format missing. Check the AI's response structure.")

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

# Function to save the actual message content to "send_whatsapp.txt" in the specified format

def save_message_to_file(contact_name, message_content):
    # Get the current date and time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Use regex to replace any placeholder after "Sent Time: " with the current time
    formatted_message = re.sub(r"(Sent Time:).+", f"\\1 {current_time}", message_content)
    
    # Extract the actual message without the confirmation line
    formatted_message = "\n".join(formatted_message.splitlines()[:-1])
    
    with open("send_whatsapp.txt", "a") as file:
        file.write(formatted_message + "\n")
    print("Message saved to send_whatsapp.txt.")

# Main AI Agent function for user interaction
def ai_agent_interact():
    print("AI Agent ready. Type queries about unread messages or 'exit' to quit.")
    
    while True:
        check_and_reload_messages()  # Always check and reload messages in the loop
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
