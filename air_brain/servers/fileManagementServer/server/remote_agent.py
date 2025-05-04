from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
import uuid
import re
import json
from datetime import datetime, timedelta
from models.connection import Connection, ConnectionState
import logging
from typing import List, Dict, Optional
import os
from config import connection_config
from dotenv import load_dotenv
from remote_connection import (
    get_connection_status,
    connect_to_server,
    list_directory,
    create_directory,
    remove_directory,
    remove_file,
    rename_file,
    upload_file,
    download_file,
    read_file,
    write_file,
    disconnect_from_server,
    get_current_directory,
    change_directory,
    list_directories,
    list_current_files,
    create_file,
    update_file,
    get_file_info,
    find_files,
    ensure_connection,
    close_connection,
    get_connection_state,
    update_connection_state,
    verify_connection,
    CONNECTION_ID, IS_CONNECTED, CONNECTION_INFO, ERROR
)
from utils.logging_utils import log_agent_operation, log_connection_operation, log_file_operation
from pathlib import Path
import paramiko
import threading
import time
import subprocess
import traceback
from flask import Flask, request, jsonify
from functools import wraps
from utils.rate_limiter import RateLimiter
import sys

# Load environment variables
load_dotenv()

memory = MemorySaver()

# Get default values from config
config = connection_config.load_config()
DEFAULT_HOSTNAME = config['current_connection']['hostname']
DEFAULT_PORT = config['current_connection']['port']
DEFAULT_USERNAME = config['current_connection']['username']
DEFAULT_PASSWORD = config['current_connection']['password']

# Initialize the model with API key from environment
model = ChatOpenAI(
    model="gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY")
)

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Add verbose_server flag at the top with other configurations
verbose_server = False  # Set to True to see Flask server logs in terminal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "remote_agent.log"),
        logging.StreamHandler() if verbose_server else logging.NullHandler()
    ]
)

# Create a separate logger for SSH operations
ssh_logger = logging.getLogger('ssh')
ssh_logger.setLevel(logging.INFO)
ssh_handler = logging.FileHandler(log_dir / "ssh.log")
ssh_handler.setFormatter(logging.Formatter('--------------------\nTimestamp: %(asctime)s\nLevel: %(levelname)s\n\n%(message)s\n--------------------\n'))
ssh_logger.addHandler(ssh_handler)

# Initialize rate limiter
rate_limiter = RateLimiter()

# Connection state management
class ConnectionManager:
    def __init__(self):
        self.current_connection = None
        self.connection_history = []
        self.log_file = "logs/connection_manager.log"
        self.is_connected = False
        self.connection_info = None
        self.connection_id = None
        self.device_name = None

    def get_connection_status(self) -> str:
        """Get a human-readable connection status"""
        if not self.is_connected:
            return "No active connection"
        
        status = f"Connection ID: {self.connection_id}\n"
        status += f"Device: {self.connection_info}\n"
        status += f"Status: {'connected' if self.is_connected else 'disconnected'}\n"
        return status

    def check_and_reconnect(self) -> bool:
        """Check if connection is active and try to reconnect if needed"""
        if self.is_connected:
            try:
                ssh, _ = ensure_connection()
                if verify_connection(ssh):
                    return True
            except Exception as e:
                log_connection_operation("Connection Check Failed", f"Error verifying connection: {str(e)}")
        
        return False

    def update_connection_state(self, is_connected: bool, connection_info: str = None, 
                              connection_id: str = None, device_name: str = None):
        """Update the connection state"""
        self.is_connected = is_connected
        self.connection_info = connection_info
        self.connection_id = connection_id
        self.device_name = device_name

# Initialize connection manager
connection_manager = ConnectionManager()

# Prepare your tools
tools = [
    get_connection_status,
    list_directory,
    create_directory,
    remove_directory,
    remove_file,
    rename_file,
    upload_file,
    download_file,
    read_file,
    write_file,
    disconnect_from_server,
    get_current_directory,
    change_directory,
    list_directories,
    list_current_files,
    create_file,
    update_file,
    get_file_info,
    find_files
]

