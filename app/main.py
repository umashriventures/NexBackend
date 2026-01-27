import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

from .logging_config import setup_logging, logging_middleware
from loguru import logger
from contextlib import asynccontextmanager
from .services import services

# Import Routers
from .routers import auth, nex, memory, subscription

# Initialize production-grade logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await services.init_services()
    yield
    # Shutdown logic (if any)

app = FastAPI(
    title="NEX Backend API",
    description="""
    NEX is a voice-first AI interface with a single continuous interaction context.
    """,
    version="3.0.0",
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

# Add logging middleware
@app.middleware("http")
async def add_logging_middleware(request, call_next):
    return await logging_middleware(request, call_next)

# Include Routers
app.include_router(auth.router)
app.include_router(nex.router)
app.include_router(memory.router)
app.include_router(subscription.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
