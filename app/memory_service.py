from datetime import datetime, timezone
from .services import get_db
from .models import MemoryItem, MemoryListResponse, TIER_LIMITS
from firebase_admin import firestore
from loguru import logger

class MemoryService:
    @property
    def db(self):
        return get_db()

    def _get_memory_collection(self, uid: str):
        return self.db.collection("memories").document(uid).collection("items")
    
    async def get_memory(self, uid: str, memory_id: str) -> MemoryItem | None:
        doc = self._get_memory_collection(uid).document(memory_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        return MemoryItem(
            id=doc.id,
            content=data["content"],
            created_at=data["created_at"].isoformat() if hasattr(data["created_at"], "isoformat") else str(data["created_at"])
        )

    async def list_memories(self, uid: str, tier: str, memory_used: int) -> MemoryListResponse:
        docs = self._get_memory_collection(uid).order_by("created_at", direction=firestore.Query.DESCENDING).stream()
        items = []
        for doc in docs:
            data = doc.to_dict()
            items.append(MemoryItem(
                id=doc.id,
                content=data["content"],
                created_at=data["created_at"].isoformat() if hasattr(data["created_at"], "isoformat") else str(data["created_at"])
            ))
        
        limit = TIER_LIMITS[tier]["memory"]
        return MemoryListResponse(
            memory_limit=limit,
            memory_used=memory_used,
            items=items
        )

    async def add_memory(self, uid: str, content: str):
        mem_ref = self._get_memory_collection(uid).document()
        mem_ref.set({
            "content": content,
            "created_at": datetime.now(timezone.utc)
        })
        
        # Increment memory_used in user doc
        user_ref = self.db.collection("users").document(uid)
        user_ref.update({"memory_used": firestore.Increment(1)})
        return mem_ref.id

    async def get_all_memory_content(self, uid: str) -> str:
        docs = self._get_memory_collection(uid).stream()
        contents = [doc.to_dict()["content"] for doc in docs]
        return "\n".join(contents)

    async def update_memory(self, uid: str, memory_id: str, content: str) -> bool:
        mem_ref = self._get_memory_collection(uid).document(memory_id)
        try:
            # Check if exists to avoid creating if not present (though update usually fails if not found)
            doc = mem_ref.get()
            if not doc.exists:
                return False
                
            mem_ref.update({
                "content": content,
                # We could add updated_at here if model supported it
            })
            return True
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False

    async def delete_memory(self, uid: str, memory_id: str) -> bool:
        mem_ref = self._get_memory_collection(uid).document(memory_id)
        
        doc = mem_ref.get()
        if not doc.exists:
            return False
            
        mem_ref.delete()
        
        # Decrement memory_used
        user_ref = self.db.collection("users").document(uid)
        # Ensure we don't go below 0
        # However, firestore increment(-1) is atomic. logic to prevent <0 should be robust but strict relies on check.
        # We can just decrement. 
        user_ref.update({"memory_used": firestore.Increment(-1)})
        
        return True

memory_service = MemoryService()
