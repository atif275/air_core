import os
import pygame
from gtts import gTTS

def speak(text):
    """
    Convert text to speech using gTTS and play the output audio.
    """
    try:
        tts = gTTS(text=text, lang='en')
        audio_file = "response.mp3"
        tts.save(audio_file)

        pygame.mixer.init()
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            continue

        pygame.mixer.quit()
        os.remove(audio_file)
    except Exception as e:
        print(f"[ERROR] Failed to generate speech: {e}")
