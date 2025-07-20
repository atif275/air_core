import cv2
import numpy as np
import os
from datetime import datetime
from PIL import Image
import serial
import time
import threading

# Threaded video stream for RTSP (Wyze cam)
class VideoStream:
    def __init__(self, src):
        self.cap = cv2.VideoCapture(src)
        self.ret, self.frame = self.cap.read()
        self.stopped = False
        self.lock = threading.Lock()
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            with self.lock:
                self.ret, self.frame = ret, frame

    def read(self):
        with self.lock:
            return self.ret, self.frame

    def release(self):
        self.stopped = True
        self.cap.release()

# Load OpenCV's pre-trained Haar Cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Camera selection
print("Select camera mode:")
print("1: Built-in webcam")
print("2: Wyze cam (RTSP)")
mode = input("Enter 1 or 2: ").strip()

camera_indices = [0, 1, 2]
cap = None
stream = None
using_stream = False

if mode == '1':
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
elif mode == '2':
    wyze_url = "rtsp://Atif:27516515@192.168.1.6/live"
    print(f"Connecting to Wyze cam at {wyze_url}")
    stream = VideoStream(wyze_url)
    time.sleep(2)  # Let the stream warm up
    ret, frame = stream.read()
    if ret and frame is not None:
        print(f"Successfully opened Wyze cam stream")
        print(f"Frame shape: {frame.shape}")
        print(f"Frame type: {frame.dtype}")
        using_stream = True
    else:
        print(f"Failed to open Wyze cam stream")
        stream.release()
        stream = None
else:
    print("Invalid selection. Exiting.")
    exit()

if (mode == '1' and (cap is None or not cap.isOpened())) or (mode == '2' and (stream is None)):
    print("Error: Could not open any camera. Please check your camera connections and permissions.")
    exit()

if mode == '1':
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Initialize serial connection to Arduino
# Replace '/dev/tty.usbmodemXXXX' with your actual Arduino port
ser = serial.Serial('/dev/tty.usbmodem11401', 9600, timeout=1)
time.sleep(2)  # Wait for Arduino to reset
last_command = None

# Add these variables at the top (after imports)
confirmed_face = None
confirmed_count = 0
CONFIRM_FRAMES = 15  # Number of consecutive frames to confirm a face
POSITION_MARGIN = 30  # Margin in pixels to consider the face in the same position
waiting_for_ready = False
pending_command = None

while True:
    if using_stream:
        success, img = stream.read()
    else:
        success, img = cap.read()
    if not success or img is None:
        print("Failed to capture image from camera.")
        break

    # Convert to grayscale for face detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    # Draw a persistent red rectangle in the center
    frame_height, frame_width = img.shape[:2]
    if mode == '2':  # Wyze cam: smaller box
        box_width = frame_width // 3
        box_height = (frame_height * 4) // 4
    else:  # Built-in webcam: original size
        box_width = frame_width // 2
        box_height = (frame_height * 4) // 4
    top_left_x = (frame_width - box_width) // 2
    top_left_y = (frame_height - box_height) // 2
    bottom_right_x = top_left_x + box_width
    bottom_right_y = top_left_y + box_height
    cv2.rectangle(img, (top_left_x, top_left_y), (bottom_right_x, bottom_right_y), (0, 0, 255), 2)

    # Only the largest (closest) face is tracked and used for confirmation and movement logging
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

    # Command logic: only send 'L' or 'R' if needed, 'M' only if face is gone
    command = None
    if confirmed_count >= CONFIRM_FRAMES and confirmed_face:
        x, y, w, h = confirmed_face
        face_center_x = x + w // 2
        left_bound = top_left_x
        right_bound = bottom_right_x
        if face_center_x < left_bound:
            command = 'L'
        elif face_center_x > right_bound:
            command = 'R'
        # If the face is inside the red box, do not send any command (hold position)
        else:
            command = None
    else:
        command = 'M'  # Move to center if no confirmed face

    # Only send a new command if not waiting for Arduino to finish previous move and command is not None
    if not waiting_for_ready and command:
        ser.write((command + '\n').encode())
        print(f"Sent command: {command}")
        waiting_for_ready = True
        pending_command = command

    # Check for Arduino feedback
    if ser.in_waiting:
        response = ser.readline().decode().strip()
        if response == "READY":
            waiting_for_ready = False

    cv2.imshow('Webcam', img)
    
    if cv2.getWindowProperty('Webcam', cv2.WND_PROP_VISIBLE) < 1:
        break
        
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

if using_stream:
    stream.release()
else:
    cap.release()
cv2.destroyAllWindows()
ser.close()