import datetime as dt
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from database_manager import mongo_manager
from bson import ObjectId


class AccessControlMiddleware:
    def __init__(self):
        self.db = mongo_manager.get_async_db()
        self.users = self.db["users"]
        self._cache = {}
        self._cache_ttl = 60  # secondes

    def _today(self) -> str:
        return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    async def check_access(self, user_id: str) -> tuple[bool, dict]:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return False, {"reason": "invalid_user_id"}

        today = self._today()

        # Récupérer l'utilisateur
        user = await self.users.find_one({"_id": oid}, {"hasAccess": 1, "usage": 1})
        if not user:
            return False, {"reason": "user_not_found"}

        # Premium = illimité
        if user.get("hasAccess"):
            return True, {"premium": True}

        # Reset quotidien si nécessaire
        usage = user.get("usage") or {}
        if usage.get("day") != today:
            await self.users.update_one(
                {"_id": oid}, {"$set": {"usage.day": today, "usage.count": 0}}
            )
            current_count = 0
        else:
            current_count = usage.get("count", 0)

        # Vérifier limite pour utilisateur gratuit
        if current_count >= 3:
            return False, {
                "limit": 3,
                "remaining": 0,
                "reason": "limit_reached",
                "resetAt": f"{today}T23:59:59Z",
            }

        # Consommer un chat (opération atomique)
        res = await self.users.update_one(
            {
                "_id": oid,
                "$or": [{"usage": {"$exists": False}}, {"usage.count": {"$lt": 3}}],
            },
            {
                "$set": {"usage.day": today, "hasAccess": False},
                "$inc": {"usage.count": 1},
            },
        )
        if res.modified_count == 1:
            remaining = 2 - current_count
            return True, {"limit": 3, "remaining": remaining}

        return False, {"reason": "concurrent_limit_reached"}


# Instance globale
access_control = AccessControlMiddleware()


async def access_control_middleware(request: Request, call_next):
    # Appliquer seulement sur GET /chat/stream
    if request.url.path == "/chat/stream" and request.method == "GET":
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            return JSONResponse(
                status_code=401, content={"error": "authentication_required"}
            )
        allowed, details = await access_control.check_access(user_id)
        if not allowed:
            return JSONResponse(
                status_code=402,
                content={
                    "error": "payment_required",
                    "message": "Limite quotidienne atteinte (3 chats). Passez en Premium pour un accès illimité.",
                    **details,
                },
            )
    return await call_next(request)
