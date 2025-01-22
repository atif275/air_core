import numpy as np
import argparse
import matplotlib.pyplot as plt
import cv2
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Flatten
from tensorflow.keras.layers import Conv2D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.layers import MaxPooling2D
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import os
from pygame import mixer
import serial
import time
import playsound
from gtts import gTTS
import threading

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# command line argument
ap = argparse.ArgumentParser()
ap.add_argument("--mode",help="train/display")
mode = ap.parse_args().mode
mixer.init()
ser = serial.Serial('/dev/cu.usbmodem1101', 9600)
time.sleep(2)  # Give some time for the serial connection to establish

last_speak_time = 0  # Timestamp of the last time audio was played
minimum_interval = 3  # Minimum interval in seconds between audio outputs


class VideoCapture:
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self.q = []
        self.lock = threading.Lock()
        self.mutex = threading.Lock()
        self.running = True
        thread = threading.Thread(target=self.update, args=())
        thread.daemon = True
        thread.start()

    def update(self):
        while self.running:
            self.mutex.acquire()
            try:
                if self.cap.isOpened():
                    (status, frame) = self.cap.read()
                    if status:
                        with self.lock:
                            if len(self.q) < 2:
                                self.q.append(frame)
                    else:
                        time.sleep(0.1)
            finally:
                self.mutex.release()

    def read(self):
        with self.lock:
            if self.q:
                return True, self.q.pop(0)
            return False, None

    def release(self):
        self.running = False
        with self.mutex:
            self.cap.release()


def attempt_to_speak(display_emotion, last_announced_emotion):
    print("e2")
    global last_speak_time
    current_time = time.time()
    if display_emotion != last_announced_emotion and (current_time - last_speak_time) >= minimum_interval:
        print("e3")
        last_speak_time = current_time  # Update the last speak time to current
        threading.Thread(target=play_emotion_sound, args=(display_emotion,)).start()
        return True
    

def play_emotion_sound(emotion):
    #print("xxxxxxxxx"+emotion)
    tts = gTTS(text=emotion, lang='en')
    tts.save("emotion.mp3")
    mixer.music.load("emotion.mp3")
    print("Speaking: " + emotion)
    ser.write(b's')  # Send command to start jaw movement
    mixer.music.play()  # Play the speech
    while mixer.music.get_busy():  # Wait for the speech to finish
        time.sleep(0.01)
    ser.write(b'e')  # Send command to stop jaw movement
    print("Speech and jaw movement completed.")
    #playsound.playsound("emotion.mp3", True)

# plots accuracy and loss curves
def plot_model_history(model_history):
    """
    Plot Accuracy and Loss curves given the model_history
    """
    fig, axs = plt.subplots(1,2,figsize=(15,5))
    # summarize history for accuracy
    axs[0].plot(range(1,len(model_history.history['accuracy'])+1),model_history.history['accuracy'])
    axs[0].plot(range(1,len(model_history.history['val_accuracy'])+1),model_history.history['val_accuracy'])
    axs[0].set_title('Model Accuracy')
    axs[0].set_ylabel('Accuracy')
    axs[0].set_xlabel('Epoch')
    axs[0].set_xticks(np.arange(1,len(model_history.history['accuracy'])+1),len(model_history.history['accuracy'])/10)
    axs[0].legend(['train', 'val'], loc='best')
    # summarize history for loss
    axs[1].plot(range(1,len(model_history.history['loss'])+1),model_history.history['loss'])
    axs[1].plot(range(1,len(model_history.history['val_loss'])+1),model_history.history['val_loss'])
    axs[1].set_title('Model Loss')
    axs[1].set_ylabel('Loss')
    axs[1].set_xlabel('Epoch')
    axs[1].set_xticks(np.arange(1,len(model_history.history['loss'])+1),len(model_history.history['loss'])/10)
    axs[1].legend(['train', 'val'], loc='best')
    fig.savefig('plot.png')
    plt.show()

