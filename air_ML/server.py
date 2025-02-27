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

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout  # Ensure logs are printed to stdout
)
logger = logging.getLogger(__name__)

# Server host & port
HOST = "0.0.0.0"  # Accepts connections from any device on the network
PORT = 8765       # Choose a port

# Display mode configuration
DISPLAY_MODE = os.environ.get('DISPLAY_MODE', 'save')  # Options: 'window', 'save', 'none'
SAVE_DIR = os.environ.get('SAVE_DIR', 'frames')

class FrameHandler:
    def __init__(self, mode='save'):
        self.mode = mode
        if self.mode == 'save':
            # Create frames directory if it doesn't exist
            os.makedirs(SAVE_DIR, exist_ok=True)
            logger.info(f"Saving frames to {SAVE_DIR}")
        elif self.mode == 'window':
            # Create OpenCV window
            cv2.namedWindow("Live Stream", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Live Stream", 640, 480)
            logger.info("Created OpenCV window")

    def handle_frame(self, frame, frame_count):
        if self.mode == 'window':
            # Display frame in window
            cv2.imshow("Live Stream", frame)
            cv2.waitKey(1)
        elif self.mode == 'save':
            # Save frame to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{SAVE_DIR}/frame_{frame_count}_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            logger.debug(f"Saved frame to {filename}")
        # 'none' mode does nothing with the frame

    def cleanup(self):
        if self.mode == 'window':
            cv2.destroyAllWindows()

async def handle_client(websocket):
    logger.info("Client connected!")
    frame_count = 0
    last_frame_time = time.time()
    
    # Initialize frame handler
    frame_handler = FrameHandler(DISPLAY_MODE)
    
    try:
        # Send ready message to client
        await websocket.send(json.dumps({
            "type": "ready",
            "message": "Server ready for frames"
        }))
        logger.info("Sent ready message to client")

        async for message in websocket:
            try:
                # Log raw message size
                message_size = len(message)
                logger.debug(f"Received message size: {message_size} bytes")
                
                if message_size == 0:
                    logger.warning("Received empty message")
                    continue

                data = json.loads(message)
                msg_type = data.get('type', 'image')
                logger.debug(f"Received message type: {msg_type}")
                
                if msg_type == 'heartbeat':
                    logger.debug("Received heartbeat")
                    await websocket.send(json.dumps({"type": "heartbeat_ack"}))
                    continue
                    
                if "image" in data:
                    current_time = time.time()
                    frame_time = current_time - last_frame_time
                    last_frame_time = current_time
                    
                    frame_count += 1
                    logger.info(f"Processing frame {frame_count} (Frame interval: {frame_time:.3f}s)")
                    
                    # Decode Base64 image
                    try:
                        image_data = base64.b64decode(data["image"])
                        logger.debug(f"Decoded image data size: {len(image_data)} bytes")
                        
                        # Convert to numpy array
                        np_arr = np.frombuffer(image_data, np.uint8)
                        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            logger.debug(f"Frame shape: {frame.shape}")
                            
                            # Handle frame according to display mode
                            frame_handler.handle_frame(frame, frame_count)
                            
                            # Send acknowledgment
                            await websocket.send(json.dumps({
                                "type": "frame_ack",
                                "frame_number": frame_count,
                                "timestamp": time.time()
                            }))
                            logger.debug(f"Frame {frame_count} processed and acknowledged")
                        else:
                            logger.error("Failed to decode frame into image")
                            
                    except Exception as e:
                        logger.error(f"Frame processing error: {str(e)}")
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": f"Frame processing error: {str(e)}"
                        }))

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
            except Exception as e:
                logger.error(f"Message processing error: {str(e)}")

    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"Connection closed by client: {str(e)}")
    except Exception as e:
        logger.error(f"Connection error: {str(e)}")
    finally:
        logger.info(f"Client disconnected. Processed {frame_count} frames")
        frame_handler.cleanup()

async def start_server():
    try:
        async with websockets.serve(
            handle_client, 
            HOST, 
            PORT,
            max_size=2**25,  # 32MB
            max_queue=32,
            ping_interval=20,
            ping_timeout=20,
            compression=None  # Disable compression for better performance
        ) as server:
            logger.info(f"WebSocket Server started at ws://{HOST}:{PORT}")
            await asyncio.Future()  # run forever
    except Exception as e:
        logger.error(f"Server startup error: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
