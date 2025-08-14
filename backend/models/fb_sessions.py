"""Facebook session model for database operations."""

from datetime import datetime
from typing import Optional, Dict, Any
from database_manager import mongo_manager
from schemas.fb_session import FacebookSession


class FacebookSessionModel:
    """Model for managing Facebook sessions in MongoDB."""

    def __init__(self):
        self.db = mongo_manager.get_sync_db()
        self.collection = self.db["fb_sessions"]

    def save_session(self, session: FacebookSession) -> str:
        """Save a Facebook session to database."""
        session_dict = session.dict()
        result = self.collection.insert_one(session_dict)
        return str(result.inserted_id)

    def get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get active session for a user."""
        return self.collection.find_one({"user_id": user_id, "active": True})

    def update_session(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data for a user."""
        updates["last_used"] = datetime.utcnow()
        result = self.collection.update_one(
            {"user_id": user_id, "active": True}, {"$set": updates}
        )
        return result.modified_count > 0

    def deactivate_session(self, user_id: str) -> bool:
        """Deactivate a user's session."""
        result = self.collection.update_one(
            {"user_id": user_id, "active": True}, {"$set": {"active": False}}
        )
        return result.modified_count > 0
