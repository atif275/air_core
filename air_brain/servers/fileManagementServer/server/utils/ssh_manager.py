import paramiko
import re
import logging
from threading import Lock
from models.connection import Connection, ConnectionState
from datetime import datetime, timedelta
import json
import socket
import traceback

class SSHManager:
    def __init__(self, ssh_logger=None):
        self.connections = {}
        self.lock = Lock()
        self.logger = ssh_logger or logging.getLogger(__name__)
        self.cleanup_interval = timedelta(minutes=5)
        self.connection_timeout = timedelta(minutes=30)

    def establish_connection(self, connection: Connection, password: str) -> Connection:
        """Establish SSH connection with the given credentials"""
        try:
            # Step 1: Parse SSH command (like when you type ssh -p 40681 ATIFHANIF@serveo.net)
            # Handle both formats:
            # 1. ssh -p PORT USER@HOST (serveo format)
            # 2. ssh USER@HOST -p PORT (ngrok format)
            match = re.match(r'ssh (?:-p (\d+) )?([^@]+)@([^\s]+)(?: -p (\d+))?', connection.ssh_command)
            if not match:
                self.logger.error('\n'.join([
                    'SSH Command Parsing Failed:',
                    '--------------------------',
                    f'Command: {connection.ssh_command}',
                    'Error: Invalid SSH command format',
                    'Supported formats:',
                    '1. ssh -p PORT USER@HOST',
                    '2. ssh USER@HOST -p PORT',
                    f'Device ID: {connection.device_id}',
                    f'OS Type: {connection.os_type}'
                ]))
                raise ValueError("Invalid SSH command format")

            # Extract port from either position
            port = match.group(1) or match.group(4)
            username = match.group(2)
            hostname = match.group(3)
            
            if not port:
                raise ValueError("Port number not found in SSH command")
            
            # Log attempt (like when you start typing ssh command)
            self.logger.info('\n'.join([
                'SSH Connection Attempt:',
                '----------------------',
                f'Command: {connection.ssh_command}',
                f'Host: {hostname}',
                f'Port: {port}',
                f'Username: {username}',
                f'Device ID: {connection.device_id}',
                f'OS Type: {connection.os_type}'
            ]))
            
            # Step 2: Create SSH client (like when you press enter)
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Step 3: Try to connect (like when you type password)
            try:
                ssh.connect(
                    hostname=hostname,
                    port=int(port),
                    username=username,
                    password=password,
                    timeout=10
                )

                # Log successful connection
                self.logger.info('\n'.join([
                    'SSH Connection Successful:',
                    '------------------------',
                    f'Device Name: {hostname}',
                    f'Connection ID: {connection.connection_id}',
                    f'Remote IP: {hostname}',
                    f'Logged in as: {username}',
                    f'Connected At: {datetime.now().isoformat()}'
                ]))

                # Step 4: Verify connection by running commands
                # Get hostname
                stdin, stdout, stderr = ssh.exec_command('hostname')
                device_name = stdout.read().decode().strip()
                
                # Get current user
                stdin, stdout, stderr = ssh.exec_command('whoami')
                current_user = stdout.read().decode().strip()
                
                # List home directory contents
                stdin, stdout, stderr = ssh.exec_command('ls -la ~/')
                dir_listing = stdout.read().decode().strip()
                dir_errors = stderr.read().decode().strip()

                # Log directory listing
                self.logger.info('\n'.join([
                    'Home Directory Contents:',
                    '----------------------',
                    f'Device: {device_name}',
                    f'User: {current_user}',
                    f'Directory Listing:\n{dir_listing}',
                    f'Directory Listing Errors (if any):\n{dir_errors}'
                ]))

                # Update connection status
                connection.update_status(ConnectionState.CONNECTED)
                connection.device_name = device_name
                connection.last_seen = datetime.now()
                connection.ssh_client = ssh
                connection.retry_count = 0
                
                # Store the connection in the connections dictionary
                with self.lock:
                    self.connections[connection.connection_id] = connection
                
                return connection

            except paramiko.AuthenticationException as e:
                self.logger.error('\n'.join([
                    'SSH Authentication Failed:',
                    '------------------------',
                    f'Error: {str(e)}',
                    f'Device ID: {connection.device_id}',
                    f'OS Type: {connection.os_type}'
                ]))
                connection.update_status(ConnectionState.FAILED)
                connection.error = f"Authentication failed: {str(e)}"
                return connection

            except paramiko.SSHException as e:
                self.logger.error('\n'.join([
                    'SSH Protocol Error:',
                    '------------------',
                    f'Error: {str(e)}',
                    f'Device ID: {connection.device_id}',
                    f'OS Type: {connection.os_type}'
                ]))
                connection.update_status(ConnectionState.FAILED)
                connection.error = f"SSH protocol error: {str(e)}"
                return connection

            except Exception as e:
                self.logger.error('\n'.join([
                    'SSH Connection Error:',
                    '-------------------',
                    f'Error: {str(e)}',
                    f'Device ID: {connection.device_id}',
                    f'OS Type: {connection.os_type}',
                    f'Traceback: {traceback.format_exc()}'
                ]))
                connection.update_status(ConnectionState.FAILED)
                connection.error = f"Connection error: {str(e)}"
                return connection

        except paramiko.AuthenticationException as e:
            self.logger.error('\n'.join([
                'SSH Authentication Failed:',
                '------------------------',
                f'Device ID: {connection.device_id}',
                f'OS Type: {connection.os_type}',
                'Error: Authentication failed',
                f'Details: {str(e)}',
                f'Timestamp: {datetime.utcnow().isoformat()}'
            ]))
            connection.update_status(ConnectionState.FAILED, "Authentication failed")
            return False, None, "Authentication failed"
        
        except paramiko.SSHException as e:
            self.logger.error('\n'.join([
                'SSH Connection Error:',
                '-------------------',
                f'Device ID: {connection.device_id}',
                f'OS Type: {connection.os_type}',
                'Error Type: SSH Exception',
                f'Details: {str(e)}',
                f'Timestamp: {datetime.utcnow().isoformat()}'
            ]))
            connection.update_status(ConnectionState.FAILED, str(e))
            return False, None, f"SSH error: {str(e)}"
        
        except Exception as e:
            self.logger.error('\n'.join([
                'SSH General Error:',
                '----------------',
                f'Device ID: {connection.device_id}',
                f'OS Type: {connection.os_type}',
                f'Error Type: {type(e).__name__}',
                f'Details: {str(e)}',
                f'Timestamp: {datetime.utcnow().isoformat()}'
            ]))
            connection.update_status(ConnectionState.FAILED, str(e))
            return False, None, f"Connection error: {str(e)}"

    def get_connection_status(self, connection_id: str):
        with self.lock:
            connection = self.connections.get(connection_id)
            if not connection:
                return None

            # Check if connection is still alive
            if connection.is_active():
                try:
                    # Try to execute a simple command to verify connection
                    stdin, stdout, stderr = connection.ssh_client.exec_command('echo "Connection check" && ls -la ~/ | wc -l')
                    response = stdout.read().decode().strip()
                    connection.last_seen = datetime.utcnow()
                    
                    # Log successful status check
                    self.logger.info('\n'.join([
                        'SSH Status Check:',
                        '---------------',
                        f'Connection ID: {connection_id}',
                        f'Device Name: {connection.device_name}',
                        'Status: Active',
                        f'Last Seen: {connection.last_seen.isoformat()}',
                        f'Files in Home Dir: {response.split()[1]} items'
                    ]))
                except Exception as e:
                    # Log connection check failure
                    self.logger.error('\n'.join([
                        'SSH Status Check Failed:',
                        '----------------------',
                        f'Connection ID: {connection_id}',
                        f'Device Name: {connection.device_name}',
                        f'Error: {str(e)}',
                        f'Timestamp: {datetime.utcnow().isoformat()}'
                    ]))
                    connection.update_status(ConnectionState.DISCONNECTED)
                    self._cleanup_connection(connection)

            return connection

    def disconnect(self, connection_id: str):
        with self.lock:
            connection = self.connections.get(connection_id)
            if not connection:
                return False

            # Log disconnection
            self.logger.info('\n'.join([
                'SSH Disconnection:',
                '----------------',
                f'Connection ID: {connection_id}',
                f'Device Name: {connection.device_name}',
                f'Device ID: {connection.device_id}',
                f'OS Type: {connection.os_type}',
                f'Last Seen: {connection.last_seen.isoformat()}',
                f'Disconnected At: {datetime.utcnow().isoformat()}'
            ]))

            self._cleanup_connection(connection)
            return True

    def _cleanup_connection(self, connection: Connection):
        try:
            if connection.ssh_client:
                connection.ssh_client.close()
            connection.update_status(ConnectionState.DISCONNECTED)
        except Exception as e:
            self.logger.error('\n'.join([
                'SSH Cleanup Error:',
                '----------------',
                f'Connection ID: {connection.connection_id}',
                f'Device Name: {connection.device_name}',
                f'Error: {str(e)}',
                f'Timestamp: {datetime.utcnow().isoformat()}'
            ]))
        finally:
            if connection.connection_id in self.connections:
                del self.connections[connection.connection_id]

    def cleanup_inactive_connections(self):
        """Cleanup connections that haven't been active for too long"""
        current_time = datetime.utcnow()
        with self.lock:
            inactive_connections = [
                conn for conn in self.connections.values()
                if current_time - conn.last_seen > self.connection_timeout
            ]
            for connection in inactive_connections:
                self.logger.info('\n'.join([
                    'SSH Auto-Cleanup:',
                    '---------------',
                    f'Connection ID: {connection.connection_id}',
                    f'Device Name: {connection.device_name}',
                    f'Device ID: {connection.device_id}',
                    f'Last Seen: {connection.last_seen.isoformat()}',
                    f'Cleanup At: {current_time.isoformat()}',
                    f'Reason: Inactivity timeout ({self.connection_timeout.total_seconds()} seconds)'
                ]))
                self._cleanup_connection(connection) 