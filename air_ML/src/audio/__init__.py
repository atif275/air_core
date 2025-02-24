from .speech_to_text import recognize_speech
from .text_to_speech import speak
from .wake_word import detect_wake_word
from .core.microphone import setup_microphone

__all__ = ['recognize_speech', 'speak', 'detect_wake_word', 'setup_microphone']
