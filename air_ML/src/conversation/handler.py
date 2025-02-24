import threading
from queue import Queue, Empty
import sys
from src.audio.speech_to_text import recognize_speech
from src.audio.text_to_speech import speak
from src.conversation.summary import summarize_conversations
from src.audio.core.microphone import setup_microphone

def get_text_input(input_queue, stop_event):
    """Thread function to handle text input."""
    while not stop_event.is_set():
        try:
            text = input("Type (or press Enter to skip): ")
            if text.strip():  # Only add non-empty input to queue
                input_queue.put(("text", text))
        except EOFError:
            break

def get_voice_input(input_queue, stop_event):
    """Thread function to handle voice input."""
    setup_microphone()
    while not stop_event.is_set():
        speech = recognize_speech()
        if speech:
            input_queue.put(("voice", speech))

def recognize_speech_and_chat(stop_event, chatbot):
    """
    Handles both voice and text-based conversation simultaneously.
    """
    input_queue = Queue()
    
    # Start text input thread
    text_thread = threading.Thread(
        target=get_text_input, 
        args=(input_queue, stop_event)
    )
    text_thread.daemon = True
    text_thread.start()
    
    # Start voice input thread
    voice_thread = threading.Thread(
        target=get_voice_input, 
        args=(input_queue, stop_event)
    )
    voice_thread.daemon = True
    voice_thread.start()

    print("Ready for input! You can either type or speak.")
    
    while not stop_event.is_set():
        try:
            # Get input from either source with timeout
            input_type, user_input = input_queue.get(timeout=0.1)
            
            print(f"You ({input_type}): {user_input}")

            if user_input.lower() in ["bye", "exit", "quit"]:
                speak("Goodbye! Have a great day!")
                print("ChatBot: Goodbye! Have a great day!")
                summarize_conversations()
                stop_event.set()
                break

            response = chatbot.respond(user_input)
            print(f"ChatBot: {response}")

            # Remove sensitive info before speaking
            filtered_response = "\n".join(
                line for line in response.split("\n") 
                if not any(attr in line for attr in ["NAME=", "AGE=", "ETHNICITY="])
            )
            speak(filtered_response)
            
        except Empty:
            # Ignore timeout exceptions silently
            continue
        except Exception as e:
            print(f"Error: {str(e)}")
            continue
