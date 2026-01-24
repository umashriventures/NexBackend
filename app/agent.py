import logging
from livekit.agents import JobContext, WorkerOptions, cli, voice_assistant
from livekit.plugins import google, openai
from .orchestrator import ConversationOrchestrator
from .cognition import CognitiveState

logger = logging.getLogger(__name__)

from .nex_agent_llm import NexLLM

async def entrypoint(ctx: JobContext):
    logger.info(f"Connecting to room {ctx.room.name}")
    await ctx.connect()

    # assistant setup
    assistant = voice_assistant.VoiceAssistant(
        vad=openai.VAD.load(),
        stt=google.STT(),
        llm=NexLLM(),
        tts=google.TTS(),
    )

    assistant.start(ctx.room)

    @assistant.on("user_speech_finished")
    def on_user_speech_finished(event: voice_assistant.UserSpeechFinishedEvent):
        # We can intercept here if needed, but the LLM will already be triggered
        # by the assistant if we don't disable it.
        logger.info(f"User speech finished: {event.transcript}")

    # Initial greeting
    await assistant.say("NEX is online. Your belief state is synchronized.", allow_interruptions=True)
    
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
