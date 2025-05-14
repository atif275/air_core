"""Configuration settings for facial analysis."""
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import shared config
from src.config import DB_PATH

# Configuration
MIN_FACE_SIZE = 60  # Minimum size of face to consider
MIN_FRAMES_TO_REGISTER = 5  # Number of frames before auto-registration
TRACKING_THRESHOLD = 0.5  # IOU threshold for tracking
AUTO_REGISTER = True  # Automatically register new faces
DETECTION_SIZE = (640, 640)  # InsightFace detection size
RECOGNITION_THRESHOLD = 0.85  # Similarity threshold for face matching
EVALUATION_FRAMES = 30  # Number of frames to evaluate before determining identity
DEBUG_MODE = True  # Enable debug output
DEFAULT_DISPLAY_CONFIDENCE = 0.01  # Default confidence to display when there's no match 