# Function to preprocess user queries for better search detection
def preprocess_query(query):
    # Detect search-related queries and normalize them
    search_patterns = [
        # Match: find file(s) X, find a file named X, etc.
        r"find\s+(a\s+)?(file|files)(\s+named|\s+called|\s+with\s+name)?\s+(.+)",
        # Match: search for X files, search X, etc.
        r"search(\s+for)?\s+(.+?)(\s+files?)?",
        # Match: locate X, look for X, etc.
        r"(locate|look\s+for)\s+(.+)"
    ]
    
    for pattern in search_patterns:
        match = re.search(pattern, query.lower())
        if match:
            # Extract the search term based on which pattern matched
            if "find" in pattern:
                search_term = match.group(4).strip()
            elif "search" in pattern:
                search_term = match.group(2).strip()
            else:  # locate or look for
                search_term = match.group(2).strip()
                
            # Clean up the search term
            search_term = search_term.strip('"\'')
            
            # Make explicit that this is a find_files request
            return f"Please use the find_files function to search for '{search_term}'"
    
    # If no search patterns matched, return the original query
    return query

prompt = """
**Core Responsibilities**
You are a professional remote file management assistant. Your primary focus is efficient file and directory management on remote servers via SSH/SFTP.

**Important Note**
The system has ALREADY established a connection to the server. You do NOT need to ask for or collect connection details.
When a user requests any file operation, you can proceed directly without authentication steps.

**Tool Usage Guide**
Strictly follow these tool selection rules:
1. get_connection_status - To check if connection is active (it should be)
2. connect_to_server - NOT NEEDED as connection is already established
3. get_current_directory - To show the current working directory on the remote server
4. change_directory - To navigate to a different directory on the remote server
5. list_directory - When user wants to see contents of a directory. Format: 'path'
6. list_directories - When user wants to see only directories in the current path
7. list_current_files - When user wants to see detailed information about files in a directory
8. create_directory - When user wants to create a new directory. Format: 'path'
9. remove_directory - When user wants to delete an empty directory. Format: 'path'
10. remove_file - When user wants to delete a file. Format: 'path'
11. rename_file - When user wants to rename a file or directory. Format: 'old_path new_path'
12. upload_file - When user wants to upload a local file. Format: 'local_path remote_path'
13. download_file - When user wants to download a file. Format: 'remote_path local_path'
14. read_file - When user wants to view file contents. Format: 'path'
15. create_file - When user wants to create a new file. Format: 'path content'
16. update_file - When user wants to modify an existing file. Format: 'path content'
17. write_file - When user wants to create or overwrite a file. Format: 'path content'
18. get_file_info - To show detailed information about a specific file (size, type, etc.)
19. find_files - When user wants to search for files matching a pattern. IMPORTANT: RECOGNIZE search queries like "find file X", "search for X", "locate X", etc.
20. disconnect_from_server - When user is done working with the server

**Search Query Understanding**
When a user asks to find or search for files:
- "find files named X" → use find_files with pattern "X"
- "search for files with X" → use find_files with pattern "*X*"
- "locate X files" → use find_files with pattern "X"
- "find files matching X" → use find_files with pattern "X"
- "look for X" → use find_files with pattern "*X*"
Remember that patterns can use wildcards: * (any characters) and ? (single character)

**Common File Operations Examples**
- Get current location: use get_current_directory
- Navigate to another directory: use change_directory with 'directory_path'
- List only directories: use list_directories with optional 'path'
- List files with details: use list_current_files with optional 'path'
- Create a file: use create_file with 'filename content'
- Update a file: use update_file with 'filename content'
- Create or overwrite a file: use write_file with 'filename content'
- Create an empty file: use write_file with 'filename '
- Create a directory: use create_directory with 'directory_name'
- List files: use list_directory with '.' or a specific path
- Read file content: use read_file with 'filename'
- Get file details: use get_file_info with 'filename'
- Find files: use find_files with 'pattern' and optional directory
- Example: When user says "find file test.txt", call find_files with pattern "test.txt"
- Example: When user says "search for python files", call find_files with pattern "*.py"

**Interaction Style**
- Professional and efficient tone
- Provide clear confirmations after each operation
- Don't ask for connection details - the connection is already established
- Focus on executing the requested file operations directly
"""

