import os
import logging
import asyncio
from typing import List, Any, Optional
import google.generativeai as genai
from pydantic import BaseModel
import datetime

from graphiti_core import Graphiti
from graphiti_core.driver.neo4j_driver import Neo4jDriver
from graphiti_core.llm_client.gemini_client import GeminiClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig

logger = logging.getLogger(__name__)

# Configure Gemini (legacy SDK for other parts of the app if needed)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

class GraphitiMemory:
    def __init__(self):
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        self.api_key = GOOGLE_API_KEY
        
        self.driver = None
        self.graphiti = None
        self.connected = False

    async def connect(self):
        """
        Establish connection to Neo4j and initialize Graphiti with official Gemini clients.
        """
        logger.info(f"Connecting to Neo4j at {self.neo4j_uri}...")
        try:
            self.driver = Neo4jDriver(
                uri=self.neo4j_uri, 
                user=self.neo4j_user, 
                password=self.neo4j_password
            )
            
            # Verify Neo4j connection
            async with self.driver.client.session() as session:
                await session.run("RETURN 1")
            
            # Configure official Graphiti Gemini clients
            llm_config = LLMConfig(
                api_key=self.api_key,
                model="gemini-2.0-flash"
            )
            llm_client = GeminiClient(config=llm_config)
            
            embed_config = GeminiEmbedderConfig(
                api_key=self.api_key,
                embedding_model="text-embedding-004"
            )
            embedder = GeminiEmbedder(config=embed_config)
            
            self.graphiti = Graphiti(
                graph_driver=self.driver,
                llm_client=llm_client,
                embedder=embedder
            )
            self.connected = True
            logger.info("Successfully connected to Neo4j and initialized Graphiti with official Gemini clients.")
        except Exception as e:
            self.connected = False
            logger.error(f"Failed to connect to Neo4j or init Graphiti: {e}")
    
    # ... Shim methods for orchestrator usage compatibility ...
    
    async def store_memory_node(self, user_id: str, content: str, metadata: dict = None):
         await self.add_episode(user_id, content)

    async def retrieve_relevant_nodes(self, user_id: str, query: str):
        if not self.connected:
            return []
        try:
            results = await self.graphiti.search(query, group_ids=[user_id])
            
            class StartNode:
                def __init__(self, content):
                    self.content = content
            
            if isinstance(results, list):
                 final_results = []
                 for r in results:
                     if isinstance(r, str):
                         final_results.append(StartNode(r))
                     elif hasattr(r, 'content'):
                         final_results.append(r)
                     else:
                         final_results.append(StartNode(str(r)))
                 return final_results
            return results 
        except Exception as e:
            logger.error(f"Error retrieving nodes: {e}")
            return []

    async def add_episode(self, user_id: str, content: str):
        if not self.connected:
            logger.warning("Graphiti not connected, skipping episode storage.")
            return
        
        try:
            await self.graphiti.add_episode(
                name=user_id,
                episode_body=content,
                source_description="Conversation turn",
                reference_time=datetime.datetime.now(),
                group_id=user_id
            )
            logger.info(f"Successfully added episode to Graphiti for user: {user_id}")
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
        # Stub for getting graph data if needed by UI
        return {"nodes": [], "edges": []}
