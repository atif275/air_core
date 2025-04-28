import pyaudio
import wave
import numpy as np
import requests
import json
import whisper
import os
from datetime import datetime

class VoiceInput:
    def __init__(self):
        # Audio recording parameters
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.SILENCE_THRESHOLD = 500  # Adjust based on your microphone
        self.SILENCE_DURATION = 1.0  # seconds
        self.RECORD_SECONDS = 5  # Maximum recording duration
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        
        # Initialize Whisper model
        self.model = whisper.load_model("base")
        
        # Server endpoint
        self.server_url = "http://192.168.8.102:5001/transcription"
        
        # Create temp directory if it doesn't exist
        self.temp_dir = "temp_audio"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def record_audio(self):
        """Record audio until silence is detected or max duration is reached"""
        stream = self.p.open(format=self.FORMAT,
                           channels=self.CHANNELS,
                           rate=self.RATE,
                           input=True,
                           frames_per_buffer=self.CHUNK)

        print("Recording...")
        frames = []
        silence_frames = 0
        silence_threshold_frames = int(self.SILENCE_DURATION * self.RATE / self.CHUNK)
        max_frames = int(self.RECORD_SECONDS * self.RATE / self.CHUNK)

        for i in range(0, max_frames):
            data = stream.read(self.CHUNK)
            frames.append(data)
            
            # Convert to numpy array to check amplitude
            audio_data = np.frombuffer(data, dtype=np.int16)
            if np.abs(audio_data).mean() < self.SILENCE_THRESHOLD:
                silence_frames += 1
            else:
                silence_frames = 0
                
            if silence_frames > silence_threshold_frames:
                print("Silence detected, stopping recording")
                break

        print("Recording finished")
        stream.stop_stream()
        stream.close()

        # Save the recorded data as a WAV file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.temp_dir, f"recording_{timestamp}.wav")
        
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return filename

    def transcribe_audio(self, audio_file):
        """Transcribe audio file using Whisper"""
        try:
            result = self.model.transcribe(audio_file)
            return result["text"]
        except Exception as e:
            print(f"Error in transcription: {e}")
            return ""

    def send_to_server(self, text):
        """Send transcribed text to the server"""
        try:
            response = requests.post(
                self.server_url,
                json={
                    "text": text,
                    "timestamp": datetime.now().isoformat()
                },
                headers={"Content-Type": "application/json"}
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending to server: {e}")
            return False

    def cleanup(self):
        """Clean up resources"""
        self.p.terminate()

def main():
    voice_input = VoiceInput()
    try:
        while True:
            input("Press Enter to start recording...")
            audio_file = voice_input.record_audio()
            text = voice_input.transcribe_audio(audio_file)
            
            if text:
                print(f"Transcribed text: {text}")
                success = voice_input.send_to_server(text)
                if success:
                    print("Successfully sent to server")
                else:
                    print("Failed to send to server")
            
            # Clean up the audio file
            try:
                os.remove(audio_file)
            except:
                pass
                
    except KeyboardInterrupt:
        print("\nStopping voice input...")
    finally:
        voice_input.cleanup()

if __name__ == "__main__":
    main() 