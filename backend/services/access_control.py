

import datetime as dt
from typing import Tuple,Dict,Any
from database_manager import mongo_manager
from bson import ObjectId

class AccessControlService:
    def __init__(self):
        self.db = mongo_manager.get_sync_db()
        self.users = self.db["users"]
        
    def _today(self) -> str:
        return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    
    async def ensure_user_fields(self, user_id: str) -> dict[str, Any]:
        """ S'assure que les chammps hasAccess/usage existent et reset le compter"""
        
        try:
            oid = ObjectId(user_id)
        except Exception:
            return {}
        
        today = self._today()
        user = await self.users.find_one({"_id":oid}, {"hasAccess": 1, "usage":1, "email": 1})
        if not user:
            return {}
        usage = user.get("usage") or {}
        
        #update le jour
        if usage.get("day") != today:
            await self.users.update_one({"_id":oid}, {"$set": {"usage.day": today, "usage.count":0}})
            user["usage"] = {"day": today, "count":0}
        #si  hasAccess n'est pas la ajouter    
        if "hasAccess" not in user:
            await self.users.update_one({"_id":oid}, {"$set": {"hasAccess": False}})
            user["hasAccess"] = False
        return user
        
    async def get_limit_and_remaining(self,user_id: str) -> tuple[int,int]:
        
        user = await self.ensure_user_fields(user_id)
        
        if not user:
            return (0,0)
        
        if user.get("hasAccess"):
            return(9999,9999)
        
        usage = (user.get("usage") or {"count": 0})
        limit = 3
        remaining = max(0,limit - int(usage.get("count",0)))
        return (limit,remaining)
    
    async def consume_one_chat(self, user_id:str) -> tuple[bool, dict[str, Any]]:
        
        try:
            oid = ObjectId(user_id)
        except Exception:
            return (False, {"reason":"invalid_user_id"})
        
        today = self._today()
        
        # Reset si jour changé
        await self.users.update_one(
            {"_id": oid, "usage.day": {"$ne": today}},
            {"$set":{"usage.day":today, "usage.count": 0}}
        )
        
        #Vérifier si premium
        premium_doc = await self.users.find_one(
            {"_id":oid},
            {"hasAccess": 1, "usage": 1}     
        )
        
        if not premium_doc:
            return (False, {"reason": "user_not_found"})
        
        #A le premium
        if premium_doc.get("hasAccess") is True:
            return(True, {"premium": True})
        
        
        res = await self.users.update_one(
            {
                "_id":oid,
                "$or":[
                    {"usage": {"exist": False}},
                    {"usage.count": {"$lt":3}},
                ],
                
            },
            {
                "$set": {"usage.day": today, "hasAccess": False},
                "$inc": {"usage.count": 1},
            },
        )
        
        if res.modified_count == 1:
            limit = remaining = await self.get_limit_and_remaining(user_id)
            return(True, {"limit": limit, "remaining":remaining})
        
        
        limit, remaining = await self.get_limit_and_remaining(user_id)
        return (
            False,
            {
                "limit":limit,
                "remaining":remaining,
                "reason": "limit_reached",
                "resetAt": f"{today}T23:59:59Z"
            }
        )
           
            
    
        
    
    
        
        
   