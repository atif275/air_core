import sqlite3
from typing import Optional
from src.config.settings import DATABASE_PATH

def update_active_person_id(person_id: int) -> None:
    """
    Update the active person ID in the database.
    
    Args:
        person_id: The ID of the person to set as active
    
    Raises:
        sqlite3.Error: If database operation fails
    """
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM active_person")
            cursor.execute("INSERT INTO active_person (id) VALUES (?)", (person_id,))
            connection.commit()
    except sqlite3.Error as e:
        print(f"[ERROR] Failed to update active person: {e}")
        raise

def get_active_person_id() -> Optional[int]:
    """
    Retrieve the current active person ID from the database.
    
    Returns:
        int or None: The ID of the active person, or None if no active person
    
    Raises:
        sqlite3.Error: If database operation fails
    """
    try:
        with sqlite3.connect(DATABASE_PATH) as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM active_person LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        print(f"[ERROR] Failed to get active person: {e}")
        raise
