# AIR PC Integration Server

A Flask-based HTTP server that handles SSH connections between mobile devices and computers.

## Features

- SSH connection management
- Connection status monitoring
- Rate limiting
- Automatic connection cleanup
- Secure password handling
- Cross-platform support (Windows, Linux, macOS)

## Requirements

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. Clone the repository
2. Navigate to the server directory:
   ```bash
   cd server
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate the virtual environment:
   - On Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

1. Make sure you're in the server directory with the virtual environment activated
2. Start the server:
   ```bash
   python app.py
   ```
   The server will start on port 5003.

For production deployment, use gunicorn:
```bash
gunicorn -b 0.0.0.0:5003 app:app
```

## API Endpoints

### 1. Connect to PC
- **URL:** `/api/pc/connect`
- **Method:** POST
- **Body:**
  ```json
  {
    "ssh_command": "ssh -p 2222 user@hostname",
    "password": "user_password",
    "os_type": "macOS",
    "device_id": "device_123"
  }
  ```

### 2. Check Connection Status
- **URL:** `/api/pc/status`
- **Method:** GET
- **Query Parameters:**
  - `connection_id`: The connection ID returned from the connect endpoint

### 3. Disconnect
- **URL:** `/api/pc/disconnect`
- **Method:** POST
- **Body:**
  ```json
  {
    "connection_id": "connection_xyz"
  }
  ```

## Security Features

- Rate limiting to prevent abuse
- Secure password handling
- Automatic connection cleanup
- Thread-safe operations
- Connection timeouts

## Error Handling

The server provides detailed error messages for:
- Invalid SSH commands
- Authentication failures
- Connection timeouts
- Network issues
- Rate limit exceeded

## Logging

Logs are stored in the `logs` directory with automatic rotation:
- Maximum log file size: 10MB
- Keeps last 5 log files
- Includes timestamps and line numbers

## Logging Examples

The server maintains detailed logs of all requests, responses, and SSH operations in `logs/server.log`. Here are examples of what the logs look like:

### 1. Connect Request Log Example
```
--------------------
Timestamp: 2024-03-16 14:30:45,123
Level: INFO
Location: /server/app.py:125

REQUEST:
--------
Method: POST
URL: http://192.168.1.4:5003/api/pc/connect
Headers: {
  "Content-Type": "application/json",
  "User-Agent": "AIR-Mobile/1.0",
  "Accept": "application/json"
}
Query Args: {}
Body: {
  "ssh_command": "ssh -p 2222 user@192.168.1.100",
  "password": "[REDACTED]",
  "os_type": "macOS",
  "device_id": "device_123abc"
}

RESPONSE:
---------
Status Code: 200
Headers: {
  "Content-Type": "application/json",
  "Content-Length": "157"
}
Body: {
  "status": "connected",
  "connection_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "User-MacBook-Pro",
  "error": null
}
--------------------
```

### 2. Status Check Log Example
```
--------------------
Timestamp: 2024-03-16 14:30:50,456
Level: INFO
Location: /server/app.py:189

REQUEST:
--------
Method: GET
URL: http://192.168.1.4:5003/api/pc/status?connection_id=550e8400-e29b-41d4-a716-446655440000
Headers: {
  "Accept": "application/json",
  "User-Agent": "AIR-Mobile/1.0"
}
Query Args: {
  "connection_id": "550e8400-e29b-41d4-a716-446655440000"
}
Body: No body

RESPONSE:
---------
Status Code: 200
Headers: {
  "Content-Type": "application/json",
  "Content-Length": "183"
}
Body: {
  "status": "connected",
  "device_name": "User-MacBook-Pro",
  "last_seen": "2024-03-16T14:30:50.456Z",
  "error": null
}
--------------------
```

### 3. Disconnect Request Log Example
```
--------------------
Timestamp: 2024-03-16 14:31:15,789
Level: INFO
Location: /server/app.py:234

