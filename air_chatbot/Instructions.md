# AIR Chatbot Server Instructions

## Running Servers in Background

### 1. Main Chatbot Server (Port 5001)
```bash
nohup python app.py > chatbot_server.log 2>&1 &
```

### 2. Task Sync Server (Port 5002)
```bash
nohup python task_sync.py > task_sync.log 2>&1 &
```

### 3. Remote Agent Server (Port 5003)
```bash
nohup python src/file_system/server/remote_agent.py > remote_agent.log 2>&1 &
```

### 4. Email Server (Port 5004)
```bash
nohup python email_server.py > email_server.log 2>&1 &
```

### 5. WebSocket Server (Port 8765)
```bash
nohup python server.py > websocket_server.log 2>&1 &
```

### 6. Run All Servers at Once
```bash
nohup python app.py > chatbot_server.log 2>&1 &
nohup python task_sync.py > task_sync.log 2>&1 &
nohup python src/file_system/server/remote_agent.py > remote_agent.log 2>&1 &
nohup python email_server.py > email_server.log 2>&1 &
nohup python server.py > websocket_server.log 2>&1 &
```

## Checking Server Status

### View running processes
```bash
ps aux | grep python
```

### Check server logs
```bash
tail -f chatbot_server.log
tail -f task_sync.log
tail -f remote_agent.log
tail -f email_server.log
tail -f websocket_server.log
```

### Check if ports are listening
```bash
netstat -tlnp | grep -E ':(5001|5002|5003|5004|8765)'
```

## Stopping Servers

### Method 1: Stop by Process ID
```bash
# Find process IDs
ps aux | grep python

# Kill specific processes (replace PID with actual process ID)
kill -9 PID
```

### Method 2: Stop by Port
```bash
# Find and kill processes by port
sudo lsof -ti:5001 | xargs kill -9  # Chatbot server
sudo lsof -ti:5002 | xargs kill -9  # Task sync server
sudo lsof -ti:5003 | xargs kill -9  # Remote agent server
sudo lsof -ti:5004 | xargs kill -9  # Email server
sudo lsof -ti:8765 | xargs kill -9  # WebSocket server
```

### Method 3: Stop All Python Servers
```bash
pkill -f "python.*\.py"
```

### Method 4: Stop Specific Servers by Name
```bash
pkill -f "python app.py"           # Chatbot server
pkill -f "python task_sync.py"     # Task sync server
pkill -f "python.*remote_agent.py" # Remote agent server
pkill -f "python email_server.py"  # Email server
pkill -f "python server.py"        # WebSocket server
```

## Server Ports Summary
- **5001**: Main Chatbot Server (Flask)
- **5002**: Task Sync Server (Flask)
- **5003**: Remote Agent Server (Flask)
- **5004**: Email Server (Flask)
- **8765**: WebSocket Server (WebSocket)

## Health Check URLs
- `http://localhost:5001/health` - Chatbot server
- `http://localhost:5002/` - Task sync server
- `http://localhost:5003/` - Remote agent server
- `http://localhost:5004/` - Email server
- WebSocket: `ws://localhost:8765` - WebSocket server
