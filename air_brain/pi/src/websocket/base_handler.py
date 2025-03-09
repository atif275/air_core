from abc import ABC, abstractmethod
from typing import Dict, Any
import websockets
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketHandler(ABC):
    """Base class for WebSocket handlers"""
    
    def __init__(self):
        self.clients = set()
        
    async def register(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new client"""
        self.clients.add(websocket)
        logger.info(f"New client registered. Total clients: {len(self.clients)}")
        
    async def unregister(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a client"""
        self.clients.remove(websocket)
        logger.info(f"Client unregistered. Total clients: {len(self.clients)}")
        
    @abstractmethod
    async def handle_command(self, websocket: websockets.WebSocketServerProtocol, command: Dict[str, Any]):
        """Handle incoming commands"""
        pass
        
    @abstractmethod
    async def send_updates(self):
        """Send periodic updates to clients"""
        pass 