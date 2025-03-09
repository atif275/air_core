import asyncio
import json
import websockets
from datetime import datetime
import cv2
import os
import sys
import logging
from typing import Dict, Set

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitoring.system_monitor import SystemMonitor

logger = logging.getLogger(__name__)

class MonitoringWebSocket:
    def __init__(self, config_path: str = "src/config/robot_config.json"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Server settings
        self.host = self.config['server']['host']
        self.port = self.config['server']['port']
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Camera settings
        self.camera_url = self.config['camera']['url']
        self.display_window = self.config['camera']['display_window']
        self.cap = None
        self.streaming = False
        
        # Monitoring settings
        self.system_monitor = SystemMonitor()
        self.update_interval = self.config['monitoring']['update_interval']

    async def setup_camera(self):
        """Initialize camera capture"""
        try:
            self.cap = cv2.VideoCapture(self.camera_url)
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera: {self.camera_url}")
                return False
            logger.info("Camera initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Camera setup error: {e}")
            return False

    async def process_frame(self):
        """Process and return camera frame"""
        if not self.cap or not self.cap.isOpened():
            return None
            
        ret, frame = self.cap.read()
        if not ret:
            return None
            
        # Display frame if configured
        if self.display_window:
            cv2.imshow('Robot Camera', frame)
            cv2.waitKey(1)
            
        # Encode frame for streaming
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()

    async def start_streaming(self, websocket):
        """Start camera streaming"""
        if not self.streaming:
            if not self.cap and not await self.setup_camera():
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Failed to initialize camera"
                }))
                return False
                
        self.streaming = True
        await websocket.send(json.dumps({
            "type": "command_response",
            "action": "start_streaming",
            "status": "success"
        }))
        return True

    async def stop_streaming(self):
        """Stop camera streaming"""
        self.streaming = False
        if self.display_window:
            cv2.destroyAllWindows()
        if self.cap:
            self.cap.release()
            self.cap = None

    async def register(self, websocket):
        """Register a new client connection"""
        self.clients.add(websocket)
        print(f"New client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket):
        """Unregister a client connection"""
        self.clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(self.clients)}")

    async def send_updates(self):
        """Send periodic updates to all connected clients"""
        while True:
            if self.clients:
                try:
                    # Prepare monitoring data
                    monitoring_data = {
                        "timestamp": datetime.now().isoformat(),
                        "basic_status": self.system_monitor.get_basic_status(),
                        "health_metrics": self.system_monitor.get_health_metrics(),
                        "diagnostic_info": self.system_monitor.get_diagnostic_info()
                    }
                    
                    # Add camera frame if streaming
                    if self.streaming:
                        frame_data = await self.process_frame()
                        if frame_data:
                            monitoring_data["camera_frame"] = frame_data
                    
                    # Send to all clients
                    message = json.dumps(monitoring_data)
                    
                    # Send to all connected clients
                    for websocket in self.clients.copy():  # Use copy to avoid modification during iteration
                        try:
                            await websocket.send(message)
                        except websockets.exceptions.ConnectionClosed:
                            await self.unregister(websocket)
                            
                except Exception as e:
                    print(f"Error sending updates: {e}")
            
            await asyncio.sleep(self.update_interval)

    async def handle_client_message(self, websocket):
        """Handle incoming messages from clients"""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    command = data.get("command")
                    
                    # Handle different commands
                    if command == "get_full_status":
                        response = {
                            "type": "full_status",
                            "data": {
                                "basic_status": self.system_monitor.get_basic_status(),
                                "health_metrics": self.system_monitor.get_health_metrics(),
                                "diagnostic_info": self.system_monitor.get_diagnostic_info()
                            }
                        }
                        await websocket.send(json.dumps(response))
                    
                    elif command == "update_interval":
                        new_interval = data.get("value")
                        if new_interval and isinstance(new_interval, (int, float)):
                            self.update_interval = max(0.1, float(new_interval))
                            await websocket.send(json.dumps({
                                "type": "confirmation",
                                "message": f"Update interval set to {self.update_interval} seconds"
                            }))

                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            pass

    async def handler(self, websocket):
        """Handle new websocket connections"""
        await self.register(websocket)
        try:
            await self.handle_client_message(websocket)
        finally:
            await self.unregister(websocket)

    async def start_server(self):
        """Start the WebSocket server"""
        async with websockets.serve(self.handler, self.host, self.port):
            print(f"WebSocket server started on ws://{self.host}:{self.port}")
            await self.send_updates()  # Start sending periodic updates

    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_streaming()
        if self.clients:
            for websocket in self.clients.copy():
                await websocket.close()
            self.clients.clear()

def run_server():
    """Run the WebSocket server"""
    server = MonitoringWebSocket()
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        asyncio.run(server.cleanup())

if __name__ == "__main__":
    run_server() 