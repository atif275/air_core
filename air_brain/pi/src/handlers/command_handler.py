import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from common.commands import (
    Command, Response, CommandType, ResponseType,
    create_error_response, create_success_response, create_heartbeat_response
)
from camera.camera_manager import CameraManager
from monitoring.system_monitor import SystemMonitor

logger = logging.getLogger(__name__)

class CommandHandler:
    def __init__(self, camera_url: Optional[str] = None):
        self.camera_manager: Optional[CameraManager] = None
        self.system_monitor = SystemMonitor()
        self.camera_url = camera_url
        
    async def handle_command(self, command_data: Dict[str, Any], client_id: str) -> Response:
        """Process incoming commands and return appropriate responses"""
        try:
            # Log incoming command
            logger.info(f"Received command from client {client_id}: {command_data}")
            
            # Parse command
            command_type = CommandType(command_data.get("type"))
            
            # Handle action-based commands
            if command_type == CommandType.COMMAND:
                action = command_data.get("action")
                logger.info(f"Processing action command: {action}")
                
                if action == "start_streaming":
                    if not self.camera_manager:
                        return create_error_response("Camera not initialized", client_id)
                        
                    success = self.camera_manager.start_streaming()
                    if success:
                        logger.info("Camera streaming started successfully")
                        return create_success_response(
                            "Camera streaming started",
                            client_id=client_id
                        )
                    else:
                        logger.error("Failed to start camera streaming")
                        return create_error_response("Failed to start streaming", client_id)
                        
                elif action == "stop_streaming":
                    if not self.camera_manager:
                        return create_error_response("Camera not initialized", client_id)
                        
                    success = self.camera_manager.stop_streaming()
                    if success:
                        logger.info("Camera streaming stopped successfully")
                        return create_success_response(
                            "Camera streaming stopped",
                            client_id=client_id
                        )
                    else:
                        logger.error("Failed to stop camera streaming")
                        return create_error_response("Failed to stop streaming", client_id)
                else:
                    logger.warning(f"Unknown command action: {action}")
                    return create_error_response(f"Unknown command action: {action}", client_id)
            
            # Handle other command types
            command = Command(
                type=command_type,
                data=command_data.get("data", {}),
                client_id=client_id
            )
            
            if command_type == CommandType.HEARTBEAT:
                return create_heartbeat_response(client_id)
                
            elif command_type == CommandType.CONNECT:
                return create_success_response(
                    "Connected successfully",
                    response_type=ResponseType.CONNECTION_STATUS,
                    client_id=client_id
                )
                
            # Camera Commands
            elif command_type == CommandType.INIT_CAMERA:
                return await self._handle_camera_init(command)
                
            elif command_type == CommandType.START_STREAMING:
                return await self._handle_start_streaming(command)
                
            elif command_type == CommandType.STOP_STREAMING:
                return await self._handle_stop_streaming(command)
                
            elif command_type == CommandType.GET_CAMERA_STATUS:
                return await self._handle_camera_status(command)
                
            elif command_type == CommandType.SET_DISPLAY_WINDOW:
                return await self._handle_display_window(command)
                
            # System Monitoring Commands
            elif command_type == CommandType.GET_FULL_STATUS:
                return await self._handle_full_status(command)
                
            elif command_type == CommandType.GET_BASIC_STATUS:
                return self._handle_basic_status(command)
                
            elif command_type == CommandType.GET_HEALTH_METRICS:
                return self._handle_health_metrics(command)
                
            elif command_type == CommandType.GET_DIAGNOSTIC_INFO:
                return self._handle_diagnostic_info(command)
                
            else:
                return create_error_response(
                    f"Unknown command type: {command_type}",
                    client_id
                )
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            return create_error_response(str(e), client_id)

    async def _handle_camera_init(self, command: Command) -> Response:
        """Initialize camera with specified settings"""
        try:
            if not self.camera_url:
                return create_error_response("No camera URL configured", command.client_id)
                
            if not self.camera_manager:
                self.camera_manager = CameraManager(
                    self.camera_url,
                    is_display_window=command.data.get("display_window", False)
                )
                
            success = self.camera_manager.init_camera()
            if success:
                return create_success_response(
                    "Camera initialized successfully",
                    data=self.camera_manager.get_status(),
                    client_id=command.client_id
                )
            else:
                return create_error_response(
                    "Failed to initialize camera",
                    command.client_id
                )
                
        except Exception as e:
            logger.error(f"Error initializing camera: {e}")
            return create_error_response(str(e), command.client_id)

    async def _handle_start_streaming(self, command: Command) -> Response:
        """Start camera streaming"""
        try:
            if not self.camera_manager:
                logger.error("Camera manager not initialized")
                return create_error_response(
                    "Camera not initialized",
                    command.client_id
                )
                
            # Initialize camera if needed
            if not self.camera_manager.video_capture:
                logger.info("Initializing camera connection...")
                if not self.camera_manager.init_camera():
                    logger.error("Camera initialization failed")
                    return create_error_response(
                        "Failed to initialize camera",
                        command.client_id
                    )
            
            # Start streaming
            logger.info("Starting camera stream...")
            if self.camera_manager.start_streaming():
                # Create frame streaming task if not already running
                if not hasattr(self, 'frame_task') or self.frame_task is None:
                    logger.info("Creating frame streaming task...")
                    self.frame_task = asyncio.create_task(self._stream_frames())
                
                logger.info("Camera streaming started successfully")
                return create_success_response(
                    "Streaming started",
                    data=self.camera_manager.get_status(),
                    client_id=command.client_id
                )
            else:
                logger.error("Failed to start camera streaming")
                return create_error_response(
                    "Failed to start streaming",
                    command.client_id
                )
                
        except Exception as e:
            logger.error(f"Error starting stream: {e}")
            return create_error_response(str(e), command.client_id)

    async def _stream_frames(self):
        """Stream frames to connected clients through WebSocket server"""
        try:
            while self.camera_manager and self.camera_manager.is_streaming:
                frame_data = await self.camera_manager.get_frame()
                if frame_data:
                    # Create frame message
                    message = {
                        "type": ResponseType.CAMERA_FRAME.value,
                        "data": frame_data,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Send to WebSocket server for broadcasting
                    if hasattr(self, 'websocket_server'):
                        await self.websocket_server.broadcast_message(message)
                        
                await asyncio.sleep(1/30)  # Target 30 FPS
                
        except Exception as e:
            logger.error(f"Error in frame streaming: {e}")
        finally:
            self.frame_task = None

    async def _handle_stop_streaming(self, command: Command) -> Response:
        """Stop camera streaming"""
        try:
            if not self.camera_manager:
                return create_error_response(
                    "Camera not initialized",
                    command.client_id
                )
                
            success = self.camera_manager.stop_streaming()
            return create_success_response(
                "Streaming stopped",
                data=self.camera_manager.get_status(),
                client_id=command.client_id
            )
                
        except Exception as e:
            logger.error(f"Error stopping stream: {e}")
            return create_error_response(str(e), command.client_id)

    async def _handle_camera_status(self, command: Command) -> Response:
        """Get current camera status"""
        if not self.camera_manager:
            return create_error_response(
                "Camera not initialized",
                command.client_id
            )
            
        return create_success_response(
            "Camera status retrieved",
            data=self.camera_manager.get_status(),
            client_id=command.client_id
        )

    async def _handle_display_window(self, command: Command) -> Response:
        """Set display window state"""
        try:
            if not self.camera_manager:
                return create_error_response(
                    "Camera not initialized",
                    command.client_id
                )
                
            display_enabled = command.data.get("enabled", False)
            self.camera_manager.is_display_window = display_enabled
            
            return create_success_response(
                f"Display window {'enabled' if display_enabled else 'disabled'}",
                data={"display_window": display_enabled},
                client_id=command.client_id
            )
                
        except Exception as e:
            logger.error(f"Error setting display window: {e}")
            return create_error_response(str(e), command.client_id)

    async def _handle_full_status(self, command: Command) -> Response:
        """Get full system status including camera if available"""
        try:
            status_data = {
                "system": {
                    "basic_status": self.system_monitor.get_basic_status(),
                    "health_metrics": self.system_monitor.get_health_metrics(),
                    "diagnostic_info": self.system_monitor.get_diagnostic_info()
                }
            }
            
            if self.camera_manager:
                status_data["camera"] = self.camera_manager.get_status()
                
            return create_success_response(
                "Full status retrieved",
                data=status_data,
                client_id=command.client_id
            )
                
        except Exception as e:
            logger.error(f"Error getting full status: {e}")
            return create_error_response(str(e), command.client_id)

    def _handle_basic_status(self, command: Command) -> Response:
        """Get basic system status"""
        try:
            return create_success_response(
                "Basic status retrieved",
                data=self.system_monitor.get_basic_status(),
                client_id=command.client_id
            )
        except Exception as e:
            logger.error(f"Error getting basic status: {e}")
            return create_error_response(str(e), command.client_id)

    def _handle_health_metrics(self, command: Command) -> Response:
        """Get system health metrics"""
        try:
            return create_success_response(
                "Health metrics retrieved",
                data=self.system_monitor.get_health_metrics(),
                client_id=command.client_id
            )
        except Exception as e:
            logger.error(f"Error getting health metrics: {e}")
            return create_error_response(str(e), command.client_id)

    def _handle_diagnostic_info(self, command: Command) -> Response:
        """Get system diagnostic information"""
        try:
            return create_success_response(
                "Diagnostic info retrieved",
                data=self.system_monitor.get_diagnostic_info(),
                client_id=command.client_id
            )
        except Exception as e:
            logger.error(f"Error getting diagnostic info: {e}")
            return create_error_response(str(e), command.client_id)

    def cleanup(self):
        """Clean up resources"""
        try:
            # Cancel frame streaming task if running
            if hasattr(self, 'frame_task') and self.frame_task:
                self.frame_task.cancel()
                self.frame_task = None
                
            if self.camera_manager:
                self.camera_manager.release_camera()
                
            if self.system_monitor:
                self.system_monitor.stop_monitoring()
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}") 