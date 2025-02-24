import openai
import sqlite3
from src.config.settings import DATABASE_PATH

def get_conversation_summary():
    """
    Fetch all conversation summaries from the 'conversation_summaries' table.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    # ✅ Retrieve all stored summaries, ordered by end_time (oldest first)
    cursor.execute("""
        SELECT summary FROM conversation_summaries 
        WHERE summary LIKE '**Summary%' 
        ORDER BY end_time ASC
    """)
    results = cursor.fetchall()
    connection.close()

    if results:
        summaries = "\n\n".join([f"{i+1}. {row[0]}" for i, row in enumerate(results)])
        return f"Summary of past conversations:\n{summaries}"
    return "No conversation summaries available."

def fetch_conversation_from_db():
    """
    Fetch conversation history from the database for all persons.
    :return: Dictionary with person_id as keys and list of conversation messages as values.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT person_id, message, role, timestamp FROM conversations ORDER BY timestamp"
        )
        conversation_data = cursor.fetchall()
        conversations = {}
        role_mapping = {"user": "user", "bot": "assistant"}  # Map 'bot' to 'assistant'

        for person_id, message, role, timestamp in conversation_data:
            if person_id not in conversations:
                conversations[person_id] = {"messages": [], "start_time": timestamp, "end_time": timestamp}
            
            mapped_role = role_mapping.get(role.lower(), "user")  # Default to 'user' if unknown
            conversations[person_id]["messages"].append({"role": mapped_role, "content": message})
            conversations[person_id]["end_time"] = timestamp
        return conversations
    finally:
        connection.close()

def save_summary_to_db(person_ids, summary, start_time, end_time):
    """
    Save the conversation summary to the database.
    :param person_ids: List of person IDs involved in the conversation.
    :param summary: Summary text.
    :param start_time: Start time of the conversation.
    :param end_time: End time of the conversation.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO conversation_summaries (person_ids, summary, start_time, end_time) VALUES (?, ?, ?, ?)",
            (" ".join(map(str, person_ids)), summary, start_time, end_time)
        )
        connection.commit()
        print("Conversation summary saved successfully.")
    except Exception as e:
        print(f"Error saving conversation summary: {e}")
    finally:
        connection.close()

def delete_conversation_from_db(person_id):
    """
    Delete conversation history from the database for the given person ID.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM conversations WHERE person_id = ?", (person_id,))
        connection.commit()
        print(f"Deleted conversation history for person ID {person_id}")
    except Exception as e:
        print(f"Error deleting conversation: {e}")
    finally:
        connection.close()

def summarize_conversations():
    """
    Summarize all conversations in the database and save them with meaningful details.
    """
    try:
        conversations = fetch_conversation_from_db()
        if not conversations:
            print("No conversations found.")
            return

        for person_id, data in conversations.items():
            # Define a solid system prompt with clear instructions
            summary_prompt = (
                "Summarize the following conversation in a concise and meaningful way. "
                "The summary should include:\n"
                "1. All users involved in the conversation (mention names, or IDs if names are not available).\n"
                "2. The purpose or key topics of the conversation, including any heated or debated subjects.\n"
                "3. Any conclusions or decisions made during the conversation.\n"
                "4. Notable information about users, such as:\n"
                "   - Names, relationships, education, work, hobbies, interests, or ideas.\n"
                "   - Anything deeply personal or relevant to the user (e.g., allergies, family member names, business, or places they discussed).\n"
                "5. Any information requested to be remembered for future reference.\n"
                "6. Anything that could be helpful or important in the future.\n"
                "7. Any introductions made (e.g., user names or identities revealed).\n"
                "8. Key first-time actions (e.g., a user introducing themselves or sharing personal details).\n"
                "9. Skip generic conversational exchanges like greetings, pleasantries, or irrelevant back-and-forth.\n"
                "10. Use a simple format, e.g., '<Name> introduces himself for the first time.'\n\n"
                "Ensure the summary is concise but captures all essential points and key aspects of the conversation.\n"
            )

            # Prepare messages for the OpenAI API
            messages = [{"role": "system", "content": summary_prompt}] + data["messages"]

            # Call the OpenAI API for summarization
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=messages
            )

            # Extract and clean the summary
            summary = response['choices'][0]['message']['content'].strip()
            
            # Save the summary to the database
            save_summary_to_db([person_id], summary, data["start_time"], data["end_time"])
            delete_conversation_from_db(person_id)
            print(f"[INFO] Summary saved for person ID {person_id}.")

    except Exception as e:
        print(f"Error generating summary: {str(e)}")
