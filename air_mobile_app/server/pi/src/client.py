import asyncio
import websockets
import json
import cv2
import numpy as np
import base64
import logging
import argparse
from datetime import datetime
import os

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Setup file logging
file_handler = logging.FileHandler(f'logs/client_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger('CameraClient')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

def print_and_log(message, level='info'):
    """Print to terminal and log to file"""
    print(message)
    if level == 'info':
        logger.info(message)
    elif level == 'error':
        logger.error(message)
    elif level == 'debug':
        logger.debug(message)

class CameraClient:
    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.running = True
        self.connected = False
        self.streaming = False
        self.monitoring = False
        self.status_interval = 10  # Status polling interval in seconds
        
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            print_and_log(f"Attempting to connect to {self.uri}")
            self.websocket = await websockets.connect(
                self.uri,
                ping_interval=20,
                ping_timeout=30,
                close_timeout=10
            )
            print_and_log("WebSocket connection established")
            
            response = await self.websocket.recv()
            print_and_log(f"Received initial response: {response}")
            data = json.loads(response)
            
            if data['type'] == 'connection_status' and data['status'] == 'success':
                print_and_log("Connected to server successfully")
                self.connected = True
                return True
            else:
                print_and_log(f"Connection failed: {data.get('message', 'Unknown error')}", 'error')
                return False
                
        except ConnectionRefusedError:
            print_and_log(f"Connection refused - Is the server running on {self.uri}?", 'error')
            return False
        except Exception as e:
            print_and_log(f"Connection error: {e}", 'error')
            return False

    async def start_streaming(self):
        """Request camera streaming"""
        try:
            await self.websocket.send(json.dumps({
                'type': 'command',
                'action': 'start_streaming'
            }))
            
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data['type'] == 'command_response' and data['status'] == 'success':
                print_and_log("Streaming started successfully")
                self.streaming = True
                return True
            else:
                print_and_log(f"Failed to start streaming: {data.get('message', 'Unknown error')}", 'error')
                return False
                
        except Exception as e:
            print_and_log(f"Error starting stream: {e}", 'error')
            return False

    async def start_monitoring(self):
        """Request system monitoring"""
        try:
            await self.websocket.send(json.dumps({
                'type': 'command',
                'action': 'start_monitoring'
            }))
            
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data['type'] == 'command_response' and data['status'] == 'success':
                print_and_log("Monitoring started successfully")
                self.monitoring = True
                return True
            else:
                print_and_log(f"Failed to start monitoring: {data.get('message', 'Unknown error')}", 'error')
                return False
                
        except Exception as e:
            print_and_log(f"Error starting monitoring: {e}", 'error')
            return False

    async def get_system_status(self):
        """Request current system status"""
        try:
            await self.websocket.send(json.dumps({
                'type': 'command',
                'action': 'get_system_status'
            }))
        except Exception as e:
            print_and_log(f"Error requesting system status: {e}", 'error')

    async def poll_system_status(self):
        """Poll system status every 10 seconds"""
        while self.running:
            try:
                await self.get_system_status()
                await asyncio.sleep(self.status_interval)
            except Exception as e:
                print_and_log(f"Error in status polling: {e}", 'error')
                break

    def _log_monitoring_data(self, data):
        """Format and print monitoring data"""
        try:
            divider = "="*50
            output = [
                f"\n{divider}",
                "SYSTEM STATUS UPDATE",
                f"{divider}\n",
                "📊 BASIC STATUS:",
            ]

            # Basic Status
            basic = data.get('basic_status', {})
            battery = basic.get('battery', {})
            output.extend([
                "  🔋 Battery:",
                f"    • Level: {battery.get('level', 'N/A')}",
                f"    • Status: {'🔌 Charging' if battery.get('power_plugged') else '🔋 On Battery'}",
                f"    • Drain Rate: {battery.get('average_drain', 'N/A')}",
                f"    • Remaining: {battery.get('estimated_remaining', 'N/A')}",
                f"  💻 System Health: {basic.get('system_health', 'N/A')}",
                f"  ⏱️ Uptime: {basic.get('operating_time', 'N/A')}",
                f"  🌐 Network Latency: {basic.get('network', {}).get('latency', 'N/A')}\n"
            ])

            # Sensor Readings
            sensor = data.get('sensor_readings', {})
            output.extend([
                "📡 SENSOR READINGS:",
                f"  🌡️ Temperature: {sensor.get('temperature', 'N/A')}",
                f"  💧 Humidity: {sensor.get('humidity', 'N/A')}",
                f"  📏 Proximity: {sensor.get('proximity', 'N/A')}",
                f"  💡 Light Level: {sensor.get('light_level', 'N/A')}",
                f"  🔄 Motion: {sensor.get('motion_status', 'N/A')}",
                f"  🔄 Orientation: {sensor.get('orientation', 'N/A')}\n"
            ])

            # Motor Metrics
            motor = data.get('motor_metrics', {})
            output.extend([
                "⚙️ MOTOR METRICS:",
                f"  🌡️ Temperature: {motor.get('temperature', 'N/A')}",
                f"  📊 Load: {motor.get('load', 'N/A')}",
                f"  📈 Peak Load: {motor.get('peak_load', 'N/A')}",
                f"  ⚡ Speed: {motor.get('movement_speed', 'N/A')}\n"
            ])

            # Performance Metrics
            perf = data.get('performance_metrics', {})
            cpu = perf.get('cpu', {})
            memory = perf.get('memory', {})
            disk = perf.get('disk', {})

            output.extend([
                "💻 PERFORMANCE METRICS:",
                "  CPU:",
                f"    • Usage: {cpu.get('percent', 'N/A')}%",
                f"    • Frequency: {cpu.get('frequency', {}).get('current', 'N/A')} MHz",
                f"    • Cores: {cpu.get('count', 'N/A')}\n",
                "  Memory:",
                f"    • Usage: {memory.get('percent', 'N/A')}%",
                f"    • Available: {memory.get('available', 0) / (1024*1024*1024):.1f} GB",
                f"    • Total: {memory.get('total', 0) / (1024*1024*1024):.1f} GB\n",
                "  Disk:",
                f"    • Usage: {disk.get('percent', 'N/A')}%",
                f"    • Free: {disk.get('free', 0) / (1024*1024*1024):.1f} GB",
                f"    • Total: {disk.get('total', 0) / (1024*1024*1024):.1f} GB\n",
                f"{divider}\n"
            ])

            # Print to terminal and log to file
            print_and_log('\n'.join(output))

        except Exception as e:
            print_and_log(f"Error formatting monitoring data: {e}", 'error')
            print_and_log(f"Raw data: {data}", 'debug')

    async def receive_data(self):
        """Receive and process streaming frames and monitoring data"""
        try:
            while self.running:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data['type'] == 'image':
                    # Handle camera frame
                    img_data = base64.b64decode(data['image'])
                    nparr = np.frombuffer(img_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    cv2.imshow("Camera Stream", frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:  # ESC key to quit
                        self.running = False
                        break
                        
                elif data['type'] in ['monitoring_update', 'system_status']:
                    # Handle monitoring data
                    self._log_monitoring_data(data['data'])
                    
        except Exception as e:
            print_and_log(f"Error receiving data: {e}", 'error')
        finally:
            if self.streaming:
                cv2.destroyAllWindows()

    async def send_heartbeat(self):
        """Send periodic heartbeat"""
        while self.running:
            try:
                await self.websocket.send(json.dumps({
                    'type': 'heartbeat'
                }))
                await asyncio.sleep(10)
            except Exception as e:
                print_and_log(f"Heartbeat error: {e}", 'error')
                break

    async def run(self, stream: bool = False, monitor: bool = False):
        """Main client loop"""
        try:
            if not await self.connect():
                return
                
            tasks = [
                asyncio.create_task(self.send_heartbeat()),
                asyncio.create_task(self.poll_system_status())  # Add status polling
            ]
            
            if stream:
                if await self.start_streaming():
                    print_and_log("Streaming started")
                    
            if monitor:
                if await self.start_monitoring():
                    print_and_log("Monitoring started")
            
            if stream or monitor:
                tasks.append(asyncio.create_task(self.receive_data()))
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            print_and_log(f"Client error: {e}", 'error')
        finally:
            self.running = False
            if hasattr(self, 'websocket'):
                await self.websocket.close()

async def main():
    parser = argparse.ArgumentParser(description='Robot Control Client')
    parser.add_argument('--host', default='localhost', help='Server hostname')
    parser.add_argument('--port', type=int, default=8765, help='Server port')
    parser.add_argument('--stream', action='store_true', help='Start camera streaming')
    parser.add_argument('--monitor', action='store_true', help='Start system monitoring')
    
    args = parser.parse_args()
    
    uri = f"ws://{args.host}:{args.port}"
    client = CameraClient(uri)
    await client.run(stream=args.stream, monitor=args.monitor)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_and_log("Client stopped by user") 