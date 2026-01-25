import os
import json
import yaml
import logging
import asyncio
from typing import AsyncGenerator, Optional
from llama_cpp import Llama
from .cognition import RoutingDecision
from . import prompts

logger = logging.getLogger(__name__)

# Load models config
MODELS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models.yml")
with open(MODELS_CONFIG_PATH, "r") as f:
    models_config = yaml.safe_load(f)

LLM_REPO = models_config["default_llm"]["repo"]
LLM_FILENAME = models_config["default_llm"]["filename"]
CACHE_DIR = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))

# Global model instance
_llm_instance = None

def get_llm_instance():
    global _llm_instance
    if _llm_instance is None:
        logger.info(f"Loading local GGUF LLM: {LLM_REPO}/{LLM_FILENAME}...")
        _llm_instance = Llama.from_pretrained(
            repo_id=LLM_REPO,
            filename=LLM_FILENAME,
            n_ctx=4096,
            n_threads=os.cpu_count(),
            # Caching is handled by HF/llama-cpp internally using cache_dir
        )
    return _llm_instance

async def get_routing_decision(transcript: str) -> RoutingDecision:
    """
    Determine if the query needs past memory via local Llama.
    """
    try:
        llm = get_llm_instance()
        prompt = prompts.ROUTING_PROMPT.format(transcript=transcript)
        
        response = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_object",
                "schema": RoutingDecision.model_json_schema()
            },
            temperature=0.1
        )
        data = json.loads(response["choices"][0]["message"]["content"])
        return RoutingDecision(**data)
    except Exception as e:
        logger.error(f"Error in get_routing_decision: {e}")
        return RoutingDecision(needs_past_memory=False, memory_one_liner="User interaction.", reasoning="Error fallback")

async def stream_llm_tokens(prompt: str, context: str = "") -> AsyncGenerator[str, None]:
    """
    Stream tokens from local Llama instance.
    """
    try:
        llm = get_llm_instance()
        context_str = context if context else "No past memory provided."
        system_instruction = prompts.NEX_SYSTEM_INSTRUCTION.format(context_str=context_str)
        
        stream = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            stream=True
        )
        
        for chunk in stream:
            token = chunk["choices"][0]["delta"].get("content", "")
            if token:
                yield token
                await asyncio.sleep(0) # Yield control
                
        yield "<END>"
    except Exception as e:
        logger.error(f"Error in stream_llm_tokens: {e}")
        yield f"Error calling local GGUF LLM: {str(e)}"
        yield "<END>"

async def get_memory_one_liner(transcript: str, response: str) -> str:
    """
    Generate a one-liner summary of the interaction.
    """
    try:
        llm = get_llm_instance()
        prompt = prompts.MEMORY_ONE_LINER_PROMPT.format(transcript=transcript, response=response)
        
        res = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        return res["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Error generating memory one-liner: {e}")
        return f"User said: {transcript[:50]}"
