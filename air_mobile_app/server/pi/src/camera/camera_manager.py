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

logger = logging.getLogger('CameraManager')
# Configure logging to show more details
logging.basicConfig(level=logging.DEBUG)

class CameraManager:
    def __init__(self, camera_url: str, is_display_window: bool = False, max_retries: int = 3):
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
        if not self.is_streaming and self.video_capture:
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
            
            # Update frame queue (drop frames if queue is full)
            try:
                self.frame_queue.put((frame, current_time), block=False)
            except queue.Full:
                try:
                    self.frame_queue.get_nowait()  # Remove oldest frame
                    self.frame_queue.put((frame, current_time), block=False)
                except:
                    pass

    async def get_frame(self) -> dict:
        """Get the next frame as a JSON-compatible dictionary"""
        try:
            frame, capture_time = self.frame_queue.get_nowait()
            
            # Convert to JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            encode_start = time.time()
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