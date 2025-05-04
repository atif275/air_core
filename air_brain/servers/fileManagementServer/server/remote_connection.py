import paramiko
from langchain_core.tools import tool
from datetime import datetime
from config import connection_config
import logging
from utils.logging_utils import log_connection_operation, log_file_operation
import os
import threading

# Global SSH connection variables
ssh_client = None
sftp = None

# Connection state variables
IS_CONNECTED = False
CONNECTION_INFO = ""
CONNECTION_ID = None
DEVICE_ID = None
OS_TYPE = None
LAST_SEEN = None
ERROR = None
REMOTE_CWD = "."

# Add these global variables at the top of the file
ACTIVE_CONNECTIONS = {}  # Track all active connections by host:port
CONNECTION_LOCK = threading.Lock()  # Thread-safe access to ACTIVE_CONNECTIONS

def track_connection(hostname, port, connection_id, ssh_client, sftp_client):
    """Track a new connection in the global connection registry."""
    global ACTIVE_CONNECTIONS
    key = f"{hostname}:{port}"
    with CONNECTION_LOCK:
        if key not in ACTIVE_CONNECTIONS:
            ACTIVE_CONNECTIONS[key] = []
        ACTIVE_CONNECTIONS[key].append({
            'connection_id': connection_id,
            'ssh_client': ssh_client,
            'sftp_client': sftp_client,
            'created_at': datetime.now()
        })

def untrack_connection(hostname, port, connection_id):
    """Remove a connection from the global connection registry."""
    global ACTIVE_CONNECTIONS
    key = f"{hostname}:{port}"
    with CONNECTION_LOCK:
        if key in ACTIVE_CONNECTIONS:
            ACTIVE_CONNECTIONS[key] = [conn for conn in ACTIVE_CONNECTIONS[key] 
                                     if conn['connection_id'] != connection_id]
            if not ACTIVE_CONNECTIONS[key]:
                del ACTIVE_CONNECTIONS[key]

def close_all_connections_for_host(hostname, port):
    """Close all active connections for a specific host:port."""
    global ACTIVE_CONNECTIONS
    key = f"{hostname}:{port}"
    with CONNECTION_LOCK:
        if key in ACTIVE_CONNECTIONS:
            for conn in ACTIVE_CONNECTIONS[key]:
                try:
                    if conn['sftp_client']:
                        conn['sftp_client'].close()
                    if conn['ssh_client']:
                        conn['ssh_client'].close()
                except Exception as e:
                    log_connection_operation("Close Connection Warning", 
                                          f"Error closing connection {conn['connection_id']}: {str(e)}")
            del ACTIVE_CONNECTIONS[key]

# Regular functions for direct calling
def verify_connection(ssh_client) -> bool:
    """Verify if the SSH connection is still active by executing a simple command."""
    try:
        if not ssh_client:
            log_connection_operation("Connection Verification", "No SSH client provided")
            return False
            
        if not ssh_client.get_transport():
            log_connection_operation("Connection Verification", "No SSH transport available")
            return False
            
        if not ssh_client.get_transport().is_active():
            log_connection_operation("Connection Verification", "SSH transport is not active")
            return False
        
        # Try to execute a simple command to verify connection
        stdin, stdout, stderr = ssh_client.exec_command('ls', timeout=5)
        exit_status = stdout.channel.recv_exit_status()  # Wait for command to complete
        if exit_status != 0:
            log_connection_operation("Connection Verification", f"Command failed with exit status {exit_status}")
            return False
            
        log_connection_operation("Connection Verification", "Connection is active and verified")
        return True
    except Exception as e:
        log_connection_operation("Connection Verification Failed", f"Error: {str(e)}")
        return False

