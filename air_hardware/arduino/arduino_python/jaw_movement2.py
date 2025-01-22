import time
import serial
from gtts import gTTS
from pygame import mixer

# Initialize pygame mixer
mixer.init()

# Setup serial connection (Update the port name to the one used by your Arduino)
ser = serial.Serial('/dev/cu.usbmodem1101', 9600)
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
        time.sleep(0.01)
    ser.write(b'e')  # Send command to stop jaw movement
    print("Speech and jaw movement completed.")

if __name__ == "__main__":
    speak("Hello, I am Chappie, the robot created by .")

# Cleanup and close serial
ser.close()
