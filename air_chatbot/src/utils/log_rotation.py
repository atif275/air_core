"""
Log rotation utility for managing log file sizes.

This module provides log rotation functionality to prevent log files from growing
too large. When a log file exceeds MAX_LOG_SIZE (50MB), it is rotated by renaming
it with an index suffix (e.g., system.log_0, system.log_1, etc.). The system
maintains up to MAX_LOGS (3) rotated files.

Usage:
    # Register a log handler when setting up logging
    from utils.log_rotation import register_log_handler, setup_logging
    
    log_file = "logs/myapp.log"
    setup_logging(log_file)
    handler = logging.FileHandler(log_file)
    register_log_handler(log_file, handler)
    
    # Periodically call rotate_log_files (e.g., in a background thread or main loop)
    from utils.log_rotation import rotate_log_files
    
    # In a main loop or periodic task:
    rotate_log_files(log_file)
    
    # Or rotate all known log files:
    from utils.log_rotation import rotate_all_logs
    rotate_all_logs("logs")

Example integration in a main loop:
    rotation_counter = 0
    while True:
        # Your main loop code here
        ...
        
        # Rotate logs every N iterations (e.g., every 10 minutes)
        rotation_counter += 1
        if rotation_counter >= 20:  # Adjust based on loop frequency
            rotate_log_files("logs/myapp.log")
            rotation_counter = 0
"""
import os
from datetime import datetime
from typing import Dict, Optional
import logging

# Constants
MAX_LOG_SIZE = 50 * 1024 * 1024  # 50MB
MAX_LOGS = 3

# Global dictionary to store log file handlers and their indices
_log_handlers: Dict[str, logging.FileHandler] = {}
_log_file_indices: Dict[str, int] = {}
_log_file_to_logger: Dict[str, str] = {}  # Map log file path to logger name


def create_dir_if_not_exists(path: str) -> bool:
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        return True
    return True


def get_file_size(filename: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(filename)
    except (OSError, FileNotFoundError):
        return 0


def rotate_log_files(log_file_path: str) -> bool:
    """
    Rotate log files when size exceeds limit.
    
    Args:
        log_file_path: Path to the log file to rotate
        
    Returns:
        True if rotation was successful or not needed, False otherwise
    """
    # Check if file exists and get size
    if not os.path.exists(log_file_path):
        return True
        
    size = get_file_size(log_file_path)
    if size < MAX_LOG_SIZE:
        return True
    
    # Close current file handler if it exists
    if log_file_path in _log_handlers:
        try:
            handler = _log_handlers[log_file_path]
            handler.close()
            # Remove handler from logger if it's attached
            for logger_name in ['system_logger', 'memory_logger', 'face_logger', 'ssh', 'agent', 'connection', 'file']:
                logger = logging.getLogger(logger_name)
                if handler in logger.handlers:
                    logger.removeHandler(handler)
        except Exception as e:
            print(f"[LOG ROTATION WARNING] Error closing handler for {log_file_path}: {e}")
    
    # Get current index for this log file
    if log_file_path not in _log_file_indices:
        _log_file_indices[log_file_path] = -1  # Start at -1 so first rotation becomes 0
    
    # Calculate next index (rotate through MAX_LOGS: 0, 1, 2)
    _log_file_indices[log_file_path] = (_log_file_indices[log_file_path] + 1) % MAX_LOGS
    new_path = f"{log_file_path}_{_log_file_indices[log_file_path]}"
    
    # Remove old rotated file if it exists (to keep only MAX_LOGS files)
    if os.path.exists(new_path):
        try:
            os.remove(new_path)
        except Exception as e:
            print(f"[LOG ROTATION WARNING] Could not remove old log file {new_path}: {e}")
    
    # Rename current file to rotated name
    try:
        os.rename(log_file_path, new_path)
    except Exception as e:
        print(f"[LOG ROTATION ERROR] Could not rotate log file {log_file_path}: {e}")
        return False
    
    # Recreate file handler if it was in our tracking
    if log_file_path in _log_handlers:
        try:
            old_handler = _log_handlers[log_file_path]
            
            # Create new handler
            new_handler = logging.FileHandler(log_file_path, mode='a')
            new_handler.setLevel(logging.INFO)
            
            # Copy formatter from old handler if possible
            if hasattr(old_handler, 'formatter') and old_handler.formatter:
                new_handler.setFormatter(old_handler.formatter)
            else:
                # Default formatter if old handler didn't have one
                formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s - %(message)s')
                new_handler.setFormatter(formatter)
            
            # Update stored handler
            _log_handlers[log_file_path] = new_handler
            
            # Re-add handler to the appropriate logger
            if log_file_path in _log_file_to_logger:
                logger_name = _log_file_to_logger[log_file_path]
                logger = logging.getLogger(logger_name)
                logger.addHandler(new_handler)
                print(f"[LOG ROTATION] Rotated {log_file_path} -> {new_path}, new handler added to {logger_name}")
            else:
                print(f"[LOG ROTATION WARNING] Could not find logger for {log_file_path}")
        except Exception as e:
            print(f"[LOG ROTATION WARNING] Could not recreate handler for {log_file_path}: {e}")
    
    return True


def register_log_handler(log_file_path: str, handler: logging.FileHandler, logger_name: str = None) -> None:
    """
    Register a log file handler for rotation tracking.
    
    Args:
        log_file_path: Path to the log file
        handler: The FileHandler instance
        logger_name: Name of the logger this handler belongs to (auto-detected if not provided)
    """
    _log_handlers[log_file_path] = handler
    
    # Auto-detect logger name if not provided
    if logger_name is None:
        # Try to find which logger has this handler
        for name in ['system_logger', 'memory_logger', 'face_logger']:
            logger = logging.getLogger(name)
            if handler in logger.handlers:
                logger_name = name
                break
    
    if logger_name:
        _log_file_to_logger[log_file_path] = logger_name


def setup_logging(log_file_path: str) -> bool:
    """
    Setup logging directory and file.
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        True if setup was successful
    """
    # Create logs directory
    logs_dir = os.path.dirname(log_file_path)
    if logs_dir:
        create_dir_if_not_exists(logs_dir)
    
    return True


def rotate_all_logs(log_dir: str = "logs") -> None:
    """
    Rotate all log files in the specified directory.
    Call this function periodically (e.g., in a background thread or after certain operations).
    
    Args:
        log_dir: Directory containing log files
    """
    log_files = [
        os.path.join(log_dir, "system.log"),
        os.path.join(log_dir, "memory.log"),
        os.path.join(log_dir, "face.log"),
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            rotate_log_files(log_file)