def ensure_connection(hostname=None, port=None, username=None, password=None, connection_id=None, device_id=None, os_type=None):
    """Ensure SSH and SFTP connections are established."""
    global ssh_client, sftp, IS_CONNECTED, CONNECTION_INFO, CONNECTION_ID, DEVICE_ID, OS_TYPE, LAST_SEEN, ERROR
    
    # First check if we have an active connection
    if ssh_client and verify_connection(ssh_client):
        log_connection_operation("Connection Check", "Using existing active connection")
        return ssh_client, sftp
    
    # If no active connection, establish new one
    try:
        log_connection_operation("Connection Attempt", f"Trying to connect to {hostname}:{port} as {username}")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=hostname, port=port, username=username, password=password, timeout=10)
        sftp = ssh_client.open_sftp()
        IS_CONNECTED = True
        CONNECTION_INFO = f"{username}@{hostname}:{port}"
        CONNECTION_ID = connection_id
        DEVICE_ID = device_id
        OS_TYPE = os_type
        LAST_SEEN = datetime.now()
        ERROR = None
        
        # Track the new connection
        track_connection(hostname, port, connection_id, ssh_client, sftp)
        
        # Get device name
        stdin, stdout, stderr = ssh_client.exec_command('hostname')
        device_name = stdout.read().decode().strip()
        CONNECTION_INFO = f"{device_name} ({CONNECTION_INFO})"
        
        log_connection_operation("Connection Success", f"Successfully connected to {hostname}:{port}")
        return ssh_client, sftp
    except Exception as e:
        ERROR = str(e)
        IS_CONNECTED = False
        CONNECTION_INFO = ""
        CONNECTION_ID = None
        DEVICE_ID = None
        OS_TYPE = None
        LAST_SEEN = None
        
        # Clean up failed connection
        if ssh_client:
            ssh_client.close()
            ssh_client = None
        if sftp:
            sftp.close()
            sftp = None
            
        log_connection_operation("Connection Failed", f"Error: {str(e)}")
        raise

def close_connection():
    """Close the SFTP and SSH connections and clean up connection state."""
    global ssh_client, sftp, IS_CONNECTED, CONNECTION_INFO, CONNECTION_ID, DEVICE_ID, OS_TYPE, LAST_SEEN, ERROR, REMOTE_CWD
    
    try:
        log_connection_operation("Close Connection", "Starting connection cleanup")
        
        # Close SFTP connection if it exists
        if sftp:
            try:
                sftp.close()
                log_connection_operation("Close Connection", "SFTP connection closed")
            except Exception as e:
                log_connection_operation("Close Connection Warning", f"Error closing SFTP: {str(e)}")
            finally:
                sftp = None
        
        # Close SSH connection if it exists
        if ssh_client:
            try:
                # First try to close the transport
                if ssh_client.get_transport():
                    ssh_client.get_transport().close()
                    log_connection_operation("Close Connection", "SSH transport closed")
                # Then close the client
                ssh_client.close()
                log_connection_operation("Close Connection", "SSH client closed")
            except Exception as e:
                log_connection_operation("Close Connection Warning", f"Error closing SSH: {str(e)}")
            finally:
                ssh_client = None
        
        # Reset all connection state variables
        IS_CONNECTED = False
        CONNECTION_INFO = ""
        CONNECTION_ID = None
        DEVICE_ID = None
        OS_TYPE = None
        LAST_SEEN = None
        ERROR = None
        REMOTE_CWD = "."
        
        # Force garbage collection to ensure resources are released
        import gc
        gc.collect()
        
        log_connection_operation("Close Connection", "Connection cleanup completed successfully")
        return True
    except Exception as e:
        log_connection_operation("Close Connection Failed", f"Error during cleanup: {str(e)}")
        return False

def get_connection_state():
    """Get the current connection state as a dictionary."""
    return {
        "is_connected": IS_CONNECTED,
        "connection_info": CONNECTION_INFO,
        "connection_id": CONNECTION_ID,
        "device_id": DEVICE_ID,
        "os_type": OS_TYPE,
        "last_seen": LAST_SEEN.isoformat() if LAST_SEEN else None,
        "error": ERROR,
        "remote_cwd": REMOTE_CWD
    }

# ============= TOOL FUNCTIONS FOR LLM AGENT =============

