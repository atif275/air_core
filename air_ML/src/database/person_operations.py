import sqlite3
from typing import Dict, Optional
from src.config.settings import DATABASE_PATH
from src.types.person import PersonData
from src.services.memory_service import memory_service
from .db_operations import db_ops

def save_to_database(age, gender, emotion, ethnicity, embedding):
    """
    Save a new person's details to the database.
    Returns the ID of the newly added person.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    cursor.execute('''
        INSERT INTO persons (age, gender, emotion, ethnicity, embedding)
        VALUES (?, ?, ?, ?, ?)
    ''', (age, gender, emotion, ethnicity, str(embedding)))
    person_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return person_id

def update_person_attribute(person_id: int, attribute: str, value: str) -> None:
    """Update a single attribute for a person."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE persons SET {attribute} = ? WHERE id = ?",
            (value, person_id)
        )
        conn.commit()

def fetch_person_data(person_id: int) -> PersonData:
    """Fetch person data from database."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, age, gender, emotion, ethnicity FROM persons WHERE id = ?",
            (person_id,)
        )
        row = cursor.fetchone()
        if row:
            return PersonData(
                id=row[0],
                name=row[1],
                age=row[2],
                gender=row[3],
                emotion=row[4],
                ethnicity=row[5]
            )
        return PersonData()

def extract_and_update_person_attributes(active_person_id: int, assistant_reply: str) -> Optional[Dict]:
    """Extract attributes from assistant reply and update both database and memory."""
    extracted_data = {}
    
    for attribute in ["NAME", "AGE", "ETHNICITY"]:
        if attribute + "=" in assistant_reply:
            value = assistant_reply.split(attribute + "=")[1].split('\n')[0].strip()
            extracted_data[attribute.lower()] = value
            db_ops.update_person_attribute(active_person_id, attribute.lower(), value)
    
    if extracted_data:
        memory_service.update_memory(active_person_id, extracted_data)
        return extracted_data
    
    return None

# Export the database operations
fetch_person_data = db_ops.fetch_person_data
update_person_attribute = db_ops.update_person_attribute
