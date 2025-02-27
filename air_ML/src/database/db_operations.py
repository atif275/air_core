import sqlite3
from src.config.settings import DATABASE_PATH
from src.types.person import PersonData

class DatabaseOperations:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    def fetch_person_data(self, person_id: int) -> PersonData:
        """Fetch person data from database."""
        with sqlite3.connect(self.db_path) as conn:
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

    def update_person_attribute(self, person_id: int, attribute: str, value: str) -> None:
        """Update a single attribute for a person."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE persons SET {attribute} = ? WHERE id = ?",
                (value, person_id)
            )
            conn.commit()

db_ops = DatabaseOperations() 