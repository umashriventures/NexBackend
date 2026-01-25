import logging
from pydantic import BaseModel
from typing import List
from .memory_graph import GraphitiMemory

logger = logging.getLogger(__name__)

class MemoryNode(BaseModel):
    id: str
    content: str
    metadata: dict

class MemoryEngine:
    def __init__(self):
        # Initialize Milvus connection here if needed
        self.connected = False
        self.graphiti = GraphitiMemory()

    async def connect(self):
        """
        Initialize connections for all memory systems.
        """
        logger.info("Initializing MemoryEngine connections...")
        try:
            await self.graphiti.connect()
            self.connected = True
            logger.info("MemoryEngine connections initialized successfully.")
        except Exception as e:
            self.connected = False
            logger.error(f"MemoryEngine failed to initialize: {e}")
            raise e

    async def retrieve_relevant_nodes(self, user_id: str, query: str) -> List[MemoryNode]:
        """ Hybrid Query: Vector DB (Milvus) + Knowledge Graph (Graphiti). """
        logger.info(f"Retrieving hybrid memory for user {user_id}: {query}")
        
        # 1. Search Knowledge Graph (Graphiti/Neo4j)
        graph_context = await self.graphiti.search(user_id, query)
        
        # 2. Search Vector DB (Milvus) - Stubbed for now
        vector_nodes = [] 
        
        # Merge results into a list of MemoryNodes
        nodes = []
        if graph_context:
            nodes.append(MemoryNode(id="graph_0", content=graph_context, metadata={"source": "graph"}))
        
        nodes.extend(vector_nodes)
        return nodes

    async def store_memory_node(self, user_id: str, content: str, metadata: dict):
        """ Store a new memory unit in both systems. """
        # 1. Ingest into Graphiti (Async is handled by orchestrator calling this)
        await self.graphiti.add_episode(user_id, content)
        
        # 2. Store in Milvus (Stubbed)
        logger.info(f"Storing vector memory node: {content[:50]}...")
