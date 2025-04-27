import os
import sqlite3
from datetime import datetime, timedelta
import json

def setup_database():
    """
    Creates a data folder in the root directory and initializes a database.db file
    with the necessary tables for the chatbot system.
    """
    try:
        # Create data directory if it doesn't exist
        if not os.path.exists('data'):
            os.makedirs('data')
            print("Created 'data' directory")
        
        # Database path
        db_path = os.path.join('data', 'database.db')
        
        # Connect to the database (creates it if it doesn't exist)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create persons table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            age INTEGER NOT NULL,
            gender VARCHAR(50) NOT NULL,
            ethnicity VARCHAR(100) NOT NULL,
            language VARCHAR(50) NOT NULL,
            personality_traits TEXT NOT NULL,
            image BLOB,
            features BLOB,
            timestamp TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("Created 'persons' table")
        
        # Create active table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS active (
            person_id INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES persons(id),
            CHECK (is_active = TRUE)  -- Ensures this is always TRUE as we only have one row
        )
        ''')
        print("Created 'active' table")
        
        # Create face_embeddings table for facial recognition
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS face_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            features BLOB NOT NULL,
            quality_score FLOAT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES persons(id)
        )
        ''')
        print("Created 'face_embeddings' table")
        
        # Create index on person_id for face_embeddings table
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_person_id 
        ON face_embeddings(person_id)
        ''')
        print("Created index on face_embeddings table")
        
        # Drop existing summary table if it exists (since we're changing its structure)
        cursor.execute("DROP TABLE IF EXISTS summary")
        
        # Create new summary table with updated structure
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            FOREIGN KEY (person_id) REFERENCES persons(id)
        )
        ''')
        print("Created 'summary' table with updated structure")
        
        # Check if there's any data in persons table
        cursor.execute("SELECT COUNT(*) FROM persons")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insert first person with properly formatted JSON
            sample_traits_1 = json.dumps({
                "traits": ["friendly", "outgoing", "tech-savvy"]
            })
            
            cursor.execute('''
            INSERT INTO persons (name, age, gender, ethnicity, language, personality_traits)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', ('John Doe', 25, 'Male', 'Asian', 'English', sample_traits_1))
            person_id_1 = cursor.lastrowid
            print(f"Inserted first person with ID: {person_id_1}")
            
            # Insert second person
            sample_traits_2 = json.dumps({
                "traits": ["creative", "analytical", "curious"]
            })
            
            cursor.execute('''
            INSERT INTO persons (name, age, gender, ethnicity, language, personality_traits)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', ('Jane Smith', 30, 'Female', 'Caucasian', 'English', sample_traits_2))
            person_id_2 = cursor.lastrowid
            print(f"Inserted second person with ID: {person_id_2}")
            
            # Clear any existing active records and insert the single row
            cursor.execute("DELETE FROM active")
            cursor.execute('''
            INSERT INTO active (person_id, is_active, last_active)
            VALUES (?, TRUE, ?)
            ''', (person_id_1, datetime.utcnow()))
            print(f"Set person {person_id_1} as active")
            
            # Insert sample conversation summaries
            now = datetime.utcnow()
            
            # Summary for person 1's first conversation
            cursor.execute('''
            INSERT INTO summary (person_id, summary, start_time, end_time)
            VALUES (?, ?, ?, ?)
            ''', (
                person_id_1,
                "Discussed personal interests including technology and programming. Expressed interest in AI and machine learning. Mentioned goal to become a software architect.",
                now - timedelta(days=1),
                now - timedelta(days=1, minutes=30)
            ))
            
            # Summary for person 2's conversation
            cursor.execute('''
            INSERT INTO summary (person_id, summary, start_time, end_time)
            VALUES (?, ?, ?, ?)
            ''', (
                person_id_2,
                "Shared educational background in data science. Planning to pursue advanced degree in AI. Currently working on a research project about natural language processing.",
                now - timedelta(hours=2),
                now - timedelta(hours=1)
            ))
            
            print("Inserted sample conversation summaries")
            
            # Verify the data was inserted
            cursor.execute("SELECT * FROM persons")
            persons = cursor.fetchall()
            print(f"Verified persons data: {persons}")
            
            cursor.execute("SELECT * FROM active")
            active = cursor.fetchone()
            print(f"Verified active data: {active}")
            
            cursor.execute("SELECT * FROM summary")
            summaries = cursor.fetchall()
            print(f"Verified conversation summaries: {summaries}")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        print(f"Database setup complete at {db_path}")
        
    except Exception as e:
        print(f"Error setting up database: {str(e)}")
        raise

if __name__ == "__main__":
    setup_database() 