# Create the LangGraph agent executor
file_agent = create_react_agent(
    model=model,
    tools=tools,
    checkpointer=memory,
    prompt=prompt
)

def print_welcome():
    print("======================================")
    print("Remote File Management Assistant")
    print("======================================")
    print("This assistant can help you with:")
    print("- Browsing remote directories")
    print("- Creating and removing files/directories")
    print("- Uploading and downloading files")
    print("- Reading and writing file contents")
    print("- Finding files in the remote filesystem")
    print("- Getting detailed file information")
    print("======================================")

# Initialize Flask app
app = Flask(__name__)

# Configure Flask logging
if not verbose_server:
    # Disable Flask's default logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    # Also disable Flask's server startup messages
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *args, **kwargs: None

def log_request_response(response):
    """Log detailed request and response information"""
    try:
        request_data = {
            'method': request.method,
            'url': request.url,
            'headers': dict(request.headers),
            'args': request.args.to_dict(),
            'form': request.form.to_dict(),
            'json': request.get_json(silent=True)
        }

        response_data = response.get_json() if response.is_json else str(response.data)

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
        # Always log to file
        app.logger.info(log_message)
        
        # Only print to terminal if verbose_server is True
        if verbose_server:
            print(log_message)
            
    except Exception as e:
        error_msg = f"Error in logging: {str(e)}"
        app.logger.error(error_msg)
        if verbose_server:
            print(error_msg)

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
            "disconnect": "/api/pc/disconnect",
            "agent": "/api/agent/query"
        }
    })

