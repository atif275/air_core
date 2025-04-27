from flask import Flask, request, jsonify
from flask_cors import CORS
from src.chatbot import chatbot
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Check if OpenAI API key is set
if not os.getenv("OPENAI_API_KEY"):
    print("⚠️ Warning: OPENAI_API_KEY not found in environment variables.")
    print("Please add OPENAI_API_KEY to your .env file.")

app = Flask(__name__)
CORS(app)

@app.route('/transcription', methods=['POST'])
def receive_transcription():
    """Endpoint to receive transcribed text and return chatbot response."""
    data = request.json
    text = data.get('text')
    timestamp = data.get('timestamp', 'N/A')
    
    print(f"Received transcription at {timestamp}: {text}")

    # Check if user wants to exit
    if text.lower().strip() in ['exit', 'quit', 'bye', 'exit.', 'quit.', 'bye.']:
        response = "Goodbye! Have a great day!"
    else:
        # Get response from chatbot
        response = chatbot.get_response(text)
    
    return jsonify({
        'status': 'success',
        'response': response
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'Server is running'
    })

if __name__ == '__main__':
    print("🤖 Chatbot server started!")
    print("Listening on http://localhost:5001")
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=False
    )
