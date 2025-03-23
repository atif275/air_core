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
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='--------------------\nTimestamp: %(asctime)s\nLevel: %(levelname)s\nLocation: %(pathname)s:%(lineno)d\n\n%(message)s\n--------------------\n',
    handlers=[
        logging.FileHandler('logs/server.log'),
        logging.FileHandler('logs/ssh.log'),  # Add separate SSH log file
        logging.StreamHandler()
    ]
)

# Create a separate logger for SSH operations
ssh_logger = logging.getLogger('ssh')
ssh_logger.setLevel(logging.INFO)
ssh_handler = logging.FileHandler('logs/ssh.log')
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
@rate_limit
def connect():
    try:
        data = request.get_json()
        required_fields = ['ssh_command', 'password', 'os_type', 'device_id']
        
        # Validate required fields
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': 'failed',
                'connection_id': None,
                'device_name': None,
                'error': 'Missing required fields'
            }), 400

        # Generate unique connection ID
        connection_id = str(uuid.uuid4())

        # Create connection object
        connection = Connection(
            connection_id=connection_id,
            device_id=data['device_id'],
            os_type=data['os_type'],
            ssh_command=data['ssh_command']
        )

        # Attempt SSH connection
        connection = ssh_manager.establish_connection(
            connection,
            data['password']
        )

        if connection.state == ConnectionState.CONNECTED:
            return jsonify({
                'status': 'connected',
                'connection_id': connection.connection_id,
                'device_name': connection.device_name,
                'error': None
            })
        else:
            return jsonify({
                'status': 'failed',
                'connection_id': None,
                'device_name': None,
                'error': connection.error or 'Connection failed'
            }), 401

    except Exception as e:
        app.logger.error(f'Connection error: {str(e)}\n{traceback.format_exc()}')
        return jsonify({
            'status': 'failed',
            'connection_id': None,
            'device_name': None,
            'error': 'Internal server error'
        }), 500

@app.route('/api/pc/status', methods=['GET'])
def status():
    try:
        connection_id = request.args.get('connection_id')
        if not connection_id:
            return jsonify({
                'status': 'failed',
                'device_name': None,
                'last_seen': None,
                'error': 'Connection ID is required'
            }), 400

        connection_status = ssh_manager.get_connection_status(connection_id)
        if connection_status:
            return jsonify({
                'status': connection_status.state.value,
                'device_name': connection_status.device_name,
                'last_seen': connection_status.last_seen.isoformat(),
                'error': None
            })
        else:
            return jsonify({
                'status': 'disconnected',
                'device_name': None,
                'last_seen': None,
                'error': 'Connection not found'
            }), 404

    except Exception as e:
        app.logger.error(f'Status check error: {str(e)}\n{traceback.format_exc()}')
        return jsonify({
            'status': 'failed',
            'device_name': None,
            'last_seen': None,
            'error': 'Internal server error'
        }), 500

@app.route('/api/pc/disconnect', methods=['POST'])
def disconnect():
    try:
        data = request.get_json()
        connection_id = data.get('connection_id')
        
        if not connection_id:
            return jsonify({
                'status': 'failed',
                'error': 'Connection ID is required'
            }), 400

        success = ssh_manager.disconnect(connection_id)
        if success:
            return jsonify({
                'status': 'disconnected',
                'error': None
            })
        else:
            return jsonify({
                'status': 'failed',
                'error': 'Connection not found or already disconnected'
            }), 404

    except Exception as e:
        app.logger.error(f'Disconnect error: {str(e)}\n{traceback.format_exc()}')
        return jsonify({
            'status': 'failed',
            'error': 'Internal server error'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=False) 