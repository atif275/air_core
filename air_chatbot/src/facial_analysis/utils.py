import cv2
import numpy as np
from logger import face_logger

def calculate_iou(box1, box2):
    """Calculate IoU between two bounding boxes"""
    # box format: (x1, y1, x2, y2)
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    if x1 >= x2 or y1 >= y2:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    
    iou = intersection / union
    face_logger.log(f"IoU calculated: {iou:.4f} between boxes {box1} and {box2}", "INFO")
    return iou

def calculate_brightness(img):
    """Calculate the average brightness of an image"""
    if len(img.shape) == 3:
        # Convert to grayscale if the image is in color
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Calculate mean brightness
    mean_brightness = np.mean(gray)
    # face_logger.log(f"Image brightness calculated: {mean_brightness:.2f}", "INFO")
    return mean_brightness

def check_face_pose(face_img, landmarks):
    """
    Check if face is frontal/straight using facial landmarks
    Returns (is_straight, reason)
    """
    if landmarks is None:
        face_logger.log("No landmarks detected for pose check", "WARNING")
        return False, "No landmarks detected"
        
    # Get key landmarks for pose estimation
    left_eye = landmarks[0]
    right_eye = landmarks[1]
    nose = landmarks[2]
    left_mouth = landmarks[3]
    right_mouth = landmarks[4]
    
    # Calculate eye angle to check if face is tilted - make more strict
    eye_angle = np.degrees(np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0]))
    if abs(eye_angle) > 10:  # More strict: 10 degrees instead of 15
        face_logger.log(f"Face pose rejected: tilted {eye_angle:.1f} degrees", "INFO")
        return False, "Face is tilted"
    
    # Check if face is turned sideways using eye distance ratio - make more strict
    eye_distance = np.linalg.norm(right_eye - left_eye)
    face_width = face_img.shape[1]
    eye_ratio = eye_distance / face_width
    if eye_ratio < 0.25:  # More strict: 0.25 instead of 0.2
        face_logger.log(f"Face pose rejected: not frontal (eye ratio {eye_ratio:.2f})", "INFO")
        return False, "Face is not frontal"
    
    # Check nose position relative to eyes (horizontal center) - make more strict
    eye_center = (left_eye + right_eye) / 2
    nose_offset = abs(nose[0] - eye_center[0]) / face_width
    if nose_offset > 0.08:  # More strict: 0.08 instead of 0.1
        face_logger.log(f"Face pose rejected: turned sideways (nose offset {nose_offset:.2f})", "INFO")
        return False, "Face is turned sideways"
        
    # Check vertical angle (looking up/down) - make more strict
    eye_level = (left_eye[1] + right_eye[1]) / 2
    mouth_level = (left_mouth[1] + right_mouth[1]) / 2
    nose_to_eye = nose[1] - eye_level
    nose_to_mouth = mouth_level - nose[1]
    vertical_ratio = nose_to_eye / nose_to_mouth if nose_to_mouth != 0 else float('inf')
    
    # More strict ratios for vertical angle
    if vertical_ratio < 0.8:  # Looking up (was 0.7)
        face_logger.log(f"Face pose rejected: looking up (ratio {vertical_ratio:.2f})", "INFO")
        return False, "Face is looking up"
    if vertical_ratio > 1.5:  # Looking down (was 1.5)
        face_logger.log(f"Face pose rejected: looking down (ratio {vertical_ratio:.2f})", "INFO")
        return False, "Face is looking down"
    
    face_logger.log("Face pose check passed", "INFO")
    return True, None

def check_face_quality(face_img, landmarks=None, for_registration=False):
    """Check various quality metrics of a face image"""
    try:
        # Check brightness (existing check)
        brightness = calculate_brightness(face_img)
        if brightness < 65:
            face_logger.log(f"Face quality check failed: too dark ({brightness:.1f})", "INFO")
            return False, "Too dark"
        if brightness > 165:
            face_logger.log(f"Face quality check failed: too bright ({brightness:.1f})", "INFO")
            return False, "Too bright"
        
        # Check blur - make it stricter for registration
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if blur_value < 20:  # Basic check for recognition
            face_logger.log(f"Face quality check failed: too blurry ({blur_value:.1f})", "INFO")
            return False, "Too blurry"
            
        # Check face size - stricter for registration
        height, width = face_img.shape[:2]
        min_dimension = min(height, width)
        
        if min_dimension < 80:  # Stricter size requirement for registration
            face_logger.log(f"Face quality check failed: too small ({min_dimension}px)", "INFO")
            return False, "Face too small for registration"
            
        # Check face aspect ratio (to detect partial faces)
        aspect_ratio = height / width
        if for_registration:
            if not (0.5 <= aspect_ratio <= 1.5):  # Stricter aspect ratio for registration
                face_logger.log(f"Face quality check failed: invalid proportions for registration ({aspect_ratio:.2f})", "INFO")
                return False, "Invalid face proportions for registration"
        else:
            if not (0.5 <= aspect_ratio <= 1.5):  # Basic check for recognition
                face_logger.log(f"Face quality check failed: invalid proportions ({aspect_ratio:.2f})", "INFO")
                return False, "Invalid face proportions"
        
        # Face pose checks only for registration
        if for_registration and landmarks is not None:
            is_straight, pose_reason = check_face_pose(face_img, landmarks)
            if not is_straight:
                face_logger.log(f"Face quality check failed: {pose_reason}", "INFO")
                return False, f"Poor face pose: {pose_reason}"
        
        face_logger.log("Face quality check passed", "INFO")
        return True, None
        
    except Exception as e:
        face_logger.log(f"Face quality check failed with error: {str(e)}", "ERROR")
        return False, f"Quality check failed: {str(e)}"

