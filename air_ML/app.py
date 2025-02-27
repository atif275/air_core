from flask import Flask, request, jsonify
from flask_cors import CORS
from src.conversation.chatbot import OpenAIChatBot
from src.config.settings import load_api_key
from src.conversation.summary import summarize_conversations

app = Flask(__name__)
CORS(app)

# Initialize chatbot
api_key = load_api_key()
chatbot = OpenAIChatBot(api_key)

@app.route('/transcription', methods=['POST'])
def receive_transcription():
    data = request.json
    text = data.get('text')
    timestamp = data.get('timestamp')
    
    print(f"Received transcription at {timestamp}: {text}")
    
    # Check if user wants to exit
    if text.lower().strip() in ['exit', 'quit', 'bye', 'exit.', 'quit.', 'bye.']:
        response = "Goodbye! Have a great day!"
        summarize_conversations()
    else:
        # Get chatbot response
        response = chatbot.respond(text)
    
    print(f"ChatBot: {response}")
    
    return jsonify({
        'status': 'success',
        'response': response
    })

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=False
    )
