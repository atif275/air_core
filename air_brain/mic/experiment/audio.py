import pyaudio
import numpy as np
import wave
import threading
import time
import subprocess
import os
from datetime import datetime
import sys
import platform
import select

class AudioMonitor:
    def __init__(self):
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.system = platform.system().lower()
        # Set sample rate based on system
        self.RATE = 16000 if self.system == 'darwin' else 48000  # 16kHz for macOS, 48kHz for Pi
        self.THRESHOLD = 1000  # Adjust this value based on your environment
        self.is_recording = False
        self.recording_thread = None
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording_process = None
        self.output_file = None
        self.level_file = "level.txt"
        
        # Print system info and available devices
        print(f"Running on {self.system}")
        print(f"Using sample rate: {self.RATE} Hz")
        print("Available audio devices:")
        for i in range(self.audio.get_device_count()):
            dev_info = self.audio.get_device_info_by_index(i)
            print(f"Device {i}: {dev_info['name']}")

    def get_audio_input_device(self):
        """Get the appropriate audio input device based on the system"""
        if self.system == 'darwin':  # macOS
            # On macOS, we need to find the built-in microphone
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                # Check if it's an input device and has "Microphone" in the name
                if dev_info['maxInputChannels'] > 0 and 'microphone' in dev_info['name'].lower():
                    print(f"Selected input device: {dev_info['name']}")
                    return i
            # If no microphone found, use the first input device
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if dev_info['maxInputChannels'] > 0:
                    print(f"Using fallback input device: {dev_info['name']}")
                    return i
            return 0  # Default to first device if no input devices found
        else:  # Linux (Raspberry Pi)
            # On Raspberry Pi, we need to find the USB audio device
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if dev_info['maxInputChannels'] > 0 and 'usb' in dev_info['name'].lower():
                    print(f"Selected USB audio device: {dev_info['name']}")
                    return i
            # If no USB device found, try to find any input device
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if dev_info['maxInputChannels'] > 0:
                    print(f"Using fallback input device: {dev_info['name']}")
                    return i
            return 0  # Default to first device if no input devices found

    def start_monitoring(self):
        """Start monitoring audio input"""
        input_device = self.get_audio_input_device()
        print(f"Opening audio stream with device index: {input_device}")
        
        # Get device info for the selected device
        dev_info = self.audio.get_device_info_by_index(input_device)
        print(f"Device info: {dev_info}")
        
        # Use the device's default sample rate for monitoring
        if self.system != 'darwin':  # Only for Pi
            self.RATE = int(dev_info['defaultSampleRate'])
            print(f"Using device's default sample rate: {self.RATE} Hz")
        
        # Adjust channels based on device capabilities
        channels = min(self.CHANNELS, int(dev_info['maxInputChannels']))
        print(f"Using {channels} channels")
        
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=channels,
            rate=self.RATE,
            input=True,
            input_device_index=input_device,
            frames_per_buffer=self.CHUNK
        )
        
        print("🎤 Audio monitoring started...")
        print("Press 'r' to start recording, 's' to stop recording, 'q' to quit")
        
        try:
            while True:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Calculate audio level
                level = np.abs(audio_data).mean()
                
                # Visualize audio level
                self.visualize_audio(level)
                
                # Write level to file
                self.write_level_to_file(level)
                
                # Check for user input
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    cmd = sys.stdin.readline().strip().lower()
                    if cmd == 'r' and not self.is_recording:
                        self.start_recording()
                    elif cmd == 's' and self.is_recording:
                        self.stop_recording()
                    elif cmd == 'q':
                        break
                
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()

    def visualize_audio(self, level):
        """Visualize audio level in terminal"""
        # Scale the level to a reasonable range for visualization
        scaled_level = min(int(level / 100), 50)
        bar = '█' * scaled_level + '░' * (50 - scaled_level)
        print(f"\rAudio Level: [{bar}] {level:.0f}", end='')

    def write_level_to_file(self, level):
        """Write audio level to file with timestamp"""
        #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.level_file, "a") as f:
            f.write(f"Level: {level:.0f}\n")

    def start_recording(self):
        """Start recording audio using ffmpeg"""
        if not self.is_recording:
            self.is_recording = True
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_file = f"recording_{timestamp}.wav"
            
            print(f"\n🎙️ Started recording to {self.output_file}")
            
            if self.system == 'darwin':  # macOS
                self.recording_process = subprocess.Popen([
                    "ffmpeg",
                    "-f", "avfoundation",  # macOS audio input
                    "-i", ":0",  # Default input device
                    "-ac", "1",
                    "-ar", "16000",  # Fixed 16kHz for macOS
                    self.output_file
                ])
            else:  # Linux (Raspberry Pi)
                self.recording_process = subprocess.Popen([
                    "ffmpeg",
                    "-f", "alsa",
                    "-i", "plughw:2,0",  # Use the USB audio device directly
                    "-ac", "1",
                    "-ar", "16000",  # Always use 16kHz for recording on Pi
                    self.output_file
                ])

    def stop_recording(self):
        """Stop recording audio"""
        if self.is_recording and self.recording_process:
            self.is_recording = False
            self.recording_process.terminate()
            self.recording_process.wait()
            print(f"\n✅ Recording saved to {self.output_file}")

    def cleanup(self):
        """Clean up resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        if self.is_recording:
            self.stop_recording()

if __name__ == "__main__":
    monitor = AudioMonitor()
    monitor.start_monitoring() 
    