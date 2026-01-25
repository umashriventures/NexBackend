import os
import logging
from typing import List, Optional
from graphiti_core import Graphiti
from graphiti_core.driver.neo4j_driver import Neo4jDriver
from graphiti_core.llm_client.gemini_client import GeminiClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig
from graphiti_core.cross_encoder.gemini_reranker_client import GeminiRerankerClient
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class GraphNode(BaseModel):
    id: str
    label: str
    properties: dict

class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str

class GraphitiMemory:
    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        
        self.driver = None
        self.graphiti = None
        self.connected = False

    async def connect(self):
        """
        Establish connection to Neo4j and initialize Graphiti.
        """
        logger.info(f"Connecting to Neo4j at {self.neo4j_uri}...")
        try:
            # Configure Gemini clients
            llm_config = LLMConfig(api_key=self.google_api_key)
            llm_client = GeminiClient(config=llm_config)
            
            # Using text-embedding-004 as text-embedding-001 is deprecated/not found
            embedder_config = GeminiEmbedderConfig(
                api_key=self.google_api_key,
                embedding_model="models/text-embedding-004"
            )
            embedder = GeminiEmbedder(config=embedder_config)
            
            reranker = GeminiRerankerClient(config=llm_config)

            self.driver = Neo4jDriver(uri=self.neo4j_uri, user=self.neo4j_user, password=self.neo4j_password)
            
            # Verify Neo4j connection using the internal client
            async with self.driver.client.session() as session:
                await session.run("RETURN 1")
            
            self.graphiti = Graphiti(
                graph_driver=self.driver,
                llm_client=llm_client,
                embedder=embedder,
                cross_encoder=reranker
            )
            self.connected = True
            logger.info("Successfully connected to Neo4j and initialized Graphiti.")
        except Exception as e:
            self.connected = False
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise e

    async def add_episode(self, user_id: str, content: str):
        """
        Ingest a conversation turn into the graph as an episode.
        """
        if not self.connected:
            return
        
        import datetime
        try:
            # Graphiti's add_episode signature: (name, episode_body, source_description, reference_time, ...)
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
        """
        Search the graph for facts related to the query.
        """
        if not self.connected:
            return ""
        
        try:
            # Graphiti's search signature: (query, center_node_uuid, group_ids, ...)
            results = await self.graphiti.search(query, group_ids=[user_id])
            # Format the graph results (nodes/edges) into a readable context string
            # This is a simplified version; Graphiti returns a rich object.
            context = str(results)
            return context
        except Exception as e:
            logger.error(f"Error searching Graphiti: {e}")
            return ""

    async def get_graph_data(self, user_id: str) -> dict:
        """
        Retrieve the full graph for a user (debug/search endpoint).
        """
        if not self.connected:
            return {}
        
        try:
            # Simplified retrieval for debug
            return {"nodes": [], "edges": []} 
        except Exception as e:
            logger.error(f"Error getting graph data: {e}")
            return {}
