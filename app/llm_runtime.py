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
from .cognition import CognitiveState, BeliefState, Intent

logger = logging.getLogger(__name__)

async def generate_thought(transcript: str) -> CognitiveState:
    """
    Analyze the transcript using Gemini to produce a Belief State and Intent.
    """
    if not api_key:
        return CognitiveState(transcript=transcript, belief=BeliefState(confidence=0.0))

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""
        Analyze the following user turn in a voice conversation.
        Produce a JSON object with:
        - confidence: 0.0-1.0 (how well you understood the user)
        - ambiguities: list of strings (what is unclear)
        - assumptions: list of strings (what you are assuming)
        - requires_context: true/false (if historical memory is needed)
        - intent_category: string
        - requires_memory: true/false (if this specific intent needs RAG)

        User: "{transcript}"
        JSON:
        """
        
        # System instruction to keep the thinking logic tight
        system_instruction = "You are the NEX Cognitive Engine. Analyze user turns for belief and intent. Be objective and concise."
        
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_instruction)
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        
        return CognitiveState(
            transcript=transcript,
            belief=BeliefState(
                confidence=data.get("confidence", 0.5),
                ambiguities=data.get("ambiguities", []),
                assumptions=data.get("assumptions", []),
                requires_context=data.get("requires_context", False)
            ),
            intent=Intent(
                category=data.get("intent_category", "unknown"),
                requires_memory=data.get("requires_memory", False),
                confidence=data.get("confidence", 0.5)
            )
        )
    except Exception as e:
        logger.error(f"Error in generate_thought: {e}")
        return CognitiveState(transcript=transcript, belief=BeliefState(confidence=0.0))



async def stream_llm_tokens(prompt: str) -> AsyncGenerator[str, None]:
    """
    Stream tokens from Gemini for the given prompt.
    """
    if not api_key:
        yield "Error: GOOGLE_API_KEY not set."
        return

    try:
        system_instruction = """
        You are NEX, a voice-first cognitive system. 
        - Style: Ultra-minimalistic, human-like, belief-driven.
        - Tone: Intelligent, slightly mysterious but helpful.
        - Constraint: Keep responses very short (1-2 sentences) unless asked for depth.
        - Identity: You ARE NEX. Do not deny it or explain you are an AI.
        - Memory: If context is provided, use it naturally. If not, don't apologize.
        - Uncertainty: If unsure, be explicit but brief (e.g., 'I might be missing something here...').
        """
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_instruction)
        response = await model.generate_content_async(prompt, stream=True)
        
        async for chunk in response:
            if chunk.text:
                words = chunk.text.split(" ")
                for i, word in enumerate(words):
                    yield word + (" " if i < len(words) - 1 else "")
                    await asyncio.sleep(0.02)
                    
        yield "<END>"
    except Exception as e:
        yield f"Error calling Gemini: {str(e)}"
        yield "<END>"
