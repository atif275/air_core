import cv2
import os
import time
from src.vision.face_detection import detect_faces_and_landmarks
from src.vision.active_person import identify_active_person
from src.database.active_person import update_active_person_id

def process_camera_feed(stop_event, shared_data, lock):
    frames_dir = "frames"
    print("Starting frame processing from directory...", flush=True)

    while not stop_event.is_set():
        try:
            files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.jpg')])
            if not files:
                time.sleep(0.1)
                continue

            # Process the first image in the sorted list
            image_path = os.path.join(frames_dir, files[0])
            
            frame = cv2.imread(image_path)
            if frame is None:
                print(f"Failed to read image: {image_path}")
                os.remove(image_path)
                continue

            # Detect faces and get results
            detected_faces = detect_faces_and_landmarks(frame)
            
            if detected_faces and len(detected_faces) > 0:
                active_person_id, face_coords = identify_active_person(detected_faces, frame)

                if active_person_id and face_coords:
                    with lock:
                        shared_data["active_person_id"] = active_person_id
                        update_active_person_id(active_person_id)

            # Remove the processed image
            os.remove(image_path)
            print(f"Processed and removed: {image_path}", flush=True)

        except Exception as e:
            print(f"Error processing {image_path}: {e}", flush=True)
            try:
                os.remove(image_path)
            except:
                pass

    print("Frame processing stopped.", flush=True)
