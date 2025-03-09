import cv2
import base64
import json
import logging
import time
from datetime import datetime
import threading
import queue
import sys

logger = logging.getLogger('CameraManager')

class CameraManager:
    def __init__(self, camera_url: str, is_display_window: bool = False):
        self.camera_url = camera_url
        self.video_capture = None
        self.is_streaming = False
        self.is_display_window = is_display_window
        self.frame_queue = queue.Queue(maxsize=3)  # Buffer 3 frames max
        self.frame_thread = None
        self.frame_interval = 1/15  # Target 15 FPS

    def test_rtsp_connection(self) -> bool:
        """Test RTSP connection using ffmpeg"""
        try:
            logger.info(f"Testing RTSP connection to {self.camera_url}")
            
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
                timeout=5
            )
            
            if process.returncode == 0:
                logger.info("RTSP connection test successful")
                return True
            else:
                logger.error(f"RTSP connection test failed: {process.stderr.decode()}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("RTSP connection test timed out")
            return False
        except Exception as e:
            logger.error(f"Error testing RTSP connection: {e}")
            return False

    def init_camera(self) -> bool:
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

    def _capture_frames(self):
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
        self.stop_streaming()
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
        if self.is_display_window:
            cv2.destroyAllWindows() 