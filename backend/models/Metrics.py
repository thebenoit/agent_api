
from datetime import datetime
from typing import Optional, Dict, Any
from database_manager import mongo_manager
from schemas.fb_session import FacebookSession
import logging

logger = logging.getLogger(__name__)


class Metrics:
    
    def __init__(self):
        self.db = mongo_manager.get_sync_db()
        
    def inserer_metrics(self,collection,payload):
        
        collection = self.db[collection]
        
        if collection is None:
            logger.info("La collection est vide")
            return None
        
        try:
            payload_dict = payload.dict()
            result = collection.insert_one(payload_dict)
            inserted_id = str(result.inserted_id)
            logger.info(
                    "Metric sauvegardée avec succès , inserted_id=%s",
                )
        except Exception as e:
            logger.info("erreur lors de l'insertion de metrix e=%s",e)
            
        