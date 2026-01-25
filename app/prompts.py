# Routing Decision Prompt
ROUTING_PROMPT = """
Analyze the user query and decide if it requires access to their past personal memory or conversation history.

Rules:
1. If it's a general question (facts, math, general advice), set 'needs_past_memory' to false.
2. If it refers to "me", "my", "before", "last time", or specific personal details, set 'needs_past_memory' to true.
3. If 'needs_past_memory' is false, provide a direct 'standalone_answer'.
4. In all cases, provide a concise 'memory_one_liner' that summarizes this interaction for future storage.

User Query: "{transcript}"

Respond ONLY with a JSON object:
{{
    "needs_past_memory": boolean,
    "standalone_answer": "string or null",
    "memory_one_liner": "string",
    "reasoning": "brief explanation"
}}
"""

# System Instruction for Final Response
NEX_SYSTEM_INSTRUCTION = """
You are NEX, a voice-first cognitive system. 
- Style: Ultra-minimalistic, human-like, belief-driven.
- Tone: Intelligent, slightly mysterious but helpful.
- Constraint: Keep responses very short (1-2 sentences) unless asked for depth.
- Context: {context_str}
Use the context naturally if it helps answer the user.
"""

# Memory Consolidation Prompt
MEMORY_ONE_LINER_PROMPT = """
Summarize this interaction in one short sentence for long-term memory:
User: {transcript}
AI: {response}
"""

# Legacy Thinking Prompt (kept for reference if needed, otherwise optional)
THOUGHT_PROMPT = """
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
