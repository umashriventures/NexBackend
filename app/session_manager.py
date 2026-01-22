import uuid
from typing import List, Dict, Any

class Session:
    """Represents a conversation session.
    
    Attributes:
        session_id: Unique identifier for the session.
        user_id: Identifier of the user owning the session.
        state: Current state of the session (listening, thinking, responding).
        partial_transcript_buffer: List of received audio chunk strings.
        belief_state: Arbitrary dict representing the belief model.
        short_term_memory: List of recent transcript entries.
    """
    def __init__(self, user_id: str):
        self.session_id: str = str(uuid.uuid4())
        self.user_id: str = user_id
        self.state: str = "listening"
        self.partial_transcript_buffer: List[str] = []
        self.belief_state: Dict[str, Any] = {}
        self.short_term_memory: List[str] = []

    def add_chunk(self, chunk: str) -> None:
        self.partial_transcript_buffer.append(chunk)
        self.short_term_memory.append(chunk)
        # Keep short‑term memory limited (e.g., last 20 chunks)
        if len(self.short_term_memory) > 20:
            self.short_term_memory.pop(0)

    def finalize(self) -> str:
        """Combine buffered chunks into a final transcript and reset buffer."""
        transcript = " ".join(self.partial_transcript_buffer).strip()
        self.partial_transcript_buffer.clear()
        self.state = "thinking"
        return transcript

# Simple in‑memory session registry
_sessions: Dict[str, Session] = {}

def get_session(user_id: str) -> Session:
    """Retrieve an existing session for a user or create a new one."""
    # For MVP we keep a single session per user
    for sess in _sessions.values():
        if sess.user_id == user_id:
            return sess
    # Create new session
    sess = Session(user_id)
    _sessions[sess.session_id] = sess
    return sess
