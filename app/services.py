import logging
from .memory_engine import MemoryEngine

logger = logging.getLogger(__name__)

class Services:
    def __init__(self):
        self.memory_engine = None

    async def init_services(self):
        """
        Initialize all core services and verify connections.
        """
        logger.info("Starting NEX core services...")
        
        # Initialize Memory Engine (Neo4j/Graphiti + Milvus)
        self.memory_engine = MemoryEngine()
        try:
            await self.memory_engine.connect()
            logger.info("Neo4j connection verified on service start.")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to connect to Neo4j on startup: {e}")
            # We might want to exit here if Neo4j is critical, 
            # but let's allow starting with limited functionality for now
            # sys.exit(1)

services = Services()

def get_memory_engine() -> MemoryEngine:
    return services.memory_engine
