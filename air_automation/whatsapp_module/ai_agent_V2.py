# version 2 that is capable to store conversion memory
# two component in ConversationBufferMemory:
    # human memeory
    #ai agent memeory
import openai
import os
import time
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import OpenAI  # Updated import

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Dictionary to store messages in memory
unread_messages_memory = {}
last_active_contact = None

# Initialize LangChain memory for conversation context
memory = ConversationBufferMemory()
last_modified_time = None  # Variable to store the last modified time of the file

# Function to load unread messages from "whatsapp_recv.txt" into memory
def load_unread_messages():
    global unread_messages_memory
    unread_messages_memory.clear()  # Clear memory before reloading

    try:
        with open("whatsapp_recv.txt", "r", encoding="utf-8") as file:
            messages = file.read().split("---------\n")
            for message in messages:
                if message.strip():  # Ensure it's not empty
                    # Parse message details
                    lines = message.strip().split("\n")
                    contact_name = lines[0].split(": ")[1]
                    received_time = lines[1].split(": ")[1]
                    unread_count = int(lines[2].split(": ")[1])
                    message_text = lines[3].split(": ", 1)[1]

                    # Store in memory
                    unread_messages_memory[contact_name] = {
                        "received_time": received_time,
                        "unread_count": unread_count,
                        "message_text": message_text,
                        "referenced": False  # Track whether message has been referenced
                    }
    except FileNotFoundError:
        print("No 'whatsapp_recv.txt' file found.")
    except Exception as e:
        print(f"Error loading messages: {e}")

# Function to monitor the file and reload messages if the file has changed
def check_and_reload_messages():
    global last_modified_time
    try:
        # Get the last modified time of the file
        current_modified_time = os.path.getmtime("whatsapp_recv.txt")
        # Check if the file has changed since last loaded
        if last_modified_time is None or current_modified_time > last_modified_time:
            load_unread_messages()
            last_modified_time = current_modified_time  # Update the last modified time
    except FileNotFoundError:
        print("No 'whatsapp_recv.txt' file found.")

# Function to create a refined prompt for the AI
def create_refined_prompt(query):
    message_summary = "\n".join([
        f"{contact} sent '{details['message_text']}' at {details['received_time']}."
        for contact, details in unread_messages_memory.items()
    ])
    
    # Enhanced prompt explaining the assistant's role and context
    refined_prompt = (
        f"You are a WhatsApp AI assistant. The user has unread messages summarized here:\n"
        f"{message_summary}\n\n"
        f"Please interpret the following query and respond accordingly. If they ask about unread messages, "
        f"provide the details. If they ask to respond, generate a direct reply. You may clarify if needed, "
        f"especially if multiple contacts are in memory.\n\nUser query: '{query}'"
    )
    return refined_prompt

# Function to interact with AI for answering queries about unread messages with memory
def ai_query_unread_messages(query):
    global last_active_contact

    # Generate the refined prompt based on the query and add memory context
    prompt = create_refined_prompt(query)

    # Save the user query as 'content' without specifying "role"
    memory.save_context({"content": query}, {"content": ""})  # Initialize with an empty output

    try:
        # Convert messages to JSON-serializable format
        # message is a datastructure to append memeory and send to the ai agent for context concious
        messages = [
            {"role": "user" if message.type == "human" else "assistant", "content": message.content}
            for message in memory.chat_memory.messages
        ]
        messages.append({"role": "user", "content": prompt})  # Add the current user query

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=messages,
            max_tokens=100
        )
        ai_response = response.choices[0].message['content'].strip()

        # Save the AI's response to memory for context in future queries
        memory.save_context({"content": query}, {"content": ai_response})
        
        # Update last active contact if a specific contact is referenced in response
        for contact in unread_messages_memory.keys():
            if contact in ai_response:
                last_active_contact = contact
                break
        
        return ai_response

    except Exception as e:
        print(f"Error with AI query: {e}")
        return "I'm here to help, but it seems there was an issue processing that request. Could you try again."

# Main AI Agent function to respond to queries
def ai_agent_interact():
    print("AI Agent ready. Type queries about unread messages or 'exit' to quit.")
    
    while True:
        check_and_reload_messages()  # Check and reload messages if file changes
        user_query = input("Your query: ").strip()
        if user_query.lower() == "exit":
            print("Exiting AI agent.")
            break
        elif user_query:  # Process non-empty queries
            answer = ai_query_unread_messages(user_query)
            print("AI Response:", answer)
        # Pause briefly to reduce excessive file checks
        time.sleep(1)

# Main execution
if __name__ == "__main__":
    ai_agent_interact()
