from flask import Flask, request, jsonify
import os
import threading
import pygame

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def play_audio(filepath):
    pygame.mixer.init()
    pygame.mixer.music.load(filepath)
    pygame.mixer.music.play()

    # Keep running until music finishes playing
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not file.filename.lower().endswith('.mp3'):
        return jsonify({'error': 'Only MP3 files are allowed'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Play audio in a separate thread so server stays responsive
    threading.Thread(target=play_audio, args=(filepath,)).start()

    return jsonify({'message': f'File {file.filename} uploaded and playing'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5005)
