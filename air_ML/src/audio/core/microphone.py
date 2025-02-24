import speech_recognition as sr

recognizer = sr.Recognizer()
mic = sr.Microphone()

def setup_microphone():
    """Setup and calibrate the microphone."""
    with mic as source:
        print("[INFO] Calibrating microphone... Please wait...")
        recognizer.adjust_for_ambient_noise(source, duration=3)
        print("[INFO] Microphone calibrated. You can start speaking.")
    return recognizer, mic 