@tool
def get_connection_status() -> str:
    """Check if there is an active connection to a remote server."""
    global IS_CONNECTED, CONNECTION_INFO
    if IS_CONNECTED:
        return f"Currently connected to {CONNECTION_INFO}"
    else:
        return "Not currently connected to any server."

@tool
def connect_to_server(server_info: str) -> str:
    """Connect to a remote server via SSH. 
    Format: 'hostname:port username password'"""
    global IS_CONNECTED, CONNECTION_INFO
    
    # If already connected, just return status
    if IS_CONNECTED:
        return f"Already connected to {CONNECTION_INFO}"
    
    try:
        parts = server_info.split()
        if len(parts) < 3:
            return "Error: Need hostname:port, username, and password."
            
        host_port = parts[0].split(':')
        hostname = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 22
        username = parts[1]
        password = parts[2]
        
        ensure_connection(hostname, port, username, password)
        return f"Successfully connected to {hostname}:{port} as {username}"
    except Exception as e:
        return f"Failed to connect: {str(e)}"

@tool
def get_current_directory() -> str:
    """Get the current working directory on the remote server."""
    global IS_CONNECTED, REMOTE_CWD
    
    if not IS_CONNECTED:
        log_file_operation("Get Current Directory Failed", "Not connected to server")
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        log_file_operation("Get Current Directory", "Getting current working directory")
        
        ssh, _ = ensure_connection()
        if not verify_connection(ssh):
            log_file_operation("Get Current Directory Failed", "Connection verification failed")
            return "Error: Connection is not active. Please reconnect."
            
        stdin, stdout, stderr = ssh.exec_command("pwd")
        remote_pwd = stdout.read().decode().strip()
        REMOTE_CWD = remote_pwd
        
        log_file_operation("Get Current Directory Success", f"Current directory: {remote_pwd}")
        return f"Current Remote Directory: {remote_pwd}"
    except Exception as e:
        log_file_operation("Get Current Directory Failed", f"Error: {str(e)}")
        return f"Error getting current directory: {str(e)}"

@tool
def change_directory(remote_dir: str) -> str:
    """Change current working directory on the remote server."""
    global IS_CONNECTED, REMOTE_CWD
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        ssh, sftp_client = ensure_connection()
        
        # Check if directory exists by trying to list it
        try:
            sftp_client.listdir(remote_dir)
        except FileNotFoundError:
            return f"Error: Directory '{remote_dir}' does not exist on the remote server."
        except PermissionError:
            return f"Error: Permission denied accessing directory '{remote_dir}'."
        
        # If successful, update the current working directory
        REMOTE_CWD = remote_dir
        return f"Changed to remote directory: {remote_dir}"
    except Exception as e:
        return f"Error changing directory: {str(e)}"

@tool
def list_directory(remote_path: str = ".") -> str:
    """List files and directories at the given remote path."""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        log_file_operation("List Directory Failed", "Not connected to server")
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        log_file_operation("List Directory", f"Listing contents of: {remote_path}")
        
        ssh, sftp_client = ensure_connection()
        if not verify_connection(ssh):
            log_file_operation("List Directory Failed", "Connection verification failed")
            return "Error: Connection is not active. Please reconnect."
            
        files = sftp_client.listdir(remote_path)
        log_file_operation("List Directory Success", f"Found {len(files)} items in {remote_path}")
        return f"Contents of {remote_path}: {files}"
    except Exception as e:
        log_file_operation("List Directory Failed", f"Error: {str(e)}")
        return f"Error listing directory: {str(e)}"

@tool
def list_directories(remote_path: str = ".") -> str:
    """List only directories at the given remote path."""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        ssh, sftp_client = ensure_connection()
        
        # Execute ls -la to get detailed listing
        cmd = f"ls -la {remote_path} | grep '^d'"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode()
        
        if not output:
            return f"No directories found in {remote_path}"
        
        directories = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 9:
                dir_name = " ".join(parts[8:])
                directories.append(f"- {dir_name}/")
        
        return "Available Directories:\n" + "\n".join(directories)
    except Exception as e:
        return f"Error listing directories: {str(e)}"

