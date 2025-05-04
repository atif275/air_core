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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "remote_agent.log"),
        logging.StreamHandler()
    ]
)

# Connection state management
class ConnectionManager:
    def __init__(self):
        self.current_connection = None
        self.connection_history = []
        self.log_file = "logs/connection_manager.log"

    def get_connection_status(self) -> str:
        """Get a human-readable connection status"""
        state = get_connection_state()
        if not state["is_connected"]:
            return "No active connection"
        
        status = f"Connection ID: {state['connection_id']}\n"
        status += f"Device: {state['connection_info']}\n"
        status += f"Status: {'connected' if state['is_connected'] else 'disconnected'}\n"
        if state['error']:
            status += f"Error: {state['error']}\n"
        if state['last_seen']:
            status += f"Last seen: {state['last_seen']}\n"
        
        return status

    def check_and_reconnect(self) -> bool:
        """Check if connection is active and try to reconnect if needed"""
        state = get_connection_state()
        
        if state["is_connected"]:
            # Verify the connection is actually active
            try:
                ssh, _ = ensure_connection()
                if verify_connection(ssh):
                    return True
            except Exception as e:
                log_connection_operation("Connection Check Failed", f"Error verifying connection: {str(e)}")
        
        # Try to reconnect using the most recent connection file
        try:
            connection_files = [f for f in os.listdir('.') if f.startswith('connection_') and f.endswith('.json')]
            if connection_files:
                # Sort by modification time to get the most recent
                connection_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                latest_file = connection_files[0]
                
                with open(latest_file, 'r') as f:
                    connection_data = json.load(f)
                    if connection_data.get("state") == "connected":
                        update_connection_state(connection_data)
                        return True
        except Exception as e:
            log_connection_operation("Reconnection Failed", f"Error reconnecting: {str(e)}")
        
        return False

    def update_connection_state(self):
        """Update the current connection state"""
        # The connection state is managed by remote_connection.py
        pass

    def disconnect(self) -> bool:
        """Disconnect the current connection"""
        try:
            close_connection()
            return True
        except Exception as e:
            logging.error(f"Failed to disconnect: {str(e)}")
            return False

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

if __name__ == "__main__":
    print_welcome()
    
    # Generate a unique thread ID for this conversation
    thread_id = str(uuid.uuid4())
    
    # Check if we have an active connection
    state = get_connection_state()
    if not state["is_connected"]:
        # Try to load the connection from the most recent connection file
        try:
            # Find all connection files
            connection_files = [f for f in os.listdir('.') if f.startswith('connection_') and f.endswith('.json')]
            if connection_files:
                # Sort by modification time to get the most recent
                connection_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                latest_file = connection_files[0]
                
                with open(latest_file, 'r') as f:
                    connection_data = json.load(f)
                    if connection_data.get("state") == "connected":
                        # Update the connection state
                        update_connection_state(connection_data)
                        state = get_connection_state()
                        print(f"\nLoaded existing connection to {state['connection_info']}")
                    else:
                        print("Found connection file but connection is not active")
                        print("Please establish a connection through the mobile app first.")
                        exit(1)
            else:
                print("No active connection found. Please establish a connection through the mobile app first.")
                exit(1)
        except Exception as e:
            print(f"Error loading connection: {str(e)}")
            print("Please establish a connection through the mobile app first.")
            exit(1)
    
    # Set initial context for the LLM
    initial_context = f"""I'm connected to {state['connection_info']}. 
    You can directly perform file operations without asking for connection details."""
    
    messages = file_agent.invoke(
        {"messages": [("system", initial_context)]},
        {"configurable": {"thread_id": thread_id}}
    )
    
    while True:
        query = input("\nWhat would you like to do? (type 'exit' to quit, 'status' for connection status): ").strip()

        if query.lower() == "exit":
            if connection_manager.disconnect():
                print("Disconnected from server.")
            print("Exiting Remote File Manager. Goodbye!")
            break
        elif query.lower() == "status":
            print("\nConnection Status:")
            print(connection_manager.get_connection_status())
            continue
            
        # Check connection status before processing query
        if not connection_manager.check_and_reconnect():
            print("\nNo active connection. Please establish a connection through the mobile app first.")
            print("Connection Status:")
            print(connection_manager.get_connection_status())
            continue
            
        # Preprocess the query to better detect search requests
        processed_query = preprocess_query(query)
        
        # If the query was modified, notify the user
        if processed_query != query:
            print(f"\nInterpreting as a search request...")

        # Invoke the agent
        messages = file_agent.invoke(
            {"messages": [("human", processed_query)]},
            {"configurable": {"thread_id": thread_id}}
        )

        # Extract and print the response
        response = messages["messages"][-1].content
        print("\n" + response)