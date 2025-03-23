import asyncio
import websockets
import cv2
import base64
import json
import logging
import time
from datetime import datetime
import threading
import queue
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger('RobotCameraServer')

class RobotCameraServer:
    def __init__(self, camera_url, websocket_host='0.0.0.0', websocket_port=8765, is_display_window=False):
        self.camera_url = camera_url
        self.websocket_host = websocket_host
        self.websocket_port = websocket_port
        self.is_display_window = is_display_window  # New flag for window display
        self.clients = set()
        self.is_streaming = False
        self.video_capture = None
        self.frame_queue = queue.Queue(maxsize=3)  # Buffer 3 frames max
        self.frame_thread = None
        self.last_heartbeat = {}  # Track client heartbeats
        self.frame_interval = 1/15  # Target 15 FPS

    def init_camera(self):
        """Initialize camera without starting stream"""
        try:
            if self.video_capture is None:
                logger.info(f"Initializing camera at {self.camera_url}")
                self.video_capture = cv2.VideoCapture(self.camera_url)
                self.video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.video_capture.set(cv2.CAP_PROP_FPS, 30)
                
                if not self.video_capture.isOpened():
                    raise Exception("Failed to open camera stream")
                
                # Test first frame
                ret, _ = self.video_capture.read()
                if not ret:
                    raise Exception("Could not read first frame")
                    
                logger.info("Camera initialized successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            self.video_capture = None
            return False

    def start_streaming(self):
        """Start streaming frames"""
        if not self.is_streaming and self.video_capture:
            self.is_streaming = True
            logger.info("Starting camera stream")
            
            # Start frame capture thread
            self.frame_thread = threading.Thread(target=self.capture_frames)
            self.frame_thread.daemon = True
            self.frame_thread.start()
            
            # Start frame streaming
            asyncio.create_task(self.stream_frames())
            return True
        return False

    def stop_streaming(self):
        """Stop streaming frames but keep camera initialized"""
        if self.is_streaming:
            self.is_streaming = False
            if self.frame_thread:
                self.frame_thread.join(timeout=1.0)
            self.frame_thread = None
            # Clear frame queue
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break
            # Only destroy windows if display was enabled
            if self.is_display_window:
                cv2.destroyAllWindows()
            logger.info("Camera streaming stopped")
            return True
        return False

    def capture_frames(self):
        """Capture frames in a separate thread"""
        frame_count = 0
        last_time = time.time()
        
        while self.is_streaming:
            if self.video_capture is None or not self.video_capture.isOpened():
                logger.error("Camera disconnected")
                break
                
            ret, frame = self.video_capture.read()
            if not ret:
                logger.warning("Failed to read frame")
                time.sleep(0.1)
                continue

            current_time = time.time()
            frame_time = current_time - last_time
            last_time = current_time

            # Resize frame
            frame = cv2.resize(frame, (640, 480))
            frame_count += 1
            
            if frame_count % 30 == 0:  # Log stats every 30 frames
                logger.debug(f"Frame capture rate: {1/frame_time:.1f} FPS")
            
            # Update frame queue (drop frames if queue is full)
            try:
                self.frame_queue.put((frame, current_time), block=False)
            except queue.Full:
                try:
                    self.frame_queue.get_nowait()  # Remove oldest frame
                    self.frame_queue.put((frame, current_time), block=False)
                except:
                    pass

    async def handle_client(self, websocket, path=None):
        client_id = id(websocket)
        try:
            self.clients.add(websocket)
            self.last_heartbeat[client_id] = time.time()
            logger.info(f"New client connected. ID: {client_id}. Total clients: {len(self.clients)}")
            
            # Send connection success
            await websocket.send(json.dumps({
                'type': 'connection_status',
                'status': 'success',
                'message': 'Connected to robot camera successfully',
                'timestamp': datetime.now().isoformat()
            }))

            # Initialize camera if needed
            if not self.video_capture:
                if not self.init_camera():
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Failed to initialize camera'
                    }))
                    return

            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    if msg_type == 'heartbeat':
                        self.last_heartbeat[client_id] = time.time()
                        await websocket.send(json.dumps({'type': 'heartbeat_ack'}))
                    
                    elif msg_type == 'command':
                        action = data.get('action')
                        if action == 'start_streaming':
                            if self.start_streaming():
                                await websocket.send(json.dumps({
                                    'type': 'command_response',
                                    'action': 'start_streaming',
                                    'status': 'success',
                                    'message': 'Streaming started'
                                }))
                            else:
                                await websocket.send(json.dumps({
                                    'type': 'command_response',
                                    'action': 'start_streaming',
                                    'status': 'error',
                                    'message': 'Failed to start streaming'
                                }))
                        elif action == 'stop_streaming':
                            if self.stop_streaming():
                                await websocket.send(json.dumps({
                                    'type': 'command_response',
                                    'action': 'stop_streaming',
                                    'status': 'success',
                                    'message': 'Streaming stopped'
                                }))
                    
                    elif msg_type == 'disconnect':
                        break
                        
                except json.JSONDecodeError:
                    logger.error(f"Invalid message format from client {client_id}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} connection closed unexpectedly")
        finally:
            self.clients.remove(websocket)
            self.last_heartbeat.pop(client_id, None)
            logger.info(f"Client {client_id} disconnected. Remaining clients: {len(self.clients)}")
            if not self.clients:
                self.stop_streaming()
                if self.video_capture:
                    self.video_capture.release()
                    self.video_capture = None

    async def stream_frames(self):
        """Stream frames to all connected clients"""
        frame_count = 0
        last_time = time.time()
        
        # Only create window if display is enabled
        if self.is_display_window:
            cv2.namedWindow("Robot Camera Stream", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Robot Camera Stream", 640, 480)
        
        try:
            while self.is_streaming and self.clients:
                try:
                    # Get frame from queue
                    frame, capture_time = self.frame_queue.get_nowait()
                    frame_count += 1
                    
                    # Only display frame if window display is enabled
                    if self.is_display_window:
                        try:
                            cv2.imshow("Robot Camera Stream", frame)
                            key = cv2.waitKey(1) & 0xFF
                            if key == 27:  # ESC key to quit
                                break
                        except Exception as e:
                            logger.error(f"Display error: {e}")
                    
                    # Convert to JPEG
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                    encode_start = time.time()
                    _, buffer = cv2.imencode('.jpg', frame, encode_param)
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                    
                    # Log processing times periodically
                    if frame_count % 30 == 0:
                        current_time = time.time()
                        encode_time = current_time - encode_start
                        total_time = current_time - last_time
                        last_time = current_time
                        logger.debug(
                            f"Frame stats - Size: {len(jpg_as_text)} bytes, "
                            f"Encode time: {encode_time*1000:.1f}ms, "
                            f"Rate: {30/total_time:.1f} FPS"
                        )
                    
                    # Prepare frame data
                    frame_data = json.dumps({
                        'type': 'image',
                        'image': jpg_as_text,
                        'timestamp': datetime.now().isoformat(),
                        'frame_number': frame_count
                    })

                    # Send to all clients
                    if self.clients:
                        await asyncio.gather(
                            *[client.send(frame_data) for client in self.clients],
                            return_exceptions=True
                        )

                    # Maintain target frame rate
                    await asyncio.sleep(self.frame_interval)

                except queue.Empty:
                    await asyncio.sleep(0.001)
                except Exception as e:
                    logger.error(f"Error in stream_frames: {e}")
                    await asyncio.sleep(0.1)
                    
        finally:
            if self.is_display_window:
                cv2.destroyAllWindows()
            logger.info(f"Streaming stopped after {frame_count} frames")

    async def start_server(self):
        """Start the WebSocket server"""
        try:
            server = await websockets.serve(
                self.handle_client,
                self.websocket_host,
                self.websocket_port,
                max_size=2**23,  # 8MB max message size
                compression=None,  # Disable compression for better performance
                ping_interval=20,
                ping_timeout=30
            )
            logger.info(f"WebSocket server started on ws://{self.websocket_host}:{self.websocket_port}")
            await asyncio.Future()  # run forever
        except Exception as e:
            logger.error(f"Failed to start server: {e}")

if __name__ == "__main__":
    # Update with your actual Wyze cam RTSP URL
    CAMERA_URL = "rtsp://Atif:27516515@192.168.1.10/live"  # Your actual camera URL
    
    # Create server with display window disabled by default
    server = RobotCameraServer(
        CAMERA_URL,
        is_display_window=False  # Set to True to enable window display
    )
    
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
