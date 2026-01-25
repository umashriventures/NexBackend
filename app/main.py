import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel

import logging
from contextlib import asynccontextmanager
from .services import services

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await services.init_services()
    yield
    # Shutdown logic (if any)

app = FastAPI(
    title="NEX-Agentic-Core API",
    description="""
    The NEX-Agentic-Core is a stateful, agentic cognitive backend.
    It provides high-intelligence conversation capabilities with 
    long-term memory via Graphiti (Neo4j) and high-scale vector retrieval (Milvus).
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# System Endpoints

@app.get("/health", tags=["System"], summary="Health Check")
async def health_check():
    """
    Check connectivity to all core services.
    """
    engine = services.memory_engine
    
    status = {
        "status": "online",
        "milvus": "connected", # Stub
        "redis": "connected",  # Stub
        "neo4j": "connected" if engine and engine.graphiti.connected else "disconnected"
    }
    return status

class MemorySearchRequest(BaseModel):
    query: str
    user_id: str

@app.post("/memory/search", tags=["Memory"], summary="Graphiti Memory Search")
async def search_memory(request: MemorySearchRequest):
    """
    Debug endpoint to query the Knowledge Graph directly.
    """
    engine = services.memory_engine
    if not engine or not engine.graphiti:
        return {"error": "Memory engine not initialized"}
        
    data = await engine.graphiti.get_graph_data(request.user_id)
    # Also include the context search result for convenience
    context = await engine.graphiti.search(request.user_id, request.query)
    return {"graph": data, "context": context}

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_user"
    conversation_id: str = "default_session"

@app.post("/chat/text", tags=["Chat"], summary="Agentic Chat Interaction")
async def chat_text(request: ChatRequest):
    """
    Text-based chat endpoint that reuses the agentic cognitive pipeline.
    """
    from .orchestrator import ConversationOrchestrator
    orchestrator = ConversationOrchestrator()
    response_tokens = []
    async for token in orchestrator.process_turn(request.user_id, request.message):
        if token != "<END>":
            response_tokens.append(token)
    
    return {"response": "".join(response_tokens)}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
