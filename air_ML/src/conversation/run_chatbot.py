import sys
import os
import threading
import signal

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(project_root)

from src.conversation.chatbot import OpenAIChatBot
from src.config.settings import load_api_key
from src.audio.wake_word import detect_wake_word
from src.database.db_setup import ensure_database
from src.audio.text_to_speech import speak
from src.conversation.handler import recognize_speech_and_chat

def handle_exit(stop_event):
    """
    Handles graceful exit on Ctrl+C or termination signal.
    """
    print("\n[INFO] Interrupt received. Cleaning up...")
    stop_event.set()
    sys.exit(0)

def run_chatbot():
    print("[INFO] Waiting for wake word...")
    detect_wake_word()  # This will block until the wake word is detected
    print("[INFO] Wake word detected. Starting chatbot...")

    api_key = load_api_key()
    if not api_key:
        print("Error: OpenAI API key is not set.")
        exit(1)

    chatbot = OpenAIChatBot(api_key)
    speak("Hello!")
    print("ChatBot: Hello!")

    stop_event = threading.Event()
    signal.signal(signal.SIGINT, lambda signum, frame: handle_exit(stop_event))

    chatbot_thread = threading.Thread(target=recognize_speech_and_chat, args=(stop_event, chatbot))
    chatbot_thread.start()

    try:
        chatbot_thread.join()
    except KeyboardInterrupt:
        handle_exit(stop_event)

if __name__ == "__main__":
    # Ensure database is set up before starting the chatbot
    ensure_database()
    run_chatbot()

__all__ = ['run_chatbot']  # Make run_chatbot available when importing from this module
