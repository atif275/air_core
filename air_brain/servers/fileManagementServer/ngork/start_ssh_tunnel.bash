#!/bin/bash

# Function to check if ngrok is installed
check_ngrok() {
    if ! command -v ngrok &> /dev/null; then
        echo "[!] Ngrok is not installed or not in PATH."
        echo "→ Download it from: https://ngrok.com/download"
        exit 1
    fi
}

# Function to check if SSH server is running
check_ssh_server() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo service ssh status &> /dev/null || echo "[!] SSH server is not running. Start it with: sudo service ssh start"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        sudo systemsetup -getremotelogin | grep "On" &> /dev/null || echo "[!] SSH server is not enabled. Enable it from System Preferences > Sharing > Remote Login."
    fi
}

# Start ngrok TCP tunnel
start_ngrok() {
    echo "[+] Killing any existing ngrok sessions..."
    pkill ngrok &> /dev/null

    echo "[+] Starting Ngrok TCP tunnel on port 22..."
    ngrok tcp 22 > /dev/null &
    NGROK_PID=$!
    sleep 5
}

# Extract the public ngrok TCP URL
get_ngrok_url() {
    NGROK_API=$(curl --silent http://localhost:4040/api/tunnels)
    PUBLIC_URL=$(echo "$NGROK_API" | grep -o 'tcp://[^"]*')
    
    if [[ -z "$PUBLIC_URL" ]]; then
        echo "[!] Failed to retrieve Ngrok tunnel. Is it running?"
        kill $NGROK_PID
        exit 1
    fi

    HOSTPORT=${PUBLIC_URL#tcp://}
    HOST=$(echo $HOSTPORT | cut -d: -f1)
    PORT=$(echo $HOSTPORT | cut -d: -f2)
    USERNAME=$(whoami)
    
    echo ""
    echo "[🔐] Use this SSH command from another computer:"
    echo ""
    echo "ssh $USERNAME@$HOST -p $PORT"
    echo ""
    echo "[✅] Username auto-filled as: $USERNAME"
}

# Main execution
check_ngrok
check_ssh_server
start_ngrok
get_ngrok_url
