"""Logging module for the chatbot."""
import logging
import os
import inspect
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SystemLogger:
    """Singleton logger for the chatbot system."""
    _instance: Optional['SystemLogger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SystemLogger, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the logger with file and console handlers."""
        self.logger = logging.getLogger('system_logger')
        self.logger.setLevel(logging.INFO)
        
        # Check if logging is enabled for system and memory
        self.system_logging_enabled = os.getenv('SYSTEM_LOGGING_ENABLED', 'true').lower() == 'true'
        self.memory_logging_enabled = os.getenv('MEMORY_LOGGING_ENABLED', 'true').lower() == 'true'
        
        # If both logging types are disabled, set level to CRITICAL to suppress all logs
        if not (self.system_logging_enabled or self.memory_logging_enabled):
            self.logger.setLevel(logging.CRITICAL)
            return
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # System log file handler
        if self.system_logging_enabled:
            system_log_file = os.path.join('logs', 'system.log')
            system_file_handler = logging.FileHandler(system_log_file)
            system_file_handler.setLevel(logging.INFO)
            system_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s')
            system_file_handler.setFormatter(system_formatter)
            self.logger.addHandler(system_file_handler)
        
        # Memory log file handler
        if self.memory_logging_enabled:
            memory_log_file = os.path.join('logs', 'memory.log')
            memory_file_handler = logging.FileHandler(memory_log_file)
            memory_file_handler.setLevel(logging.INFO)
            memory_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s')
            memory_file_handler.setFormatter(memory_formatter)
            
            # Create memory logger
            self.memory_logger = logging.getLogger('memory_logger')
            self.memory_logger.setLevel(logging.INFO)
            self.memory_logger.addHandler(memory_file_handler)
            
            # Prevent propagation to avoid duplicate logs
            self.memory_logger.propagate = False
        
        # Console handler (only if either logging type is enabled)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Add console handler to appropriate loggers
        if self.system_logging_enabled:
            self.logger.addHandler(console_handler)
        if self.memory_logging_enabled:
            self.memory_logger.addHandler(console_handler)
    
    def _get_caller_info(self):
        """Get information about the caller of the log function."""
        frame = inspect.currentframe()
        try:
            # Go up two frames to get the caller of the log function
            caller_frame = frame.f_back.f_back
            return {
                'filename': os.path.basename(caller_frame.f_code.co_filename),
                'lineno': caller_frame.f_lineno,
                'funcName': caller_frame.f_code.co_name
            }
        finally:
            del frame
    
    def log(self, message: str, level: str = "INFO", is_memory_log: bool = False) -> None:
        """
        Log a message with the specified level.
        
        Args:
            message: The message to log
            level: The log level (INFO, WARNING, ERROR)
            is_memory_log: Whether this is a memory/session related log
        """
        # Check if the appropriate logging type is enabled
        if is_memory_log and not self.memory_logging_enabled:
            return
        if not is_memory_log and not self.system_logging_enabled:
            return
            
        logger = self.memory_logger if is_memory_log else self.logger
        log_func = getattr(logger, level.lower(), logger.info)
        
        # Get caller information
        caller_info = self._get_caller_info()
        
        # Create a LogRecord with the caller information
        record = logging.LogRecord(
            name=logger.name,
            level=getattr(logging, level.upper()),
            pathname=caller_info['filename'],
            lineno=caller_info['lineno'],
            msg=message,
            args=(),
            exc_info=None
        )
        record.funcName = caller_info['funcName']
        
        # Handle the log record
        logger.handle(record)

# Create singleton instance
system_logger = SystemLogger() 