REQUEST:
--------
Method: POST
URL: http://192.168.1.4:5003/api/pc/disconnect
Headers: {
  "Content-Type": "application/json",
  "User-Agent": "AIR-Mobile/1.0",
  "Accept": "application/json"
}
Query Args: {}
Body: {
  "connection_id": "550e8400-e29b-41d4-a716-446655440000"
}

RESPONSE:
---------
Status Code: 200
Headers: {
  "Content-Type": "application/json",
  "Content-Length": "54"
}
Body: {
  "status": "disconnected",
  "error": null
}
--------------------
```

### 4. SSH Connection Success Log Example
```
--------------------
Timestamp: 2024-03-16 14:30:45,234
Level: INFO
Location: /server/utils/ssh_manager.py:89

SSH Connection Successful:
------------------------
Device Name: User-MacBook-Pro
Connection ID: 550e8400-e29b-41d4-a716-446655440000
Remote IP: 192.168.1.100
Connected At: 2024-03-16T14:30:45.234Z

Home Directory Contents:
-----------------------
total 56
drwxr-xr-x  31 user  staff   992 Mar 16 14:30 .
drwxr-xr-x   5 root  admin   160 Jan  1  2024 ..
-rw-r--r--   1 user  staff  8196 Mar 16 14:30 .DS_Store
drwx------   3 user  staff    96 Jan  1  2024 .Trash
-rw-------   1 user  staff   737 Mar 16 14:30 .bash_history
-rw-r--r--   1 user  staff    52 Jan  1  2024 .bash_profile
drwx------  16 user  staff   512 Mar 16 14:30 .config
drwx------   3 user  staff    96 Jan  1  2024 .local
drwxr-xr-x   4 user  staff   128 Jan  1  2024 Documents
drwxr-xr-x   3 user  staff    96 Jan  1  2024 Downloads
drwxr-xr-x   4 user  staff   128 Jan  1  2024 Pictures

Directory Listing Errors (if any):
--------------------------------
None
--------------------
```

### 5. SSH Status Check Log Example
```
--------------------
Timestamp: 2024-03-16 14:30:50,567
Level: INFO
Location: /server/utils/ssh_manager.py:156

SSH Status Check:
---------------
Connection ID: 550e8400-e29b-41d4-a716-446655440000
Device Name: User-MacBook-Pro
Status: Active
Last Seen: 2024-03-16T14:30:50.567Z
Files in Home Dir: 31 items
--------------------
```

### 6. SSH Authentication Failure Log Example
```
--------------------
Timestamp: 2024-03-16 14:31:00,789
Level: ERROR
Location: /server/utils/ssh_manager.py:123

SSH Authentication Failed:
------------------------
Device ID: device_123abc
OS Type: macOS
Error: Authentication failed
Details: Authentication failed for user@192.168.1.100
Timestamp: 2024-03-16T14:31:00.789Z
--------------------
```

### 7. SSH Disconnection Log Example
```
--------------------
Timestamp: 2024-03-16 14:31:15,901
Level: INFO
Location: /server/utils/ssh_manager.py:189

SSH Disconnection:
----------------
Connection ID: 550e8400-e29b-41d4-a716-446655440000
Device Name: User-MacBook-Pro
Device ID: device_123abc
OS Type: macOS
Last Seen: 2024-03-16T14:31:15.789Z
Disconnected At: 2024-03-16T14:31:15.901Z
--------------------
```

### 8. SSH Auto-Cleanup Log Example
```
--------------------
Timestamp: 2024-03-16 15:00:45,123
Level: INFO
Location: /server/utils/ssh_manager.py:234

SSH Auto-Cleanup:
---------------
Connection ID: 550e8400-e29b-41d4-a716-446655440000
Device Name: User-MacBook-Pro
Device ID: device_123abc
Last Seen: 2024-03-16T14:30:45.234Z
Cleanup At: 2024-03-16T15:00:45.123Z
Reason: Inactivity timeout (1800 seconds)
--------------------
```

## Performance

- Supports 100 concurrent connections
- Connection establishment within 5 seconds
- Status updates within 1-second latency
- Automatic cleanup of inactive connections after 30 minutes 