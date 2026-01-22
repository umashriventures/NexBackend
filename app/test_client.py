import os
import asyncio
import json
import jwt
import datetime
import websockets

# Helper to generate JWT token (same logic as in README)
def generate_token() -> str:
    secret = os.getenv('JWT_SECRET', 'supersecretkey')
    payload = {
        "user_id": "test_user",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, secret, algorithm='HS256')

async def test_ws():
    uri = "ws://localhost:8000/ws"
    token = generate_token()
    async with websockets.connect(uri) as ws:
        # Send auth message
        await ws.send(json.dumps({"type": "auth", "token": token}))
        print("<-", await ws.recv())  # should be authenticated status
        # Send audio chunks
        await ws.send(json.dumps({"type": "audio", "chunk": "hello "}))
        print("<-", await ws.recv())
        await ws.send(json.dumps({"type": "audio", "chunk": "world"}))
        print("<-", await ws.recv())
        # End of transcript
        await ws.send(json.dumps({"type": "end"}))
        # Receive remaining messages until the server signals completion
        try:
            while True:
                msg = await ws.recv()
                print("<-", msg)
                data = json.loads(msg)
                if data.get("type") == "status_update" and data.get("status") == "completed":
                    print("Prompt complete. Closing connection.")
                    break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
