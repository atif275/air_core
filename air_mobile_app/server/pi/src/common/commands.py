from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

class CommandType(Enum):
    # Connection commands
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    COMMAND = "command"
    
    # Camera commands
    INIT_CAMERA = "init_camera"
    START_STREAMING = "start_streaming"
    STOP_STREAMING = "stop_streaming"
    GET_CAMERA_STATUS = "get_camera_status"
    SET_DISPLAY_WINDOW = "set_display_window"
    
    # System monitoring commands
    GET_FULL_STATUS = "get_full_status"
    GET_BASIC_STATUS = "get_basic_status"
    GET_HEALTH_METRICS = "get_health_metrics"
    GET_DIAGNOSTIC_INFO = "get_diagnostic_info"
    UPDATE_INTERVAL = "update_interval"

class CommandAction(Enum):
    START_STREAMING = "start_streaming"
    STOP_STREAMING = "stop_streaming"

class ResponseType(Enum):
    # General responses
    SUCCESS = "success"
    ERROR = "error"
    
    # Connection responses
    CONNECTION_STATUS = "connection_status"
    HEARTBEAT_ACK = "heartbeat_ack"
    
    # Data responses
    CAMERA_FRAME = "camera_frame"
    SYSTEM_STATUS = "system_status"
    COMMAND_RESPONSE = "command_response"

@dataclass
class Command:
    type: CommandType
    data: Optional[Dict[str, Any]] = None
    client_id: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.data is None:
            self.data = {}

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "data": self.data,
            "client_id": self.client_id,
            "timestamp": self.timestamp
        }

@dataclass
class Response:
    type: ResponseType
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    client_id: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.data is None:
            self.data = {}

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "status": self.status,
            "message": self.message,
            "data": self.data,
            "client_id": self.client_id,
            "timestamp": self.timestamp
        }

def create_error_response(message: str, client_id: Optional[str] = None) -> Response:
    return Response(
        type=ResponseType.ERROR,
        status="error",
        message=message,
        client_id=client_id
    )

def create_success_response(
    message: str,
    data: Optional[Dict[str, Any]] = None,
    response_type: ResponseType = ResponseType.SUCCESS,
    client_id: Optional[str] = None
) -> Response:
    return Response(
        type=response_type,
        status="success",
        message=message,
        data=data,
        client_id=client_id
    )

def create_heartbeat_response(client_id: Optional[str] = None) -> Response:
    return Response(
        type=ResponseType.HEARTBEAT_ACK,
        status="success",
        message="Heartbeat acknowledged",
        client_id=client_id,
        data={"timestamp": datetime.now().isoformat()}
    ) 