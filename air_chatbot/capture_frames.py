import cv2
import os
import time

# Create 'frames' directory if it doesn't exist
os.makedirs('frames', exist_ok=True)

# Initialize the video capture object
cap = cv2.VideoCapture(0)

frame_count = 0
start_time = time.time()

while True:
    # Capture frame-by-frame
    ret, frame = cap.read()
    if not ret:
        break

    # Save the frame as an image file
    frame_filename = f'frames/frame_{frame_count:04d}.jpg'
    cv2.imwrite(frame_filename, frame)
    print(f'Saved {frame_filename}')

    frame_count += 1

    # Calculate and display FPS
    elapsed_time = time.time() - start_time
    fps = frame_count / elapsed_time
    print(f'FPS: {fps:.2f}')

    # Display the resulting frame
    cv2.imshow('Frame Capture', frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the capture and close windows
cap.release()
cv2.destroyAllWindows() 