from pymongo import MongoClient
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from bson import ObjectId
import os

load_dotenv()


class MongoDB:
    def __init__(self, connection_string: str):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("MONGO_DB")]
        self.collection = self.db["users"]
        self.memory_collection = self.db["Memory"]

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:

        try:
            object_id = ObjectId(user_id)
            user = self.collection.find_one({"_id": object_id})
            return user
        except Exception as e:
            print(f"Error getting user by id: {e}")
            return None

    async def get_chat_history(self, chat_id: str) -> Optional[Dict[str, Any]]:
        try:
            object_id = ObjectId(chat_id)
            chat_history = self.memory_collection.find_one({"_id": object_id})
            print("messages ", chat_history)
            return chat_history
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return None
    
    async def add_message_to_history

    async def update_chat_history(
        self, chat_id: str, chat_history: List[dict], who: str
    ):
        try:
            object_id = ObjectId(chat_id)
            self.memory_collection.update_one(
                {"_id": object_id}, {"$set": {"content": chat_history, "type": who}}
            )
        except Exception as e:
            print(f"Error updating chat history: {e}")
            return None


mongo_db = MongoDB(os.getenv("MONGO_URI"))