def get_embedding_based_threshold(embedding_count):
    """
    Adjust threshold based on number of stored embeddings:
    - Few embeddings (< 5): Require higher match percentage (35%)
    - Medium embeddings (5-15): Standard threshold (20%)
    - Many embeddings (> 15): Lower threshold acceptable (15%)
    """
    if embedding_count < 5:
        threshold = 0.35  # Require 35% match for few embeddings
    elif embedding_count < 15:
        threshold = 0.20  # Standard threshold
    else:
        threshold = 0.15  # Can be more lenient with many embeddings
    
    face_logger.log(f"Embedding-based threshold: {threshold:.2f} (count: {embedding_count})", "INFO")
    return threshold

def get_quality_based_threshold(matches):
    """
    Adjust threshold based on the quality of matching embeddings:
    - High quality matches can use lower threshold
    - Low quality matches require higher threshold
    """
    if not matches:
        face_logger.log("No matches for quality-based threshold, using default 0.20", "INFO")
        return 0.20  # Default threshold if no matches
        
    # Extract quality scores if available, otherwise use similarity as proxy
    quality_scores = []
    for match in matches:
        if 'quality_score' in match:
            quality_scores.append(match['quality_score'])
        else:
            # Use similarity as a proxy for quality
            quality_scores.append(match['avg_similarity'])
    
    avg_quality = sum(quality_scores) / len(quality_scores)
    
    # Base threshold adjusted by quality (0.5-1.5 range)
    base_threshold = 0.20
    quality_factor = 1.0 + (0.5 - avg_quality)
    threshold = base_threshold * quality_factor
    
    face_logger.log(f"Quality-based threshold: {threshold:.2f} (avg quality: {avg_quality:.2f})", "INFO")
    return threshold

def get_confidence_based_threshold(similarities):
    """
    Adjust threshold based on:
    - Similarity score distribution
    - Gap between best and second-best matches
    - Consistency of matches
    """
    if len(similarities) < 2:
        face_logger.log("Not enough similarities for confidence-based threshold, using default 0.20", "INFO")
        return 0.20  # Default threshold if not enough data
    
    # Sort similarities in descending order
    sorted_sims = sorted(similarities, reverse=True)
    best_sim = sorted_sims[0]
    second_best = sorted_sims[1]
    
    # Calculate confidence metrics
    similarity_gap = best_sim - second_best
    similarity_std = np.std(similarities)
    
    # Base threshold
    threshold = 0.20
    
    # Adjust based on separation between best and second-best match
    if similarity_gap > 0.15:  # Clear separation
        threshold *= 0.8  # Lower threshold
    elif similarity_gap < 0.05:  # Close matches
        threshold *= 1.2  # Raise threshold
    
    # Adjust based on consistency
    if similarity_std < 0.1:  # Consistent matches
        threshold *= 0.9
    else:  # Inconsistent matches
        threshold *= 1.1
    
    face_logger.log(f"Confidence-based threshold: {threshold:.2f} (gap: {similarity_gap:.2f}, std: {similarity_std:.2f})", "INFO")
    return threshold

def get_adaptive_threshold(matches, embedding_count, similarities):
    """
    Combine all factors for a comprehensive adaptive threshold
    """
    # Get individual thresholds
    embedding_threshold = get_embedding_based_threshold(embedding_count)
    quality_threshold = get_quality_based_threshold(matches)
    confidence_threshold = get_confidence_based_threshold(similarities)
    
    # Weighted combination
    weights = {
        'embedding': 0.3,
        'quality': 0.4,
        'confidence': 0.3
    }
    
    final_threshold = (
        weights['embedding'] * embedding_threshold +
        weights['quality'] * quality_threshold +
        weights['confidence'] * confidence_threshold
    )
    
    # Ensure threshold stays within reasonable bounds
    final_threshold = max(0.15, min(0.40, final_threshold))
    
    face_logger.log(f"Adaptive threshold: {final_threshold:.2f} (embedding: {embedding_threshold:.2f}, quality: {quality_threshold:.2f}, confidence: {confidence_threshold:.2f})", "INFO")
    return final_threshold 