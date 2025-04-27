import os

# Database path
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/database.db'))

# Create database directory if it doesn't exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

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