# Define data generators
train_dir = 'data/train'
val_dir = 'data/test'

num_train = 28709
num_val = 7178
batch_size = 64
num_epoch = 50

train_datagen = ImageDataGenerator(rescale=1./255)
val_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_directory(
        train_dir,
        target_size=(48,48),
        batch_size=batch_size,
        color_mode="grayscale",
        class_mode='categorical')

validation_generator = val_datagen.flow_from_directory(
        val_dir,
        target_size=(48,48),
        batch_size=batch_size,
        color_mode="grayscale",
        class_mode='categorical')

# Create the model
model = Sequential()

model.add(Conv2D(32, kernel_size=(3, 3), activation='relu', input_shape=(48,48,1)))
model.add(Conv2D(64, kernel_size=(3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Dropout(0.25))

model.add(Conv2D(128, kernel_size=(3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Conv2D(128, kernel_size=(3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Dropout(0.25))

model.add(Flatten())
model.add(Dense(1024, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(7, activation='softmax'))

# If you want to train the same model or try other models, go for this
if mode == "train":
    model.compile(loss='categorical_crossentropy',optimizer=Adam(lr=0.0001, decay=1e-6),metrics=['accuracy'])
    model_info = model.fit_generator(
            train_generator,
            steps_per_epoch=num_train // batch_size,
            epochs=num_epoch,
            validation_data=validation_generator,
            validation_steps=num_val // batch_size)
    plot_model_history(model_info)
    model.save_weights('model.h5')

# emotions will be displayed on your face from the webcam feed
elif mode == "display":
    video_stream = VideoCapture("rtsp://Atif:27516515@192.168.26.217/live")
    
    model.load_weights('EMOTUNE.h5')

    # prevents openCL usage and unnecessary logging messages
    cv2.ocl.setUseOpenCL(False)

    # dictionary which assigns each label an emotion (alphabetical order)
    emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Neutral", 3: "Happy", 4: "Neutral", 5: "Sad", 6: "Surprised"}

    # start the webcam feed
    #video_stream = cv2.VideoCapture(0)
    emotion_buffer = []
    buffer_size = 10  # Number of frames to consider for smoothing the prediction
    last_announced_emotion = None
    try:

        while True:
            # Find haar cascade to draw bounding box around face
            ret, frame = video_stream.read()
            if not ret:
                print("Failed to capture image from video stream.")
                continue
                #break
            facecasc = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = facecasc.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y-50), (x+w, y+h+10), (255, 0, 0), 2)
                roi_gray = gray[y:y + h, x:x + w]
                cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray, (48, 48)), -1), 0)
                prediction = model.predict(cropped_img)
                maxindex = int(np.argmax(prediction))

                # Update the emotion buffer with the most recent prediction
                if len(emotion_buffer) >= buffer_size:
                    emotion_buffer.pop(0)
                emotion_buffer.append(maxindex)

                # Find the most frequent emotion in the buffer to display
                if len(emotion_buffer) == buffer_size:
                    most_frequent_emotion = max(set(emotion_buffer), key=emotion_buffer.count)
                    display_emotion = emotion_dict[most_frequent_emotion]
                    cv2.putText(frame, display_emotion, (x+20, y-60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
                    # gTTS integration
                    # if display_emotion != last_announced_emotion:
                    #     threading.Thread(target=play_emotion_sound, args=(display_emotion,)).start()
                    #     last_announced_emotion = display_emotion
                    print("e1")
                    if attempt_to_speak(display_emotion, last_announced_emotion):

                        last_announced_emotion = display_emotion
            
            cv2.imshow('Emotion Detection', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            # cv2.imshow('Video', cv2.resize(frame, (1600,960), interpolation=cv2.INTER_CUBIC))
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break
    finally:
        video_stream.release()
        #cap.release()
        cv2.destroyAllWindows()
    