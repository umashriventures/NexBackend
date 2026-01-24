import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
# from .api_gateway import websocket_endpoint  # removed per request
from .livekit_token import generate_livekit_token
from pydantic import BaseModel

app = FastAPI(
    title="NEX Backend Service",
    description="Minimal viable product for the NEX Backend Service with WebSocket streaming, JWT authentication, and load‑testing harness.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket endpoint removed per request

class TokenRequest(BaseModel):
    room_name: str
    identity: str

@app.post("/livekit/token")
async def get_livekit_token(request: TokenRequest):
    """
    Generate a LiveKit token for the given room and identity.
    """
    token = generate_livekit_token(request.room_name, request.identity)
    return {"token": token}

class ChatRequest(BaseModel):
    message: str
    conversation_id: str

@app.post("/chat/text")
async def chat_text(request: ChatRequest):
    """
    Text-based chat endpoint that reuses the cognitive pipeline.
    """
    from .orchestrator import ConversationOrchestrator
    orchestrator = ConversationOrchestrator()
    response_tokens = []
    async for token in orchestrator.process_turn("default_user", request.message):
        if token != "<END>":
            response_tokens.append(token)
    
    return {"response": "".join(response_tokens)}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
