import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis
from insightface.app.common import Face
from insightface.model_zoo import get_model
from skimage.feature import local_binary_pattern
from config import DETECTION_SIZE
import time
from logger import face_logger

def init_face_detector():
    """Initialize the InsightFace detector (CPU only)"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            face_logger.log(f"Initializing InsightFace detector (attempt {attempt + 1}/{max_retries})", "INFO")
            face_analyzer = FaceAnalysis(
                providers=['CPUExecutionProvider'],
                allowed_modules=['detection', 'recognition'],  # Enable both detection and recognition
                name='buffalo_l'  # Use the larger model for better accuracy
            )
            face_analyzer.prepare(ctx_id=-1, det_size=DETECTION_SIZE)
            face_logger.log("InsightFace detector initialized successfully", "INFO")
            return face_analyzer
        except Exception as e:
            face_logger.log(f"Error initializing InsightFace (attempt {attempt + 1}): {str(e)}", "ERROR")
            if attempt < max_retries - 1:
                face_logger.log(f"Retrying in {retry_delay} seconds...", "INFO")
                time.sleep(retry_delay)
            else:
                face_logger.log("Failed to initialize InsightFace after multiple attempts", "ERROR")
                return None

# Cache for feature calculations
_feature_cache = {}
_cache_size = 1000  # Maximum number of cached features

def _clear_old_cache():
    """Clear old entries from the feature cache"""
    if len(_feature_cache) > _cache_size:
        # Remove oldest entries
        oldest_keys = sorted(_feature_cache.keys(), key=lambda k: _feature_cache[k]['timestamp'])[:len(_feature_cache) - _cache_size]
        for key in oldest_keys:
            del _feature_cache[key]

def calculate_face_features(face_img):
    """Calculate feature vector from a face image with recovery mechanism"""
    if face_img is None or face_img.size == 0:
        face_logger.log("Invalid face image provided for feature calculation", "ERROR")
        return None
        
    try:
        # Create cache key from image hash
        img_hash = hash(face_img.tobytes())
        if img_hash in _feature_cache:
            face_logger.log("Retrieved features from cache", "INFO")
            return _feature_cache[img_hash]['features']
        
        # Resize to standard size
        face_resized = cv2.resize(face_img, (64, 64))
        
        # Convert to grayscale
        gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        
        # Normalize lighting
        gray = cv2.equalizeHist(gray)
        
        # Calculate features in parallel where possible
        features = []
        
        # Global histogram (faster calculation with fewer bins)
        global_hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
        global_hist = cv2.normalize(global_hist, global_hist).flatten()
        features.extend(global_hist)
        
        # Regional histograms (optimized calculation)
        h, w = gray.shape
        cell_h, cell_w = h // 3, w // 3
        for i in range(3):
            for j in range(3):
                roi = gray[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
                hist = cv2.calcHist([roi], [0], None, [16], [0, 256])  # Reduced bins for speed
                hist = cv2.normalize(hist, hist).flatten()
                features.extend(hist)
        
        # Edge features (optimized calculation)
        edges = cv2.Canny(gray, 100, 200)
        edge_hist = cv2.calcHist([edges], [0], None, [32], [0, 256])  # Reduced bins
        edge_hist = cv2.normalize(edge_hist, edge_hist).flatten()
        features.extend(edge_hist)
        
        # Texture features using Local Binary Patterns (optimized)
        radius = 1
        n_points = 8
        lbp = local_binary_pattern(gray, n_points, radius, method='uniform')
        lbp_hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, range=(0, n_points + 2), density=True)
        features.extend(lbp_hist)
        
        # Convert to numpy array and normalize
        features = np.array(features)
        features = features / np.linalg.norm(features)
        
        # Cache the result
        _feature_cache[img_hash] = {
            'features': features,
            'timestamp': time.time()
        }
        _clear_old_cache()
        face_logger.log("Calculated and cached new features", "INFO")
        
        return features
    except Exception as e:
        face_logger.log(f"Error calculating face features: {str(e)}", "ERROR")
        face_logger.log("Attempting to recover by clearing feature cache", "INFO")
        _feature_cache.clear()
        try:
            features = calculate_face_features(face_img)
            face_logger.log("Successfully recovered feature calculation", "INFO")
            return features
        except Exception as e:
            face_logger.log(f"Recovery failed: {str(e)}", "ERROR")
            return None

def detect_faces(face_analyzer, frame):
    """Detect faces in a frame using InsightFace with recovery mechanism"""
    if face_analyzer is None:
        face_logger.log("Face analyzer not initialized, attempting to reinitialize", "WARNING")
        face_analyzer = init_face_detector()
        if face_analyzer is None:
            face_logger.log("Failed to reinitialize face analyzer", "ERROR")
            return []
    
    try:
        # Ensure frame is in correct format and size
        if frame is None or frame.size == 0:
            face_logger.log("Invalid frame received", "WARNING")
            return []
            
        # Detect faces
        faces = face_analyzer.get(frame)
        num_faces = len(faces) if faces is not None else 0
        face_logger.log(f"Detected {num_faces} faces in frame", "INFO")
        
        if faces is None:
            return []
            
        # Filter out low confidence detections
        valid_faces = []
        for face in faces:
            if hasattr(face, 'det_score') and face.det_score > 0.5:  # Adjust threshold if needed
                valid_faces.append(face)
        
        face_logger.log(f"Found {len(valid_faces)} valid faces after filtering", "INFO")
        return valid_faces
        
    except Exception as e:
        face_logger.log(f"Error detecting faces: {str(e)}", "ERROR")
        face_logger.log("Attempting to recover face analyzer", "INFO")
        face_analyzer = init_face_detector()
        if face_analyzer is not None:
            try:
                faces = face_analyzer.get(frame)
                face_logger.log("Successfully recovered face detection", "INFO")
                return faces if faces is not None else []
            except Exception as e:
                face_logger.log(f"Recovery failed: {str(e)}", "ERROR")
        return [] 