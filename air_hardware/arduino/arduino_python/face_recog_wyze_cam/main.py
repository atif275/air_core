import cv2
import numpy as np
import os
from datetime import datetime
from PIL import Image

# Load OpenCV's pre-trained Haar Cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Camera stream code only
camera_indices = [0, 1, 2]
cap = None

for camera_index in camera_indices:
    print(f"Trying camera index: {camera_index}")
    cap = cv2.VideoCapture(camera_index)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"Successfully opened camera at index {camera_index}")
            print(f"Frame shape: {frame.shape}")
            print(f"Frame type: {frame.dtype}")
            break
        else:
            print(f"Camera {camera_index} opened but failed to read frame")
            cap.release()
    else:
        print(f"Failed to open camera at index {camera_index}")
        cap.release()

if cap is None or not cap.isOpened():
    print("Error: Could not open any camera. Please check your camera connections and permissions.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Add these variables at the top (after imports)
confirmed_face = None
confirmed_count = 0
CONFIRM_FRAMES = 15  # Number of consecutive frames to confirm a face
POSITION_MARGIN = 30  # Margin in pixels to consider the face in the same position

while True:
    success, img = cap.read()
    if not success or img is None:
        print("Failed to capture image from camera.")
        break

    # print(f"Captured image shape: {img.shape}")
    # print(f"Captured image type: {img.dtype}")

    # Convert to grayscale for face detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # Draw a persistent red rectangle in the center (width: half, height: full frame)
    frame_height, frame_width = img.shape[:2]
    box_width = frame_width // 2
    box_height = (frame_height * 4) // 4
    top_left_x = (frame_width - box_width) // 2
    top_left_y = (frame_height - box_height) // 2
    bottom_right_x = top_left_x + box_width
    bottom_right_y = top_left_y + box_height
    cv2.rectangle(img, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), (0, 0, 255), 2)

    # Track only the largest face
    largest_face = None
    largest_area = 0
    for (x, y, w, h) in faces:
        area = w * h
        if area > largest_area:
            largest_area = area
            largest_face = (x, y, w, h)

    if largest_face:
        x, y, w, h = largest_face
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        face_center_x = x + w // 2
        face_center_y = y + h // 2
        # Check if the face is in a similar position as the previous confirmed face
        if confirmed_face:
            prev_x, prev_y, prev_w, prev_h = confirmed_face
            prev_center_x = prev_x + prev_w // 2
            prev_center_y = prev_y + prev_h // 2
            if (abs(face_center_x - prev_center_x) < POSITION_MARGIN and
                abs(face_center_y - prev_center_y) < POSITION_MARGIN):
                confirmed_count += 1
            else:
                confirmed_count = 1
        else:
            confirmed_count = 1
        confirmed_face = (x, y, w, h)
    else:
        confirmed_face = None
        confirmed_count = 0

    # Only log movement if the face is confirmed
    if confirmed_count >= CONFIRM_FRAMES and confirmed_face:
        x, y, w, h = confirmed_face
        face_center_x = x + w // 2
        left_bound = top_left_x
        right_bound = bottom_right_x
        if face_center_x < left_bound:
            print("move left")
        elif face_center_x > right_bound:
            print("move right")

    cv2.imshow('Webcam', img)
    
    if cv2.getWindowProperty('Webcam', cv2.WND_PROP_VISIBLE) < 1:
        break
        
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()