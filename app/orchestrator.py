import asyncio
from typing import AsyncGenerator

from .llm_runtime import stream_llm_tokens
from .event_streamer import LLMTokenEvent

async def process_final_transcript(user_id: str, transcript: str) -> AsyncGenerator[LLMTokenEvent, None]:
    """Process the final transcript and stream LLM tokens.
    For the MVP this simply echoes the transcript word by word as tokens.
    """
    # In a real implementation we would classify intent, manage belief state, etc.
    async for token in stream_llm_tokens(transcript):
        yield LLMTokenEvent(token=token)
