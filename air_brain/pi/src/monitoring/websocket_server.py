import asyncio
import json
import websockets
from datetime import datetime
from typing import Dict, Set
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitoring.system_monitor import SystemMonitor

class MonitoringWebSocket:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.system_monitor = SystemMonitor()
        self.update_interval = 1.0  # seconds

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
            if self.clients:  # Only gather data if there are connected clients
                try:
                    # Gather all monitoring data
                    monitoring_data = {
                        "timestamp": datetime.now().isoformat(),
                        "basic_status": self.system_monitor.get_basic_status(),
                        "health_metrics": self.system_monitor.get_health_metrics(),
                        "diagnostic_info": self.system_monitor.get_diagnostic_info()
                    }
                    
                    # Convert to JSON string once for all clients
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

def run_server():
    """Run the WebSocket server"""
    server = MonitoringWebSocket()
    asyncio.run(server.start_server())

if __name__ == "__main__":
    run_server() 