from src.database.person_operations import save_to_database
from src.vision.face_analysis import get_eye_aspect_ratio, get_mouth_aspect_ratio
from src.vision.face_embedding import get_face_embedding, analyze_person_attributes
from src.vision.person_finder import find_matching_person
from typing import Tuple, Optional
import dlib

EYE_CONTACT_THRESHOLD = 0.20
MOUTH_MOVEMENT_THRESHOLD = 0.4

def identify_active_person(detected_faces, frame) -> Tuple[Optional[int], Optional[Tuple[int, int, int, int]]]:
    """Identify the most prominent face as the active person."""
    if not detected_faces:
        return None, None

    try:
        # Get the first face (assuming it's the most prominent)
        face, landmarks = detected_faces[0]  # dlib returns (rectangle, landmarks)
        
        # Verify that face is a dlib.rectangle object
        if not isinstance(face, dlib.rectangle):
            print(f"Invalid face object type: {type(face)}")
            return None, None
        
        # Convert dlib rectangle to coordinates
        x = face.left()
        y = face.top()
        w = face.right() - x
        h = face.bottom() - y
        
        # Extract face ROI (Region of Interest)
        face_roi = frame[y:y+h, x:x+w]
        
        # Get face embedding
        embedding = get_face_embedding(face_roi)
        if embedding is None:
            return None, None
            
        # Try to find matching person in database
        person_id = find_matching_person(embedding)
        
        if person_id is None:
            # New person detected - analyze and save to database
            attributes = analyze_person_attributes(face_roi)
            if attributes:
                person_id = save_to_database(
                    age=attributes["age"],
                    gender=attributes["gender"],
                    emotion=attributes["emotion"],
                    ethnicity=attributes["ethnicity"],
                    embedding=embedding
                )
                print(f"[INFO] New person saved with ID: {person_id}")
            else:
                return None, None

        return person_id, (x, y, w, h)
        
    except Exception as e:
        print(f"Error in identify_active_person: {e}")
        return None, None
