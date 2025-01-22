import os
import cv2
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Flatten, Conv2D, MaxPooling2D
from tensorflow.keras.optimizers import Adam
from gtts import gTTS
import threading
import speech_recognition as sr
from dotenv import load_dotenv
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import openai
from openai import OpenAI

current_emotion = "Neutral"
emotion_lock = threading.Lock()
# Load environment variables
load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
#OPENAI_API_KEY='sk-proj-u0Xwj6nrRQ8klTVD2xwrT3BlbkFJ5E6jFxMs4Jh77iZMNkjM'
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("API key not found. Please check your .env file and ensure the OPENAI_API_KEY variable is set.")
else:
    print(f"API key loaded successfully: {api_key}")

# Manually setting the API key for debugging (remove in production)
openai.api_key = api_key or 'sk-proj-u0Xwj6nrRQ8klTVD2xwrT3BlbkFJ5E6jFxMs4Jh77iZMNkjM'

# Define the model globally if not already
model = Sequential([
    Conv2D(32, kernel_size=(3, 3), activation='relu', input_shape=(48, 48, 1)),
    Conv2D(64, kernel_size=(3, 3), activation='relu'),
    MaxPooling2D(pool_size=(2, 2)),
    Dropout(0.25),
    Conv2D(128, kernel_size=(3, 3), activation='relu'),
    MaxPooling2D(pool_size=(2, 2)),
    Conv2D(128, kernel_size=(3, 3), activation='relu'),
    MaxPooling2D(pool_size=(2, 2)),
    Dropout(0.25),
    Flatten(),
    Dense(1024, activation='relu'),
    Dropout(0.5),
    Dense(7, activation='softmax')
])

def speak(text):
    tts = gTTS(text=text, lang='en')
    tts.save("output.mp3")
    os.system("afplay output.mp3")

# def handle_response(text, emotion):
#     try:
#         response = openai.Completion.create(
#             model="gpt-3.5-turbo",
#             prompt=f"The user seems to be {emotion}. They said: '{text}'. How should I respond?",
#             max_tokens=150,
#             temperature=0.7
#         )
#         response_text = response.choices[0].text.strip()
#         speak(response_text)
#     except Exception as e:
#         print(f"Failed to generate response: {e}")
def async_handle_response(text, emotion):
    """
    This function runs in a separate thread to handle the response generation
    and speaking, which allows the main video processing to continue uninterrupted.
    """
    client = OpenAI()
    try:
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful personal assistant that generates responses considering user emotions. Keep responses brief and humanistic.",
                },
                {
                    "role": "user",
                    "content": f"The user seems to be {emotion}. They said: '{text}'. How should I respond?",
                }
            ],
            model="gpt-3.5-turbo-16k",
        )
        response_text = completion.choices[0].message.content
        speak(response_text)
    except Exception as e:
        print(f"Failed to generate response: {e}")

def handle_response(text, emotion):
    """
    Initiates an asynchronous response handling to prevent blocking the main thread
    that processes video and detects emotion.
    """
    threading.Thread(target=async_handle_response, args=(text, emotion)).start()

def listen_and_respond():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        while True:
            try:
                print("Listening...")
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                text = recognizer.recognize_google(audio)
                print(f"Recognized speech: {text}")
                with emotion_lock:
                    handle_response(text, current_emotion)
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                print("Could not understand audio")
            except sr.RequestError as e:
                print(f"Could not request results; {e}")

# def handle_response(text,emotion):
#     if "what is my emotion" in text.lower() or "how do I look" in text.lower():
#         speak(f"Your current emotion seems to be {emotion}.")
#         return
#     client = OpenAI()
#     try:
#         completion = client.chat.completions.create(
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "You are a helpful personal assistant That generate response and keep track od user emotions provided by the user. Generate short answers only. Make sure the conversation looks more humanistic.",
#                 },
#                 {
#                     "role": "user",
#                     "content": f"The user seems to be {emotion}. They said: '{text}'. How should I respond?",
#                 }
#             ],
#             model="gpt-3.5-turbo-16k",
#         )
#         response_text = completion.choices[0].message.content
#         speak(response_text)
#     except Exception as e:
#         print(f"Failed to generate response: {e}")

# def listen_and_respond():
#     global current_emotion
#     recognizer = sr.Recognizer()
#     with sr.Microphone() as source:
#         while True:
#             try:
#                 print("Listening...")
#                 audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
#                 text = recognizer.recognize_google(audio)
#                 print(f"Recognized speech: {text}")
#                 with emotion_lock:
#                     handle_response(text, current_emotion)
#             except sr.WaitTimeoutError:
#                 continue
#             except sr.UnknownValueError:
#                 print("Could not understand audio")
#             except sr.RequestError as e:
#                 print(f"Could not request results; {e}")


def webcam_feed(model):
    global current_emotion
    cap = cv2.VideoCapture(0)
    model.load_weights('model.h5')
    emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Fearful", 3: "Happy", 4: "Neutral", 5: "Sad", 6: "Surprised"}
    emotion_buffer = []
    buffer_size = 10

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        facecasc = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = facecasc.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y-50), (x+w, y+h+10), (255, 0, 0), 2)
            roi_gray = gray[y:y + h, x:x + w]
            cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray, (48, 48)), -1), 0)
            prediction = model.predict(cropped_img)
            maxindex = int(np.argmax(prediction))

            if len(emotion_buffer) >= buffer_size:
                emotion_buffer.pop(0)
            emotion_buffer.append(maxindex)

            if len(emotion_buffer) == buffer_size:
                most_frequent_emotion = max(set(emotion_buffer), key=emotion_buffer.count)
                with emotion_lock:
                    current_emotion = emotion_dict[most_frequent_emotion]

                cv2.putText(frame, current_emotion, (x+20, y-60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.imshow('Video', cv2.resize(frame, (1600,960), interpolation=cv2.INTER_CUBIC))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


def main():
    threading.Thread(target=listen_and_respond).start()
    webcam_feed(model)

if __name__ == "__main__":
    main()
