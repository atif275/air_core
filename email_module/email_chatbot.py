import openai
import os
import time
import asyncio
import faiss
import numpy as np
from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import OpenAI
from sentence_transformers import SentenceTransformer
from email_sender import send_email  # Make sure send_email function is correctly imported

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
os.environ["TOKENIZERS_PARALLELISM"] = "false"
# Initialize LangChain memory for conversation context and vector model
memory = ConversationBufferMemory(return_messages=True)
model = SentenceTransformer('all-MiniLM-L6-v2')  # Model for embedding

# Initialize FAISS index for vector storage
d = 384  # Dimension for 'all-MiniLM-L6-v2' embeddings
index = faiss.IndexFlatL2(d)
email_data = []  # To store email details along with vector embeddings

# System prompt to guide the chatbot's tone and structure
system_prompt = (
    "You are an AI email assistant named EmailBot. Your tone should always be professional, "
    "concise, and respectful.\n\n"
    "Guidelines:\n"
    "- If the user asks about unread emails, follow this output structure:\n"
    "  name: <name>, email: <email>, subject: <subject>, body: <body>\n\n"
    "- If the user requests to respond to a specific email or user, follow this structure:\n"
    "  recipient: <recipient's email address>\n"
    "  subject: <appropriate subject>\n"
    "  body: <appropriate body text>\n\n"
    "  Always end emails with the name: Maaz Asghar.\n\n"
    "- Strictly avoid adding any extra symbols or formatting (such as '*', '-', or other characters) before or "
    "after 'recipient:', 'subject:', or 'body:' as this will affect data retrieval.\n\n"
    "- For all other general queries, respond concisely and professionally based on the question."
)

# Function to embed and store email data in vector database
def add_email_to_vector_db(sender, subject, body):
    email_summary = f"From: {sender}, Subject: {subject}, Snippet: {body[:100]}..."
    vector = model.encode([email_summary])[0]
    index.add(np.array([vector]))  # Add vector to FAISS index
    email_data.append({"sender": sender, "subject": subject, "body": body, "vector": vector})

# Function to load emails from "emails.txt" and add them to the vector database
def load_emails_to_vector_db():
    global email_data  # Ensure we are using the global email_data list
    email_data.clear()
    index.reset()  # Clear FAISS index

    try:
        with open("emails.txt", "r", encoding="utf-8") as file:
            emails = file.read().split("----- New Email -----")
            for email_entry in emails:  # Renamed variable to avoid conflict
                if email_entry.strip():
                    lines = email_entry.strip().split("\n")
                    sender = lines[0].split(": ")[1]
                    subject = lines[1].split(": ")[1]
                    body = "\n".join(lines[2:])
                    add_email_to_vector_db(sender, subject, body)  # Add to vector DB
    except FileNotFoundError:
        print("No 'emails.txt' file found.")
    except Exception as e:
        print(f"Error loading emails: {e}")

# Function to find relevant emails from vector database based on query
def query_vector_db(query, k=5):
    query_vector = model.encode([query])[0]
    distances, indices = index.search(np.array([query_vector]), k)
    
    # Filter out -1 and ensure uniqueness
    unique_indices = list(set(i for i in indices[0] if i >= 0))
    relevant_emails = [email_data[i] for i in unique_indices if i < len(email_data)]
    
    return relevant_emails

# Asynchronous function to process AI queries with email context
async def ai_query_with_email_context(query):
    memory.save_context({"content": query}, {"content": ""})  # Save query to memory

    try:
        # Retrieve relevant emails from vector DB
        relevant_emails = query_vector_db(query)
        if relevant_emails:
            email_context = "\n".join([
                f"name: {email['sender']}, email: <{email['sender']}>, "
                f"subject: {email['subject']}, body: {email['body']}"
                for email in relevant_emails
            ])
        else:
            email_context = "No related emails found in memory."

        # Check if the user wants to generate an email response
        if "respond to" in query.lower():
            # Generate a subject and body for email response
            recipient_email = relevant_emails[0]["sender"] if relevant_emails else None
            print("recp email"+recipient_email)
            if recipient_email:
                prompt = (
                    f"You are an email assistant. The user wants to respond to an email from {recipient_email}.\n"
                    f"Generate a professional and contextually relevant subject and body for this email, "
                    f"following this structure:\n\n"
                    f"recipient: {recipient_email}\nsubject: <appropriate subject>\n"
                    f"body: <appropriate body text>\n\nEnd with 'Maaz Asghar'."
                )
                response = await openai.ChatCompletion.acreate(
                    model="gpt-4-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200
                )
                ai_response = response.choices[0].message['content'].strip()
                return ai_response
            else:
                return "No suitable email found to respond to."

        # Build AI prompt with email context for general queries
        prompt = (
            f"User query: '{query}'\n\n"
            f"Relevant email information:\n{email_context}\n\n"
            f"Provide a response based on the user's query and email context above."
        )

        # Convert messages to JSON-serializable format
        messages = [{"role": "system", "content": system_prompt}]  # Include system prompt here

        # Add conversation memory messages to the list
        messages.extend(
            {"role": "user" if message.type == "human" else "assistant", "content": message.content}
            for message in memory.chat_memory.messages
        )

        # Add the current user query as a prompt
        messages.append({"role": "user", "content": prompt})

        # Get AI response for general query
        response = await openai.ChatCompletion.acreate(
            model="gpt-4-turbo",
            messages=messages,
            max_tokens=200
        )
        ai_response = response.choices[0].message['content'].strip()
        
        memory.save_context({"content": query}, {"content": ai_response})
        return ai_response

    except Exception as e:
        print(f"Error with AI query: {e}")
        return "I'm here to help, but it seems there was an issue processing that request. Could you try again."

# Main AI Agent function to interact with user queries and check for email format
async def ai_agent_interact():
    print("AI Agent ready. Type your queries or 'exit' to quit.")
    load_emails_to_vector_db()  # Load emails to vector DB initially

    while True:
        user_query = input("\033[1;32m\nYou: \033[0m").strip()
        if user_query.lower() == "exit":
            print("\nExiting AI agent.\n")
            break
        elif user_query:
            answer = await ai_query_with_email_context(user_query)
            print("\033[1;31m\nBot:\033[0m", answer)

            # Check if response contains email fields and prompt user
            if "recipient:" in answer and "subject:" in answer and "body:" in answer:
                confirmation = input("Do you want to send this email? (yes/no): ").strip().lower()
                if confirmation == "yes":
                    try:
                        # Extract recipient and subject
                        recipient = answer.split("recipient: ")[1].split("\n")[0].strip()
                        subject = answer.split("subject: ")[1].split("\n")[0].strip()

                        # Extract body - everything after 'body:' keyword
                        body_start_index = answer.find("body:") + len("body:")
                        body = answer[body_start_index:].strip().lstrip("\n")

                        # Send email using extracted details
                        send_email(recipient, subject, body)
                        print("The email has been sent.")
                    except IndexError:
                        print("Error: Unable to parse email fields from the response. Please ensure the format is correct.")
                else:
                    print("Email sending canceled.")
        time.sleep(1)

# Main execution
if __name__ == "__main__":
    asyncio.run(ai_agent_interact())