@tool
def list_current_files(remote_path: str = ".") -> str:
    """List files with details in the current directory."""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        ssh, sftp_client = ensure_connection()
        
        # Execute ls -la to get detailed listing
        cmd = f"ls -la {remote_path} | grep -v '^d'"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.read().decode()
        
        if not output:
            return f"No files found in {remote_path}"
        
        files_info = []
        for line in output.splitlines():
            if line.startswith("total") or not line.strip():
                continue
                
            parts = line.split()
            if len(parts) >= 9:
                permissions = parts[0]
                size = parts[4]
                date = " ".join(parts[5:8])
                filename = " ".join(parts[8:])
                
                files_info.append(f"- {filename} (Size: {size} bytes, Modified: {date}, Permissions: {permissions})")
        
        return "Files in current directory:\n" + "\n".join(files_info)
    except Exception as e:
        return f"Error listing files: {str(e)}"

@tool
def create_directory(remote_path: str) -> str:
    """Create a directory at the specified remote path."""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        _, sftp_client = ensure_connection()
        sftp_client.mkdir(remote_path)
        return f"Directory '{remote_path}' created successfully."
    except Exception as e:
        return f"Error creating directory: {str(e)}"

@tool
def remove_directory(remote_path: str) -> str:
    """Remove an empty directory at the specified remote path."""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        _, sftp_client = ensure_connection()
        sftp_client.rmdir(remote_path)
        return f"Directory '{remote_path}' removed successfully."
    except Exception as e:
        return f"Error removing directory: {str(e)}"

@tool
def remove_file(remote_path: str) -> str:
    """Remove a file at the specified remote path."""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        _, sftp_client = ensure_connection()
        sftp_client.remove(remote_path)
        return f"File '{remote_path}' removed successfully."
    except Exception as e:
        return f"Error removing file: {str(e)}"

@tool
def rename_file(paths: str) -> str:
    """Rename a remote file or directory. Format: 'old_path new_path'"""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        parts = paths.split(' ', 1)
        if len(parts) != 2:
            return "Error: Format should be 'old_path new_path'"
            
        remote_old, remote_new = parts
        _, sftp_client = ensure_connection()
        sftp_client.rename(remote_old, remote_new)
        return f"Renamed '{remote_old}' to '{remote_new}' successfully."
    except Exception as e:
        return f"Error renaming file: {str(e)}"

@tool
def upload_file(paths: str) -> str:
    """Upload a local file to the remote server. Format: 'local_path remote_path'"""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        parts = paths.split(' ', 1)
        if len(parts) != 2:
            return "Error: Format should be 'local_path remote_path'"
            
        local_path, remote_path = parts
        _, sftp_client = ensure_connection()
        sftp_client.put(local_path, remote_path)
        return f"File '{local_path}' uploaded to '{remote_path}'."
    except Exception as e:
        return f"Error uploading file: {str(e)}"

@tool
def download_file(paths: str) -> str:
    """Download a remote file to the local machine. Format: 'remote_path local_path'"""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        parts = paths.split(' ', 1)
        if len(parts) != 2:
            return "Error: Format should be 'remote_path local_path'"
            
        remote_path, local_path = parts
        _, sftp_client = ensure_connection()
        sftp_client.get(remote_path, local_path)
        return f"File '{remote_path}' downloaded to '{local_path}'."
    except Exception as e:
        return f"Error downloading file: {str(e)}"

