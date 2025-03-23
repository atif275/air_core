#!/bin/bash

# Define ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

# ==================================================================
# start_serveo.sh
#
# This script starts an SSH reverse tunnel using Serveo,
# captures the allocated port, and prints the SSH connection
# command that Computer A (your friend) can use.
# ==================================================================

# ------------------------------------------------------------------
# Get the current username
# ------------------------------------------------------------------
USER_NAME=$(whoami)
SERVEON_HOST="serveo.net"

# ------------------------------------------------------------------
# Create a temporary file to capture Serveo's output
# ------------------------------------------------------------------
TMPFILE=$(mktemp)

# ------------------------------------------------------------------
# Start the SSH tunnel in the background and redirect output
# ------------------------------------------------------------------
echo -e "${CYAN}Starting Serveo tunnel...${RESET}"
ssh -o ExitOnForwardFailure=yes -R 0:localhost:22 $SERVEON_HOST > "$TMPFILE" 2>&1 &
SSH_PID=$!

echo -e "\n${GREEN}Serveo tunnel process started (PID: $SSH_PID)${RESET}"
echo -e "${YELLOW}Waiting for Serveo to allocate a port...${RESET}\n"

# ------------------------------------------------------------------
# Wait until the output contains "Allocated port"
# ------------------------------------------------------------------
while true; do
    if grep -q "Allocated port" "$TMPFILE"; then
        break
    fi
    sleep 1
done

# ------------------------------------------------------------------
# Extract the allocated port from the output.
# ------------------------------------------------------------------
ALLOCATED_PORT=$(grep "Allocated port" "$TMPFILE" | head -n 1 | sed -E 's/Allocated port ([0-9]+) for remote forward.*/\1/')
echo -e "\n${GREEN}Allocated port is: ${ALLOCATED_PORT}${RESET}\n"

# ------------------------------------------------------------------
# Print the SSH command for Computer A.
# ------------------------------------------------------------------
echo -e "${CYAN}Share the following command with your friend (Computer A):${RESET}\n"
echo -e "${YELLOW}ssh -p ${ALLOCATED_PORT} ${USER_NAME}@${SERVEON_HOST}${RESET}\n"

# ------------------------------------------------------------------
# Optionally, display the Serveo output
# ------------------------------------------------------------------
echo -e "${CYAN}Tunnel output (press Ctrl+C to exit):${RESET}"
tail -f "$TMPFILE"
