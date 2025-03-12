import cv2
import base64
import json
import logging
import time
from datetime import datetime
import threading
import queue
import sys
import subprocess
from typing import Optional
import asyncio
import websockets
import os

logger = logging.getLogger('CameraManager')
# Configure logging to show more details
logging.basicConfig(level=logging.DEBUG)

class CameraManager:
    def __init__(self, camera_url: str, is_display_window: bool = False, max_retries: int = 3, ml_config=None):
        logger.info(f"Initializing CameraManager with URL: {camera_url}")
        self.camera_url = camera_url
        self.video_capture = None
        self.is_streaming = False
        self.is_display_window = is_display_window
        self.frame_queue = queue.Queue(maxsize=3)  # Buffer 3 frames max
        self.frame_thread = None
        self.frame_interval = 1/15  # Target 15 FPS
        self.max_retries = max_retries
        self.current_retry = 0
        
        # ML Server configuration - completely separate from main streaming
        self.ml_config = ml_config
        self.ml_enabled = ml_config and ml_config.get('enabled', False)
        self.ml_websocket = None
        self.ml_connected = False
        self.ml_thread = None
        self.ml_frame_queue = queue.Queue(maxsize=10)  # Buffer for ML frames
        self.last_ml_frame_time = 0
        self.ml_frame_interval = 1.0 / ml_config.get('max_fps', 2) if ml_config else 0.5  # Default to 2 FPS
        
        # Initialize ML server connection if enabled
        if self.ml_enabled:
            self.init_ml_connection()

    def init_ml_connection(self):
        """Initialize connection to ML server in a separate thread"""
        if not self.ml_enabled or not self.ml_config:
            logger.warning("ML server is not enabled or configured")
            return False
            
        # Create and start the ML connection thread
        self.ml_thread = threading.Thread(target=self._ml_connection_thread, daemon=True)
        self.ml_thread.start()
        logger.info("ML connection thread started")
        return True
        
    def _ml_connection_thread(self):
        """Thread to maintain connection with ML server and send frames"""
        ml_host = self.ml_config.get('host', '127.0.0.1')
        ml_port = self.ml_config.get('port', 8765)
        ml_uri = f"ws://{ml_host}:{ml_port}"
        
        logger.info(f"Starting ML connection thread to {ml_uri}")
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def connect_and_send():
            while True:
                if not self.ml_enabled or not self.is_streaming:
                    logger.info("ML server disabled or streaming stopped, pausing ML connection")
                    await asyncio.sleep(1.0)
                    continue
                    
                try:
                    logger.info(f"Connecting to ML server at {ml_uri}")
                    async with websockets.connect(ml_uri, max_size=2**25, ping_interval=None) as websocket:
                        self.ml_websocket = websocket
                        self.ml_connected = True
                        logger.info("Connected to ML server")
                        
                        # Wait for ready message
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            response_data = json.loads(response)
                            if response_data.get('type') == 'ready':
                                logger.info("ML server is ready to receive frames")
                        except (asyncio.TimeoutError, Exception) as e:
                            logger.warning(f"Did not receive ready message from ML server: {e}")
                        
                        # Process frames from the queue while connected
                        while self.ml_connected and self.ml_enabled and self.is_streaming:
                            try:
                                # Non-blocking get with timeout
                                frame_data = self.ml_frame_queue.get(timeout=1.0)
                                
                                # Send frame to ML server
                                await websocket.send(json.dumps(frame_data))
                                
                                # Don't wait for acknowledgment - this was causing delays
                                # Just continue processing the next frame
                                
                            except queue.Empty:
                                # No frames in queue, just continue
                                await asyncio.sleep(0.1)
                            except Exception as e:
                                logger.error(f"Error processing ML frame: {e}")
                                await asyncio.sleep(1.0)
                                
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("ML server connection closed")
                except Exception as e:
                    logger.error(f"ML connection error: {e}")
                
                # Reset connection state
                self.ml_websocket = None
                self.ml_connected = False
                
                # Wait before reconnecting
                logger.info("Waiting 5 seconds before reconnecting to ML server")
                await asyncio.sleep(5)
        
        # Run the async function in the thread's event loop
        try:
            loop.run_until_complete(connect_and_send())
        except Exception as e:
            logger.error(f"ML connection thread error: {e}")
        finally:
            loop.close()

    def test_rtsp_connection(self) -> bool:
        """Test RTSP connection using ffmpeg with retry logic"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Testing RTSP connection to {self.camera_url} (Attempt {attempt + 1}/{self.max_retries})")
                
                # Use ffmpeg to test RTSP connection
                command = [
                    'ffprobe',
                    '-v', 'error',
                    '-rtsp_transport', 'tcp',  # Try TCP first
                    '-i', self.camera_url,
                    '-show_entries',
                    'stream=width,height',
                    '-of', 'json'
                ]
                
                process = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10  # Increased timeout to 10 seconds
                )
                
                if process.returncode == 0:
                    logger.info("RTSP connection test successful")
                    return True
                else:
                    error_msg = process.stderr.decode()
                    logger.warning(f"RTSP connection test failed (Attempt {attempt + 1}): {error_msg}")
                    # If this is not the last attempt, wait before retrying
                    if attempt < self.max_retries - 1:
                        time.sleep(2)  # Wait 2 seconds between attempts
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"RTSP connection test timed out (Attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    time.sleep(2)
            except Exception as e:
                logger.error(f"Error testing RTSP connection (Attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2)
        
        logger.error("All RTSP connection attempts failed")
        return False

    def init_camera(self) -> bool:
        """Initialize camera without starting stream"""
        for attempt in range(self.max_retries):
            try:
                if self.video_capture is None:
                    logger.info(f"Initializing camera at {self.camera_url} (Attempt {attempt + 1}/{self.max_retries})")
                    
                    # First test the RTSP connection
                    if self.camera_url.startswith('rtsp://'):
                        if not self.test_rtsp_connection():
                            if attempt < self.max_retries - 1:
                                time.sleep(2)
                                continue
                            return False
                    
                    # Simple initialization with FFMPEG backend
                    self.video_capture = cv2.VideoCapture(self.camera_url, cv2.CAP_FFMPEG)
                    
                    if not self.video_capture.isOpened():
                        logger.warning(f"Failed to open camera (Attempt {attempt + 1}) - camera not accessible")
                        if attempt < self.max_retries - 1:
                            time.sleep(2)
                            continue
                        return False
                    
                    # Configure camera properties
                    self.video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.video_capture.set(cv2.CAP_PROP_FPS, 30)
                    
                    # Test first frame with timeout
                    start_time = time.time()
                    while time.time() - start_time < 5:  # 5 second timeout for first frame
                        ret, frame = self.video_capture.read()
                        if ret and frame is not None:
                            logger.info("Camera initialized successfully")
                            return True
                        time.sleep(0.1)
                    
                    logger.warning(f"Could not read first frame (Attempt {attempt + 1})")
                    self.video_capture.release()
                    self.video_capture = None
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(2)
                        continue
                    
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to initialize camera (Attempt {attempt + 1}): {str(e)}", exc_info=True)
                if self.video_capture:
                    self.video_capture.release()
                self.video_capture = None
                if attempt < self.max_retries - 1:
                    time.sleep(2)
                    continue
                return False
        
        return False

    def start_streaming(self) -> bool:
        """Start streaming frames"""
        if not self.is_streaming and self.init_camera():
            self.is_streaming = True
            logger.info("Starting camera stream")
            
            # Start frame capture thread
            self.frame_thread = threading.Thread(target=self._capture_frames)
            self.frame_thread.daemon = True
            self.frame_thread.start()
            
            return True
        return False

    def stop_streaming(self) -> bool:
        """Stop streaming frames but keep camera initialized"""
        if self.is_streaming:
            self.is_streaming = False
            logger.info("Camera streaming stopped")
            
            # Wait for frame thread to finish
            if self.frame_thread and self.frame_thread.is_alive():
                self.frame_thread.join(timeout=2.0)
                
            # Properly release the camera to ensure it can be reinitialized
            if self.video_capture:
                self.video_capture.release()
                self.video_capture = None
                
            # Clear the frame queue
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break
                    
            return True
        return False

    def _capture_frames(self):
        """Capture frames in a separate thread"""
        frame_count = 0
        last_time = time.time()
        
        # Create display window if enabled
        if self.is_display_window:
            try:
                # Create window with specific flags to ensure visibility
                cv2.namedWindow("Live Camera Feed", cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_EXPANDED)
                cv2.resizeWindow("Live Camera Feed", 640, 480)
                # Move window to a visible position on screen
                cv2.moveWindow("Live Camera Feed", 100, 100)
                logger.info("Display window created successfully")
            except Exception as e:
                logger.error(f"Failed to create display window: {e}")
                self.is_display_window = False  # Disable display window on error
        
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
            
            # Display frame if enabled and window was created successfully
            if self.is_display_window:
                try:
                    cv2.imshow("Live Camera Feed", frame)
                    # Bring window to front periodically
                    if frame_count % 30 == 0:
                        cv2.setWindowProperty("Live Camera Feed", cv2.WND_PROP_TOPMOST, 1)
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:  # ESC key to quit
                        self.is_streaming = False
                        break
                except Exception as e:
                    logger.error(f"Error displaying frame: {e}")
                    self.is_display_window = False  # Disable display on error
            
            if frame_count % 30 == 0:  # Log stats every 30 frames
                logger.debug(f"Frame capture rate: {1/frame_time:.1f} FPS")
            
            # Update frame queue for client streaming (drop frames if queue is full)
            try:
                self.frame_queue.put((frame, current_time), block=False)
            except queue.Full:
                try:
                    self.frame_queue.get_nowait()  # Remove oldest frame
                    self.frame_queue.put((frame, current_time), block=False)
                except:
                    pass
            
            # Handle ML frame separately - only if ML is enabled and connected
            # This is done in a non-blocking way to avoid affecting main streaming
            if self.ml_enabled and self.ml_connected:
                current_ml_time = time.time()
                if current_ml_time - self.last_ml_frame_time >= self.ml_frame_interval:
                    # Process ML frame in a separate thread to avoid blocking the main capture thread
                    threading.Thread(
                        target=self._process_ml_frame,
                        args=(frame.copy(), current_ml_time, frame_count),
                        daemon=True
                    ).start()
                    self.last_ml_frame_time = current_ml_time

    def _process_ml_frame(self, frame, timestamp, frame_count):
        """Process a frame for ML in a separate thread to avoid blocking the main capture thread"""
        try:
            # Convert frame to JPEG for ML server
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
            # Add to ML queue if not full
            if not self.ml_frame_queue.full():
                self.ml_frame_queue.put({
                    'type': 'image',
                    'image': jpg_as_text,
                    'frame_number': frame_count,
                    'timestamp': int(timestamp * 1000)
                })
                logger.debug(f"Processed frame {frame_count} for ML server")
        except Exception as e:
            logger.error(f"Error processing ML frame: {e}")

    async def get_frame(self) -> dict:
        """Get the next frame as a JSON-compatible dictionary"""
        try:
            frame, capture_time = self.frame_queue.get_nowait()
            
            # Convert to JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
            return {
                'type': 'image',
                'image': jpg_as_text,
                'timestamp': datetime.now().isoformat()
            }
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error getting frame: {e}")
            return None

    def get_status(self) -> dict:
        """Get current camera status"""
        return {
            "is_streaming": self.is_streaming,
            "is_connected": self.video_capture.isOpened() if self.video_capture else False,
            "frame_queue_size": self.frame_queue.qsize(),
            "camera_url": self.camera_url,
            "ml_enabled": self.ml_enabled,
            "ml_connected": self.ml_connected,
            "timestamp": datetime.now().isoformat()
        }

    def cleanup(self):
        """Clean up resources"""
        self.is_streaming = False
        
        # Wait for frame thread to finish
        if self.frame_thread and self.frame_thread.is_alive():
            self.frame_thread.join(timeout=2.0)
            
        # Release camera
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
            
        # Close any OpenCV windows
        if self.is_display_window:
            try:
                cv2.destroyAllWindows()
            except:
                pass
                
        # Clear the frame queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
                
        # Disconnect from ML server
        if self.ml_enabled:
            self.ml_enabled = False
            self.ml_connected = False
            # Wait for ML thread to finish
            if self.ml_thread and self.ml_thread.is_alive():
                self.ml_thread.join(timeout=2.0) 