from typing import Optional, Dict, Any, List
from bson import ObjectId
from database_manager import mongo_manager
import logging

logger = logging.getLogger(__name__)


class MongoDB:
    def __init__(self):
        self.db = mongo_manager.get_sync_db()
        self.collection = self.db["users"]
        self.memory_collection = self.db["Memory"]

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            object_id = ObjectId(user_id)
            user = self.collection.find_one({"_id": object_id})
            return user
        except Exception as e:
            logger.error(f"Error getting user by id: {e}")
            return None

    def get_chat_history(self, chat_id: str) -> Optional[Dict[str, Any]]:
        try:
            object_id = ObjectId(chat_id)
            chat_history = self.memory_collection.find_one({"_id": object_id})
            logger.info(f"messages: {chat_history}")
            return chat_history
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return None

    def update_chat_history(self, chat_id: str, chat_history: List[dict], who: str):
        try:
            object_id = ObjectId(chat_id)
            self.memory_collection.update_one(
                {"_id": object_id}, {"$set": {"content": chat_history, "type": who}}
            )
        except Exception as e:
            logger.error(f"Error updating chat history: {e}")
            return None


# Instance globale
mongo_db = MongoDB()
