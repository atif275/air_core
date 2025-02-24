import cv2
from src.vision.face_detection import detect_faces_and_landmarks
from src.vision.active_person import identify_active_person
from src.database.active_person import update_active_person_id

def process_camera_feed(stop_event, shared_data, lock):
    cap = cv2.VideoCapture(0)
    print("Starting optimized camera feed...", flush=True)

    frame_count = 0

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % 5 != 0:
            continue

        detected_faces = detect_faces_and_landmarks(frame)
        active_person_id, face_coords = identify_active_person(detected_faces, frame)  # ✅ Now gets face_coords too

        if active_person_id:
            with lock:
                shared_data["active_person_id"] = active_person_id
                update_active_person_id(active_person_id)

            if face_coords:  # ✅ Draw bounding box around active person
                x, y, w, h = face_coords
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"ID: {active_person_id}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Camera Feed - AIR", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_event.set()
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Camera feed stopped.", flush=True)
