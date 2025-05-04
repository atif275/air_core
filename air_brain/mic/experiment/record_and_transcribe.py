import subprocess
import os
import requests
from dotenv import load_dotenv
import platform
import pyaudio
import numpy as np
import threading
import time

# Load OpenAI API key
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
assert API_KEY, "OPENAI_API_KEY not found in .env file!"

class AudioVisualizer:
    def __init__(self):
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_visualizing = False
        self.visualization_thread = None

    def start_visualization(self):
        """Start audio visualization in a separate thread"""
        system = platform.system().lower()
        if system == 'darwin':  # macOS
            input_device = self.find_mac_input_device()
        else:  # Linux (Raspberry Pi)
            input_device = 0

        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            input_device_index=input_device,
            frames_per_buffer=self.CHUNK
        )
        
        self.is_visualizing = True
        self.visualization_thread = threading.Thread(target=self._visualize_loop)
        self.visualization_thread.start()

    def find_mac_input_device(self):
        """Find the built-in microphone on macOS"""
        for i in range(self.audio.get_device_count()):
            dev_info = self.audio.get_device_info_by_index(i)
            if dev_info['maxInputChannels'] > 0 and 'built-in' in dev_info['name'].lower():
                return i
        return 0

    def _visualize_loop(self):
        """Main visualization loop"""
        try:
            while self.is_visualizing:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                level = np.abs(audio_data).mean()
                self.visualize_audio(level)
        except Exception as e:
            print(f"Visualization error: {e}")

    def visualize_audio(self, level):
        """Visualize audio level in terminal"""
        scaled_level = min(int(level / 100), 50)
        bar = '█' * scaled_level + '░' * (50 - scaled_level)
        print(f"\rAudio Level: [{bar}] {level:.0f}", end='')

    def stop_visualization(self):
        """Stop audio visualization"""
        if self.is_visualizing:
            self.is_visualizing = False
            if self.visualization_thread:
                self.visualization_thread.join()
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.audio.terminate()

def record_audio(filename="output.wav", duration=10):
    print(f"🎙️ Recording {duration} seconds of audio...")
    
    # Start visualization
    visualizer = AudioVisualizer()
    visualizer.start_visualization()
    
    # Get system type
    system = platform.system().lower()
    
    if system == 'darwin':  # macOS
        command = [
            "ffmpeg",
            "-f", "avfoundation",  # macOS audio input
            "-i", ":0",  # Default input device
            "-t", str(duration),
            "-ac", "1",
            "-ar", "16000",
            filename
        ]
    else:  # Linux (Raspberry Pi)
    command = [
        "ffmpeg",
        "-f", "alsa",
        "-i", "default",
        "-t", str(duration),
        "-ac", "1",
        "-ar", "16000",
        filename
    ]
    
    subprocess.run(command, check=True)
    print(f"\n✅ Saved audio to: {filename}")
    
    # Stop visualization
    visualizer.stop_visualization()

def transcribe_audio(filepath):
    print("⏳ Sending audio to OpenAI Whisper API...")
    with open(filepath, "rb") as f:
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            data={"model": "whisper-1"},
            files={"file": ("audio.wav", f, "audio/wav")},
        )

    if response.status_code == 200:
        print("\n🧾 Transcribed Text:\n" + response.json()["text"])
    else:
        print(f"❌ API Error [{response.status_code}]: {response.text}")

if __name__ == "__main__":
    record_audio("recorded.wav", duration=10)
    transcribe_audio("recorded.wav")
