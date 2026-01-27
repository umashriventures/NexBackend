import google.generativeai as genai
from .memory_service import memory_service
from .user_service import user_service
from .models import Tier, TIER_LIMITS
from loguru import logger

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
            model = genai.GenerativeModel(self.model_name)
            # We don't use history here as per NEX philosophy (no threads)
            # but we pass memories as context
            response = await model.generate_content_async(
                f"{system_prompt}\n\nUser: {user_input}"
            )
            reply = response.text

            # 5. Increment usage
            await user_service.increment_message_usage(uid)
            
            return reply, user_state.tier
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "ERROR", user_state.tier

nex_service = NexService()
domestic_ai = nex_service  # Alias if needed
