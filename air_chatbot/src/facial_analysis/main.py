"""Main facial analysis script."""
import cv2
import time
import numpy as np
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import (
    MIN_FACE_SIZE, MIN_FRAMES_TO_REGISTER, AUTO_REGISTER,
    DEBUG_MODE, RECOGNITION_THRESHOLD
)
from database import (
    init_database, save_face, clear_database, get_all_faces,
    load_face_embeddings, update_active_person
)
from detector import (
    init_face_detector, calculate_face_features
)
from tracker import FaceTracker
from utils import (
    calculate_brightness, check_face_quality,
    get_adaptive_threshold
)
from display import (
    draw_face_box, draw_status
)
from logger import face_logger
from src.database.database_manager import db_manager

# Cache for face features
face_features_cache = {}

def match_face(cursor, avg_features):
    """Match averaged face features against stored averaged embeddings and handle continuous learning"""
    try:
        face_logger.log("Starting face matching process", "INFO")
        # Get all faces from database if cache is empty
        if not face_features_cache:
            face_logger.log("Loading face embeddings from database", "INFO")
            face_features_cache.update(load_face_embeddings(cursor))
        
        if not face_features_cache:
            face_logger.log("No faces found in database", "WARNING")
            return None, 0.0, None  # No faces in database
        
        # Store all matches above threshold
        matches = []
        all_similarities = []  # For debugging
        
        face_logger.log(f"Comparing with {len(face_features_cache)} stored faces", "INFO")
        
        # Compare with all stored averaged embeddings for each person
        for face_id, face_data in face_features_cache.items():
            name = face_data['name']
            stored_embeddings = face_data['embeddings']
            
            # Calculate similarities with all stored averaged embeddings
            similarities = []
            for stored_embedding in stored_embeddings:
                similarity = np.dot(avg_features, stored_embedding) / (np.linalg.norm(avg_features) * np.linalg.norm(stored_embedding))
                similarities.append(similarity)
            
            # Get best similarity for this person
            max_similarity = max(similarities)
            matches_above_threshold = [s for s in similarities if s > RECOGNITION_THRESHOLD]
            
            if matches_above_threshold:
                avg_similarity = sum(matches_above_threshold) / len(matches_above_threshold)
                matches.append({
                    'face_id': face_id,
                    'name': name,
                    'match_count': len(matches_above_threshold),
                    'avg_similarity': avg_similarity,
                    'max_similarity': max_similarity,
                    'embedding_count': len(stored_embeddings),
                    'quality_score': avg_similarity
                })
            
            # Store best similarity for debugging
            all_similarities.append((face_id, name, max_similarity))
        
        # Sort matches by average similarity
        matches.sort(key=lambda x: x['avg_similarity'], reverse=True)
        
        # Debug output only for significant changes
        if DEBUG_MODE and matches and matches[0]['avg_similarity'] > RECOGNITION_THRESHOLD:
            # Only print if this is a new match or significant change in similarity
            best_match = matches[0]
            face_id = best_match['face_id']
            
            # Store last printed similarity in cache to avoid repeating
            if 'last_printed_similarity' not in face_features_cache[face_id]:
                face_features_cache[face_id]['last_printed_similarity'] = 0.0
            
            # Only print if similarity changed significantly (>0.01) or first time
            if abs(best_match['avg_similarity'] - face_features_cache[face_id]['last_printed_similarity']) > 0.01:
                face_logger.log(f"Best match found: {best_match['name']} with similarity {best_match['avg_similarity']:.4f}", "INFO")
                face_logger.log(f"Matched embeddings: {best_match['match_count']}/{len(face_features_cache[best_match['face_id']]['embeddings'])}", "INFO")
                
                # Update last printed similarity
                face_features_cache[face_id]['last_printed_similarity'] = best_match['avg_similarity']
        
        # Return best match if we have one
        if matches:
            best_match = matches[0]
            total_embeddings = len(face_features_cache[best_match['face_id']]['embeddings'])
            
            # Calculate adaptive threshold
            adaptive_threshold = get_adaptive_threshold(
                matches=matches,
                embedding_count=total_embeddings,
                similarities=[m['avg_similarity'] for m in matches]
            )
            
            if DEBUG_MODE and best_match['avg_similarity'] > RECOGNITION_THRESHOLD:
                face_logger.log(f"Adaptive threshold: {adaptive_threshold:.4f}", "INFO")
            
            # Check if match percentage exceeds adaptive threshold
            match_percentage = best_match['match_count'] / total_embeddings
            if match_percentage >= adaptive_threshold:
                # Store match result for display
                match_info = {
                    'face_id': best_match['face_id'], 
                    'name': best_match['name'],
                    'embedding_count': best_match['embedding_count'],
                    'similarity': best_match['avg_similarity']
                }
                face_logger.log(f"Match confirmed: {best_match['name']} with {match_percentage:.2%} match rate", "INFO")
                # Return tuple with face_id and name
                return (best_match['face_id'], best_match['name']), best_match['avg_similarity'], match_info
        
        # If no match found, return highest similarity for reference
        max_similarity = max(s[2] for s in all_similarities) if all_similarities else 0.0
        face_logger.log(f"No match found. Highest similarity: {max_similarity:.4f}", "INFO")
        return None, max_similarity, None
            
    except Exception as e:
        face_logger.log(f"Error in face matching: {str(e)}", "ERROR")
        return None, 0.0, None

