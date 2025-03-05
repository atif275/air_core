import cv2
import base64
import json
import logging
import threading
import queue
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger('CameraManager')

class CameraManager:
    def __init__(self, camera_url: str):
        self.camera_url = camera_url
        self.is_streaming = False
        self.video_capture: Optional[cv2.VideoCapture] = None
        self.frame_queue = queue.Queue(maxsize=2)
        self.frame_thread: Optional[threading.Thread] = None

    def start_camera(self) -> bool:
        """Start camera streaming"""
        try:
            self.video_capture = cv2.VideoCapture(self.camera_url)
            self.video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Configure camera
            self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.video_capture.set(cv2.CAP_PROP_FPS, 30)
            
            if not self.video_capture.isOpened():
                raise Exception("Failed to open camera stream")
                
            self.is_streaming = True
            
            # Start frame capture thread
            self.frame_thread = threading.Thread(target=self._capture_frames)
            self.frame_thread.daemon = True
            self.frame_thread.start()
            
            logger.info("Camera stream started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start camera: {e}")
            self.is_streaming = False
            return False

    def _capture_frames(self):
        """Capture frames in a separate thread"""
        while self.is_streaming:
            if self.video_capture is None or not self.video_capture.isOpened():
                break
                
            ret, frame = self.video_capture.read()
            if not ret:
                continue

            frame = cv2.resize(frame, (640, 480))
            
            try:
                self.frame_queue.put(frame, block=False)
            except queue.Full:
                try:
                    self.frame_queue.get_nowait()
                    self.frame_queue.put(frame, block=False)
                except:
                    pass

    async def get_frame(self) -> Optional[Dict]:
        """Get the next frame as a JSON-compatible dictionary"""
        try:
            frame = self.frame_queue.get_nowait()
            
            # Convert to JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            # Convert to base64
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
            return {
                'type': 'camera_frame',
                'image': jpg_as_text,
                'timestamp': datetime.now().isoformat()
            }
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error getting frame: {e}")
            return None

    def stop_camera(self):
        """Stop camera streaming"""
        self.is_streaming = False
        if self.frame_thread:
            self.frame_thread.join(timeout=1.0)
        if self.video_capture:
            self.video_capture.release()
        logger.info("Camera stream stopped")

    def get_camera_status(self) -> Dict:
        """Get current camera status"""
        return {
            "is_streaming": self.is_streaming,
            "camera_url": self.camera_url,
            "frame_queue_size": self.frame_queue.qsize(),
            "last_update": datetime.now().isoformat()
        } 