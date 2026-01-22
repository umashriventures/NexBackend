import uvicorn
from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
load_dotenv()
from .api_gateway import websocket_endpoint

app = FastAPI(
    title="NEX Backend Service",
    description="Minimal viable product for the NEX Backend Service with WebSocket streaming, JWT authentication, and load‑testing harness.",
    version="0.1.0",
)

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    # The websocket_endpoint will handle authentication via an initial "auth" message.
    await websocket_endpoint(websocket)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