def main():
    face_logger.log("Starting facial analysis system", "INFO")
    
    # Initialize components
    try:
        init_database()  # This will use the context manager internally
    except Exception as e:
        face_logger.log(f"Failed to initialize database: {str(e)}", "ERROR")
        return

    face_analyzer = init_face_detector()
    if not face_analyzer:
        face_logger.log("Failed to initialize face detector", "ERROR")
        return

    # Initialize face tracker
    tracker = FaceTracker()
    face_logger.log("Face tracker initialized", "INFO")

    # Initialize the video capture
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        face_logger.log("Failed to open webcam", "ERROR")
        return

    face_logger.log("Video capture initialized", "INFO")
    face_logger.log("System ready for face recognition", "INFO")

    # FPS tracking
    frame_count = 0
    fps_update_interval = 30  # Update FPS every 30 frames
    start_time = time.time()
    fps = 0.0

    try:
        while True:
            # Read frame
            ret, frame = cap.read()
            if not ret:
                face_logger.log("Failed to capture frame", "ERROR")
                break

            # Update FPS less frequently
            frame_count += 1
            if frame_count % fps_update_interval == 0:
                current_time = time.time()
                fps = fps_update_interval / (current_time - start_time)
                start_time = current_time
                face_logger.log(f"Current FPS: {fps:.2f}", "INFO")

            # Process frame and handle database operations
            with db_manager.get_sqlite_connection() as (conn, cursor):
                # Detect faces using InsightFace
                insightface_results = face_analyzer.get(frame)
                face_count = len(insightface_results)
                if face_count > 0:
                    face_logger.log(f"Detected {face_count} faces in frame", "INFO")

                # Extract face images and bounding boxes
                face_images = []
                for face in insightface_results:
                    bbox = face.bbox.astype(int)
                    x1, y1, x2, y2 = bbox

                    # Check minimum face size
                    if (x2-x1) < MIN_FACE_SIZE or (y2-y1) < MIN_FACE_SIZE:
                        face_logger.log(f"Face too small: {x2-x1}x{y2-y1}", "INFO")
                        continue

                    # Extract face image - with additional checks to prevent errors
                    try:
                        if y1 < 0: y1 = 0
                        if x1 < 0: x1 = 0
                        if y2 > frame.shape[0]: y2 = frame.shape[0]
                        if x2 > frame.shape[1]: x2 = frame.shape[1]

                        face_img = frame[y1:y2, x1:x2]

                        # Skip invalid faces
                        if face_img is None or face_img.size == 0 or face_img.shape[0] <= 0 or face_img.shape[1] <= 0:
                            face_logger.log("Invalid face image extracted", "WARNING")
                            continue

                        face_images.append((face_img, (x1, y1, x2, y2), face))
                    except Exception as e:
                        face_logger.log(f"Error extracting face: {str(e)}", "ERROR")
                        continue

                # Process faces only if there are any
                if face_images:
                    # Update tracking
                    current_time = time.time()
                    matched_tracks = tracker.update_tracks(face_images, current_time)
                    face_logger.log(f"Updated {len(matched_tracks)} face tracks", "INFO")

                    # Make a copy for display only if we need to draw on it
                    display = frame.copy()

                    # Track recognized faces for center-based selection
                    recognized_faces = []
                    frame_center_x = frame.shape[1] / 2
                    frame_center_y = frame.shape[0] / 2

                    # Process each detected face
                    for face_img, bbox, insight_face in face_images:
                        # Calculate brightness for display
                        brightness = calculate_brightness(face_img)

                        # Find corresponding track
                        track_id = None
                        for tid in matched_tracks:
                            if tracker.face_tracking[tid]['bbox'] == bbox:
                                track_id = tid
                                break

                        if track_id:
                            track_info = tracker.face_tracking[track_id]
                            name = track_info['name']  # Initialize name from track info
                            similarity = track_info['similarity']  # Initialize similarity from track info

                            # Store recognized face info for center-based selection
                            if track_info['matched'] and track_info.get('face_id') is not None:
                                x1, y1, x2, y2 = bbox
                                face_center_x = (x1 + x2) / 2
                                face_center_y = (y1 + y2) / 2
                                distance_to_center = ((face_center_x - frame_center_x) ** 2 + 
                                                    (face_center_y - frame_center_y) ** 2) ** 0.5
                                recognized_faces.append({
                                    'face_id': track_info['face_id'],
                                    'distance': distance_to_center
                                })
                                face_logger.log(f"Face {track_info['face_id']} recognized at distance {distance_to_center:.2f}", "INFO")

                            # Try to match with database if not already matched
                            if not track_info['matched']:
                                features = calculate_face_features(face_img)
                                
                                # Check quality based on current phase
                                is_good_quality, reason = check_face_quality(
                                    face_img, 
                                    insight_face.kps, 
                                    for_registration=(track_info['phase'] == 'registration')
                                )
                                
                                if not is_good_quality:
                                    face_logger.log(f"Low quality frame for {track_info['phase']}: {reason}", "WARNING")
                                    continue
                                
                                # Calculate quality score
                                quality_score = calculate_brightness(face_img) / 255.0
                                
                                # Add embedding to collection for current phase
                                tracker.add_embedding(track_id, features, quality_score)
                                
                                # Only proceed with matching if we have enough embeddings
                                if tracker.has_enough_embeddings(track_id):
                                    if track_info['phase'] == 'recognition':
                                        # Skip if already matched with high confidence
                                        if track_info.get('matched', False) and track_info.get('similarity', 0.0) > 0.90:
                                            continue
                                            
                                        # Get average embedding for recognition
                                        avg_features = tracker.get_average_embedding(track_id)
                                        match_result, similarity, match_info = match_face(cursor, avg_features)
                                        
                                        if match_result and match_info:
                                            face_id, name = match_result
                                            embedding_count = match_info['embedding_count']
                                            similarity = match_info['similarity']  # Use stored similarity
                                            
                                            # Update track identity with match result
                                            tracker.update_track_identity(track_id, match_result, similarity)
                                            
                                            # If match found with high confidence (>0.90), mark as matched and stop
                                            if similarity > 0.90:
                                                track_info['matched'] = True
                                                track_info['evaluated'] = True
                                                track_info['recognition_embeddings'] = []
                                                track_info['embedding_qualities'] = []
                                                track_info['name'] = name
                                                track_info['face_id'] = face_id  # Set face_id
                                                track_info['similarity'] = similarity
                                                
                                                # Update active person for high confidence match
                                                face_logger.log(f"High confidence match found for {name} (ID: {face_id})", "INFO")
                                                update_active_person(cursor, face_id)
                                                break
                                            
                                            # If similarity is between 0.85 and 0.90, collect embeddings for continuous learning
                                            elif 0.85 <= similarity <= 0.90 and embedding_count < 30:
                                                # Update active person for medium confidence match
                                                face_logger.log(f"Medium confidence match for {name} (ID: {face_id})", "INFO")
                                                update_active_person(cursor, face_id)
                                                
                                                # Only save if we have collected all 30 frames
                                                if len(track_info['recognition_embeddings']) >= tracker.EMBEDDING_COLLECTION_FRAMES:
                                                    # Get averaged embedding from all 30 frames
                                                    avg_features = tracker.get_average_embedding(track_id)
                                                    avg_quality = np.mean(track_info['embedding_qualities'])
                                                    
                                                    # Save to database
                                                    save_face(cursor, conn, face_img, name, avg_features, avg_quality)
                                                    
                                                    # Update cache with the new averaged embedding
                                                    if len(face_features_cache[face_id]['embeddings']) < 30:
                                                        face_features_cache[face_id]['embeddings'].append(avg_features)
                                                        face_features_cache[face_id]['qualities'].append(avg_quality)
                                                        
                                                        face_logger.log(f"Added new averaged embedding for {name} ({embedding_count + 1}/30)", "INFO")
                                                    
                                                    # Clear embeddings after saving
                                                    track_info['recognition_embeddings'] = []
                                                    track_info['embedding_qualities'] = []
                                        else:
                                            # No match found, switch to registration phase
                                            track_info['can_register'] = True
                                            tracker.start_registration_phase(track_id)
                                            name = "Unknown"
                                            similarity = 0.0
                                            face_logger.log("No match found, starting registration phase", "INFO")
                                    
                                    elif track_info['phase'] == 'registration' and track_info.get('can_register', False):
                                        # Now do registration with collected high-quality embeddings
                                        if current_time - tracker.last_registration_time > 2.0:
                                            # Get the averaged embedding from registration phase
                                            avg_features = tracker.get_average_embedding(track_id)
                                            
                                            # Check if this face is too similar to any existing face
                                            max_similarity = 0.0
                                            similar_face_name = None
                                            for face_id, face_data in face_features_cache.items():
                                                for stored_embedding in face_data['embeddings']:
                                                    similarity = np.dot(avg_features, stored_embedding) / (
                                                        np.linalg.norm(avg_features) * np.linalg.norm(stored_embedding)
                                                    )
                                                    if similarity > max_similarity:
                                                        max_similarity = similarity
                                                        similar_face_name = face_data['name']
                                            
                                            if max_similarity > 0.85:  # If too similar to existing face
                                                face_logger.log(f"Cannot register: Too similar to existing face '{similar_face_name}' ({max_similarity:.4f})", "WARNING")
                                                track_info['matched'] = True  # Prevent further registration attempts
                                                continue
                                            
                                            # Quality is acceptable and face is unique, proceed with registration
                                            tracker.last_face_id += 1
                                            auto_name = f"Person_{tracker.last_face_id}"
                                            
                                            # Save to database with averaged embedding
                                            avg_quality = np.mean(track_info['embedding_qualities'])
                                            face_id = save_face(cursor, conn, face_img, auto_name, avg_features, avg_quality)
                                            
                                            if face_id is not None:
                                                # Update cache
                                                face_features_cache[face_id] = {
                                                    'name': auto_name,
                                                    'embeddings': [avg_features],
                                                    'qualities': [avg_quality]
                                                }
                                                
                                                # Update track info with face_id
                                                track_info['name'] = auto_name
                                                track_info['face_id'] = face_id
                                                track_info['matched'] = True
                                                tracker.last_registration_time = current_time
                                                
                                                # Start collecting additional embeddings
                                                tracker.start_post_registration_collection(track_id)
                                                
                                                # Update active person after registration
                                                face_logger.log(f"Auto-registered new face as {auto_name} (ID: {face_id})", "INFO")
                                                update_active_person(cursor, face_id)
                            else:
                                remaining = tracker.EMBEDDING_COLLECTION_FRAMES - len(track_info['embeddings'])
                                face_logger.log(f"Collecting {track_info['phase']} embeddings... {remaining} more needed", "INFO")

                            # Handle post-registration embedding collection
                            if track_info['matched'] and tracker.needs_more_embeddings(track_id):
                                features = calculate_face_features(face_img)
                                
                                # Use recognition quality checks
                                is_good_quality, reason = check_face_quality(
                                    face_img,
                                    insight_face.kps,
                                    for_registration=False  # Use recognition quality checks
                                )
                                
                                if not is_good_quality:
                                    face_logger.log(f"Skipping low quality frame for additional embedding: {reason}", "WARNING")
                                    continue
                                
                                # Calculate quality score
                                quality_score = calculate_brightness(face_img) / 255.0
                                
                                # Add embedding to collection
                                track_info['recognition_embeddings'].append(features)
                                track_info['embedding_qualities'].append(quality_score)
                                
                                # Check if we have enough frames for an averaged embedding
                                if len(track_info['recognition_embeddings']) >= tracker.EMBEDDING_COLLECTION_FRAMES:
                                    # Get averaged embedding
                                    avg_features = tracker.get_average_embedding(track_id)
                                    avg_quality = np.mean(track_info['embedding_qualities'])
                                    
                                    # Save to database
                                    save_face(cursor, conn, face_img, track_info['name'], avg_features, avg_quality)
                                    
                                    # Update cache
                                    face_id = track_info['face_id']
                                    if face_id in face_features_cache:
                                        face_features_cache[face_id]['embeddings'].append(avg_features)
                                        face_features_cache[face_id]['qualities'].append(avg_quality)
                                    
                                    # Clear embeddings and increment counter
                                    track_info['recognition_embeddings'] = []
                                    track_info['embedding_qualities'] = []
                                    count = tracker.increment_post_registration_embeddings(track_id)
                                    
                                    face_logger.log(f"Added additional averaged embedding {count}/5 for {track_info['name']}", "INFO")

                        # Draw face box and information
                        draw_face_box(display, bbox, name, similarity, brightness, insight_face, track_info)

                    # Update active person to the most centered recognized face
                    if recognized_faces:
                        # Sort by distance to center
                        recognized_faces.sort(key=lambda x: x['distance'])
                        most_centered = recognized_faces[0]
                        face_logger.log(f"Updating active person to most centered face (ID: {most_centered['face_id']})", "INFO")
                        update_active_person(cursor, most_centered['face_id'])

                    # Draw status information
                    draw_status(display, tracker.face_tracking, tracker.last_face_id, fps)

            # Show the result
            cv2.imshow("Hybrid Face Recognition", display if face_images else frame)

            # Key handling
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                face_logger.log("Quit command received", "INFO")
                break
            elif key == ord('r'):
                if face_images:
                    face_img, bbox, insight_face = face_images[0]
                    
                    # Check face quality including pose
                    is_good_quality, reason = check_face_quality(face_img, insight_face.kps, for_registration=True)
                    if not is_good_quality:
                        face_logger.log(f"Cannot register: {reason}", "WARNING")
                        cv2.putText(frame, f"Cannot register: {reason}",
                                  (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                                  0.7, (0, 0, 255), 2)
                        cv2.imshow("Hybrid Face Recognition", frame)
                        cv2.waitKey(1500)
                        continue
                    else:
                        tracker.last_face_id += 1
                        name = f"Person_{tracker.last_face_id}"
                        
                        # Calculate features
                        features = calculate_face_features(face_img)
                        
                        # Save to database
                        face_id = save_face(cursor, conn, face_img, name, features)

                        if face_id is not None:
                            # Update cache
                            face_features_cache[face_id] = {
                                'name': name,
                                'embeddings': [features],
                                'qualities': [1.0]  # Default quality score for manual registration
                            }
                            
                            # Update active person after manual registration
                            face_logger.log(f"Manually registered new face as {name} (ID: {face_id})", "INFO")
                            update_active_person(cursor, face_id)
                        else:
                            tracker.last_face_id -= 1
                            face_logger.log("Failed to save face to database", "ERROR")
                        
                        tracker.last_registration_time = current_time
            elif key == ord('c'):
                face_logger.log("Clearing database", "INFO")
                clear_database(cursor, conn)
                face_features_cache.clear()  # Clear the cache
                tracker.face_tracking = {}
                tracker.last_face_id = 0
            elif key == ord('s'):
                faces = get_all_faces(cursor)
                if faces:
                    face_logger.log("Retrieved saved faces from database", "INFO")
                    print("Saved faces:")
                    for face_id, name in faces:
                        print(f"  {face_id}: {name}")
                else:
                    face_logger.log("No faces found in database", "INFO")
                    print("No faces saved in database")

    except Exception as e:
        face_logger.log(f"Error in main loop: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
    finally:
        cap.release()
        cv2.destroyAllWindows()
        db_manager.cleanup()  # Clean up all database connections
        face_logger.log("Application terminated", "INFO")
        print("Application terminated.")

if __name__ == "__main__":
    main() 