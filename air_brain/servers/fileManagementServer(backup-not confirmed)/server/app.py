from flask import Flask, request, jsonify
import logging
from datetime import datetime
import uuid
import os
from logging.handlers import RotatingFileHandler
from functools import wraps
import paramiko
import json
from utils.ssh_manager import SSHManager
from utils.rate_limiter import RateLimiter
from models.connection import Connection, ConnectionState
from config import connection_config
import traceback
from utils.logging_utils import log_connection_operation, log_agent_operation, log_file_operation
from remote_connection import ensure_connection, close_connection, verify_connection
from pathlib import Path

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "server.log"),
        logging.StreamHandler()
    ]
)

# Create a separate logger for SSH operations
ssh_logger = logging.getLogger('ssh')
ssh_logger.setLevel(logging.INFO)
ssh_handler = logging.FileHandler(log_dir / "ssh.log")
ssh_handler.setFormatter(logging.Formatter('--------------------\nTimestamp: %(asctime)s\nLevel: %(levelname)s\n\n%(message)s\n--------------------\n'))
ssh_logger.addHandler(ssh_handler)

# Initialize Flask app
app = Flask(__name__)

# Initialize managers
ssh_manager = SSHManager(ssh_logger)
rate_limiter = RateLimiter()

def log_request_response(response):
    """Log detailed request and response information"""
    try:
        # Get request details
        request_data = {
            'method': request.method,
            'url': request.url,
            'headers': dict(request.headers),
            'args': request.args.to_dict(),
            'form': request.form.to_dict(),
            'json': request.get_json(silent=True)
        }

        # Get response details
        response_data = response.get_json() if response.is_json else str(response.data)

        # Create detailed log message
        log_message = f"""
REQUEST:
--------
Method: {request_data['method']}
URL: {request_data['url']}
Headers: {json.dumps(request_data['headers'], indent=2)}
Query Args: {json.dumps(request_data['args'], indent=2)}
Body: {json.dumps(request_data['json'], indent=2) if request_data['json'] else 'No body'}

RESPONSE:
---------
Status Code: {response.status_code}
Headers: {json.dumps(dict(response.headers), indent=2)}
Body: {json.dumps(response_data, indent=2) if isinstance(response_data, (dict, list)) else response_data}
"""
        app.logger.info(log_message)
    except Exception as e:
        app.logger.error(f"Error in logging: {str(e)}\n{traceback.format_exc()}")

    return response

# Register logging after_request handler
app.after_request(log_request_response)

# Decorator for rate limiting
def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not rate_limiter.is_allowed(request.remote_addr):
            response = jsonify({
                'status': 'failed',
                'connection_id': None,
                'device_name': None,
                'error': 'Rate limit exceeded'
            }), 403
            return response
        return f(*args, **kwargs)
    return decorated_function

# Root route handler
@app.route('/')
def root():
    """Root endpoint that provides API information"""
    return jsonify({
        "status": "success",
        "message": "AIR PC Integration Server is running",
        "version": "1.0.0",
        "endpoints": {
            "connect": "/api/pc/connect",
            "status": "/api/pc/status",
            "disconnect": "/api/pc/disconnect"
        }
    })

