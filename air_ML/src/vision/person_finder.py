import sqlite3
import numpy as np
from src.vision.similarity import cosine_similarity
from src.config.settings import DATABASE_PATH

def find_matching_person(embedding, threshold=0.4):
    """
    Finds a matching person in the database based on embedding similarity.

    Args:
        embedding (list): The embedding of the detected face.
        threshold (float): The similarity threshold for matching.

    Returns:
        int or None: The ID of the matching person or None if no match is found.
    """
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    try:
        # Fetch all embeddings from the database
        cursor.execute('SELECT id, embedding FROM persons')
        rows = cursor.fetchall()

        # If no persons in database, return None
        if not rows:
            return None

        for row in rows:
            person_id, db_embedding = row
            db_embedding = np.array(eval(db_embedding))  # Convert string back to NumPy array
            similarity = cosine_similarity(embedding, db_embedding)
            if similarity > threshold:
                return person_id

        return None

    except sqlite3.Error as e:
        print(f"Database error in find_matching_person: {e}")
        return None
    finally:
        cursor.close()
        connection.close()