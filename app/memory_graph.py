import os
import yaml
import logging
import torch
import asyncio
from typing import List, Optional, Any, Iterable
from pydantic import BaseModel
from graphiti_core import Graphiti
from graphiti_core.driver.neo4j_driver import Neo4jDriver
from graphiti_core.llm_client import LLMClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.client import EmbedderClient, EmbedderConfig
from sentence_transformers import SentenceTransformer
from .llm_runtime import get_llm_instance

logger = logging.getLogger(__name__)

# Load models config
MODELS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models.yml")
with open(MODELS_CONFIG_PATH, "r") as f:
    models_config = yaml.safe_load(f)

LLM_REPO = models_config["default_llm"]["repo"]
EMBEDDER_REPO = models_config["default_embedder"]["repo"]

class HuggingFaceLLMClient(LLMClient):
    """
    Custom LLM client for Graphiti using local Llama GGUF instance.
    """
    def __init__(self, config: LLMConfig | None = None, cache: bool = False):
        super().__init__(config, cache)
        logger.info("Using shared Llama GGUF instance for Graphiti...")
        self.llm = None # Retrieve on-demand

    async def _generate_response(
        self,
        messages: List[Any],
        response_model: Optional[type[BaseModel]] = None,
        max_tokens: int = 500,
        model_size: Any = None,
    ) -> dict[str, Any]:
        if self.llm is None:
            self.llm = get_llm_instance()
            
        # Convert Graphiti messages to Llama format
        llama_messages = [{"role": m.role.value if hasattr(m.role, 'value') else str(m.role), "content": m.content} for m in messages]
        
        response = self.llm.create_chat_completion(
            messages=llama_messages,
            max_tokens=max_tokens,
            temperature=0.1
        )
        output_text = response["choices"][0]["message"]["content"]
        
        return {"text": output_text}

class HuggingFaceEmbedder(EmbedderClient):
    """
    Custom Embedder client for Graphiti using local SentenceTransformers.
    """
    def __init__(self, config: EmbedderConfig | None = None):
        self.config = config or EmbedderConfig()
        logger.info(f"Initializing HuggingFaceEmbedder with {EMBEDDER_REPO}...")
        self.model = SentenceTransformer(EMBEDDER_REPO)

    async def create(
        self, input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]
    ) -> list[float] | list[list[float]]:
        if isinstance(input_data, str):
            embeddings = self.model.encode([input_data])
            return embeddings[0].tolist()
        elif isinstance(input_data, list) and isinstance(input_data[0], str):
            embeddings = self.model.encode(input_data)
            return embeddings.tolist()
        else:
            raise ValueError("Unsupported input format for HuggingFaceEmbedder")

class GraphitiMemory:
    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        self.driver = None
        self.graphiti = None
        self.connected = False

    async def connect(self):
        """
        Establish connection to Neo4j and initialize Graphiti with HuggingFace/Llama clients.
        """
        logger.info(f"Connecting to Neo4j at {self.neo4j_uri}...")
        try:
            # Configure clients
            llm_client = HuggingFaceLLMClient()
            embedder = HuggingFaceEmbedder()
            
            self.driver = Neo4jDriver(
                uri=self.neo4j_uri, 
                user=self.neo4j_user, 
                password=self.neo4j_password
            )
            
            # Verify Neo4j connection
            async with self.driver.client.session() as session:
                await session.run("RETURN 1")
            
            self.graphiti = Graphiti(
                graph_driver=self.driver,
                llm_client=llm_client,
                embedder=embedder
            )
            self.connected = True
            logger.info("Successfully connected to Neo4j and initialized Graphiti with Llama.cpp.")
        except Exception as e:
            self.connected = False
            logger.error(f"Failed to connect to Neo4j or init Llama clients: {e}")
            raise e

    async def add_episode(self, user_id: str, content: str):
        if not self.connected:
            return
        
        import datetime
        try:
            await self.graphiti.add_episode(
                name=user_id,
                episode_body=content,
                source_description="Conversation turn",
                reference_time=datetime.datetime.now(),
                group_id=user_id
            )
            logger.info(f"Added episode for user {user_id}")
        except Exception as e:
            logger.error(f"Error adding episode to Graphiti: {e}")

    async def search(self, user_id: str, query: str) -> str:
        if not self.connected:
            return ""
        
        try:
            results = await self.graphiti.search(query, group_ids=[user_id])
            return str(results)
        except Exception as e:
            logger.error(f"Error searching Graphiti: {e}")
            return ""

    async def get_graph_data(self, user_id: str) -> dict:
        if not self.connected:
            return {}
        return {"nodes": [], "edges": []} 