@tool
def read_file(remote_path: str) -> str:
    """Read and return the content of a remote file."""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        _, sftp_client = ensure_connection()
        with sftp_client.open(remote_path, 'r') as remote_file:
            content = remote_file.read().decode()
        return f"Content of '{remote_path}':\n{content}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def create_file(file_info: str) -> str:
    """Create a new file on the remote server.
    Format: 'path content' or 'path' for empty file"""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        log_file_operation("Create File Failed", "Not connected to server")
        return "Error: Not connected to any server. Use connect_to_server first."
    
    try:
        # Parse file path and content
        parts = file_info.split(' ', 1)
        remote_path = parts[0]
        content = parts[1] if len(parts) > 1 else ""
        
        log_file_operation("Create File", f"Attempting to create file: {remote_path}")
        
        # Ensure connection is active
        ssh, sftp_client = ensure_connection()
        if not verify_connection(ssh):
            log_file_operation("Create File Failed", "Connection verification failed")
            return "Error: Connection is not active. Please reconnect."
        
        # Create the file
        with sftp_client.open(remote_path, 'w') as f:
            f.write(content)
        
        log_file_operation("Create File Success", f"Successfully created file: {remote_path}")
        return f"Successfully created file: {remote_path}"
    except Exception as e:
        log_file_operation("Create File Failed", f"Error: {str(e)}")
        return f"Error creating file: {str(e)}"

@tool
def update_file(file_info: str) -> str:
    """Update an existing file on the remote server. Format: 'remote_path content'"""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        parts = file_info.split(' ', 1)
        if len(parts) != 2:
            return "Error: Format should be 'remote_path content'"
            
        remote_path, content = parts
        _, sftp_client = ensure_connection()
        
        # Check if file exists
        try:
            sftp_client.stat(remote_path)
        except FileNotFoundError:
            return f"Error: File '{remote_path}' does not exist on the remote server."
        
        # Update the file
        with sftp_client.open(remote_path, 'w') as remote_file:
            remote_file.write(content.encode())
        return f"File '{remote_path}' updated successfully."
    except Exception as e:
        return f"Error updating file: {str(e)}"

@tool
def write_file(file_info: str) -> str:
    """Write data to a remote file (create or overwrite). Format: 'remote_path DATA_CONTENT'"""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        parts = file_info.split(' ', 1)
        if len(parts) != 2:
            return "Error: Format should be 'remote_path DATA_CONTENT'"
            
        remote_path, data = parts
        _, sftp_client = ensure_connection()
        with sftp_client.open(remote_path, 'w') as remote_file:
            remote_file.write(data.encode())
        return f"Data written to file '{remote_path}'."
    except Exception as e:
        return f"Error writing file: {str(e)}"

@tool
def get_file_info(remote_path: str) -> str:
    """Get detailed information about a remote file."""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        ssh, sftp_client = ensure_connection()
        
        # Get file stats
        stats = sftp_client.stat(remote_path)
        
        # Execute file command to determine file type
        cmd = f"file {remote_path}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        file_type_output = stdout.read().decode().strip()
        
        # Build info string
        info = f"File Information for '{remote_path}':\n"
        
        # Extract file type from the output
        if ":" in file_type_output:
            file_type = file_type_output.split(":", 1)[1].strip()
            info += f"Type: {file_type}\n"
        else:
            # Determine file type from extension
            if remote_path.endswith(('.txt', '.md', '.csv')):
                file_type = "Text file"
            elif remote_path.endswith(('.py', '.js', '.java', '.c', '.cpp')):
                file_type = "Source code"
            elif remote_path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                file_type = "Image file"
            elif remote_path.endswith(('.mp3', '.wav', '.flac')):
                file_type = "Audio file"
            elif remote_path.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                file_type = "Video file"
            elif remote_path.endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                file_type = "Document file"
            else:
                file_type = "Unknown"
            info += f"Type: {file_type}\n"
        
        # Add size information
        size = stats.st_size
        info += f"Size: {size} bytes ({size/1024:.2f} KB)\n"
        
        # Add timestamps
        # Note: These may not be accurate depending on the server's timezone
        info += f"Last Modified: {datetime.fromtimestamp(stats.st_mtime)}\n"
        info += f"Last Accessed: {datetime.fromtimestamp(stats.st_atime)}\n"
        
        # Add permissions
        info += f"File Mode: {stats.st_mode}\n"
        info += f"Owner UID: {stats.st_uid}\n"
        info += f"Group GID: {stats.st_gid}\n"
        
        return info
    except FileNotFoundError:
        return f"Error: File '{remote_path}' does not exist on the remote server."
    except Exception as e:
        return f"Error getting file info: {str(e)}"

