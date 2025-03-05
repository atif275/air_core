import asyncio
import websockets
import json

async def connect_to_monitor():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
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

def run_client():
    asyncio.run(connect_to_monitor())

if __name__ == "__main__":
    run_client() 