# import google.generativeai as genai  <-- Removed
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import random
from .memory_service import memory_service
from .user_service import user_service
from .models import Tier, TIER_LIMITS
from loguru import logger
import asyncio
from google.api_core import exceptions
from pydantic import BaseModel
from typing import Optional
from .prompts import get_system_prompt
from datetime import datetime

class NexResponse(BaseModel):
    reply: str
    memory: Optional[str] = None

class NexService:
    def __init__(self):
        self.model_name = "gemini-2.0-flash"

    async def interact(self, uid: str, user_input: str, conversation_history: Optional[list[dict]] = None):
        # ... (rest of method interact remains same until _generate_with_retry call) ...
        # 1. Get user state
        user_state = await user_service.get_user_state(uid)
        
        # 2. Check limits
        msg_limit = TIER_LIMITS[user_state.tier]["messages"]
        if user_state.messages_used_today >= msg_limit:
            return "LIMIT_REACHED", user_state.tier

        # 3. Retrieve memories
        memories = await memory_service.get_all_memory_content(uid)

        # 4. Check Memory Availability
        mem_limit = TIER_LIMITS[user_state.tier]["memory"]
        can_add_memory = user_state.memory_used < mem_limit
        
        # Format history
        history_str = ""
        if conversation_history:
            for msg in conversation_history:
                role = msg.get("role", "User").upper()
                content = msg.get("content", "")
                history_str += f"{role}: {content}\n"

        # 5. Construct Prompt
        # Minimal tokens, clear instructions.
        current_time = datetime.now().strftime("%A, %B %d, %Y, %H:%M:%S")
        system_prompt = get_system_prompt(memories, history_str, user_input, can_add_memory, current_time)
        
        # Define schema manually to avoid "default" field issues in Pydantic conversion
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "reply": {"type": "STRING"},
                "memory": {"type": "STRING", "nullable": True}
            },
            "required": ["reply"]
        }

        try:
            # We don't use history here as per NEX philosophy (no threads)
            # but we pass memories as context
            response_json = await self._generate_with_retry(
                system_prompt,
                response_schema=response_schema
            )
            
            # Parse response
            import json
            try:
                data = json.loads(response_json)
                reply = data.get("reply", "")
                memory_content = data.get("memory")
            except json.JSONDecodeError:
                # Fallback if something went wrong
                logger.error(f"Failed to parse JSON from Gemini: {response_json}")
                reply = str(response_json)
                memory_content = None

            if reply == "RATE_LIMITED":
                return "RATE_LIMITED", user_state.tier

            # 6. Store Memory if generated and allowed
            if memory_content and can_add_memory:
                 await memory_service.add_memory(uid, memory_content)

            # 7. Increment usage
            await user_service.increment_message_usage(uid)
            
            return reply, user_state.tier
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "ERROR", user_state.tier

    async def _generate_with_retry(self, prompt: str, response_schema=None, max_retries: int = 5) -> str:
        """
        Generates content with exponential backoff retry logic for rate limits.
        """
        model = GenerativeModel(self.model_name)
        base_delay = 2
        
        generation_config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=response_schema
        ) if response_schema else None

        for attempt in range(max_retries):
            try:
                # User requested synchronous generate_content. 
                # Running in thread to avoid blocking the event loop.
                response = await asyncio.to_thread(
                    model.generate_content, 
                    prompt, 
                    generation_config=generation_config
                )
                return response.text
            except exceptions.ResourceExhausted as e:
                jitter = random.uniform(0, 1)
                wait_time = (base_delay * (2 ** attempt)) + jitter
                logger.warning(f"Gemini rate limit hit. Retrying in {wait_time:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            except exceptions.ServiceUnavailable as e:
                jitter = random.uniform(0, 1)
                wait_time = (base_delay * (2 ** attempt)) + jitter
                logger.warning(f"Gemini service unavailable. Retrying in {wait_time:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            except Exception as e:
                # For other errors, re-raise immediately
                logger.error(f"Non-retriable Gemini error: {e}")
                raise e
        
        logger.error(f"Gemini rate limit retries exhausted after {max_retries} attempts.")
        return "RATE_LIMITED"

nex_service = NexService()
domestic_ai = nex_service  # Alias if needed