@tool
def find_files(pattern: str, remote_path: str = ".", recursive: bool = True) -> str:
    """Find files matching a pattern on the remote server.
    
    Args:
        pattern: The search pattern (supports * and ? wildcards)
        remote_path: The directory to search in (default: current directory)
        recursive: If True, searches subdirectories recursively (default: True)
    """
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        return "Error: Not connected to any server. Use connect_to_server first."
        
    try:
        print("find_files function called")
        ssh, _ = ensure_connection()
        
        # Handle depth parameter for find command
        depth_param = "" if recursive else "-maxdepth 1"
        
        # Check if pattern already has wildcards, if not, add wildcards to make it more flexible
        if '*' not in pattern and '?' not in pattern:
            # Use two find commands - one for exact match and one with wildcards
            exact_cmd = f"find {remote_path} {depth_param} -type f -name '{pattern}' 2>/dev/null"
            wildcard_cmd = f"find {remote_path} {depth_param} -type f -name '*{pattern}*' 2>/dev/null"
            
            # Execute both commands
            stdin, stdout, stderr = ssh.exec_command(exact_cmd)
            exact_output = stdout.read().decode().strip()
            
            stdin, stdout, stderr = ssh.exec_command(wildcard_cmd)
            wildcard_output = stdout.read().decode().strip()
            
            # Combine and deduplicate results
            exact_files = exact_output.split('\n') if exact_output else []
            wildcard_files = wildcard_output.split('\n') if wildcard_output else []
            
            # Remove duplicates and empty entries
            exact_files = [f for f in exact_files if f]
            wildcard_files = [f for f in wildcard_files if f and f not in exact_files]
            
            all_matched_files = exact_files + wildcard_files
            
            # Format search scope message
            scope_msg = "all subdirectories" if recursive else "current directory only"
            
            if exact_files and not wildcard_files:
                # Only exact matches found
                return f"Found {len(exact_files)} file(s) matching exactly '{pattern}' in {scope_msg}:\n" + "\n".join(exact_files)
            elif not exact_files and wildcard_files:
                # Only wildcard matches found
                return f"Found {len(wildcard_files)} file(s) containing '{pattern}' in {scope_msg}:\n" + "\n".join(wildcard_files)
            elif exact_files and wildcard_files:
                # Both exact and wildcard matches found
                return f"Found {len(all_matched_files)} file(s) in {scope_msg}:\n" + \
                       f"Exact matches for '{pattern}':\n" + "\n".join(exact_files) + \
                       f"\n\nFiles containing '{pattern}':\n" + "\n".join(wildcard_files)
            else:
                # No files found
                return f"No files matching or containing '{pattern}' found in {scope_msg}."
        else:
            # Pattern already has wildcards, use it as is
            cmd = f"find {remote_path} {depth_param} -type f -name '{pattern}' 2>/dev/null"
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.read().decode()
            
            matched_files = output.strip().split('\n')
            matched_files = [f for f in matched_files if f]  # Remove empty strings
            
            # Format search scope message
            scope_msg = "all subdirectories" if recursive else "current directory only"
            
            if matched_files:
                return f"Found {len(matched_files)} file(s) matching '{pattern}' in {scope_msg}:\n" + "\n".join(matched_files)
            else:
                return f"No files matching '{pattern}' found in {scope_msg}."
    except Exception as e:
        return f"Error finding files: {str(e)}"

