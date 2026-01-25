import asyncio
import logging
from typing import AsyncGenerator, Optional
from .llm_runtime import stream_llm_tokens
from .event_streamer import LLMTokenEvent
from .memory_engine import MemoryEngine, MemoryNode

logger = logging.getLogger(__name__)

from .services import services

from fastapi import BackgroundTasks

class ConversationOrchestrator:
    def __init__(self):
        self.memory_engine = services.memory_engine

    async def _store_memory_background(self, user_id: str, content: str, transcript: str):
        """Internal helper for background memory storage."""
        await self.memory_engine.store_memory_node(
            user_id=user_id,
            content=content,
            metadata={"transcript": transcript}
        )

    async def process_turn(
        self, 
        user_id: str, 
        transcript: str, 
        background_tasks: Optional[BackgroundTasks] = None
    ) -> AsyncGenerator[str, None]:
        """
        Processes a conversation turn with optimized routing:
        1. Decision: Needs past memory?
        2. Context: Selective retrieval.
        3. Response: Generation & Streaming.
        4. Memory: Consolidation with one-liner.
        """
        from .llm_runtime import get_routing_decision, stream_llm_tokens, get_memory_one_liner
        
        # 1. Routing Decision
        decision = await get_routing_decision(transcript)
        logger.info(f"Routing Decision: needs_past_memory={decision.needs_past_memory}, reasoning={decision.reasoning}")

        context = ""
        full_response = []

        # 2. Selective Memory Retrieval (Sequential)
        if decision.needs_past_memory:
            nodes = await self.memory_engine.retrieve_relevant_nodes(user_id, transcript)
            if nodes:
                context = "\n".join([n.content for n in nodes])
                logger.info(f"Retrieved {len(nodes)} context nodes.")

        # 3. Response Generation
        if not decision.needs_past_memory and decision.standalone_answer:
            # Optimal path: Use the pre-generated standalone answer
            for token in decision.standalone_answer.split():
                yield token + " "
                full_response.append(token + " ")
            yield "<END>"
        else:
            # Standard path: Stream tokens from LLM (potentially with context)
            async for token in stream_llm_tokens(transcript, context=context):
                if token != "<END>":
                    full_response.append(token)
                yield token

        if full_response:
            response_text = "".join(full_response)
            
            # Use the one-liner from decision or generate a new one
            one_liner = decision.memory_one_liner
            if not one_liner or decision.needs_past_memory:
                one_liner = await get_memory_one_liner(transcript, response_text)

            if background_tasks:
                background_tasks.add_task(
                    self._store_memory_background,
                    user_id,
                    one_liner,
                    transcript
                )
            else:
                # Fallback to local async task if for some reason background_tasks is not provided
                asyncio.create_task(
                    self._store_memory_background(user_id, one_liner, transcript)
                )

async def process_final_transcript(user_id: str, transcript: str) -> AsyncGenerator[LLMTokenEvent, None]:
    """ Bridge for the existing WebSocket/Text API. """
    orchestrator = ConversationOrchestrator()
    async for token in orchestrator.process_turn(user_id, transcript):
        yield LLMTokenEvent(token=token)
