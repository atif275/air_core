import speech_recognition as sr
from src.audio.core.microphone import recognizer, mic, setup_microphone

def recognize_speech():
    """Captures audio and converts to text."""
    try:
        with mic as source:
            print("[INFO] Listening for speech...")
            audio = recognizer.listen(source, timeout=300)
            transcription = recognizer.recognize_google(audio)
            return transcription
    except sr.UnknownValueError:
        print("[WARNING] Could not understand the audio.")
    except sr.RequestError as e:
        print(f"[ERROR] Could not request results from Google Speech-to-Text API: {e}")
    except sr.WaitTimeoutError:
        setup_microphone()
    return None