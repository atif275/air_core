import sqlite3
import pickle
from datetime import datetime
import cv2
import numpy as np
from config import DB_PATH, DEBUG_MODE
import json

def init_database():
    """Initialize the database and return connection and cursor"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrent access
        cursor.execute("PRAGMA journal_mode=WAL")
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
        
        # Create active table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS active (
            person_id INTEGER NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES persons(id),
            CHECK (is_active = TRUE)
        )
        ''')
        
        # Create face_embeddings table
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
        
        # Create index on person_id for face_embeddings table
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_person_id 
        ON face_embeddings(person_id)
        ''')
        
        # Create summary table
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
        
        conn.commit()
        return conn, cursor
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error initializing database: {str(e)}")
        raise

def _prepare_face_data(face_img, features=None):
    """Helper function to prepare face data for database storage"""
    # Convert image to bytes
    _, img_encoded = cv2.imencode('.jpg', face_img)
    img_bytes = img_encoded.tobytes()
    
    # Convert features to bytes if provided
    features_bytes = features.tobytes() if features is not None else None
    
    # Get timestamp
    timestamp = datetime.now().isoformat()
    
    return {'image': img_bytes, 'features': features_bytes, 'timestamp': timestamp}

def save_faces_batch(cursor, conn, faces_data):
    """Save multiple faces to the database in a single transaction"""
    try:
        if not faces_data:
            return []
        
        if DEBUG_MODE:
            print(f"Saving {len(faces_data)} faces in batch...")
        
        face_ids = []
        cursor.execute("BEGIN TRANSACTION")
        
        try:
            for face_img, name, features in faces_data:
                face_data = _prepare_face_data(face_img, features)
                
                # Insert into database
                cursor.execute(
                    "INSERT INTO faces (name, image, features, timestamp) VALUES (?, ?, ?, ?)",
                    (name, face_data['image'], face_data['features'], face_data['timestamp'])
                )
                face_ids.append(cursor.lastrowid)
            
            conn.commit()
            
            if DEBUG_MODE:
                print(f"✓ Successfully saved {len(faces_data)} faces")
            return face_ids
            
        except Exception as e:
            conn.rollback()
            raise e
            
    except Exception as e:
        print(f"Error in batch save: {e}")
        return []

def save_face(cursor, conn, face_img, name, features=None, quality_score=None):
    """Save a new face to the database with additional person information"""
    try:
        # Check if person with same name already exists
        cursor.execute("SELECT id FROM persons WHERE name = ?", (name,))
        existing_person = cursor.fetchone()
        
        if existing_person:
            person_id = existing_person[0]
            if DEBUG_MODE:
                print(f"Person {name} already exists with ID {person_id}")
            return person_id
            
        # Default values for required fields
        age = 0
        gender = "Unknown"
        ethnicity = "Unknown"
        language = "English"
        personality_traits = json.dumps({"traits": []})
        
        # Prepare face data
        face_data = _prepare_face_data(face_img, features)
        
        # Insert into persons table
        cursor.execute('''
        INSERT INTO persons (
            name, age, gender, ethnicity, language, 
            personality_traits, image, features, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name, age, gender, ethnicity, language,
            personality_traits, face_data['image'], 
            face_data['features'], face_data['timestamp']
        ))
        
        person_id = cursor.lastrowid
        
        # Save face embeddings if provided
        if features is not None and quality_score is not None:
            cursor.execute('''
            INSERT INTO face_embeddings (person_id, features, quality_score)
            VALUES (?, ?, ?)
            ''', (person_id, pickle.dumps(features), quality_score))
        
        # Update active person
        cursor.execute("DELETE FROM active")
        cursor.execute('''
        INSERT INTO active (person_id, is_active, last_active)
        VALUES (?, TRUE, ?)
        ''', (person_id, datetime.utcnow()))
        
        conn.commit()
        return person_id
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error saving face: {str(e)}")
        raise

def clear_database(cursor, conn):
    """Clear all data from the database"""
    try:
        cursor.execute("DELETE FROM face_embeddings")
        cursor.execute("DELETE FROM active")
        cursor.execute("DELETE FROM summary")
        cursor.execute("DELETE FROM persons")
        conn.commit()
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error clearing database: {str(e)}")
        raise

def get_face_count(cursor):
    """Get the number of faces in the database"""
    try:
        cursor.execute("SELECT COUNT(*) FROM faces")
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Error getting face count: {e}")
        return 0

def get_all_faces(cursor):
    """Get all faces from the database"""
    try:
        cursor.execute("SELECT id, name FROM faces")
        return cursor.fetchall()
    except Exception as e:
        print(f"Error getting faces: {e}")
        return []

def load_face_embeddings(cursor):
    """Load all face embeddings from the database"""
    try:
        cursor.execute('''
        SELECT p.id, p.name, fe.features, fe.quality_score
        FROM persons p
        JOIN face_embeddings fe ON p.id = fe.person_id
        ''')
        rows = cursor.fetchall()
        
        embeddings = {}
        for row in rows:
            person_id, name, features_blob, quality_score = row
            features = pickle.loads(features_blob)
            
            if person_id not in embeddings:
                embeddings[person_id] = {
                    'name': name,
                    'embeddings': []
                }
            
            embeddings[person_id]['embeddings'].append(features)
        
        return embeddings
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error loading face embeddings: {str(e)}")
        return {}

def update_active_person(cursor, person_id):
    """Update the active person in the database"""
    try:
        cursor.execute("DELETE FROM active")
        cursor.execute('''
        INSERT INTO active (person_id, is_active, last_active)
        VALUES (?, TRUE, ?)
        ''', (person_id, datetime.utcnow()))
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error updating active person: {str(e)}")
        raise

def get_active_person(cursor):
    """Get the currently active person from the database"""
    try:
        cursor.execute('''
        SELECT p.id, p.name, p.image, p.features
        FROM persons p
        JOIN active a ON p.id = a.person_id
        ''')
        return cursor.fetchone()
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error getting active person: {str(e)}")
        return None