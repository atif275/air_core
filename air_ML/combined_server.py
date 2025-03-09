import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import logging
import sys
import os
import time
from datetime import datetime
from quart import Quart, request, jsonify
from quart_cors import cors
from src.conversation.chatbot import OpenAIChatBot
from src.config.settings import load_api_key
from src.conversation.summary import summarize_conversations
from dotenv import load_dotenv
from src.database.db_setup import ensure_database

# Load environment variables from .env
load_dotenv()

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Server configuration from .env
HOST = os.getenv('HOST', '0.0.0.0')
HTTP_PORT = int(os.getenv('PORT', 5002))
WS_PORT = HTTP_PORT + 1  # WebSocket port will be HTTP_PORT + 1
DISPLAY_MODE = os.getenv('DISPLAY_MODE', 'save')
SAVE_DIR = os.getenv('SAVE_DIR', 'frames')

# Add startup logging
logger.info("Starting Combined Server with configuration:")
logger.info(f"HOST: {HOST}")
logger.info(f"HTTP PORT: {HTTP_PORT}")
logger.info(f"WebSocket PORT: {WS_PORT}")
logger.info(f"DISPLAY_MODE: {DISPLAY_MODE}")
logger.info(f"SAVE_DIR: {SAVE_DIR}")

# Initialize database before starting server
logger.info("Initializing database...")
try:
    ensure_database()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    sys.exit(1)

# Initialize Quart app
app = Quart(__name__)
app = cors(app)

# Initialize chatbot
api_key = load_api_key()
chatbot = OpenAIChatBot(api_key)

# Frame handler from original server.py
class FrameHandler:
    def __init__(self, mode='save'):
        self.mode = mode
        if self.mode == 'save':
            os.makedirs(SAVE_DIR, exist_ok=True)
            logger.info(f"Saving frames to {SAVE_DIR}")
        elif self.mode == 'window':
            cv2.namedWindow("Live Stream", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Live Stream", 640, 480)
            logger.info("Created OpenCV window")

    def handle_frame(self, frame, frame_count):
        if self.mode == 'window':
            cv2.imshow("Live Stream", frame)
            cv2.waitKey(1)
        elif self.mode == 'save':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{SAVE_DIR}/frame_{frame_count}_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            logger.debug(f"Saved frame to {filename}")

    def cleanup(self):
        if self.mode == 'window':
            cv2.destroyAllWindows()

# WebSocket handler
async def handle_websocket(websocket):
    logger.info("WebSocket client connected!")
    frame_count = 0
    last_frame_time = time.time()
    frame_handler = FrameHandler(DISPLAY_MODE)
    
    try:
        await websocket.send(json.dumps({
            "type": "ready",
            "message": "Server ready for frames"
        }))
        
        async for message in websocket:
            try:
                message_size = len(message)
                if message_size == 0:
                    continue

                data = json.loads(message)
                msg_type = data.get('type', 'image')
                
                if msg_type == 'heartbeat':
                    await websocket.send(json.dumps({"type": "heartbeat_ack"}))
                    continue
                    
                if "image" in data:
                    current_time = time.time()
                    frame_time = current_time - last_frame_time
                    last_frame_time = current_time
                    frame_count += 1
                    
                    try:
                        image_data = base64.b64decode(data["image"])
                        np_arr = np.frombuffer(image_data, np.uint8)
                        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            frame_handler.handle_frame(frame, frame_count)
                            await websocket.send(json.dumps({
                                "type": "frame_ack",
                                "frame_number": frame_count,
                                "timestamp": time.time()
                            }))
                    except Exception as e:
                        logger.error(f"Frame processing error: {str(e)}")
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": f"Frame processing error: {str(e)}"
                        }))

            except Exception as e:
                logger.error(f"Message processing error: {str(e)}")

    except websockets.exceptions.ConnectionClosed:
        logger.info("WebSocket connection closed")
    finally:
        logger.info(f"Client disconnected. Processed {frame_count} frames")
        frame_handler.cleanup()

# HTTP Routes
@app.route('/transcription', methods=['POST'])
async def receive_transcription():
    data = await request.get_json()
    text = data.get('text')
    timestamp = data.get('timestamp')
    
    print(f"Received transcription at {timestamp}: {text}")
    
    if text.lower().strip() in ['exit', 'quit', 'bye', 'exit.', 'quit.', 'bye.']:
        response = "Goodbye! Have a great day!"
        summarize_conversations()
    else:
        response = chatbot.respond(text)
    
    return jsonify({
        'status': 'success',
        'response': response
    })

# Modified WebSocket setup
@app.before_serving
async def startup():
    logger.info("Initializing WebSocket server...")
    try:
        ws_server = await websockets.serve(
            handle_websocket,
            HOST,
            WS_PORT,  # Use separate WebSocket port
            max_size=2**25,
            max_queue=32,
            ping_interval=20,
            ping_timeout=20,
            compression=None
        )
        app.ws_server = ws_server
        logger.info(f"WebSocket server initialized on ws://{HOST}:{WS_PORT}")
        logger.info(f"HTTP server running on http://{HOST}:{HTTP_PORT}")
        logger.info("Combined server is ready to accept both HTTP and WebSocket connections")
    except Exception as e:
        logger.error(f"Failed to start WebSocket server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        logger.info("Starting Quart application...")
        app.run(
            host=HOST,
            port=HTTP_PORT,
            debug=False
        )
    except OSError as e:
        if e.errno == 48:  # Address already in use
            logger.error(f"Port {HTTP_PORT} or {WS_PORT} is already in use.")
            logger.error("Please ensure both ports are available.")
            sys.exit(1)
        raise e 