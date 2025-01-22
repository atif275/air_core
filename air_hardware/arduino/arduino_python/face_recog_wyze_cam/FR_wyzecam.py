import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime

# Set the path to your training images
path = 'Training_images'
images = []
classNames = []
myList = os.listdir(path)
print(myList)

# Filter and load images
image_extensions = ['.jpg', '.jpeg', '.png']  # Extend with other file types if needed
for cl in myList:
    if os.path.splitext(cl)[1].lower() in image_extensions:
        curImg = cv2.imread(f'{path}/{cl}')
        if curImg is not None:
            images.append(curImg)
            classNames.append(os.path.splitext(cl)[0])
        else:
            print(f'Failed to load image: {cl}')
    else:
        print(f'Skipped non-image file: {cl}')

print(classNames)

# Function to find face encodings
def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList

# Function to log attendance
def markAttendance(name):
    with open('Attendance.csv', 'r+') as f:
        myDataList = f.readlines()
        nameList = []
        for line in myDataList:
            entry = line.split(',')
            nameList.append(entry[0])
        if name not in nameList:
            now = datetime.now()
            dtString = now.strftime('%H:%M:%S')
            f.writelines(f'\n{name},{dtString}')

# Load face encodings
encodeListKnown = findEncodings(images)
print('Encoding Complete')

# Open the RTSP stream
cap = cv2.VideoCapture("rtsp://Atif:27516515@192.168.1.7/live")

if not cap.isOpened():
    print("Error: Cannot open video stream or file.")
else:
    while True:
        success, img = cap.read()
        if not success:
            print("Failed to capture image from video stream.")
            break

        # Resize image for faster face recognition processing
        imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        facesCurFrame = face_recognition.face_locations(imgS)
        encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

        # Compare faces and find matches
        for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
            matchIndex = np.argmin(faceDis)

            if matches[matchIndex]:
                name = classNames[matchIndex].upper()
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                # markAttendance(name)

        cv2.imshow('Facial Recognition', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
