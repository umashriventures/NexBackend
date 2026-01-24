import httpx
import json
import asyncio
import sys

BASE_URL = "http://localhost:8000"

async def test_livekit_token():
    print("\n--- Testing LiveKit Token Endpoint ---")
    data = {
        "room_name": "test-room",
        "identity": "test-user"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/livekit/token", json=data)
            if response.status_code == 200:
                token = response.json().get("token")
                print(f"✅ Success! Token received: {token[:30]}...")
                return token
            else:
                print(f"❌ Failed! Status Code: {response.status_code}")
                print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error connecting to backend: {e}")
    return None

import time

async def test_chat_text():
    print("\n--- Testing Chat Text Endpoint ---")
    data = {
        "message": "Hello NEX, do you remember me?",
        "conversation_id": "test-conv-123"
    }
    start_time = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{BASE_URL}/chat/text", json=data)
            duration = time.perf_counter() - start_time
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success! Duration: {duration:.2f}s")
                print(f"Response: {result.get('response')}")
            else:
                print(f"❌ Failed! Status Code: {response.status_code}")
                print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ Error connecting to backend: {e}")

async def main():
    print("🚀 Starting NEX Backend Verification...")
    print(f"Target URL: {BASE_URL}")
    
    await test_livekit_token()
    await test_chat_text()
    
    print("\nVerification complete.")

if __name__ == "__main__":
    asyncio.run(main())
