"""Logging module for facial analysis."""
import logging
import os
import inspect
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FaceLogger:
    """Singleton logger for facial analysis."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FaceLogger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance
    
    def _initialize_logger(self):
        """Initialize the logger with file and console handlers."""
        self.logger = logging.getLogger('face_logger')
        self.logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # File handler for face.log
        file_handler = logging.FileHandler('logs/face.log')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s'
        )
        
        # Set formatter for handlers
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Check if logging is enabled
        self.logging_enabled = os.getenv('FACE_LOGGING_ENABLED', 'true').lower() == 'true'
        if not self.logging_enabled:
            self.logger.setLevel(logging.CRITICAL)
            
        # Track last recognized person and state
        self.last_recognized_person = None
        self.last_face_id = None
        self.last_distance = None
        self.last_track_count = None
        self.last_distance_log_time = None
        
        # Configuration for distance logging
        self.distance_change_threshold = 10.0  # Only log if distance changes by more than 10 units
        self.min_time_between_distance_logs = timedelta(seconds=2)  # Minimum time between distance logs
    
    def _should_log(self, level: str, message: str) -> bool:
        """Determine if a message should be logged based on its content and level"""
        if not self.logging_enabled:
            return False
            
        # Skip verbose frame-by-frame logs
        if any(x in message.lower() for x in [
            'detected 1 faces in frame',
            'updated track',
            'active tracks',
            'calculated brightness',
            'face quality check passed',
            'collecting recognition embeddings',
            'updating active person',
            'calculated and cached new features'
        ]):
            return False
            
        # Skip redundant IoU calculations
        if 'iou calculated' in message.lower():
            return False
            
        # Handle track updates
        if 'updated' in message.lower() and 'face tracks' in message.lower():
            try:
                track_count = int(message.split('Updated ')[1].split(' face')[0])
                if track_count == self.last_track_count:
                    return False
                self.last_track_count = track_count
            except (IndexError, ValueError):
                pass
                
        # Handle person recognition logs
        if 'high confidence match found for' in message.lower():
            # Extract person ID from message
            try:
                person_id = int(message.split('ID: ')[1].strip(')'))
                if person_id == self.last_recognized_person:
                    return False
                self.last_recognized_person = person_id
            except (IndexError, ValueError):
                pass
                
        # Handle face recognition at distance logs
        if 'face' in message.lower() and 'recognized at distance' in message.lower():
            try:
                face_id = int(message.split('Face ')[1].split(' ')[0])
                distance = float(message.split('distance ')[1])
                current_time = datetime.now()
                
                # Check if enough time has passed since last distance log
                if (self.last_distance_log_time is not None and 
                    current_time - self.last_distance_log_time < self.min_time_between_distance_logs):
                    return False
                
                # Log if it's a new face or if distance changed significantly
                if (face_id != self.last_face_id or 
                    self.last_distance is None or 
                    abs(distance - self.last_distance) > self.distance_change_threshold):
                    self.last_face_id = face_id
                    self.last_distance = distance
                    self.last_distance_log_time = current_time
                    return True
                return False
            except (IndexError, ValueError):
                pass
                
        # Skip active person update messages
        if 'active person updated successfully' in message.lower():
            return False
                
        return True
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with the specified level if it passes filtering"""
        if not self._should_log(level, message):
            return
            
        # Get caller information
        frame = inspect.currentframe()
        try:
            caller_frame = frame.f_back
            filename = os.path.basename(caller_frame.f_code.co_filename)
            line_number = caller_frame.f_lineno
            function_name = caller_frame.f_code.co_name
            
            # Create a LogRecord with caller information
            record = logging.LogRecord(
                name='face_logger',
                level=getattr(logging, level),
                pathname=filename,
                lineno=line_number,
                msg=message,
                args=(),
                exc_info=None
            )
            record.funcName = function_name
            
            # Log the record
            self.logger.handle(record)
        finally:
            del frame

# Create a singleton instance
face_logger = FaceLogger() 