@app.route('/api/pc/connect', methods=['POST'])
def connect_to_pc():
    try:
        data = request.get_json()
        ssh_command = data.get('ssh_command')
        password = data.get('password')
        os_type = data.get('os_type')
        device_id = data.get('device_id')
        
        # Parse SSH command
        parts = ssh_command.split()
        username = parts[1].split('@')[0]
        hostname = parts[1].split('@')[1]
        port = int(parts[3]) if '-p' in parts else 22
        
        # Generate connection ID
        connection_id = str(uuid.uuid4())
        
        # Log connection attempt
        log_connection_operation(
            operation="Connection Attempt",
            details=f"Trying to connect to {hostname}:{port} as {username}"
        )
        
        # Establish connection
        ssh_client, sftp = ensure_connection(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            connection_id=connection_id,
            device_id=device_id,
            os_type=os_type
        )
        
        # Get device name
        stdin, stdout, stderr = ssh_client.exec_command('hostname')
        device_name = stdout.read().decode().strip()
        
        # Update connection_config.json with original structure
        config = {
            "current_connection": {
                "hostname": hostname,
                "port": str(port),
                "username": username,
                "password": password
            },
            "connection_history": []
        }
        
        # Save the updated config
        with open('connection_config.json', 'w') as f:
            json.dump(config, f, indent=4)
        
        # Create connection state file with original format
        state_file = f"connection_{connection_id}.json"
        state_data = {
            "connection_id": connection_id,
            "device_id": device_id,
            "os_type": os_type,
            "ssh_command": ssh_command,
            "state": "connected",
            "device_name": device_name,
            "last_seen": datetime.now().isoformat(),
            "error": None,
            "retry_count": 0,
            "max_retries": 3,
            "health_check_interval": 30,
            "last_health_check": None,
            "reconnect_delay": 5,
            "max_reconnect_attempts": 3,
            "reconnect_attempts": 0,
            "events": [
                {
                    "event_type": "connection_created",
                    "timestamp": datetime.now().isoformat(),
                    "details": {
                        "connection_id": connection_id
                    }
                },
                {
                    "event_type": "status_updated",
                    "timestamp": datetime.now().isoformat(),
                    "details": {
                        "state": "connected",
                        "error": None
                    }
                }
            ],
            "metrics": {
                "total_connections": 0,
                "successful_connections": 0,
                "failed_connections": 0,
                "total_reconnections": 0,
                "successful_reconnections": 0,
                "failed_reconnections": 0,
                "total_health_checks": 0,
                "failed_health_checks": 0,
                "total_uptime_seconds": 0.0,
                "last_connection_time": None,
                "connection_start_time": None
            }
        }
        
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=4)
        
        # Log successful connection
        log_connection_operation(
            operation="Connection Established",
            details=f"Connected to {hostname}:{port} as {username} (device: {device_name})"
        )
        
        return jsonify({
            'status': 'connected',
            'connection_id': connection_id,
            'device_name': device_name,
            'error': None
        })
    except Exception as e:
        # Log connection failure
        log_connection_operation(
            operation="Connection Failed",
            details=f"Error connecting to {hostname}:{port}: {str(e)}"
        )
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/pc/status', methods=['GET'])
def get_connection_status():
    try:
        # Get connection_id from query parameters
        connection_id = request.args.get('connection_id')
        
        if not connection_id:
            return jsonify({
                "status": "failed",
                "error": "Connection ID is required",
                "device_name": None,
                "last_seen": None
            }), 400

        # Try to load the connection state file
        state_file = f"connection_{connection_id}.json"
        if not os.path.exists(state_file):
            return jsonify({
                "status": "failed",
                "error": "Connection not found",
                "device_name": None,
                "last_seen": None
            }), 404

        # Load the connection state
        with open(state_file, 'r') as f:
            state_data = json.load(f)
        
        # Update last_seen timestamp
        state_data['last_seen'] = datetime.now().isoformat()
        
        # Update metrics
        state_data['metrics']['total_health_checks'] += 1
        
        # Save the updated state
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=4)
        
        return jsonify({
            "status": "success",
            "device_name": state_data['device_name'],
            "last_seen": state_data['last_seen'],
            "state": state_data['state'],
            "error": state_data['error'],
            "metrics": state_data['metrics']
        })

    except Exception as e:
        logging.error(f"Error getting connection status: {str(e)}")
        return jsonify({
            "status": "failed",
            "error": str(e),
            "device_name": None,
            "last_seen": None
        }), 500

@app.route('/api/pc/disconnect', methods=['POST'])
def disconnect_from_pc():
    """Disconnect from the remote PC."""
    try:
        data = request.get_json()
        connection_id = data.get('connection_id')
        
        if not connection_id:
            return jsonify({
                "status": "failed",
                "error": "Connection ID is required"
            }), 400
        
        # Close the connection using ssh_manager
        result = ssh_manager.disconnect(connection_id)
        
        if result.get("status") == "success":
            return jsonify({
                "status": "success",
                "message": "Disconnected successfully"
            })
        else:
            return jsonify({
                "status": "failed",
                "error": result.get("error", "Failed to disconnect")
            }), 404
            
    except Exception as e:
        log_connection_operation("Disconnect Failed", f"Error during disconnect: {str(e)}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False) 