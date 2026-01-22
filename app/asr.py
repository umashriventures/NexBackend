from .session_manager import get_session

async def handle_audio_chunk(user_id: str, chunk: str) -> None:
    """Append an audio chunk (as text) to the user's session buffer."""
    session = get_session(user_id)
    session.add_chunk(chunk)

async def finalize_transcript(user_id: str) -> str:
    """Combine buffered chunks into a final transcript and reset the session state."""
    session = get_session(user_id)
    transcript = session.finalize()
    return transcript
