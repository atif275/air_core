import asyncio
import logging
import sys
import os
import argparse
from typing import Optional
import json
import signal
from pathlib import Path

# Update the import path to include the parent directory
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Use absolute import
from websocket.server import WebSocketServer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('robot_server.log')
    ]
)
logger = logging.getLogger(__name__)

class RobotServer:
    def __init__(self, config: dict):
        self.config = config
        self.server: Optional[WebSocketServer] = None
        self._setup_signal_handlers()
        self._shutdown_event = asyncio.Event()

    def _setup_signal_handlers(self):
        """Setup handlers for graceful shutdown"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received (CTRL+C)")
        if self.server:
            logger.info("Initiating graceful shutdown...")
            # Set the shutdown event
            if asyncio.get_event_loop().is_running():
                asyncio.create_task(self._shutdown())
            else:
                self.server.stop()

    async def _shutdown(self):
        """Perform graceful shutdown"""
        try:
            # Stop the server
            self.server.stop()
            
            # Wait for ongoing operations to complete
            await asyncio.sleep(1)
            
            # Set shutdown event
            self._shutdown_event.set()
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    async def start(self):
        """Start the robot server"""
        try:
            logger.info("Starting Robot Server...")
            logger.info(f"Configuration: {self.config}")

            # Initialize WebSocket server
            self.server = WebSocketServer(
                host=self.config['server']['host'],
                port=self.config['server']['port'],
                camera_url=self.config['camera'].get('url'),
                heartbeat_interval=self.config['server'].get('heartbeat_interval', 30)
            )

            # Start server
            server_task = asyncio.create_task(self.server.start())
            
            # Wait for either server completion or shutdown signal
            await asyncio.wait([
                server_task,
                self._shutdown_event.wait()
            ], return_when=asyncio.FIRST_COMPLETED)

            logger.info("Server shutdown complete")

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise

def load_config(config_path: str) -> dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return get_default_config()

def get_default_config() -> dict:
    """Get default configuration"""
    return {
        "server": {
            "host": "0.0.0.0",
            "port": 8765,
            "heartbeat_interval": 30
        },
        "camera": {
            "url": None,
            "display_window": False
        },
        "monitoring": {
            "update_interval": 1.0,
            "enable_diagnostics": True
        }
    }

def create_default_config(config_path: str):
    """Create default configuration file"""
    config_dir = os.path.dirname(config_path)
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(get_default_config(), f, indent=4)
    
    logger.info(f"Created default configuration at {config_path}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Robot Server')
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/robot_config.json',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--camera-url',
        type=str,
        help='RTSP URL for the camera (overrides config file)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        help='WebSocket server port (overrides config file)'
    )
    
    parser.add_argument(
        '--display',
        action='store_true',
        help='Enable camera display window'
    )
    
    return parser.parse_args()

async def main():
    # Replace with your Wyze cam RTSP URL
    CAMERA_URL = "rtsp://Atif:27516515@192.168.1.12/live"
    
    # Make sure the server is running on 0.0.0.0
    server = WebSocketServer(
        host="0.0.0.0",  # Explicitly bind to all interfaces
        port=8765,
        camera_url=CAMERA_URL
    )
    
    try:
        logger.info(f"Starting server on 0.0.0.0:8765")
        await server.start()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        if server.camera_manager:
            server.camera_manager.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user") 