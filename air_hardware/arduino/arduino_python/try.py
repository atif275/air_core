import json
import speech_recognition as sr
from gtts import gTTS
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import serial
from pygame import mixer

# Load responses from JSON
with open('responses.json', 'r') as file:
    responses = json.load(file)

# Initialize serial connection for jaw movement (update as per your setup)
ser = serial.Serial('/dev/cu.usbmodem11101', 9600)

# Function to play text-to-speech
def speak(text):
    print("Speaking:", text)
    tts = gTTS(text=text, lang='en')
    filename = 'temp.mp3'
    tts.save(filename)
    os.system(f'afplay {filename}')
    os.remove(filename)

# Function to find the response based on keywords
def get_response(text):
    for keyword, response in responses.items():
        if keyword in text.lower():
            if "age" in keyword:
                today = datetime.now()
                if "creator" in keyword:
                    dob = datetime(2002, 3, 5)
                else:
                    dob = datetime(2024, 6, 10)
                age = relativedelta(today, dob)
                return response.replace("Calculate his age from today's date.", f"Atif is {age.years} years and {age.months} months old.").replace("Calculate my age from today's date.", f"I am {age.years} years and {age.months} months old.")
            return response
    return "Sorry, I don't understand that question."

# Listening and responding
def listen_and_respond():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        while True:
            print("Listening...")
            audio = recognizer.listen(source)
            try:
                text = recognizer.recognize_google(audio)
                print("You said:", text)
                response = get_response(text)
                ser.write(b's')  # Start jaw movement
                speak(response)
                ser.write(b'e')  # Stop jaw movement
            except sr.UnknownValueError:
                print("Could not understand audio")
            except sr.RequestError as e:
                print("Could not request results from Google Speech Recognition service; {0}".format(e))

if __name__ == '__main__':
    mixer.init()
    listen_and_respond()
