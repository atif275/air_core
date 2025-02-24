import sqlite3
from src.config.settings import DATABASE_PATH

def save_conversation(person_id, message, role):
    """Save a single conversation message."""
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO conversations (person_id, message, role) VALUES (?, ?, ?)",
        (person_id, message, role)
    )
    connection.commit()
    connection.close()
    print(f"Saved {role} message for person ID {person_id}")