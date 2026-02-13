# import google.generativeai as genai  <-- Removed
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import random
from .memory_service import memory_service
from .user_service import user_service
from .session_service import session_service
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

    async def interact(self, uid: str, session_id: str, user_input: str):
        """
        Interacts with NEX within a specific sessionContext.
        """
        # 1. Get Session & Validate
        session = await session_service.get_active_session(uid)
        if not session or session.session_id != session_id:
            # If session is invalid or mismatch, return error.
            # Client should have started a session first.
            return "SESSION_INVALID", Tier.TIER_1

        # 2. Add User Message to Session
        await session_service.add_message(session_id, "user", user_input)

        # 3. Get user state & Check Global Limits
        user_state = await user_service.get_user_state(uid)
        
        # Check Turn Limits (using session message count / 2 for turns, or just message count)
        # PRD: "Max 25 turns" -> 50 messages? 
        # TIER_LIMITS currently has "messages": 20 for Tier 1.
        # Let's trust TIER_LIMITS for daily message limits, but we also have per-session limits?
        # PRD: "Free Tier: 1 session per day. Max 25 turns."
        # If TIER_LIMITS["messages"] is daily limit, we should check that.
        
        msg_limit = TIER_LIMITS[user_state.tier]["messages"]
        if user_state.messages_used_today >= msg_limit:
            return "LIMIT_REACHED", user_state.tier

        # 4. Retrieve memories
        memories = await memory_service.get_all_memory_content(uid)

        # 5. Check Memory Availability
        mem_limit = TIER_LIMITS[user_state.tier]["memory"]
        can_add_memory = user_state.memory_used < mem_limit
        
        # 6. Format History from Session Transcript
        history_str = ""
        for msg in session.transcript:
             role = msg.role.upper()
             content = msg.content
             history_str += f"{role}: {content}\n"
        # Add current input (already added to transcript in DB but maybe not in local object if we didn't refresh? 
        # Actually add_message updates DB. The 'session' object is from get_active_session called BEFORE add_message.
        # So we should append current input to history_str manually or re-fetch.
        history_str += f"USER: {user_input}\n"

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

            # 7. Store Memory if generated and allowed
            if memory_content and can_add_memory:
                 await memory_service.add_memory(uid, memory_content)

            # 8. Add Model Reply to Session
            await session_service.add_message(session_id, "model", reply)

            # 9. Increment global usage
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
