from datetime import datetime, timezone
from .services import get_db
from .models import Tier, TIER_LIMITS, UserState
from loguru import logger

class UserService:
    @property
    def db(self):
        return get_db()

    def _get_user_ref(self, uid: str):
        return self.db.collection("users").document(uid)

    async def bootstrap_user(self, uid: str, email: str = None) -> UserState:
        """
        Get or create user record.
        """
        user_ref = self._get_user_ref(uid)
        doc = user_ref.get()

        if not doc.exists:
            # First login
            user_data = {
                "email": email,
                "tier": Tier.TIER_1,
                "messages_used_today": 0,
                "memory_used": 0,
                "subscription_expiry": None,
                "created_at": datetime.now(timezone.utc)
            }
            user_ref.set(user_data)
            logger.info(f"Bootstrapped new user: {uid}")
        else:
            user_data = doc.to_dict()
            # In a real app, you'd check if 'messages_used_today' needs resetting based on timestamp
            # For simplicity, we assume this is handled or updated elsewhere for now.

        limits = TIER_LIMITS[user_data["tier"]]
        return UserState(
            uid=uid,
            tier=user_data["tier"],
            messages_used_today=user_data["messages_used_today"],
            daily_limit=limits["messages"],
            memory_used=user_data["memory_used"],
            memory_limit=limits["memory"]
        )

    async def get_user_state(self, uid: str) -> UserState:
        user_ref = self._get_user_ref(uid)
        doc = user_ref.get()
        if not doc.exists:
            # Should not happen if bootstrapped
            return await self.bootstrap_user(uid)
        
        user_data = doc.to_dict()
        limits = TIER_LIMITS[user_data["tier"]]
        return UserState(
            uid=uid,
            tier=user_data["tier"],
            messages_used_today=user_data["messages_used_today"],
            daily_limit=limits["messages"],
            memory_used=user_data["memory_used"],
            memory_limit=limits["memory"]
        )

    async def increment_message_usage(self, uid: str):
        user_ref = self._get_user_ref(uid)
        user_ref.update({"messages_used_today": firestore.Increment(1)})

    async def update_tier(self, uid: str, tier: Tier, expiry: str = None):
        user_ref = self._get_user_ref(uid)
        user_ref.update({
            "tier": tier,
            "subscription_expiry": expiry
        })

user_service = UserService()
from firebase_admin import firestore # Ensure firestore increment works
