import os
import logging
import time
import requests
import json
import subprocess
import tempfile
from typing import Tuple, Optional
from dotenv import load_dotenv

class WhisperService:
    def __init__(self, romanize: bool = False, translate_to_english: bool = False):
        """
        Initialize the WhisperService.
        
        Args:
            romanize (bool): Whether to romanize non-English text
            translate_to_english (bool): Whether to translate to English
        """
        self.romanize = romanize
        self.translate_to_english = translate_to_english
        self.transcription_endpoint = 'https://api.openai.com/v1/audio/transcriptions'
        self.chat_endpoint = 'https://api.openai.com/v1/chat/completions'
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s'
        )
        self.logger = logging.getLogger("WhisperService")
        
        # Initialize API key
        self._initialize_api_key()
    
    def _initialize_api_key(self):
        """Initialize OpenAI API key"""
        try:
            self.logger.info("🔄 Loading API key...")
            load_dotenv()
            self.api_key = os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            self.logger.info("✅ API key loaded")
        except Exception as e:
            self.logger.error(f"❌ API key initialization failed: {str(e)}")
            raise
    
    def _optimize_audio(self, audio_file_path: str) -> str:
        """
        Optimize audio file for faster processing.
        Converts to MP3 and reduces sample rate if needed.
        
        Args:
            audio_file_path (str): Path to the audio file
            
        Returns:
            str: Path to the optimized audio file
        """
        try:
            # Create a temporary file for the optimized audio
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Use ffmpeg to optimize the audio
            cmd = [
                'ffmpeg', '-y',
                '-i', audio_file_path,
                '-ar', '16000',  # Sample rate
                '-b:a', '32k',   # Bitrate
                '-map_metadata', '-1',  # Remove metadata
                '-ac', '1',      # Convert to mono
                '-af', 'highpass=f=200,lowpass=f=3000',  # Filter frequencies
                temp_path
            ]
            
            self.logger.info("🔄 Optimizing audio file...")
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Get the size difference
            original_size = os.path.getsize(audio_file_path)
            optimized_size = os.path.getsize(temp_path)
            reduction = (original_size - optimized_size) / original_size * 100
            
            self.logger.info(f"✅ Audio optimized: {optimized_size/1024:.1f}KB (reduced by {reduction:.1f}%)")
            return temp_path
            
        except Exception as e:
            self.logger.error(f"❌ Audio optimization failed: {str(e)}")
            return audio_file_path
    
    def _make_api_request(self, url: str, headers: dict, data: dict, files: dict = None, retries: int = 3) -> requests.Response:
        """Make API request with retry logic"""
        for attempt in range(retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data if not files else None,
                    files=files,
                    data=data if files else None,
                    timeout=30.0
                )
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limit
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"API error (attempt {attempt + 1}/{retries}): {response.text}")
                    if attempt == retries - 1:
                        return response
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error (attempt {attempt + 1}/{retries}): {str(e)}")
                if attempt == retries - 1:
                    raise
        return None
    
    def transcribe_audio(self, audio_file_path: str) -> Tuple[bool, str, str, Optional[str]]:
        """
        Transcribe an audio file and optionally romanize the text.
        
        Args:
            audio_file_path (str): Path to the audio file
            
        Returns:
            Tuple[bool, str, str, Optional[str]]: 
                (success, transcribed_text, detected_language, romanized_text)
        """
        if not os.path.exists(audio_file_path):
            self.logger.error("❌ Audio file not found")
            return False, "", "", None
        
        try:
            start_time = time.time()
            
            # Optimize the audio file
            optimized_path = self._optimize_audio(audio_file_path)
            
            # Prepare the request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json'
            }
            
            files = {
                'file': open(optimized_path, 'rb')
            }
            
            data = {
                'model': 'whisper-1',
                'response_format': 'verbose_json',
                'temperature': 0.0
            }
            
            if self.translate_to_english:
                data['language'] = 'en'
            
            # Make the request
            self.logger.info("🎤 Transcribing audio...")
            response = self._make_api_request(
                self.transcription_endpoint,
                headers=headers,
                files=files,
                data=data
            )
            
            # Close the file
            files['file'].close()
            
            # Clean up the temporary file
            if optimized_path != audio_file_path:
                os.unlink(optimized_path)
            
            if not response or response.status_code != 200:
                self.logger.error(f"❌ Transcription API error: {response.text if response else 'No response'}")
                return False, "", "", None
            
            # Parse the response
            result = response.json()
            transcribed_text = result['text']
            detected_lang = result['language'].lower()
            
            elapsed = time.time() - start_time
            self.logger.info(f"✅ Transcription completed in {elapsed:.2f}s")
            
            # Handle romanization based on detected language
            romanized_text = None
            if self.romanize:
                if detected_lang == "en":
                    # For English text, just copy the original text and log
                    romanized_text = transcribed_text
                    self.logger.info("ℹ️  Skipping romanization - text is already in English")
                else:
                    self.logger.info("🔄 Romanizing text...")
                    romanized_text = self._romanize_text(transcribed_text)
                    self.logger.info("✅ Romanization completed")
            
            return True, transcribed_text, detected_lang, romanized_text
            
        except Exception as e:
            self.logger.error(f"❌ Transcription failed: {str(e)}")
            return False, "", "", None
    
    def _romanize_text(self, text: str) -> str:
        """
        Romanize the given text using GPT-3.5-turbo.
        
        Args:
            text (str): Text to romanize
            
        Returns:
            str: Romanized text
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {
                        'role': 'system',
                        'content': '''You are a translator that converts text to Roman script.
                        For Urdu/Hindi, use common romanization.
                        Keep English words unchanged.
                        Only respond with the romanized text, no explanations.'''
                    },
                    {
                        'role': 'user',
                        'content': f'Convert this text to Roman script: {text}'
                    }
                ],
                'temperature': 0.3
            }
            
            response = self._make_api_request(
                self.chat_endpoint,
                headers=headers,
                data=data
            )
            
            if not response or response.status_code != 200:
                self.logger.error(f"❌ Romanization API error: {response.text if response else 'No response'}")
                return text
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            self.logger.error(f"❌ Romanization failed: {str(e)}")
            return text

# Example usage
if __name__ == "__main__":
    # Create service instance with romanization enabled
    service = WhisperService(romanize=True, translate_to_english=False)
    
    # Audio file to test
    test_audio_file = "test_urdu.wav"  # Change this to test different files
    
    try:
        print("\n🔊 Starting transcription test...")
        print(f"📂 Testing file: {test_audio_file}")
        
        if not os.path.exists(test_audio_file):
            print(f"❌ Error: {test_audio_file} not found")
            exit(1)
            
        if not os.access(test_audio_file, os.R_OK):
            print(f"❌ Error: {test_audio_file} is not readable")
            exit(1)
            
        file_size = os.path.getsize(test_audio_file)
        print(f"📁 Original file size: {file_size/1024:.1f}KB")
        
        start_time = time.time()
        success, text, lang, romanized = service.transcribe_audio(test_audio_file)
        total_time = time.time() - start_time
        
        if success:
            print("\n✅ Transcription successful!")
            print(f"🌐 Language: {lang}")
            print("\n📝 Original Text:", text)
            if romanized:
                print("\n🔤 Romanized Text:", romanized)
            print(f"\n⏱️ Total time: {total_time:.2f}s")
        else:
            print("\n❌ Transcription failed")
            
    except Exception as e:
        print(f"\n❌ Error during transcription: {str(e)}") 