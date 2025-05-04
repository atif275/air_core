from enum import Enum
from datetime import datetime, timedelta
import json
import os
import time
import logging
from typing import Dict, List, Optional
from remote_connection import ensure_connection, close_connection, get_connection_status, get_connection_state

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('connection.log'),
        logging.StreamHandler()
    ]
)

class ConnectionState(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    RECONNECTING = "reconnecting"

class ConnectionEvent:
    def __init__(self, event_type: str, timestamp: datetime, details: Dict):
        self.event_type = event_type
        self.timestamp = timestamp
        self.details = details

    def to_dict(self) -> Dict:
        return {
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details
        }

class ConnectionMetrics:
    def __init__(self):
        self.total_connections = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.total_reconnections = 0
        self.successful_reconnections = 0
        self.failed_reconnections = 0
        self.total_health_checks = 0
        self.failed_health_checks = 0
        self.total_uptime = timedelta()
        self.last_connection_time = None
        self.connection_start_time = None

    def to_dict(self) -> Dict:
        return {
            'total_connections': self.total_connections,
            'successful_connections': self.successful_connections,
            'failed_connections': self.failed_connections,
            'total_reconnections': self.total_reconnections,
            'successful_reconnections': self.successful_reconnections,
            'failed_reconnections': self.failed_reconnections,
            'total_health_checks': self.total_health_checks,
            'failed_health_checks': self.failed_health_checks,
            'total_uptime_seconds': self.total_uptime.total_seconds(),
            'last_connection_time': self.last_connection_time.isoformat() if self.last_connection_time else None,
            'connection_start_time': self.connection_start_time.isoformat() if self.connection_start_time else None
        }

class Connection:
    def __init__(self, connection_id: str, device_id: str, os_type: str, ssh_command: str):
        self.connection_id = connection_id
        self.device_id = device_id
        self.os_type = os_type
        self.ssh_command = ssh_command
        self.state = ConnectionState.DISCONNECTED
        self.device_name = None
        self.last_seen = datetime.now()
        self.error = None
        self.retry_count = 0
        self.max_retries = 3
        self.health_check_interval = 30  # seconds
        self.last_health_check = None
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_attempts = 3
        self.reconnect_attempts = 0
        self.events: List[ConnectionEvent] = []
        self.metrics = ConnectionMetrics()
        self.ssh_client = None
        self.sftp = None
        self.log_event("connection_created", {"connection_id": connection_id})

    def log_event(self, event_type: str, details: Dict):
        """Log a connection event"""
        event = ConnectionEvent(event_type, datetime.now(), details)
        self.events.append(event)
        logging.info(f"Connection {self.connection_id}: {event_type} - {details}")

    def check_health(self) -> bool:
        """Check if the connection is healthy"""
        try:
            if self.state != ConnectionState.CONNECTED:
                return False

            # Check if we need to perform a health check
            if self.last_health_check and (datetime.now() - self.last_health_check).seconds < self.health_check_interval:
                return True

            self.metrics.total_health_checks += 1
            
            # Try to execute a simple command
            if self.ssh_client:
                stdin, stdout, stderr = self.ssh_client.exec_command('echo "health_check"')
                response = stdout.read().decode().strip()
                if response == "health_check":
                    self.last_health_check = datetime.now()
                    self.log_event("health_check_passed", {})
                    return True
            
            self.metrics.failed_health_checks += 1
            self.log_event("health_check_failed", {"error": "Command execution failed"})
            return False

        except Exception as e:
            self.error = f"Health check failed: {str(e)}"
            self.state = ConnectionState.DISCONNECTED
            self.metrics.failed_health_checks += 1
            self.log_event("health_check_failed", {"error": str(e)})
            return False

    def attempt_recovery(self, password: str) -> bool:
        """Attempt to recover the connection"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.error = "Max reconnection attempts reached"
            self.log_event("recovery_failed", {"error": self.error})
            return False

        self.state = ConnectionState.RECONNECTING
        self.reconnect_attempts += 1
        self.metrics.total_reconnections += 1

        self.log_event("recovery_attempted", {
            "attempt": self.reconnect_attempts,
            "max_attempts": self.max_reconnect_attempts
        })

        try:
            # Wait before attempting reconnection
            time.sleep(self.reconnect_delay)

            # Parse SSH command to get connection details
            ssh_parts = self.ssh_command.split()
            hostname = None
            port = 22
            username = None
            
            for i, part in enumerate(ssh_parts):
                if part == '-p':
                    port = int(ssh_parts[i + 1])
                elif '@' in part:
                    username, hostname = part.split('@')
            
            if not hostname or not username:
                self.state = ConnectionState.FAILED
                self.error = "Invalid SSH command format"
                self.log_event("recovery_failed", {"error": self.error})
                return False

            # Attempt to reconnect
            ssh_client, sftp = ensure_connection(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                connection_id=self.connection_id,
                device_id=self.device_id,
                os_type=self.os_type
            )

            if ssh_client and sftp:
                self.state = ConnectionState.CONNECTED
                self.error = None
                self.reconnect_attempts = 0
                self.last_seen = datetime.now()
                self.metrics.successful_reconnections += 1
                self.log_event("recovery_succeeded", {})
                return True
            else:
                self.state = ConnectionState.FAILED
                self.error = "Failed to reconnect"
                self.metrics.failed_reconnections += 1
                self.log_event("recovery_failed", {"error": self.error})
                return False

        except Exception as e:
            self.state = ConnectionState.FAILED
            self.error = f"Reconnection failed: {str(e)}"
            self.metrics.failed_reconnections += 1
            self.log_event("recovery_failed", {"error": str(e)})
            return False

    def establish(self, password: str) -> 'Connection':
        """Establish the SSH connection using remote_operations"""
        self.metrics.total_connections += 1
        self.metrics.connection_start_time = datetime.now()
        
        try:
            # Parse SSH command to get connection details
            ssh_parts = self.ssh_command.split()
            hostname = None
            port = 22
            username = None
            
            for i, part in enumerate(ssh_parts):
                if part == '-p':
                    port = int(ssh_parts[i + 1])
                elif '@' in part:
                    username, hostname = part.split('@')
            
            if not hostname or not username:
                self.state = ConnectionState.FAILED
                self.error = "Invalid SSH command format"
                self.metrics.failed_connections += 1
                self.log_event("connection_failed", {"error": self.error})
                return self

            # Establish connection using remote_operations
            ssh_client, sftp = ensure_connection(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                connection_id=self.connection_id,
                device_id=self.device_id,
                os_type=self.os_type
            )

            if ssh_client and sftp:
                self.state = ConnectionState.CONNECTED
                # Get device name
                stdin, stdout, stderr = ssh_client.exec_command('hostname')
                self.device_name = stdout.read().decode().strip()
                self.last_seen = datetime.now()
                self.error = None
                self.reconnect_attempts = 0
                self.metrics.successful_connections += 1
                self.metrics.last_connection_time = datetime.now()
                self.log_event("connection_established", {
                    "device_name": self.device_name,
                    "hostname": hostname,
                    "port": port,
                    "username": username
                })
            else:
                self.state = ConnectionState.FAILED
                self.error = "Failed to establish connection"
                self.metrics.failed_connections += 1
                self.log_event("connection_failed", {"error": self.error})

        except Exception as e:
            self.state = ConnectionState.FAILED
            self.error = str(e)
            self.metrics.failed_connections += 1
            self.log_event("connection_failed", {"error": str(e)})

        return self

    def disconnect(self) -> bool:
        """Disconnect the SSH connection"""
        try:
            close_connection()
            self.state = ConnectionState.DISCONNECTED
            self.last_seen = datetime.now()
            self.error = None
            self.reconnect_attempts = 0
            
            # Update uptime metrics
            if self.metrics.connection_start_time:
                self.metrics.total_uptime += datetime.now() - self.metrics.connection_start_time
                self.metrics.connection_start_time = None
            
            self.log_event("connection_disconnected", {})
            return True
        except Exception as e:
            self.error = str(e)
            self.log_event("disconnect_failed", {"error": str(e)})
            return False

    def update_status(self, state: Optional[ConnectionState] = None, error: Optional[str] = None) -> 'Connection':
        """Update the connection status"""
        try:
            if state is not None:
                self.state = state
                if error is not None:
                    self.error = error
                self.last_seen = datetime.now()
                if state == ConnectionState.CONNECTED:
                    self.error = None
                self.log_event("status_updated", {"state": state.value, "error": error})
            elif not self.check_health():
                if self.state == ConnectionState.CONNECTED:
                    self.state = ConnectionState.DISCONNECTED
                    self.log_event("connection_lost", {})
            else:
                self.state = ConnectionState.CONNECTED
                self.error = None
                self.last_seen = datetime.now()
        except Exception as e:
            self.error = str(e)
            self.log_event("status_update_failed", {"error": str(e)})
        return self

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
            'ssh_command': self.ssh_command,
            'state': self.state.value,
            'device_name': self.device_name,
            'last_seen': self.last_seen.isoformat(),
            'error': self.error,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'health_check_interval': self.health_check_interval,
            'last_health_check': self.last_health_check.isoformat() if self.last_health_check else None,
            'reconnect_delay': self.reconnect_delay,
            'max_reconnect_attempts': self.max_reconnect_attempts,
            'reconnect_attempts': self.reconnect_attempts,
            'events': [event.to_dict() for event in self.events],
            'metrics': self.metrics.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Connection':
        """Create a Connection instance from a dictionary"""
        connection = cls(
            connection_id=data['connection_id'],
            device_id=data['device_id'],
            os_type=data['os_type'],
            ssh_command=data['ssh_command']
        )
        connection.state = ConnectionState(data['state'])
        connection.device_name = data['device_name']
        connection.last_seen = datetime.fromisoformat(data['last_seen'])
        connection.error = data['error']
        connection.retry_count = data['retry_count']
        connection.max_retries = data['max_retries']
        connection.health_check_interval = data['health_check_interval']
        connection.last_health_check = datetime.fromisoformat(data['last_health_check']) if data['last_health_check'] else None
        connection.reconnect_delay = data['reconnect_delay']
        connection.max_reconnect_attempts = data['max_reconnect_attempts']
        connection.reconnect_attempts = data['reconnect_attempts']
        
        # Restore events
        connection.events = [
            ConnectionEvent(
                event['event_type'],
                datetime.fromisoformat(event['timestamp']),
                event['details']
            ) for event in data['events']
        ]
        
        # Restore metrics
        metrics = ConnectionMetrics()
        metrics.total_connections = data['metrics']['total_connections']
        metrics.successful_connections = data['metrics']['successful_connections']
        metrics.failed_connections = data['metrics']['failed_connections']
        metrics.total_reconnections = data['metrics']['total_reconnections']
        metrics.successful_reconnections = data['metrics']['successful_reconnections']
        metrics.failed_reconnections = data['metrics']['failed_reconnections']
        metrics.total_health_checks = data['metrics']['total_health_checks']
        metrics.failed_health_checks = data['metrics']['failed_health_checks']
        metrics.total_uptime = timedelta(seconds=data['metrics']['total_uptime_seconds'])
        metrics.last_connection_time = datetime.fromisoformat(data['metrics']['last_connection_time']) if data['metrics']['last_connection_time'] else None
        metrics.connection_start_time = datetime.fromisoformat(data['metrics']['connection_start_time']) if data['metrics']['connection_start_time'] else None
        connection.metrics = metrics
        
        return connection

    def save_to_file(self, filepath: str) -> bool:
        """Save connection state to a file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            return True
        except Exception as e:
            self.error = f"Failed to save connection state: {str(e)}"
            self.log_event("save_failed", {"error": str(e)})
            return False

    @classmethod
    def load_from_file(cls, filepath: str) -> 'Connection':
        """Load connection state from a file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            raise ValueError(f"Failed to load connection state: {str(e)}") 