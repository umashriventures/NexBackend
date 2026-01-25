import os
import asyncio
from typing import AsyncGenerator
import google.generativeai as genai

# Configure genai with the API key from environment
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

import json
import logging
from .cognition import RoutingDecision
from . import prompts

logger = logging.getLogger(__name__)

# Model config
MODEL_NAME = "gemini-2.5-flash" 

async def get_routing_decision(transcript: str) -> RoutingDecision:
    """
    Determine if the query needs past memory and provide a standalone answer if possible.
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = prompts.ROUTING_PROMPT.format(transcript=transcript)
        
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        
        return RoutingDecision(**data)
    except Exception as e:
        logger.error(f"Error in get_routing_decision: {e}")
        return RoutingDecision(needs_past_memory=False, memory_one_liner="User asked a question.", reasoning="Error fallback")




async def stream_llm_tokens(prompt: str, context: str = "") -> AsyncGenerator[str, None]:
    """
    Stream tokens from Gemini for the given prompt and optional context.
    """
    if not api_key:
        yield "Error: GOOGLE_API_KEY not set."
        return

    try:
        context_str = context if context else "No past memory provided."
        system_instruction = prompts.NEX_SYSTEM_INSTRUCTION.format(context_str=context_str)
        model = genai.GenerativeModel(MODEL_NAME, system_instruction=system_instruction)
        response = await model.generate_content_async(prompt, stream=True)
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text
                    
        yield "<END>"
    except Exception as e:
        yield f"Error calling Gemini: {str(e)}"
        yield "<END>"

async def get_memory_one_liner(transcript: str, response: str) -> str:
    """
    Generate a one-liner summary of the interaction for memory.
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = prompts.MEMORY_ONE_LINER_PROMPT.format(transcript=transcript, response=response)
        res = await model.generate_content_async(prompt)
        return res.text.strip()
    except Exception as e:
        logger.error(f"Error generating memory one-liner: {e}")
        return f"User said: {transcript[:50]}"
