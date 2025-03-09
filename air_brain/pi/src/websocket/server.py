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
    def __init__(self, host: str = "0.0.0.0", port: int = 8765, camera_url: str = None):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.camera_manager = CameraManager(camera_url) if camera_url else None
        self.system_monitor = SystemMonitor()
        self.running = False
        self.last_heartbeat = {}
        self.frame_interval = 1/30  # Target 30 FPS
        self.frame_task = None
        self.monitoring_task = None
        self.monitoring_interval = 1.0  # Update system stats every second

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
        last_time = time.time()
        
        if self.camera_manager.is_display_window:
            cv2.namedWindow("Robot Camera Stream", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Robot Camera Stream", 640, 480)
        
        try:
            while self.running and self.camera_manager.is_streaming and self.clients:
                try:
                    # Get frame from queue
                    frame, capture_time = self.camera_manager.frame_queue.get_nowait()
                    frame_count += 1
                    
                    if self.camera_manager.is_display_window:
                        try:
                            cv2.imshow("Robot Camera Stream", frame)
                            key = cv2.waitKey(1) & 0xFF
                            if key == 27:  # ESC key to quit
                                break
                        except Exception as e:
                            logger.error(f"Display error: {e}")
                    
                    # Convert to JPEG
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
                    encode_start = time.time()
                    _, buffer = cv2.imencode('.jpg', frame, encode_param)
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                    
                    # Log processing times periodically
                    if frame_count % 30 == 0:
                        current_time = time.time()
                        encode_time = current_time - encode_start
                        total_time = current_time - last_time
                        last_time = current_time
                        logger.debug(
                            f"Frame stats - Size: {len(jpg_as_text)} bytes, "
                            f"Encode time: {encode_time*1000:.1f}ms, "
                            f"Rate: {30/total_time:.1f} FPS"
                        )
                    
                    # Prepare frame data
                    frame_data = json.dumps({
                        'type': 'image',
                        'image': jpg_as_text,
                        'timestamp': datetime.now().isoformat(),
                        'frame_number': frame_count
                    })

                    # Send to all clients
                    if self.clients:
                        await asyncio.gather(
                            *[client.send(frame_data) for client in self.clients],
                            return_exceptions=True
                        )

                    await asyncio.sleep(self.frame_interval)

                except queue.Empty:
                    await asyncio.sleep(0.001)
                except Exception as e:
                    logger.error(f"Error in stream_frames: {e}")
                    await asyncio.sleep(0.1)
                    
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
                if self.camera_manager:
                    # Initialize camera if needed
                    if not self.camera_manager.video_capture:
                        success = self.camera_manager.init_camera()
                        if not success:
                            await websocket.send(json.dumps({
                                'type': 'error',
                                'message': 'Failed to initialize camera'
                            }))
                            return

                    # Start streaming
                    success = self.camera_manager.start_streaming()
                    if success:
                        # Start frame streaming task
                        if not self.frame_task:
                            self.frame_task = asyncio.create_task(self.stream_frames())
                            logger.info("Frame broadcasting task started")

                        await websocket.send(json.dumps({
                            'type': 'command_response',
                            'action': 'start_streaming',
                            'status': 'success',
                            'message': 'Streaming started'
                        }))
                    else:
                        await websocket.send(json.dumps({
                            'type': 'error',
                            'message': 'Failed to start streaming'
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
        await self.register(websocket)
        try:
            # Send initial connection success
            await websocket.send(json.dumps({
                'type': 'connection_status',
                'status': 'success',
                'message': 'Connected successfully',
                'timestamp': datetime.now().isoformat()
            }))

            async for message in websocket:
                try:
                    logger.debug(f"Received message: {message}")
                    data = json.loads(message)
                    await self.handle_command(websocket, data)
                except json.JSONDecodeError:
                    logger.error("Invalid message format")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed unexpectedly")
        finally:
            await self.unregister(websocket)

    async def start(self):
        """Start the WebSocket server"""
        self.running = True
        
        try:
            async with websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                max_size=2**23,  # 8MB max message size
                compression=None,  # Disable compression for better performance
                ping_interval=20,
                ping_timeout=30
            ):
                logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
                await asyncio.Future()  # run forever
                
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.running = False
            if self.camera_manager:
                self.camera_manager.cleanup()

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