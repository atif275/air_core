import os
import logging
import numpy as np
from faster_whisper import WhisperModel
from openai import OpenAI
from dotenv import load_dotenv
from typing import Optional, Tuple
import platform
import gc
import psutil
import time

class HybridTranscriber:
    def __init__(self, model_size: str = "tiny", use_detector: bool = True):
        """
        Initialize the hybrid transcriber with both faster-whisper and OpenAI API.
        
        Args:
            model_size (str): Model size to use for faster-whisper ("tiny", "base", "small", "medium", "large")
            use_detector (bool): Whether to use language detection before transcription
        """
        self.model_size = model_size
        self.use_detector = use_detector
        self.faster_model = None
        self.openai_client = None
        
        # Language mapping
        self.language_map = {
            "ur": "Urdu",
            "hi": "Hindi",
            "ar": "Arabic",
            "en": "English"
        }
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s'
        )
        self.logger = logging.getLogger("HybridTranscriber")
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize both faster-whisper and OpenAI models"""
        try:
            # Initialize faster-whisper (only if detector is enabled)
            if self.use_detector:
                self.logger.info("🔄 Initializing faster-whisper model...")
                device = "cpu"
                compute_type = "int8"
                
                self.faster_model = WhisperModel(
                    self.model_size,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=4 if platform.system() != 'Darwin' else 2
                )
                self.logger.info("✅ faster-whisper model initialized")
            
            # Initialize OpenAI client
            self.logger.info("🔄 Initializing OpenAI client...")
            load_dotenv()
            self.openai_client = OpenAI(
                api_key=os.getenv('OPENAI_API_KEY'),
                timeout=30.0  # Set timeout to 30 seconds
            )
            self.logger.info("✅ OpenAI client initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {str(e)}")
            raise
    
    def detect_language(self, audio_file_path: str) -> Tuple[bool, str, str]:
        """Detect the language of an audio file using faster-whisper."""
        if not os.path.exists(audio_file_path):
            return False, "", ""
        
        try:
            self.logger.info("🔍 Detecting language using faster-whisper...")
            start_time = time.time()
            
            segments, info = self.faster_model.transcribe(
                audio_file_path,
                beam_size=5,
                vad_filter=False
            )
            
            detected_lang = info.language
            lang_name = self.language_map.get(detected_lang, detected_lang)
            
            elapsed = time.time() - start_time
            self.logger.info(f"✅ Language detected: {lang_name} ({detected_lang}) in {elapsed:.2f}s")
            return True, detected_lang, lang_name
            
        except Exception as e:
            self.logger.error(f"❌ Language detection failed: {str(e)}")
            return False, "", ""
    
    def transcribe_file(self, audio_file_path: str) -> Tuple[bool, str, str, str]:
        """Transcribe an audio file using the appropriate model based on language."""
        if not os.path.exists(audio_file_path):
            return False, "", "", ""
        
        try:
            start_time = time.time()
            detected_lang = "en"  # Default to English if detector is disabled
            lang_name = "English"
            
            if self.use_detector:
                # Detect language first
                success, detected_lang, lang_name = self.detect_language(audio_file_path)
                if not success:
                    return False, "", "", ""
                
                # Use faster-whisper for English, OpenAI API for other languages
                if detected_lang == "en":
                    self.logger.info("🎤 Using faster-whisper for English transcription...")
                    segments, info = self.faster_model.transcribe(
                        audio_file_path,
                        beam_size=5,
                        language="en",
                        vad_filter=False
                    )
                    
                    transcription = " ".join([segment.text for segment in segments])
                    elapsed = time.time() - start_time
                    self.logger.info(f"✅ Transcription completed using faster-whisper in {elapsed:.2f}s")
                else:
                    self.logger.info(f"🎤 Using OpenAI API for {lang_name} transcription...")
                    with open(audio_file_path, "rb") as audio_file:
                        response = self.openai_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="verbose_json",
                            language=detected_lang
                        )
                    transcription = response.text
                    elapsed = time.time() - start_time
                    self.logger.info(f"✅ Transcription completed using OpenAI API in {elapsed:.2f}s")
            else:
                # Directly use OpenAI API without language detection
                self.logger.info("🎤 Using OpenAI API for transcription (detector disabled)...")
                with open(audio_file_path, "rb") as audio_file:
                    response = self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json"
                    )
                transcription = response.text
                detected_lang = response.language
                lang_name = self.language_map.get(detected_lang, detected_lang)
                elapsed = time.time() - start_time
                self.logger.info(f"✅ Transcription completed using OpenAI API in {elapsed:.2f}s")
            
            return True, transcription.strip(), detected_lang, lang_name
            
        except Exception as e:
            self.logger.error(f"❌ Transcription failed: {str(e)}")
            return False, "", "", ""
    
    def transcribe_audio_data(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Tuple[bool, str, str, str]:
        """Transcribe raw audio data using the appropriate model based on language."""
        try:
            # Save audio data to temporary file
            import soundfile as sf
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                sf.write(temp_file.name, audio_data, sample_rate)
                return self.transcribe_file(temp_file.name)
            
        except Exception as e:
            self.logger.error(f"❌ Transcription failed: {str(e)}")
            return False, "", "", ""
    
    def cleanup(self):
        """Clean up resources"""
        if self.faster_model:
            del self.faster_model
            gc.collect()

# Example usage
if __name__ == "__main__":
    # Create transcriber instance with language detection disabled
    transcriber = HybridTranscriber(model_size="base", use_detector=False)
    
    try:
        print("\n🔊 Starting transcription test (detector disabled)...")
        
        if not os.path.exists("test_urdu.wav"):
            print("❌ Error: test_urdu.wav not found")
            exit(1)
            
        if not os.access("test_urdu.wav", os.R_OK):
            print("❌ Error: test_urdu.wav is not readable")
            exit(1)
            
        file_size = os.path.getsize("test_urdu.wav")
        print(f"📁 File size: {file_size/1024:.1f}KB")
        
        start_time = time.time()
        success, text, detected_lang, lang_name = transcriber.transcribe_file("test_urdu.wav")
        total_time = time.time() - start_time
        
        if success:
            print("\n✅ Transcription successful!")
            print(f"🌐 Language: {lang_name} ({detected_lang})")
            print("📝 Text:", text if text else "No transcription received")
            print(f"⏱️ Total time: {total_time:.2f}s")
        else:
            print("\n❌ Transcription failed")
            
    except Exception as e:
        print(f"\n❌ Error during transcription: {str(e)}")
    finally:
        transcriber.cleanup() 