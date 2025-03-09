import asyncio
import json
import websockets
import logging
from typing import Dict, Set
from datetime import datetime

from common.commands import Command, CommandType, CommandResponse
from monitoring.system_monitor import SystemMonitor
from camera.camera_manager import CameraManager
from websocket.base_handler import WebSocketHandler

logger = logging.getLogger(__name__)

class UnifiedWebSocketServer(WebSocketHandler):
    def __init__(self, host: str = "0.0.0.0", port: int = 8765, camera_url: str = None):
        super().__init__()
        self.host = host
        self.port = port
        self.system_monitor = SystemMonitor()
        self.camera_manager = CameraManager(camera_url) if camera_url else None
        self.update_interval = 1.0
        
    async def handle_command(self, websocket: websockets.WebSocketServerProtocol, data: Dict):
        try:
            command = Command(
                type=CommandType(data.get("type")),
                data=data.get("data")
            )
            
            if command.type == CommandType.GET_FULL_STATUS:
                response = CommandResponse(
                    type="full_status",
                    status="success",
                    message="Full status retrieved",
                    data={
                        "system_status": self.system_monitor.get_basic_status(),
                        "health_metrics": self.system_monitor.get_health_metrics(),
                        "camera_status": self.camera_manager.get_camera_status() if self.camera_manager else None
                    }
                )
                await websocket.send(json.dumps(response.to_dict()))
                
            elif command.type == CommandType.START_STREAMING:
                if self.camera_manager:
                    success = self.camera_manager.start_camera()
                    response = CommandResponse(
                        type="camera_command",
                        status="success" if success else "error",
                        message="Camera streaming started" if success else "Failed to start camera"
                    )
                    await websocket.send(json.dumps(response.to_dict()))
                    
            elif command.type == CommandType.STOP_STREAMING:
                if self.camera_manager:
                    self.camera_manager.stop_camera()
                    response = CommandResponse(
                        type="camera_command",
                        status="success",
                        message="Camera streaming stopped"
                    )
                    await websocket.send(json.dumps(response.to_dict()))
                    
            elif command.type == CommandType.HEARTBEAT:
                await websocket.send(json.dumps({
                    "type": "heartbeat_ack",
                    "timestamp": datetime.now().isoformat()
                }))
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))

    async def send_updates(self):
        """Send periodic updates to all connected clients"""
        while True:
            if self.clients:
                try:
                    # Gather system monitoring data
                    monitoring_data = {
                        "type": "status_update",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "system_status": self.system_monitor.get_basic_status(),
                            "health_metrics": self.system_monitor.get_health_metrics()
                        }
                    }
                    
                    # Add camera frame if streaming
                    if self.camera_manager and self.camera_manager.is_streaming:
                        frame_data = await self.camera_manager.get_frame()
                        if frame_data:
                            monitoring_data["data"]["camera_frame"] = frame_data
                    
                    # Send to all clients
                    message = json.dumps(monitoring_data)
                    await asyncio.gather(
                        *[client.send(message) for client in self.clients],
                        return_exceptions=True
                    )
                    
                except Exception as e:
                    logger.error(f"Error sending updates: {e}")
            
            await asyncio.sleep(self.update_interval)

    async def start(self):
        """Start the unified WebSocket server"""
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info(f"Unified WebSocket server started on ws://{self.host}:{self.port}")
            await self.send_updates()

    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle new client connections"""
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_command(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket) 