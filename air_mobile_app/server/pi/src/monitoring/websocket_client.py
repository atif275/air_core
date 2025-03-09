import asyncio
import websockets
import json

async def connect_to_monitor():
    # Update the URI to use the Pi's IP address
    uri = "ws://192.168.1.10:8765"  # Replace with your Pi's IP
    
    try:
        async with websockets.connect(uri, ping_interval=None) as websocket:
            # Request full status
            await websocket.send(json.dumps({
                "command": "get_full_status"
            }))
            
            # Receive and print updates
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    print(f"Received update: {data}")
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                    break
    except Exception as e:
        print(f"Connection error: {e}")

def run_client():
    try:
        asyncio.run(connect_to_monitor())
    except KeyboardInterrupt:
        print("\nClient stopped by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_client() 