@tool
def disconnect_from_server() -> str:
    """Close the SSH and SFTP connections and clean up all connection states."""
    global IS_CONNECTED
    
    if not IS_CONNECTED:
        log_connection_operation("Disconnect", "No active connection to disconnect")
        return "Not currently connected to any server."
        
    try:
        log_connection_operation("Disconnect", "Starting disconnection process")
        
        # First, close the current connection
        result = close_connection()
        
        # Additional cleanup for any remaining connection files
        try:
            # Find all connection files
            connection_files = [f for f in os.listdir('.') if f.startswith('connection_') and f.endswith('.json')]
            for file in connection_files:
                try:
                    os.remove(file)
                    log_connection_operation("Disconnect", f"Deleted old connection file: {file}")
                except Exception as e:
                    log_connection_operation("Disconnect Failed", f"Error deleting old connection file {file}: {str(e)}")
        except Exception as e:
            log_connection_operation("Disconnect Failed", f"Error during additional cleanup: {str(e)}")
        
        # Verify the connection is actually closed
        if ssh_client:
            try:
                if verify_connection(ssh_client):
                    log_connection_operation("Disconnect Warning", "Connection still appears to be active after close attempt")
                    # Force close the connection
                    ssh_client.close()
                    ssh_client = None
            except Exception as e:
                log_connection_operation("Disconnect Warning", f"Error verifying connection closure: {str(e)}")
        
        log_connection_operation("Disconnect", "Disconnection process completed")
        return result
    except Exception as e:
        log_connection_operation("Disconnect Failed", f"Error during disconnection: {str(e)}")
        return f"Error disconnecting from server: {str(e)}"

def update_connection_state(connection_data: dict) -> None:
    """Update the connection state from a connection file"""
    global ssh_client, sftp, IS_CONNECTED, CONNECTION_INFO, CONNECTION_ID, DEVICE_ID, OS_TYPE, LAST_SEEN, ERROR
    
    try:
        log_connection_operation("Update Connection State", "Starting connection state update")
        
        # Update the connection state
        IS_CONNECTED = True
        CONNECTION_ID = connection_data.get("connection_id")
        CONNECTION_INFO = connection_data.get("device_name", "Unknown device")
        ERROR = None
        LAST_SEEN = datetime.now()
        
        # If we have connection details, try to establish the connection
        if "ssh_command" in connection_data:
            ssh_command = connection_data["ssh_command"]
            log_connection_operation("Update Connection State", f"Processing SSH command: {ssh_command}")
            
            # Parse the SSH command to get connection details
            parts = ssh_command.split()
            username_host = None
            port = 22  # Default SSH port
            
            # Find username@host and port
            for i, part in enumerate(parts):
                if '@' in part:
                    username_host = part
                elif part == '-p' and i + 1 < len(parts):
                    port = int(parts[i + 1])
            
            if not username_host:
                raise ValueError("Invalid SSH command format: no username@host found")
            
            username, hostname = username_host.split('@')
            
            # Get password from config
            config = connection_config.load_config()
            password = config.get("current_connection", {}).get("password")
            
            if password:
                try:
                    log_connection_operation("Update Connection State", f"Attempting to connect to {hostname}:{port}")
                    
                    # Create SSH client
                    ssh_client = paramiko.SSHClient()
                    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    
                    # Connect to the server
                    ssh_client.connect(
                        hostname=hostname,
                        port=port,
                        username=username,
                        password=password,
                        timeout=10
                    )
                    
                    # Create SFTP client
                    sftp = ssh_client.open_sftp()
                    
                    # Get device name
                    stdin, stdout, stderr = ssh_client.exec_command('hostname')
                    device_name = stdout.read().decode().strip()
                    CONNECTION_INFO = f"{device_name} ({username}@{hostname}:{port})"
                    
                    log_connection_operation("Update Connection State", "Successfully re-established connection")
                except Exception as e:
                    log_connection_operation("Update Connection State Failed", f"Error: {str(e)}")
                    ERROR = str(e)
                    IS_CONNECTED = False
                    if ssh_client:
                        ssh_client.close()
                        ssh_client = None
                    if sftp:
                        sftp.close()
                        sftp = None
            else:
                log_connection_operation("Update Connection State Failed", "No password found in config")
                ERROR = "No password found in config"
                IS_CONNECTED = False
    except Exception as e:
        log_connection_operation("Update Connection State Failed", f"Error: {str(e)}")
        ERROR = str(e)
        IS_CONNECTED = False 