@app.route('/api/pc/connect', methods=['POST'])
@rate_limit
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
        
        # Update connection state
        connection_manager.update_connection_state(
            is_connected=True,
            connection_info=f"{username}@{hostname}:{port}",
            connection_id=connection_id,
            device_name=device_name
        )
        
        # Update connection_config.json
        config = {
            "current_connection": {
                "hostname": hostname,
                "port": str(port),
                "username": username,
                "password": password
            },
            "connection_history": []
        }
        
        with open('connection_config.json', 'w') as f:
            json.dump(config, f, indent=4)
        
        # Create connection state file
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
        log_connection_operation(
            operation="Connection Failed",
            details=f"Error connecting to {hostname}:{port}: {str(e)}"
        )
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/pc/status', methods=['GET'])
@rate_limit
def get_connection_status():
    try:
        connection_id = request.args.get('connection_id')
        
        if not connection_id:
            return jsonify({
                "status": "failed",
                "error": "Connection ID is required",
                "device_name": None,
                "last_seen": None
            }), 400

        state_file = f"connection_{connection_id}.json"
        if not os.path.exists(state_file):
            return jsonify({
                "status": "failed",
                "error": "Connection not found",
                "device_name": None,
                "last_seen": None
            }), 404

        with open(state_file, 'r') as f:
            state_data = json.load(f)
        
        state_data['last_seen'] = datetime.now().isoformat()
        state_data['metrics']['total_health_checks'] += 1
        
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
@rate_limit
def disconnect_from_pc():
    try:
        data = request.get_json()
        connection_id = data.get('connection_id')
        
        if not connection_id:
            return jsonify({
                "status": "failed",
                "error": "Connection ID is required"
            }), 400
        
        result = close_connection()
        
        if result:
            # Update connection state
            connection_manager.update_connection_state(
                is_connected=False,
                connection_info=None,
                connection_id=None,
                device_name=None
            )
            
            # Reset connection_config.json to default values
            default_config = {
                "current_connection": {
                    "hostname": "",
                    "port": "",
                    "username": "",
                    "password": ""
                },
                "connection_history": []
            }
            with open('connection_config.json', 'w') as f:
                json.dump(default_config, f, indent=4)
            
            # Delete the connection state file
            state_file = f"connection_{connection_id}.json"
            if os.path.exists(state_file):
                os.remove(state_file)
                logging.info(f"Deleted connection state file: {state_file}")
            
            return jsonify({
                "status": "success",
                "message": "Disconnected successfully"
            })
        else:
            return jsonify({
                "status": "failed",
                "error": "Failed to disconnect"
            }), 404
            
    except Exception as e:
        log_connection_operation("Disconnect Failed", f"Error during disconnect: {str(e)}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

@app.route('/api/agent/query', methods=['POST'])
@rate_limit
def agent_query():
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({
                "status": "failed",
                "error": "Query is required"
            }), 400
        
        # Check connection status
        if not connection_manager.is_connected:
            return jsonify({
                "status": "success",
                "response": "No active connection to a PC. Please establish a connection first to perform file operations.",
                "is_connected": False
            })
        
        # Process query with agent
        messages = file_agent.invoke(
            {"messages": [("human", query)]},
            {"configurable": {"thread_id": str(uuid.uuid4())}}
        )
        
        response = messages["messages"][-1].content
        
        return jsonify({
            "status": "success",
            "response": response,
            "is_connected": True
        })
        
    except Exception as e:
        logging.error(f"Error processing agent query: {str(e)}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

def run_agent_interface():
    """Run the interactive agent interface"""
    print("\nAgent Interface is ready. Type your queries below (type 'exit' to quit):")
    
    while True:
        try:
            query = input("\nQuery: ").strip()
            
            if query.lower() == "exit":
                print("Exiting agent interface...")
                break
                
            # Check connection status
            if not connection_manager.is_connected:
                print("\nNo active connection to a PC. Please establish a connection first to perform file operations.")
                continue
            
            # Process query with agent
            messages = file_agent.invoke(
                {"messages": [("human", query)]},
                {"configurable": {"thread_id": str(uuid.uuid4())}}
            )
            
            # Print the response
            print("\nResponse:", messages["messages"][-1].content)
            
        except KeyboardInterrupt:
            print("\nExiting agent interface...")
            break
        except Exception as e:
            print(f"\nError processing query: {str(e)}")

if __name__ == "__main__":
    print_welcome()
    
    # Generate a unique thread ID for this conversation
    thread_id = str(uuid.uuid4())
    
    # Check if we have an active connection
    state = get_connection_state()
    if state["is_connected"]:
        # If we have an active connection, update the connection manager
        connection_manager.update_connection_state(
            is_connected=True,
            connection_info=state["connection_info"],
            connection_id=state["connection_id"],
            device_name=state.get("device_name")
        )
        print(f"\nLoaded existing connection to {state['connection_info']}")
    else:
        # If no active connection, that's fine - we'll wait for one
        print("\nNo active connection. The server is ready to accept new connections.")
        print("Please establish a connection through the mobile app when needed.")
    
    # Set initial context for the LLM
    initial_context = f"""I'm {'connected to ' + state['connection_info'] if state['is_connected'] else 'not connected to any PC'}. 
    You can help users with file operations when connected, or inform them to establish a connection first."""
    
    messages = file_agent.invoke(
        {"messages": [("system", initial_context)]},
        {"configurable": {"thread_id": thread_id}}
    )
    
    # Start the agent interface in a separate thread
    agent_thread = threading.Thread(target=run_agent_interface)
    agent_thread.daemon = True  # This thread will exit when the main thread exits
    agent_thread.start()
    
    # Start the Flask server
    print("\nStarting server on port 5003...")
    if verbose_server:
        print("Server logging is enabled. You will see all request/response logs in the terminal.")
    else:
        print("Server logging is disabled. Logs are still being written to files.")
    
    # Run Flask with custom logging configuration
    app.run(host='0.0.0.0', port=5003, debug=False, use_reloader=False)