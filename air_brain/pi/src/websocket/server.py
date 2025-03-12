import asyncio
import json
import logging
import websockets
from typing import Set, Dict
from datetime import datetime
import time
import cv2
import base64
import queue

from common.commands import (
    Command, Response, CommandType, ResponseType,
    create_error_response, create_success_response
)
from handlers.command_handler import CommandHandler
from camera.camera_manager import CameraManager
from monitoring.system_monitor import SystemMonitor

logger = logging.getLogger(__name__)

class WebSocketServer:
    def __init__(self, host="0.0.0.0", port=8766, camera_url=None, heartbeat_interval=30, config_path: str = "src/config/robot_config.json"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Override with constructor parameters if provided
        self.host = host or self.config['server']['host']
        self.port = port or self.config['server']['port']
        
        # Camera settings from config
        self.camera_url = camera_url or self.config['camera']['url']
        self.display_window = self.config['camera']['display_window']
        
        # ML server configuration
        self.ml_config = self.config.get('ml_server', {'enabled': False})
        logger.info(f"ML Server configuration: {self.ml_config}")
        
        # Initialize camera manager with display setting and ML config
        self.camera_manager = CameraManager(
            camera_url=self.camera_url,
            is_display_window=self.display_window,
            ml_config=self.ml_config
        )
        
        # Other initializations...
        self.clients = set()
        self.system_monitor = SystemMonitor()
        self.running = False
        self.last_heartbeat = {}
        self.frame_interval = 1/30  # Target 30 FPS
        self.frame_task = None
        self.monitoring_task = None
        self.monitoring_interval = self.config['monitoring'].get('update_interval', 1.0)
        self.heartbeat_interval = heartbeat_interval or self.config['server'].get('heartbeat_interval', 30)

    async def register(self, websocket):
        """Register a new client connection"""
        client_id = id(websocket)
        self.clients.add(websocket)
        self.last_heartbeat[client_id] = time.time()
        logger.info(f"New client connected. ID: {client_id}. Total clients: {len(self.clients)}")

    async def unregister(self, websocket):
        """Unregister a client connection"""
        client_id = id(websocket)
        self.clients.remove(websocket)
        self.last_heartbeat.pop(client_id, None)
        logger.info(f"Client {client_id} disconnected. Remaining clients: {len(self.clients)}")
        
        if not self.clients and self.camera_manager:
            self.camera_manager.stop_streaming()

    async def stream_frames(self):
        """Stream frames to all connected clients"""
        frame_count = 0
        try:
            while self.running and self.clients:
                try:
                    # Get frame from camera
                    frame_data = await self.camera_manager.get_frame()
                    
                    if 'error' in frame_data:
                        logger.warning(f"Error getting frame: {frame_data['error']}")
                        await asyncio.sleep(0.1)
                        continue
                        
                    # Broadcast frame to all clients
                    if self.clients:
                        await asyncio.gather(
                            *[client.send(json.dumps(frame_data)) 
                              for client in self.clients],
                            return_exceptions=True
                        )
                        frame_count += 1
                        
                    # Control frame rate
                    await asyncio.sleep(0.01)  # Small sleep to prevent CPU hogging
                    
                except Exception as e:
                    logger.error(f"Error streaming frame: {e}")
                    await asyncio.sleep(0.1)
                    
            logger.info("Streaming stopped - no clients connected or server stopped")
            
        except asyncio.CancelledError:
            logger.info("Frame streaming task cancelled")
        except Exception as e:
            logger.error(f"Streaming error: {e}")
        finally:
            if self.camera_manager.is_display_window:
                cv2.destroyAllWindows()
            logger.info(f"Streaming stopped after {frame_count} frames")

    async def handle_command(self, websocket, data: Dict):
        """Handle client commands"""
        try:
            command = data.get('command')
            if not command and data.get('type') == 'command':
                command = data.get('action')
            
            logger.debug(f"Handling command: {command}")
            
            if command == "start_monitoring":
                # Start system monitoring
                if not self.monitoring_task:
                    self.monitoring_task = asyncio.create_task(self.broadcast_system_stats())
                await websocket.send(json.dumps({
                    'type': 'command_response',
                    'action': 'start_monitoring',
                    'status': 'success',
                    'message': 'System monitoring started'
                }))

            elif command == "stop_monitoring":
                # Stop system monitoring
                if self.monitoring_task:
                    self.monitoring_task.cancel()
                    self.monitoring_task = None
                await websocket.send(json.dumps({
                    'type': 'command_response',
                    'action': 'stop_monitoring',
                    'status': 'success',
                    'message': 'System monitoring stopped'
                }))

            elif command == "get_system_status":
                # Send immediate system status with all metrics
                status = self.system_monitor.get_full_status()
                
                # Add camera and ML server status
                camera_status = self.camera_manager.get_status()
                status['camera_status'] = camera_status
                
                await websocket.send(json.dumps({
                    'type': 'system_status',
                    'data': status,
                    'timestamp': datetime.now().isoformat()
                }))

            elif command == "get_health_metrics":
                # Send detailed health metrics
                metrics = self.system_monitor.get_health_metrics()
                await websocket.send(json.dumps({
                    'type': 'health_metrics',
                    'data': metrics,
                    'timestamp': datetime.now().isoformat()
                }))

            elif command == "get_diagnostic_info":
                # Send system diagnostic information
                diagnostics = self.system_monitor.get_diagnostic_info()
                await websocket.send(json.dumps({
                    'type': 'diagnostic_info',
                    'data': diagnostics,
                    'timestamp': datetime.now().isoformat()
                }))

            elif command == "start_streaming":
                if not self.camera_manager.is_streaming:
                    # Start streaming
                    if self.camera_manager.start_streaming():
                        # Start frame broadcasting task
                        if self.frame_task is None or self.frame_task.done():
                            self.frame_task = asyncio.create_task(self.stream_frames())
                            logger.info("Frame broadcasting task started")
                        
                        await websocket.send(json.dumps({
                            "type": "command_response",
                            "action": "start_streaming",
                            "status": "success",
                            "message": "Streaming started"
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Failed to initialize camera"
                        }))
                else:
                    # Already streaming
                    await websocket.send(json.dumps({
                        "type": "command_response",
                        "action": "start_streaming",
                        "status": "success",
                        "message": "Already streaming"
                    }))
            
            elif command == "stop_streaming":
                if self.camera_manager:
                    success = self.camera_manager.stop_streaming()
                    await websocket.send(json.dumps({
                        'type': 'command_response',
                        'action': 'stop_streaming',
                        'status': 'success' if success else 'error',
                        'message': 'Streaming stopped' if success else 'Failed to stop streaming'
                    }))
            
            elif data.get('type') == 'heartbeat':
                await websocket.send(json.dumps({
                    'type': 'heartbeat_ack',
                    'timestamp': datetime.now().isoformat()
                }))
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def handle_client(self, websocket):
        """Handle client connection"""
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"New client connection from {client_info}")
        
        await self.register(websocket)
        try:
            # Send initial connection success
            await websocket.send(json.dumps({
                'type': 'connection_status',
                'status': 'success',
                'message': 'Connected successfully',
                'timestamp': datetime.now().isoformat()
            }))
            logger.info(f"Sent connection success to client {client_info}")

            async for message in websocket:
                try:
                    logger.debug(f"Received message from {client_info}: {message[:100]}...")
                    data = json.loads(message)
                    await self.handle_command(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid message format from {client_info}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid message format'
                    }))
                except Exception as e:
                    logger.error(f"Error processing message from {client_info}: {e}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': f'Error processing message: {str(e)}'
                    }))
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client connection closed: {client_info} - {e}")
        except Exception as e:
            logger.error(f"Unexpected error with client {client_info}: {e}")
        finally:
            await self.unregister(websocket)
            logger.info(f"Client disconnected: {client_info}")

    async def start(self):
        """Start the WebSocket server"""
        self.running = True
        
        try:
            logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")
            server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                max_size=2**23,  # 8MB max message size
                compression=None,  # Disable compression for better performance
                ping_interval=20,
                ping_timeout=30
            )
            
            logger.info(f"WebSocket server started successfully on ws://{self.host}:{self.port}")
            await asyncio.Future()  # run forever
                
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise  # Re-raise to allow proper shutdown
        finally:
            self.running = False
            if self.camera_manager:
                self.camera_manager.cleanup()
            logger.info("WebSocket server stopped")

    async def broadcast_system_stats(self):
        """Broadcast system statistics to all connected clients"""
        try:
            while self.running and self.clients:
                # Get comprehensive system metrics
                full_status = self.system_monitor.get_full_status()

                # Prepare monitoring data
                monitoring_data = {
                    'type': 'monitoring_update',
                    'data': full_status,
                    'timestamp': datetime.now().isoformat()
                }

                # Broadcast to all clients
                if self.clients:
                    await asyncio.gather(
                        *[client.send(json.dumps(monitoring_data)) 
                          for client in self.clients],
                        return_exceptions=True
                    )

                await asyncio.sleep(self.monitoring_interval)

        except asyncio.CancelledError:
            logger.info("System monitoring stopped")
        except Exception as e:
            logger.error(f"Error in system monitoring: {e}") 