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

    async def get_user_id_from_session(self, session_id: str) -> Optional[str]:
        """
        Récupère le user_id depuis la session de chat.
        Utilise le session_id (qui correspond au chatId) pour trouver l'utilisateur.
        """
        try:
            logger.info(f"Tentative de récupération du user_id pour session_id: {session_id}")
            
            if not session_id:
                logger.warning("Session_id est None ou vide")
                return None
            
            # Récupérer la base de données asynchrone
            db = mongo_manager.get_async_db()
            
            # Chercher dans la collection des utilisateurs via le chatId
            logger.info(f"Recherche dans la collection users avec chatId: {session_id}")
            user = await db.users.find_one({"chatId": session_id})
            
            if user and "_id" in user:
                user_id = str(user["_id"])
                logger.info(f"✅ User_id trouvé: {user_id}")
                return user_id
            else:
                logger.warning(f"❌ Aucun utilisateur trouvé pour le chatId: {session_id}")
                # Essayer de chercher par session_id directement
                logger.info("Tentative de recherche alternative par session_id...")
                user = await db.users.find_one({"session_id": session_id})
                if user and "_id" in user:
                    user_id = str(user["_id"])
                    logger.info(f"✅ User_id trouvé via session_id: {user_id}")
                    return user_id
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération du user_id: {e}")
            logger.error(f"Traceback:", exc_info=True)
            return None


# Instance globale
mongo_db = MongoDB()
