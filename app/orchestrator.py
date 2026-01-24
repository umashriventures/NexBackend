import asyncio
import logging
from typing import AsyncGenerator, List, Optional
from .llm_runtime import stream_llm_tokens
from .event_streamer import LLMTokenEvent
from .cognition import CognitiveState, BeliefState, Intent
from .memory_engine import MemoryEngine, MemoryNode

logger = logging.getLogger(__name__)

class ConversationOrchestrator:
    def __init__(self):
        self.memory_engine = MemoryEngine()

    async def _analyze_cognition(self, transcript: str) -> CognitiveState:
        """
        Analyze the transcript to produce intent and belief state.
        Now uses the real Gemini call.
        """
        from .llm_runtime import generate_thought
        return await generate_thought(transcript)

    async def process_turn(self, user_id: str, transcript: str) -> AsyncGenerator[str, None]:
        """
        Processes a stabilized turn:
        1. Cognition (Intent + Belief)
        2. Memory Gate
        3. LLM Generation
        """
        # 1. Cognitive Orchestration
        state = await self._analyze_cognition(transcript)
        
        # 2. Selective Memory Retrieval
        context = ""
        if await self.memory_engine.decide_retrieval(state):
            nodes = await self.memory_engine.retrieve_relevant_nodes(transcript)
            if nodes:
                context = "\n".join([n.content for n in nodes])
                logger.info(f"Retrieved {len(nodes)} memory nodes.")

        # 3. LLM Execution Planning & Generation
        # For simplicity, we prepend context to the prompt
        prompt = f"Context: {context}\n\nUser: {transcript}" if context else transcript
        
        async for token in stream_llm_tokens(prompt):
            yield token

async def process_final_transcript(user_id: str, transcript: str) -> AsyncGenerator[LLMTokenEvent, None]:
    """ Bridge for the existing WebSocket/Text API. """
    orchestrator = ConversationOrchestrator()
    async for token in orchestrator.process_turn(user_id, transcript):
        yield LLMTokenEvent(token=token)
