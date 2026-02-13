from datetime import datetime, timedelta, timezone
import uuid
from .services import get_db
from .models import Session, Message, UserState, Tier, TIER_LIMITS
from .user_service import user_service
from .archive_service import archive_service
from firebase_admin import firestore
from loguru import logger
import asyncio

SESSION_TIMEOUT_MINUTES = 20

class SessionService:
    @property
    def db(self):
        return get_db()

    def _get_session_ref(self):
        return self.db.collection("sessions")

    async def get_active_session(self, uid: str) -> Session | None:
        """
        Retrieves the active session for the user.
        Checks for inactivity timeout and auto-closes if needed.
        """
        docs = self._get_session_ref()\
            .where("user_id", "==", uid)\
            .limit(50).stream() # Get recent sessions (unordered)
        
        # Sort in memory
        sessions = []
        for doc in docs:
            sessions.append(Session(**doc.to_dict()))
            
        # Sort by started_at desc
        sessions.sort(key=lambda x: x.started_at, reverse=True)
        
        active_session = None
        for s in sessions:
            if s.is_active:
                active_session = s
                break
        
        if not active_session:
            return None

        # Check inactivity
        # Use timezone-aware comparison
        last_msg_time = active_session.last_message_at
        if last_msg_time.tzinfo is None:
            last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        
        if (now - last_msg_time) > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            logger.info(f"Session {active_session.session_id} timed out. Closing.")
            await self.end_session(active_session.session_id)
            return None
            
        return active_session

    async def start_session(self, uid: str) -> tuple[Session | None, str | None]:
        """
        Starts a new session. Returns (Session, error_message).
        """
        # 1. Check if user exists and get state
        user_state = await user_service.get_user_state(uid)
        
        # 2. Check overlap with existing active session
        active_session = await self.get_active_session(uid)
        if active_session:
            # Close old one to be clean before starting new.
            await self.end_session(active_session.session_id)
        
        # 3. Check Daily Limits (Free Tier = 1 session/day)
        if user_state.tier == Tier.TIER_1:
            # Query recent sessions for user and count today's sessions manually
            now = datetime.now(timezone.utc)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Optimization: limit to 50 sessions
            docs = self._get_session_ref()\
                .where("user_id", "==", uid)\
                .limit(50).stream()
            
            session_count = 0
            for doc in docs:
                 data = doc.to_dict()
                 started_at = data["started_at"]
                 if started_at.tzinfo is None:
                     started_at = started_at.replace(tzinfo=timezone.utc)
                     
                 if started_at >= start_of_day:
                     session_count += 1
            
            if session_count >= 1:
               return None, "DAILY_SESSION_LIMIT_REACHED"

        # 4. Create new session
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        new_session = Session(
            session_id=session_id,
            user_id=uid,
            started_at=now,
            last_message_at=now,
            is_active=True,
            message_count=0,
            transcript=[]
        )
        
        self._get_session_ref().document(session_id).set(new_session.dict())
        return new_session, None

    async def add_message(self, session_id: str, role: str, content: str):
        """
        Adds a message to the session transcript.
        """
        session_ref = self._get_session_ref().document(session_id)
        
        new_message = Message(role=role, content=content, timestamp=datetime.now(timezone.utc))
        
        session_ref.update({
            "transcript": firestore.ArrayUnion([new_message.dict()]),
            "last_message_at": datetime.now(timezone.utc),
            "message_count": firestore.Increment(1)
        })

    async def end_session(self, session_id: str) -> dict | None:
        """
        Ends the session, generates reflection, archives, and clears transcript.
        Returns archive data.
        """
        session_ref = self._get_session_ref().document(session_id)
        doc = session_ref.get()
        if not doc.exists:
            return None
            
        session_data = Session(**doc.to_dict())
        
        if not session_data.is_active:
             return None

        # 1. Generate Archive
        archive_entry = await archive_service.create_archive_entry(session_data.user_id, session_data.transcript)
        
        # 2. Clear Session & Mark Inactive
        # Clearing transcript for privacy as per PRD
        session_ref.update({
            "is_active": False,
            "transcript": [],
            "ended_at": datetime.now(timezone.utc) 
        })
        
        return {
            "archive_id": archive_entry.archive_id,
            "title": archive_entry.title,
            "reflection": archive_entry.reflection,
            "emotion_tag": archive_entry.emotion_tag
        }

session_service = SessionService()
