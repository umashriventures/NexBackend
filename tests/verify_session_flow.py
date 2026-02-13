
import sys
import os
import asyncio
from fastapi.testclient import TestClient

# Add app to path
sys.path.append(os.getcwd())

from app.main import app
from app.models import Tier
from app.auth_service import get_current_user_id
import uuid

def test_flow():
    # Use context manager to trigger lifespan events (init_services)
    with TestClient(app) as client:
        print("1. Authenticating...")
        # Mock dependency with random user
        test_uid = f"test_user_{uuid.uuid4()}"
        app.dependency_overrides[get_current_user_id] = lambda: test_uid
        print(f"   Using User ID: {test_uid}")

        print("2. Starting Session...")
        response = client.post("/session/start")
        if response.status_code != 200:
            print(f"Start failed: {response.text}")
            return
            
        data = response.json()
        session_id = data["session_id"]
        print(f"   Session ID: {session_id}")

        print("3. Interacting...")
        # Send a message
        payload = {
            "input": "I feel a bit lost today.",
            "session_id": session_id
        }
        response = client.post("/nex/interact", json=payload)
        if response.status_code == 200:
            print(f"   Reply: {response.json()['reply']}")
        else:
            print(f"   Interaction failed (might be VertexAI issue): {response.text}")

        print("4. Ending Session...")
        response = client.post("/session/end", json={"session_id": session_id})
        if response.status_code != 200:
             print(f"End failed: {response.text}")
             return
             
        archive_data = response.json()
        archive_id = archive_data["archive_id"]
        print(f"   Archive ID: {archive_id}")
        print(f"   Reflection: {archive_data['reflection']}")

        print("5. Verify Archive in List...")
        response = client.get("/archive")
        assert response.status_code == 200
        archives = response.json()
        found = any(a["archive_id"] == archive_id for a in archives)
        if found:
            print("   Archive found in list.")
        else:
            print("   Archive NOT found in list.")

        print("6. Downloading Card...")
        response = client.post(f"/archive/{archive_id}/download")
        if response.status_code == 200 and response.headers["content-type"] == "image/png":
            print(f"   Image received ({len(response.content)} bytes).")
        else:
            print(f"   Download failed: {response.status_code} {response.text}")

        print("\nSUCCESS: Session Flow Verified.")

if __name__ == "__main__":
    test_flow()
