import requests
import time
import uuid
import pygame
import os
from dotenv import load_dotenv
from langdetect import detect

# Load environment variables
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Pygame setup
pygame.mixer.init()

# Default voice (Rachel)
ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"

def detect_language(text):
    try:
        lang = detect(text)
        return lang
    except Exception as e:
        print(f"[LANG DETECTION ERROR] {e}")
        return "en"  # fallback to English

def speak(text, voice_id=ELEVENLABS_VOICE_ID):
    try:
        filename = f"{uuid.uuid4()}.mp3"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",  # Handles both English and Hindi
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.75
            }
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)

            # Commented out pygame audio playback
            # pygame.mixer.music.load(filename)
            # pygame.mixer.music.play()
            # while pygame.mixer.music.get_busy():
            #     time.sleep(0.1)
            # pygame.mixer.music.unload()

            send_mp3_to_flask(filename, "http://192.168.1.14:5005/upload")
            os.remove(filename)
        else:
            print(f"[TTS ERROR] ElevenLabs API returned {response.status_code}: {response.text}")

    except Exception as e:
        print(f"[TTS ERROR] {e}")

def send_mp3_to_flask(file_path, endpoint_url):
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(endpoint_url, files=files)
            if response.status_code == 200:
                print(f"[UPLOAD SUCCESS] MP3 file sent to {endpoint_url}")
            else:
                print(f"[UPLOAD ERROR] Server returned {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[UPLOAD ERROR] {e}")

def test_chatbot():
    print("\n🤖 Chatbot Test Client — Auto-detect Language & Speak with ElevenLabs")
    print("Type your message and press Enter.")
    print("Type 'exit' to quit.\n")

    url = "http://localhost:5001/transcription"

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("Exiting. Goodbye!")
            break

        data = {
            "text": user_input,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            response = requests.post(url, json=data)

            if response.status_code == 200:
                result = response.json()
                bot_response = result["response"]

                print(f"\n🤖 Bot: {bot_response}")

                lang = detect_language(bot_response)
                print(f"🈯 Detected Language: {lang}")

                speak(bot_response)

            else:
                print(f"\n❌ Error: API returned status code {response.status_code}")
                print(f"Response: {response.text}\n")

        except requests.exceptions.ConnectionError:
            print("\n❌ Error: Could not connect to the server.")
            print("Make sure the Flask server (app.py) is running on http://localhost:5001\n")

        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    test_chatbot()
