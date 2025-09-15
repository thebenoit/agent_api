import datetime as dt
import time
import os
import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from database_manager import mongo_manager
from bson import ObjectId
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    return await call_next(request)
    # try:
    #     logger.info(f"=== DÉBUT ACCESS CONTROL ===")
    #     logger.info(f"URL: {request.url}")
    #     logger.info(f"Méthode: {request.method}")

    #     # Appliquer seulement sur GET /chat/stream
    #     if request.url.path == "/chat/stream" and request.method == "GET":
    #         # Récupérer user_id depuis request.state (injecté par auth_middleware)
    #         user_id = getattr(request.state, "user_id", None)
    #         logger.info(f"user_id (state): {user_id}")

    #         # Fallback: tenter d'extraire le user_id directement depuis le token
    #         if not user_id:
    #             try:
    #                 secret_key = os.getenv("SECRET_KEY")
    #                 token = None
    #                 token_source = "unknown"

    #                 auth_header = request.headers.get("Authorization")
    #                 if auth_header and auth_header.startswith("Bearer "):
    #                     token = auth_header.split(" ")[1]
    #                     token_source = "authorization_header"
    #                 elif not token:
    #                     access_cookie = request.cookies.get("access_token")
    #                     if access_cookie:
    #                         token = access_cookie
    #                         token_source = "access_cookie"
    #                 elif not token:
    #                     session_cookie = request.cookies.get("session_id")
    #                     if session_cookie:
    #                         token = session_cookie
    #                         token_source = "session_cookie"

    #                 if token and secret_key:
    #                     decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
    #                     user_id = decoded.get("userId") or decoded.get("sub")
    #                     if user_id:
    #                         # Injecter dans le state pour la suite de la requête
    #                         request.state.user_id = user_id
    #                         request.state.token_source = token_source
    #                         logger.info(
    #                             f"user_id récupéré via fallback ({token_source}): {user_id}"
    #                         )
    #                 else:
    #                     logger.warning(
    #                         "Impossible de récupérer le token ou SECRET_KEY absente pour le fallback"
    #                     )
    #             except Exception as e:
    #                 logger.error(
    #                     f"Erreur lors du fallback d'extraction du user_id: {type(e).__name__}: {str(e)}"
    #                 )

    #         if not user_id:
    #             logger.error("user_id manquant dans request.state")
    #             return JSONResponse(
    #                 status_code=401,
    #                 content={
    #                     "error": "authentication_required",
    #                     "message": "Authentification requise pour accéder au chat",
    #                     "details": "user_id manquant dans le state",
    #                 },
    #             )

    #         logger.info(f"Vérification d'accès pour user_id: {user_id}")
    #         allowed, details = await access_control.check_access(user_id)

    #         if not allowed:
    #             logger.warning(
    #                 f"Accès refusé pour user_id: {user_id}, raison: {details.get('reason')}"
    #             )
    #             return JSONResponse(
    #                 status_code=402,
    #                 content={
    #                     "error": "payment_required",
    #                     "message": "Limite quotidienne atteinte (3 chats). Passez en Premium pour un accès illimité.",
    #                     **details,
    #                 },
    #             )

    #         logger.info(f"Accès autorisé pour user_id: {user_id}")

    #     return await call_next(request)
    # except Exception as e:
    #     logger.error(f"Erreur dans access_control_middleware: {str(e)}")
    #     logger.error("Traceback complet:", exc_info=True)
    #     return JSONResponse(
    #         status_code=500,
    #         content={
    #             "error": "internal_server_error",
    #             "message": "Une erreur inattendue s'est produite lors du contrôle d'accès",
    #         },
    #     )
