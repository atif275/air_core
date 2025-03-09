import cv2

video = cv2.VideoCapture("rtsp://Atif:27516515@192.168.1.12/live")


while True:
    _,frame = video.read()
    cv2.imshow("RSTP",frame)
    k = cv2.waitKey(1)
    if k== ord('q'):
        break

video.release()
cv2.distroyAllWindows()
