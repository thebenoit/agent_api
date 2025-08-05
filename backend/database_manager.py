from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from bson import ObjectId
import os
import logging
from langgraph.checkpoint.mongodb.aio import AsyncMongoDBSaver

load_dotenv()
logger = logging.getLogger(__name__)


class MongoDBManager:
    """Singleton pour gérer les connexions MongoDB de manière centralisée."""

    _instance = None
    _sync_client: Optional[MongoClient] = None
    _async_client: Optional[AsyncIOMotorClient] = None
    _db_name: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._db_name = os.getenv("MONGO_DB")
            self._mongo_uri = os.getenv("MONGO_URI")

    def get_sync_client(self) -> MongoClient:
        """Retourne le client MongoDB synchrone."""
        if self._sync_client is None or self._sync_client.address is None:
            logger.info("Création d'une nouvelle connexion MongoDB synchrone")
            self._sync_client = MongoClient(self._mongo_uri)
        return self._sync_client

    def get_async_client(self) -> AsyncIOMotorClient:
        """Retourne le client MongoDB asynchrone."""
        if self._async_client is None:
            logger.info("Création d'une nouvelle connexion MongoDB asynchrone")
            self._async_client = AsyncIOMotorClient(self._mongo_uri)
        return self._async_client

    def get_sync_db(self):
        """Retourne la base de données synchrone."""
        return self.get_sync_client()[self._db_name]

    def get_async_db(self):
        """Retourne la base de données asynchrone."""
        return self.get_async_client()[self._db_name]

    def close_sync_client(self):
        """Ferme proprement le client synchrone."""
        if self._sync_client is not None:
            logger.info("Fermeture de la connexion MongoDB synchrone")
            self._sync_client.close()
            self._sync_client = None

    def close_async_client(self):
        """Ferme proprement le client asynchrone."""
        if self._async_client is not None:
            logger.info("Fermeture de la connexion MongoDB asynchrone")
            self._async_client.close()
            self._async_client = None

    def close_all(self):
        """Ferme toutes les connexions."""
        self.close_sync_client()
        self.close_async_client()


# Instance globale
mongo_manager = MongoDBManager()
