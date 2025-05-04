# Voice Activity Detection and Transcription

This project provides voice activity detection (VAD) and transcription capabilities using OpenAI's Whisper API. It's designed to work on macOS and Raspberry Pi (64-bit) systems.

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On macOS
# or
source venv/Scripts/activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Testing Whisper Service
To test the Whisper service, modify the audio file name in the `__main__` section of `whisperservice.py` and run:
```bash
python whisperservice.py
```

### Running Voice Activity Detection
To run the voice activity detection system:
```bash
python vad.py
```

The system will:
- Start monitoring your microphone
- Automatically detect speech
- Save recordings to the `recordings` folder
- Transcribe the audio and save transcriptions to the `transcriptions` folder

Press Ctrl+C to stop the program. 