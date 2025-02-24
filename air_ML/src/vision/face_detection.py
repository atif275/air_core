import cv2
import dlib
import numpy as np
from typing import List, Tuple, Optional

# Initialize face detector and shape predictor
face_detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("models/face/shape_predictor_68_face_landmarks.dat")

def detect_faces_and_landmarks(frame: np.ndarray) -> List[Tuple[dlib.rectangle, np.ndarray]]:
    """
    Detect faces and their landmarks in a frame.
    
    Args:
        frame: Input image frame
        
    Returns:
        List of tuples containing face rectangles and their landmarks
    """
    # Convert frame to grayscale for face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_detector(gray)
    
    results = []
    for face in faces:
        # Get facial landmarks
        landmarks = predictor(gray, face)
        landmarks_points = np.array([[p.x, p.y] for p in landmarks.parts()])
        results.append((face, landmarks_points))
    
    return results

def draw_face_landmarks(frame: np.ndarray, faces_and_landmarks: List[Tuple[dlib.rectangle, np.ndarray]]) -> np.ndarray:
    """
    Draw detected faces and landmarks on the frame.
    
    Args:
        frame: Input image frame
        faces_and_landmarks: List of detected faces and their landmarks
        
    Returns:
        Frame with drawn faces and landmarks
    """
    for face, landmarks in faces_and_landmarks:
        # Draw face rectangle
        x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Draw landmarks
        for (x, y) in landmarks:
            cv2.circle(frame, (x, y), 2, (0, 0, 255), -1)
    
    return frame
