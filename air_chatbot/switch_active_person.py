import os
import sqlite3
from datetime import datetime
from typing import List, Tuple

def get_database_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    db_path = os.path.join('data', 'database.db')
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")
    return sqlite3.connect(db_path)

def get_all_persons() -> List[Tuple[int, str, int]]:
    """Get all persons from the database."""
    conn = get_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, age FROM persons")
        return cursor.fetchall()
    finally:
        conn.close()

def get_active_person() -> Tuple[int, str, int]:
    """Get the currently active person."""
    conn = get_database_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT p.id, p.name, p.age 
            FROM persons p
            JOIN active a ON p.id = a.person_id
            WHERE a.is_active = TRUE
        """)
        return cursor.fetchone()
    finally:
        conn.close()

def switch_active_person(person_id: int) -> bool:
    """Switch the active person to the specified ID."""
    conn = get_database_connection()
    cursor = conn.cursor()
    try:
        # First check if the person exists
        cursor.execute("SELECT id FROM persons WHERE id = ?", (person_id,))
        if not cursor.fetchone():
            print(f"Error: No person found with ID {person_id}")
            return False

        # Check if active table has any rows
        cursor.execute("SELECT COUNT(*) FROM active")
        count = cursor.fetchone()[0]

        if count == 0:
            # If no row exists, insert one
            cursor.execute("""
                INSERT INTO active (person_id, is_active, last_active)
                VALUES (?, TRUE, ?)
            """, (person_id, datetime.utcnow()))
        else:
            # Update the existing row
            cursor.execute("""
                UPDATE active 
                SET person_id = ?, last_active = ?
                WHERE is_active = TRUE
            """, (person_id, datetime.utcnow()))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error switching active person: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    """Main function to handle user interaction."""
    try:
        # Get current active person
        active = get_active_person()
        if active:
            print(f"\nCurrently active person: {active[1]} (ID: {active[0]}, Age: {active[2]})")
        else:
            print("\nNo active person currently set")

        # Show all available persons
        print("\nAvailable persons:")
        persons = get_all_persons()
        for person_id, name, age in persons:
            print(f"ID: {person_id}, Name: {name}, Age: {age}")

        # Get user input
        while True:
            try:
                choice = input("\nEnter the ID of the person to make active (or 'q' to quit): ")
                if choice.lower() == 'q':
                    break
                
                person_id = int(choice)
                if switch_active_person(person_id):
                    # Get the new active person's details
                    new_active = get_active_person()
                    print(f"\nSuccessfully switched active person to: {new_active[1]} (ID: {new_active[0]})")
                    break
                else:
                    print("Failed to switch active person. Please try again.")
            except ValueError:
                print("Please enter a valid number or 'q' to quit.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 