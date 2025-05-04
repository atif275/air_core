import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

class WhisperTranscriber:
    def __init__(self):
        """Initialize the transcriber with OpenAI API."""
        # Load environment variables
        load_dotenv()
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Configure logging
        self._setup_logging()
        
        # Language mapping for better display
        self.language_map = {
            "urdu": "Urdu",
            "hindi": "Hindi",
            "english": "English",
            "ur": "Urdu",
            "hi": "Hindi",
            "en": "English"
        }
    
    def _setup_logging(self):
        """Configure logging for the transcriber"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("WhisperTranscriber")
    
    def detect_language(self, audio_file_path: str) -> dict:
        """
        Detect the language of an audio file using OpenAI API.
        
        Args:
            audio_file_path (str): Path to the audio file
            
        Returns:
            dict: {
                'success': bool,
                'language': str,
                'language_name': str
            }
        """
        if not os.path.exists(audio_file_path):
            self.logger.error(f"Audio file not found: {audio_file_path}")
            return {
                'success': False,
                'language': '',
                'language_name': ''
            }
        
        try:
            self.logger.info(f"Detecting language for: {audio_file_path}")
            
            with open(audio_file_path, "rb") as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    language=None  # Let the model detect the language
                )
            
            detected_lang = response.language.lower()
            language_name = self.language_map.get(detected_lang, detected_lang.capitalize())
            
            self.logger.info(f"Language detected: {language_name} ({detected_lang})")
            
            return {
                'success': True,
                'language': detected_lang,
                'language_name': language_name
            }
            
        except Exception as e:
            self.logger.error(f"Language detection failed: {str(e)}")
            return {
                'success': False,
                'language': '',
                'language_name': ''
            }
    
    def transcribe_file(self, audio_file_path: str, language: str = None) -> dict:
        """
        Transcribe an audio file using OpenAI API.
        
        Args:
            audio_file_path (str): Path to the audio file
            language (str, optional): Language code to use for transcription
            
        Returns:
            dict: {
                'success': bool,
                'text': str,
                'language': str,
                'language_name': str
            }
        """
        if not os.path.exists(audio_file_path):
            self.logger.error(f"Audio file not found: {audio_file_path}")
            return {
                'success': False,
                'text': '',
                'language': '',
                'language_name': ''
            }
        
        try:
            self.logger.info(f"Starting transcription of: {audio_file_path}")
            
            with open(audio_file_path, "rb") as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    language=language  # Use specified language if provided
                )
            
            detected_lang = response.language.lower()
            language_name = self.language_map.get(detected_lang, detected_lang.capitalize())
            
            self.logger.info(f"Transcription completed successfully in {language_name}")
            
            return {
                'success': True,
                'text': response.text,
                'language': detected_lang,
                'language_name': language_name
            }
            
        except Exception as e:
            self.logger.error(f"Transcription failed: {str(e)}")
            return {
                'success': False,
                'text': '',
                'language': '',
                'language_name': ''
            }

# Example usage
if __name__ == "__main__":
    # Define the audio file to transcribe
    audio_file = "test_urdu.wav"  # Change this to test different files
    
    transcriber = None
    try:
        print("\n🔊 Starting transcription test...")
        print(f"Current directory: {os.getcwd()}")
        print(f"Looking for {audio_file} in: {os.path.abspath(audio_file)}")
        
        # Check if file exists and is readable
        if not os.path.exists(audio_file):
            print(f"❌ Error: {audio_file} not found")
            exit(1)
            
        if not os.access(audio_file, os.R_OK):
            print(f"❌ Error: {audio_file} is not readable")
            exit(1)
            
        # Get file size
        file_size = os.path.getsize(audio_file)
        print(f"📁 File size: {file_size} bytes")
        
        # Create transcriber instance
        transcriber = WhisperTranscriber()
        
        # First detect the language
        print("\n🔍 Detecting language...")
        lang_result = transcriber.detect_language(audio_file)
        
        if not lang_result['success']:
            print("❌ Language detection failed")
            exit(1)
            
        print(f"✅ Language detected: {lang_result['language_name']} ({lang_result['language']})")
        
        # Now transcribe with the detected language
        print("\n🎤 Starting transcription...")
        result = transcriber.transcribe_file(audio_file, language=lang_result['language'])
        
        if result['success']:
            print("\n✅ Transcription successful!")
            print(f"🌐 Language: {result['language_name']} ({result['language']})")
            print("\n📝 Text:", result['text'])
        else:
            print("\n❌ Transcription failed")
            
    except Exception as e:
        print(f"\n❌ Error during transcription: {str(e)}") 