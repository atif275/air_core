import os
import sqlite3
from src.config.settings import DATABASE_PATH

def ensure_database():
    """Ensure all required tables exist in the database."""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()

        # Persons table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT DEFAULT 'Unknown',
            age INTEGER,
            gender TEXT,
            emotion TEXT,
            ethnicity TEXT,
            embedding TEXT
        )
        ''')

        # Active person table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_person (
            id INTEGER PRIMARY KEY
        )
        ''')

        # Add conversations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER,
            message TEXT,
            role TEXT,  -- 'user' or 'bot'
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(person_id) REFERENCES persons(id)
        )
        ''')

        # Add conversation summaries table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_ids TEXT,  -- Comma-separated list of person IDs
            summary TEXT,
            start_time DATETIME,
            end_time DATETIME
        )
        ''')

        connection.commit()
        connection.close()
        print("Database tables created successfully!")
    except sqlite3.Error as e:
        print(f"Database error occurred: {e}")
        raise
    finally:
        if 'connection' in locals():
            connection.close()

# Remove the automatic call
# ensure_database()
