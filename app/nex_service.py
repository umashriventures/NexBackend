import google.generativeai as genai
import random
from .memory_service import memory_service
from .user_service import user_service
from .models import Tier, TIER_LIMITS
from loguru import logger
import asyncio
from google.api_core import exceptions

class NexService:
    def __init__(self):
        self.model_name = "gemini-2.0-flash"

    async def interact(self, uid: str, user_input: str):
        # 1. Get user state
        user_state = await user_service.get_user_state(uid)
        
        # 2. Check limits
        limit = TIER_LIMITS[user_state.tier]["messages"]
        if user_state.messages_used_today >= limit:
            return "LIMIT_REACHED", user_state.tier

        # 3. Retrieve memories
        memories = await memory_service.get_all_memory_content(uid)
        
        # 4. Construct Prompt
        system_prompt = f"""
        You are NEX, a voice-first AI interface. 
        You have no concept of conversations or threads.
        This is a single continuous interaction context.
        
        LONG-TERM MEMORIES:
        {memories if memories else "None."}
        
        Rules:
        - Be concise and helpful.
        - Respond naturally as a presence, not just a tool.
        """
        
        try:
            # We don't use history here as per NEX philosophy (no threads)
            # but we pass memories as context
            reply = await self._generate_with_retry(
                f"{system_prompt}\n\nUser: {user_input}"
            )
            
            if reply == "RATE_LIMITED":
                return "RATE_LIMITED", user_state.tier

            # 5. Increment usage
            await user_service.increment_message_usage(uid)
            
            return reply, user_state.tier
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "ERROR", user_state.tier

    async def _generate_with_retry(self, prompt: str, max_retries: int = 5) -> str:
        """
        Generates content with exponential backoff retry logic for rate limits.
        """
        model = genai.GenerativeModel(self.model_name)
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                # User requested synchronous generate_content. 
                # Running in thread to avoid blocking the event loop.
                response = await asyncio.to_thread(model.generate_content, prompt)
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
