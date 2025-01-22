import os
import openai

from openai import OpenAI
from gtts import gTTS
import serial
from pygame import mixer
import speech_recognition as sr
import time
from dotenv import load_dotenv
# Initialize pygame mixer
mixer.init()

# Setup serial connection (Update the port name to the one used by your Arduino)
ser = serial.Serial('/dev/cu.usbmodem11101', 9600)
time.sleep(2)  # Give some time for the serial connection to establish

def speak(text):
    print("Generating speech...")
    tts = gTTS(text=text, lang='en', tld='com', slow=False)  # Create speech
    tts.save("output.mp3")  # Save the speech to an mp3 file
    mixer.music.load("output.mp3")  # Load the mp3 file
    print("Speaking: " + text)
    ser.write(b's')  # Send command to start jaw movement
    mixer.music.play()  # Play the speech
    while mixer.music.get_busy():  # Wait for the speech to finish
        time.sleep(0.1)
    ser.write(b'e')  # Send command to stop jaw movement
    print("Speech and jaw movement completed.")

def handle_response(text):
    """
    Handle the response generation and speaking.
    """
    client = OpenAI()
    try:
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful personal assistant that generates responses just like any human being. Keep responses brief and humanistic.",
                },
                {
                    "role": "user",
                    "content": f" They said: '{text}'. How should I respond?",
                }
            ],
            model="gpt-3.5-turbo-16k",
        )
        response_text = completion.choices[0].message.content
        speak(response_text)
    except Exception as e:
        print(f"Failed to generate response: {e}")

def listen_and_respond():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        while True:
            try:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)
                text = recognizer.recognize_google(audio)
                print(f"Recognized speech: {text}")
                handle_response(text)
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                print("Could not understand audio")
            except sr.RequestError as e:
                print(f"Could not request results; {e}")

if __name__ == "__main__":
    # Ensure API Key is loaded
    load_dotenv()

    api_key = os.getenv('OPENAI_API_KEY')
    #OPENAI_API_KEY='sk-proj-u0Xwj6nrRQ8klTVD2xwrT3BlbkFJ5E6jFxMs4Jh77iZMNkjM'
    api_key = os.getenv('OPENAI_API_KEY')

    if not openai.api_key:
        print("API key not found. Please check your .env file.")
    else:
        print("API key loaded successfully.")
        
    openai.api_key = api_key or 'sk-proj-u0Xwj6nrRQ8klTVD2xwrT3BlbkFJ5E6jFxMs4Jh77iZMNkjM'
    listen_and_respond()

# Cleanup and close serial
ser.close()
