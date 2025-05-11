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
from whisperservice import WhisperService
from flask import Flask, request, jsonify
import pygame
import signal

class AudioResponseServer:
    def __init__(self):
        self.app = Flask(__name__)
        self.UPLOAD_FOLDER = 'uploads'
        os.makedirs(self.UPLOAD_FOLDER, exist_ok=True)
        self.current_audio_thread = None
        self.is_playing = False
        self.playback_lock = threading.Lock()
        
        # Initialize pygame mixer
        pygame.mixer.init()
        
        # Set up Flask routes
        self.app.route('/upload', methods=['POST'])(self.upload_audio)
        
    def play_audio(self, filepath):
        with self.playback_lock:
            if self.is_playing:
                pygame.mixer.music.stop()
            self.is_playing = True
            
        try:
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            
            # Keep running until music finishes playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
        finally:
            with self.playback_lock:
                self.is_playing = False
    
    def upload_audio(self):
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if not file.filename.lower().endswith('.mp3'):
            return jsonify({'error': 'Only MP3 files are allowed'}), 400

        filepath = os.path.join(self.UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # Play audio in a separate thread
        if self.current_audio_thread and self.current_audio_thread.is_alive():
            self.current_audio_thread.join(timeout=0.1)
        
        self.current_audio_thread = threading.Thread(target=self.play_audio, args=(filepath,))
        self.current_audio_thread.daemon = True
        self.current_audio_thread.start()

        return jsonify({'message': f'File {file.filename} uploaded and playing'}), 200
    
    def stop_playback(self):
        with self.playback_lock:
            if self.is_playing:
                pygame.mixer.music.stop()
                self.is_playing = False
    
    def run_server(self):
        self.app.run(host='0.0.0.0', port=5005, debug=False)

class VoiceActivityDetector:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.client = OpenAI()
        
        # Initialize WhisperService with romanization enabled
        self.whisper_service = WhisperService(romanize=True, translate_to_english=False)
        
        # Initialize audio response server
        self.audio_server = AudioResponseServer()
        
        # Start Flask server in a separate thread
        self.server_thread = threading.Thread(target=self.audio_server.run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
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
        
        # Enhanced VAD parameters
        self.speech_probability = 0.0
        self.is_speaking = False
        self.silence_frames = 0
        self.speech_frames = 0
        self.energy_threshold = 0.01  # Base energy threshold
        self.min_energy = float('inf')
        self.max_energy = float('-inf')
        
        # Adaptive thresholds
        self.silence_threshold = 20  # ~1 second of silence to end recording
        self.min_speech_frames = 10  # ~0.5 second of speech to start recording
        self.cooldown_frames = 20    # ~1 second cooldown between recordings
        self.vad_threshold = 0.2     # Lowered VAD threshold for Pi
        self.adaptive_threshold = 0.2 # Lowered adaptive threshold for Pi
        
        # New parameters for distant sound handling
        self.min_energy_for_speech = 0.008  # Lowered for Pi
        self.max_energy_for_speech = 0.1    # Maximum energy to consider as speech
        self.distant_sound_vad_threshold = 0.5  # Lowered for Pi
        
        # Speech pause handling
        self.pause_frames = 0
        self.max_pause_frames = 50  # ~2.5 seconds of allowed pause (at 20ms per frame)
        self.last_speech_time = 0
        
        # State tracking
        self.last_recording_time = 0
        self.audio_buffer = []
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.transcription_queue = queue.Queue()
        self.state_history = []  # Track state changes for analysis
        
        # Logging parameters
        self.log_file = "vad_analysis.log"
        self.log_interval = 100  # Log every 100 chunks
        self.chunk_counter = 0
        self.last_log_time = time.time()
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Create output directories if they don't exist
        self.output_dir = "recordings"
        self.transcription_dir = "transcriptions"
        for dir_path in [self.output_dir, self.transcription_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
        # Initialize log file
        with open(self.log_file, "w") as f:
            f.write("timestamp,chunk_counter,vad_probability,energy,adaptive_threshold,energy_threshold,is_speaking,speech_frames,silence_frames\n")
        
        # Start transcription thread
        self.transcription_thread = threading.Thread(target=self.transcription_worker)
        self.transcription_thread.daemon = True
        self.transcription_thread.start()
        
        # Load server configuration from .env
        self.server_url = os.getenv('SERVER_URL', 'http://192.168.1.9:5001/transcription')
        self.server_timeout = int(os.getenv('SERVER_TIMEOUT', '10'))

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

    def calculate_energy(self, audio_data):
        """Calculate the energy of the audio chunk"""
        # Normalize based on platform
        if platform.system() == 'Darwin':
            return np.mean(np.abs(audio_data)) / 32768.0
        else:  # Raspberry Pi
            # Apply different normalization for 48kHz
            energy = np.mean(np.abs(audio_data)) / 32768.0
            # Scale down energy for 48kHz to match 16kHz levels
            return energy * 0.5  # Reduce by half to match 16kHz levels

    def update_energy_thresholds(self, energy):
        """Update min and max energy thresholds"""
        self.min_energy = min(self.min_energy, energy)
        self.max_energy = max(self.max_energy, energy)
        
        # Update energy threshold based on min/max
        if self.max_energy > self.min_energy:
            if platform.system() == 'Darwin':
                self.energy_threshold = self.min_energy + 0.05 * (self.max_energy - self.min_energy)
                # Ensure minimum threshold
                self.energy_threshold = max(0.01, self.energy_threshold)
            else:  # Raspberry Pi
                # More aggressive threshold adaptation for Pi
                self.energy_threshold = self.min_energy + 0.02 * (self.max_energy - self.min_energy)
                # Lower minimum threshold for Pi
                self.energy_threshold = max(0.005, self.energy_threshold)
            
            # Update speech energy thresholds based on environment
            if platform.system() == 'Darwin':
                self.min_energy_for_speech = max(0.015, self.energy_threshold * 1.5)
                self.max_energy_for_speech = min(0.1, self.energy_threshold * 10)
            else:  # Raspberry Pi
                # Much more lenient thresholds for Pi
                self.min_energy_for_speech = max(0.002, self.energy_threshold * 0.5)  # Lower threshold for Pi
                self.max_energy_for_speech = min(0.2, self.energy_threshold * 20)     # Higher max for Pi

    def is_speech(self, vad_prob, energy):
        """Enhanced speech detection with distant sound handling"""
        # Update adaptive threshold based on recent history
        if len(self.state_history) > 10:
            recent_speech = sum(self.state_history[-10:]) / 10.0
            if platform.system() == 'Darwin':
                self.adaptive_threshold = max(0.2, min(0.4, self.vad_threshold - 0.15 * recent_speech))
            else:  # Raspberry Pi
                # More lenient threshold adaptation for Pi
                self.adaptive_threshold = max(0.1, min(0.3, self.vad_threshold - 0.2 * recent_speech))
        
        # Determine if sound is distant based on energy level
        is_distant = energy < self.min_energy_for_speech
        is_too_loud = energy > self.max_energy_for_speech
        
        # Adjust VAD threshold based on distance
        if is_distant:
            if platform.system() == 'Darwin':
                effective_vad_threshold = self.distant_sound_vad_threshold
            else:  # Raspberry Pi
                effective_vad_threshold = self.distant_sound_vad_threshold * 0.7  # More lenient for Pi
        else:
            effective_vad_threshold = self.adaptive_threshold
        
        # Check VAD and energy with adjusted thresholds
        vad_decision = vad_prob > effective_vad_threshold
        # For Pi, be more lenient with energy decision
        if platform.system() == 'Darwin':
            energy_decision = (self.min_energy_for_speech <= energy <= self.max_energy_for_speech)
        else:  # Raspberry Pi
            # Only check minimum energy for Pi, ignore maximum
            energy_decision = energy >= self.min_energy_for_speech
        
        # Print debug information
        if self.chunk_counter % 50 == 0:
            print(f"\n🔍 VAD Debug:")
            print(f"  - VAD Probability: {vad_prob:.4f}")
            print(f"  - Energy Level: {energy:.4f}")
            print(f"  - Adaptive Threshold: {self.adaptive_threshold:.4f}")
            print(f"  - Effective VAD Threshold: {effective_vad_threshold:.4f}")
            print(f"  - Energy Range: [{self.min_energy_for_speech:.4f}, {self.max_energy_for_speech:.4f}]")
            print(f"  - Is Distant: {is_distant}")
            print(f"  - Is Too Loud: {is_too_loud}")
            print(f"  - VAD Decision: {vad_decision}")
            print(f"  - Energy Decision: {energy_decision}")
        
        # For Pi, rely more on VAD and less on energy
        if platform.system() == 'Darwin':
            return vad_decision and energy_decision
        else:  # Raspberry Pi
            # Only require VAD decision for Pi
            return vad_decision

    def log_vad_data(self, vad_prob, energy, is_speaking):
        """Log VAD analysis data"""
        self.chunk_counter += 1
        current_time = time.time()
        
        # Log at specified intervals
        if self.chunk_counter % self.log_interval == 0:
            with open(self.log_file, "a") as f:
                f.write(f"{current_time:.3f},{self.chunk_counter},{vad_prob:.4f},{energy:.4f},{self.adaptive_threshold:.4f},{self.energy_threshold:.4f},{int(is_speaking)},{self.speech_frames},{self.silence_frames}\n")
            
            # Print summary every 1000 chunks
            if self.chunk_counter % 1000 == 0:
                print(f"\n📊 VAD Analysis Summary:")
                print(f"  - Total chunks processed: {self.chunk_counter}")
                print(f"  - Current VAD probability: {vad_prob:.4f}")
                print(f"  - Current energy: {energy:.4f}")
                print(f"  - Adaptive threshold: {self.adaptive_threshold:.4f}")
                print(f"  - Energy threshold: {self.energy_threshold:.4f}")
                print(f"  - Speech frames: {self.speech_frames}")
                print(f"  - Silence frames: {self.silence_frames}")

    def process_audio_chunk(self, audio_data):
        """Process audio chunk with enhanced VAD"""
        # Stop any playing audio when speech is detected
        if self.is_speaking:
            self.audio_server.stop_playback()
            
        # Resample to 16kHz if needed
        if self.RATE != 16000:
            audio_data = self.resample_audio(audio_data)
        
        # Ensure audio chunk is not too short
        if len(audio_data) < 512:  # Silero VAD requires at least 512 samples
            return
        
        # Calculate energy
        energy = self.calculate_energy(audio_data)
        self.update_energy_thresholds(energy)
        
        # Convert to float32 and normalize
        audio_float = audio_data.astype(np.float32) / 32768.0
        # Convert to tensor
        audio_tensor = torch.from_numpy(audio_float).unsqueeze(0)
        
        # Get speech probability
        with torch.no_grad():
            self.speech_probability = self.model(audio_tensor, 16000).item()
        
        # Log VAD data
        self.log_vad_data(self.speech_probability, energy, self.is_speaking)
        
        # Check if enough time has passed since last recording
        current_time = time.time()
        if current_time - self.last_recording_time < self.cooldown_frames * (self.CHUNK / 16000):
            return
        
        # Enhanced speech detection
        speech_detected = self.is_speech(self.speech_probability, energy)
        
        # Update speech state
        if speech_detected:
            self.speech_frames += 1
            self.silence_frames = 0
            self.pause_frames = 0  # Reset pause counter when speech is detected
            self.last_speech_time = current_time
            self.state_history.append(1)
            
            # Start recording if we've detected enough speech
            if not self.is_speaking and self.speech_frames >= self.min_speech_frames:
                self.is_speaking = True
                print("\n🎤 Speech detected! Starting recording...")
                print(f"  - VAD Probability: {self.speech_probability:.4f}")
                print(f"  - Energy Level: {energy:.4f}")
                print(f"  - Speech Frames: {self.speech_frames}")
        else:
            self.silence_frames += 1
            self.speech_frames = 0
            self.state_history.append(0)
            
            # Only increment pause frames if we're in speaking state
            if self.is_speaking:
                self.pause_frames += 1
                # Print pause information
                if self.pause_frames % 10 == 0:  # Print every 200ms
                    print(f"\n⏸️  Pause detected: {self.pause_frames} frames ({self.pause_frames * 0.02:.1f}s)")
            
            # Stop recording if we've had enough silence and exceeded pause allowance
            if self.is_speaking and (self.silence_frames >= self.silence_threshold and 
                                   self.pause_frames >= self.max_pause_frames):
                self.is_speaking = False
                print("\n🔇 Speech ended. Saving recording...")
                print(f"  - Final VAD Probability: {self.speech_probability:.4f}")
                print(f"  - Final Energy Level: {energy:.4f}")
                print(f"  - Total Speech Frames: {self.speech_frames}")
                print(f"  - Total Pause Frames: {self.pause_frames}")
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

    def _send_transcription(self, text: str, language: str, timestamp: str) -> None:
        """
        Send transcription to server in a separate thread.
        
        Args:
            text (str): The romanized text to send
            language (str): Detected language
            timestamp (str): Recording timestamp
        """
        def send_request():
            try:
                response = requests.post(
                    self.server_url,
                    json={
                        'text': text,
                        'language': language,
                        'timestamp': timestamp
                    },
                    timeout=self.server_timeout
                )
                print(f"\n📤 Server response: {response.text}")
            except Exception as e:
                print(f"\n❌ Error sending to server: {str(e)}")

        # Start sending in a separate thread
        threading.Thread(target=send_request, daemon=True).start()

    def transcription_worker(self):
        """Worker thread for handling transcriptions"""
        while True:
            try:
                # Get the next file to transcribe
                wav_file = self.transcription_queue.get()
                if wav_file is None:  # Shutdown signal
                    break
                
                # Transcribe the audio file using WhisperService
                try:
                    print("⏳ Transcribing audio with WhisperService...")
                    success, text, lang, romanized = self.whisper_service.transcribe_audio(wav_file)
                    
                    if success:
                        # Check if the text is unclear
                        if text == "Sorry i cant understand":
                            print("\n⚠️ Unclear audio detected. Skipping file save.")
                            # Delete the WAV file since we won't be using it
                            try:
                                os.remove(wav_file)
                                print("🗑️ Deleted unclear audio file")
                            except Exception as e:
                                print(f"❌ Error deleting file: {str(e)}")
                            continue
                            
                        # Save transcription to file
                        base_name = os.path.splitext(os.path.basename(wav_file))[0]
                        txt_file = os.path.join(self.transcription_dir, f"{base_name}.txt")
                        
                        with open(txt_file, "w", encoding="utf-8") as f:
                            f.write(f"Original Text ({lang}):\n{text}\n\n")
                            if romanized:
                                f.write(f"Romanized Text:\n{romanized}\n")
                        
                        # Send transcription to server in parallel
                        if romanized:
                            timestamp = base_name.split('_')[1]  # Extract timestamp from filename
                            self._send_transcription(romanized, lang, timestamp)
                        
                        print(f"\n📝 Transcription saved to {txt_file}")
                        print(f"Language: {lang}")
                        print(f"Original Text: {text}")
                        if romanized:
                            print(f"Romanized Text: {romanized}")
                    else:
                        print("❌ Transcription failed")
                
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
        self.transcription_queue.put(filename)
        
        # Clear the buffer
        self.audio_buffer = []

    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream"""
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        
        # Process with enhanced VAD
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
        print(f"Logging VAD data to {self.log_file}")
        
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
                print(f"\rCurrent state: {state} | VAD: {self.speech_probability:.2f} | Energy: {self.energy_threshold:.4f}", end='')
                
        except KeyboardInterrupt:
            print("\nStopping...")
            print(f"\n📊 Final VAD Statistics:")
            print(f"  - Total chunks processed: {self.chunk_counter}")
            print(f"  - Final VAD probability: {self.speech_probability:.4f}")
            print(f"  - Final energy threshold: {self.energy_threshold:.4f}")
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
        self.transcription_queue.put(None)
        self.transcription_thread.join()

if __name__ == "__main__":
    detector = VoiceActivityDetector()
    detector.start() 