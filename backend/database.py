from pymongo import MongoClient
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import os
load_dotenv()

class MongoDB:
    def __init__(self, connection_string: str):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("MONGO_DB")]
        self.collection = self.db["users"]
        
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        
        try:
            user = self.users.find_one({"_id":user_id})
            return user
        except Exception as e:
            print(f"Error getting user by id: {e}")
            return None
        
mongo_db = MongoDB(os.getenv("MONGO_URI"))