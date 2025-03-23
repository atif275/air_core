from enum import Enum
from datetime import datetime

class ConnectionState(Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    TIMEOUT = "timeout"

class Connection:
    def __init__(self, connection_id, device_id, os_type, ssh_command):
        self.connection_id = connection_id
        self.device_id = device_id
        self.os_type = os_type
        self.ssh_command = ssh_command
        self.state = ConnectionState.CONNECTING
        self.device_name = None
        self.last_seen = datetime.utcnow()
        self.ssh_client = None
        self.error = None
        self.retry_count = 0
        self.max_retries = 3

    def update_status(self, state: ConnectionState, error=None):
        self.state = state
        self.error = error
        self.last_seen = datetime.utcnow()

    def is_active(self):
        return self.state == ConnectionState.CONNECTED

    def can_retry(self):
        return self.retry_count < self.max_retries

    def increment_retry(self):
        self.retry_count += 1
        return self.can_retry()

    def to_dict(self):
        return {
            'connection_id': self.connection_id,
            'device_id': self.device_id,
            'os_type': self.os_type,
            'state': self.state.value,
            'device_name': self.device_name,
            'last_seen': self.last_seen.isoformat(),
            'error': self.error
        } 