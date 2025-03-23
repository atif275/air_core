from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/transcription', methods=['POST'])
def receive_transcription():
    data = request.json
    text = data.get('text')
    timestamp = data.get('timestamp')
    
    print(f"Received transcription at {timestamp}: {text}")
    
    # Process the transcribed text as needed
    
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    # Enable debug mode and make accessible on network
    app.run(
        host='0.0.0.0',  # Makes server accessible externally
        port=5001,       # Port number
        debug=False      # Disable debug mode in production
    )
