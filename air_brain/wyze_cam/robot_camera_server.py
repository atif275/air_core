import asyncio
import websockets
import cv2
import base64
import json
import logging
from datetime import datetime
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RobotCameraServer')

class RobotCameraServer:
    def __init__(self, camera_url, websocket_host='0.0.0.0', websocket_port=8765):
        self.camera_url = camera_url
        self.websocket_host = websocket_host
        self.websocket_port = websocket_port
        self.clients = set()
        self.is_streaming = False
        self.video_capture = None
        self.frame_queue = queue.Queue(maxsize=2)  # Limit queue size
        self.frame_thread = None

    def capture_frames(self):
        """Capture frames in a separate thread"""
        while self.is_streaming:
            if self.video_capture is None or not self.video_capture.isOpened():
                break
                
            ret, frame = self.video_capture.read()
            if not ret:
                continue

            # Resize frame
            frame = cv2.resize(frame, (640, 480))
            
            # Update frame queue (drop frames if queue is full)
            try:
                self.frame_queue.put(frame, block=False)
            except queue.Full:
                try:
                    self.frame_queue.get_nowait()  # Remove old frame
                    self.frame_queue.put(frame, block=False)
                except:
                    pass

    async def handle_client(self, websocket):
        try:
            self.clients.add(websocket)
            logger.info(f"New client connected. Total clients: {len(self.clients)}")
            
            await websocket.send(json.dumps({
                'type': 'connection_status',
                'status': 'success',
                'message': 'Connected to robot camera successfully',
                'timestamp': datetime.now().isoformat()
            }))

            if not self.is_streaming:
                self.start_camera()

            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('type') == 'disconnect':
                        break
                except json.JSONDecodeError:
                    logger.error("Invalid message format")

        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed unexpectedly")
        finally:
            self.clients.remove(websocket)
            logger.info(f"Client disconnected. Remaining clients: {len(self.clients)}")
            if not self.clients:
                self.stop_camera()

    def start_camera(self):
        """Start camera streaming"""
        try:
            self.video_capture = cv2.VideoCapture(self.camera_url)
            self.video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer size
            
            # Set camera properties for better performance
            self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.video_capture.set(cv2.CAP_PROP_FPS, 30)
            
            if not self.video_capture.isOpened():
                raise Exception("Failed to open camera stream")
                
            self.is_streaming = True
            logger.info("Camera stream started")
            
            # Start frame capture thread
            self.frame_thread = threading.Thread(target=self.capture_frames)
            self.frame_thread.daemon = True
            self.frame_thread.start()
            
            # Start frame streaming
            asyncio.create_task(self.stream_frames())
            
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            self.is_streaming = False

    async def stream_frames(self):
        """Stream camera frames to all connected clients"""
        cv2.namedWindow("Robot Camera Stream", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Robot Camera Stream", 640, 480)
        
        try:
            while self.is_streaming and self.clients:
                try:
                    # Get frame from queue
                    frame = self.frame_queue.get_nowait()
                    
                    # Display frame
                    cv2.imshow("Robot Camera Stream", frame)
                    cv2.waitKey(1)
                    
                    # Convert to JPEG with lower quality for faster transmission
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]
                    _, buffer = cv2.imencode('.jpg', frame, encode_param)
                    
                    # Convert to base64
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                    
                    # Prepare and send frame data
                    frame_data = json.dumps({
                        'type': 'image',
                        'image': jpg_as_text,
                        'timestamp': datetime.now().isoformat()
                    })

                    if self.clients:
                        await asyncio.gather(
                            *[client.send(frame_data) for client in self.clients],
                            return_exceptions=True
                        )

                    # Shorter sleep for higher frame rate
                    await asyncio.sleep(0.016)  # ~60 FPS

                except queue.Empty:
                    await asyncio.sleep(0.001)
                except Exception as e:
                    logger.error(f"Error in stream_frames: {e}")
                    await asyncio.sleep(0.1)
                    
        finally:
            cv2.destroyWindow("Robot Camera Stream")
            logger.info("Closed display window")

    def stop_camera(self):
        """Stop camera streaming"""
        self.is_streaming = False
        if self.frame_thread:
            self.frame_thread.join(timeout=1.0)
        if self.video_capture:
            self.video_capture.release()
        cv2.destroyAllWindows()
        logger.info("Camera stream stopped")

    async def start_server(self):
        """Start the WebSocket server"""
        try:
            server = await websockets.serve(
                self.handle_client,
                self.websocket_host,
                self.websocket_port,
                max_size=2**23,  # 8MB max message size
                compression=None  # Disable compression for better performance
            )
            logger.info(f"WebSocket server started on ws://{self.websocket_host}:{self.websocket_port}")
            await asyncio.Future()
        except Exception as e:
            logger.error(f"Failed to start server: {e}")

if __name__ == "__main__":
    # Replace with your Wyze cam RTSP URL
    CAMERA_URL = "rtsp://Atif:27516515@192.168.1.9/live"
    
    server = RobotCameraServer(CAMERA_URL)
    
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        if server.video_capture:
            server.stop_camera()
