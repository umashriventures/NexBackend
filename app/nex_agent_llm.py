from livekit.agents import llm
from typing import AsyncGenerator
from .orchestrator import ConversationOrchestrator
import logging

logger = logging.getLogger(__name__)

class NexLLM(llm.LLM):
    def __init__(self):
        super().__init__()
        self.orchestrator = ConversationOrchestrator()

    def chat(
        self,
        *,
        chat_ctx: llm.ChatContext,
        fnc_ctx: llm.FunctionContext | None = None,
        temperature: float | None = None,
        n: int | None = None,
    ) -> llm.LLMStream:
        return NexLLMStream(self.orchestrator, chat_ctx)

class NexLLMStream(llm.LLMStream):
    def __init__(self, orchestrator: ConversationOrchestrator, chat_ctx: llm.ChatContext):
        super().__init__()
        self.orchestrator = orchestrator
        self.chat_ctx = chat_ctx

    async def __aiter__(self) -> AsyncGenerator[llm.ChatChunk, None]:
        # Extract the last user message
        transcript = ""
        for msg in reversed(self.chat_ctx.messages):
            if msg.role == "user":
                transcript = msg.content
                break
        
        if not transcript:
            yield llm.ChatChunk(choices=[llm.Choice(delta=llm.ChoiceDelta(content="I didn't hear you clearly.", role="assistant"))])
            return

        # Use our orchestrator to handle thinking and RAG
        async for token in self.orchestrator.process_turn("default_user", transcript):
            if token == "<END>":
                break
            yield llm.ChatChunk(choices=[llm.Choice(delta=llm.ChoiceDelta(content=token, role="assistant"))])
