import pyaudio
import numpy as np
import wave
import os
from datetime import datetime
import torch
import torchaudio
import threading
import queue
import platform
import time
from openai import OpenAI
from dotenv import load_dotenv
import requests

class VoiceActivityDetector:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        # self.client = OpenAI()  # Commented out OpenAI client
        
        # Audio parameters
        if platform.system() == 'Darwin':  # macOS
            self.CHUNK = 512  # Standard chunk size for macOS
        else:  # Raspberry Pi
            self.CHUNK = 1536  # Increased chunk size for 48kHz (1536 = 48kHz/31.25)
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000  # Silero VAD requires 16kHz
        
        # VAD parameters
        self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                          model='silero_vad',
                                          force_reload=False)
        self.speech_probability = 0.0
        self.is_speaking = False
        self.silence_frames = 0
        self.speech_frames = 0
        
        # Timing parameters (in frames)
        self.silence_threshold = 30  # ~1.5 seconds of silence to end recording
        self.min_speech_frames = 20  # ~1 second of speech to start recording
        self.cooldown_frames = 30    # ~1.5 seconds cooldown between recordings
        
        # State tracking
        self.last_recording_time = 0
        self.audio_buffer = []
        self.is_recording = False
        self.audio_queue = queue.Queue()
        # self.transcription_queue = queue.Queue()  # Commented out transcription queue
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Create output directories if they don't exist
        self.output_dir = "recordings"
        # self.transcription_dir = "transcriptions"  # Commented out transcription directory
        for dir_path in [self.output_dir]:  # Removed transcription_dir
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
        # Start transcription thread
        # self.transcription_thread = threading.Thread(target=self.transcription_worker)  # Commented out transcription thread
        # self.transcription_thread.daemon = True
        # self.transcription_thread.start()

    def get_audio_input_device(self):
        """Get the appropriate audio input device"""
        print("\nAvailable audio devices:")
        for i in range(self.audio.get_device_count()):
            dev_info = self.audio.get_device_info_by_index(i)
            print(f"Device {i}: {dev_info['name']} (Input Channels: {dev_info['maxInputChannels']})")
        
        # On macOS, look for built-in microphone
        if platform.system() == 'Darwin':
            # First try to find the built-in microphone
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if (dev_info['maxInputChannels'] > 0 and 
                    ('built-in' in dev_info['name'].lower() or 
                     'internal' in dev_info['name'].lower() or
                     'macbook' in dev_info['name'].lower())):
                    print(f"\nSelected built-in microphone: {dev_info['name']}")
                    return i
            
            # If no built-in mic found, try to find any input device that's not BlackHole
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if (dev_info['maxInputChannels'] > 0 and 
                    'blackhole' not in dev_info['name'].lower()):
                    print(f"\nSelected fallback input device: {dev_info['name']}")
                    return i
            
            # If still no device found, use the first input device
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if dev_info['maxInputChannels'] > 0:
                    print(f"\nSelected first available input device: {dev_info['name']}")
                    return i
        else:  # For Raspberry Pi
            # On Raspberry Pi, look for USB audio device
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if (dev_info['maxInputChannels'] > 0 and 
                    'usb' in dev_info['name'].lower()):
                    print(f"\nSelected USB audio device: {dev_info['name']}")
                    # Use device's default sample rate for Pi
                    self.RATE = int(dev_info['defaultSampleRate'])
                    print(f"Using device's default sample rate: {self.RATE} Hz")
                    return i
            
            # Fallback to any input device
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if dev_info['maxInputChannels'] > 0:
                    print(f"\nSelected fallback input device: {dev_info['name']}")
                    # Use device's default sample rate for Pi
                    self.RATE = int(dev_info['defaultSampleRate'])
                    print(f"Using device's default sample rate: {self.RATE} Hz")
                    return i
        
        print("\nNo suitable input device found!")
        return 0

    def process_audio_chunk(self, audio_data):
        """Process audio chunk with Silero VAD"""
        # Resample to 16kHz if needed
        if self.RATE != 16000:
            audio_data = self.resample_audio(audio_data)
        
        # Ensure audio chunk is not too short
        if len(audio_data) < 512:  # Silero VAD requires at least 512 samples
            return
        
        # Convert to float32 and normalize
        audio_float = audio_data.astype(np.float32) / 32768.0
        # Convert to tensor
        audio_tensor = torch.from_numpy(audio_float).unsqueeze(0)
        
        # Get speech probability
        with torch.no_grad():
            self.speech_probability = self.model(audio_tensor, 16000).item()
        
        # Check if enough time has passed since last recording
        current_time = time.time()
        if current_time - self.last_recording_time < self.cooldown_frames * (self.CHUNK / 16000):
            return
        
        # Update speech state
        if self.speech_probability > 0.5:  # Speech detected
            self.speech_frames += 1
            self.silence_frames = 0
            
            # Start recording if we've detected enough speech
            if not self.is_speaking and self.speech_frames >= self.min_speech_frames:
                self.is_speaking = True
                print("\n🎤 Speech detected! Starting recording...")
        else:  # Silence detected
            self.silence_frames += 1
            self.speech_frames = 0
            
            # Stop recording if we've had enough silence
            if self.is_speaking and self.silence_frames >= self.silence_threshold:
                self.is_speaking = False
                print("\n🔇 Speech ended. Saving recording...")
                self.last_recording_time = current_time
                # Signal to save the recording
                self.audio_queue.put(("save", None))

    def resample_audio(self, audio_data):
        """Resample audio to 16kHz"""
        # Convert to float32 for resampling
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        # Calculate the number of samples needed for 16kHz
        target_length = int(len(audio_float) * 16000 / self.RATE)
        
        # Resample using linear interpolation
        resampled = np.interp(
            np.linspace(0, len(audio_float) - 1, target_length),
            np.arange(len(audio_float)),
            audio_float
        )
        
        # Convert back to int16
        return (resampled * 32768.0).astype(np.int16)

    def transcription_worker(self):
        """Worker thread for handling transcriptions"""
        while True:
            try:
                # Get the next file to transcribe
                wav_file = self.transcription_queue.get()
                if wav_file is None:  # Shutdown signal
                    break
                
                # Transcribe the audio file
                try:
                    print("⏳ Sending audio to OpenAI Whisper API...")
                    with open(wav_file, "rb") as f:
                        response = requests.post(
                            "https://api.openai.com/v1/audio/transcriptions",
                            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
                            data={
                                "model": "whisper-1",
                                "language": "ur",  # Set primary language to Urdu
                                "prompt": """Respond only in Urdu, English, or Arabic. 
                                - Keep Urdu words in Urdu script
                                - Keep English words as they are
                                - Keep Arabic words in Arabic script
                                - Translate Hindi to Urdu
                                - Translate other languages to English"""
                            },
                            files={"file": ("audio.wav", f, "audio/wav")},
                        )

                    if response.status_code == 200:
                        transcript = response.json()["text"]
                        # Save transcription to file
                        base_name = os.path.splitext(os.path.basename(wav_file))[0]
                        txt_file = os.path.join(self.transcription_dir, f"{base_name}.txt")
                        
                        with open(txt_file, "w", encoding="utf-8") as f:
                            f.write(transcript)
                        
                        print(f"\n📝 Transcription saved to {txt_file}")
                        print(f"Transcription: {transcript}")
                    else:
                        print(f"❌ API Error [{response.status_code}]: {response.text}")
                
                except Exception as e:
                    print(f"\n❌ Transcription error: {str(e)}")
                
                # Mark task as done
                self.transcription_queue.task_done()
            except queue.Empty:
                time.sleep(0.1)

    def save_recording(self):
        """Save the recorded audio to a WAV file"""
        if not self.audio_buffer:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"recording_{timestamp}.wav")
        
        # Convert buffer to numpy array
        audio_data = np.concatenate(self.audio_buffer)
        
        # Save to WAV file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(audio_data.tobytes())
        
        print(f"✅ Saved recording to {filename}")
        
        # Queue the file for transcription
        # self.transcription_queue.put(filename)  # Commented out transcription queue
        
        # Clear the buffer
        self.audio_buffer = []

    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream"""
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        
        # Process with VAD
        self.process_audio_chunk(audio_data)
        
        # If speaking, add to buffer
        if self.is_speaking:
            self.audio_buffer.append(audio_data)
        
        return (in_data, pyaudio.paContinue)

    def start(self):
        """Start voice activity detection"""
        input_device = self.get_audio_input_device()
        
        # Open audio stream
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            input_device_index=input_device,
            frames_per_buffer=self.CHUNK,
            stream_callback=self.audio_callback
        )
        
        print("\n🎤 Voice Activity Detection started...")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                # Check for save signal
                try:
                    cmd, _ = self.audio_queue.get_nowait()
                    if cmd == "save":
                        self.save_recording()
                except queue.Empty:
                    pass
                
                # Visualize speech state
                state = "SPEAKING" if self.is_speaking else "SILENT"
                print(f"\rCurrent state: {state} | VAD: {self.speech_probability:.2f}", end='')
                
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        
        # Save any remaining audio
        if self.audio_buffer:
            self.save_recording()
        
        # Signal transcription thread to stop
        # self.transcription_queue.put(None)  # Commented out transcription cleanup
        # self.transcription_thread.join()  # Commented out transcription thread join

if __name__ == "__main__":
    detector = VoiceActivityDetector()
    detector.start() 