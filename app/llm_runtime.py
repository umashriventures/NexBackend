import os
import asyncio
from typing import AsyncGenerator
import google.generativeai as genai

# Configure genai with the API key from environment
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

async def stream_llm_tokens(prompt: str) -> AsyncGenerator[str, None]:
    """
    Stream tokens from Gemini for the given prompt.
    """
    if not api_key:
        yield "Error: GOOGLE_API_KEY not set."
        return

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        # Use generate_content with stream=True
        # Note: google-generativeai's streaming is synchronous-iterator based in the current version, 
        # so we use asyncio.to_thread or simply iterate if it's fast enough. 
        # However, it also supports async streaming via the async client.
        
        response = await model.generate_content_async(prompt, stream=True)
        
        async for chunk in response:
            if chunk.text:
                # To simulate token-level streaming, we can split by space or just yield pieces
                # Most UI/clients expect small chunks.
                words = chunk.text.split(" ")
                for i, word in enumerate(words):
                    # Add back the space if it's not the last word in this chunk
                    yield word + (" " if i < len(words) - 1 else "")
                    await asyncio.sleep(0.02) # Subtle delay for "streaming" feel
                    
        yield "<END>"
    except Exception as e:
        yield f"Error calling Gemini: {str(e)}"
        yield "<END>"
