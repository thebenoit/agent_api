from ...database_manager import mongo_manager

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from .Metrics import Metrics
import statistics
import logging

logger = logging.getLogger(__name__)



class SessionMetrics(Metrics):
    """
    Metriques liées aux sessions FB
    """
    def __init__(self):
        super().__init__()
        # Récupérer la connexion MongoDB
        self.db = mongo_manager.get_sync_db()
        self.collection = self.db["session_metrics"]
        
        # Créer des index pour rechercher rapidement
        self.collection.create_index("user_id")
        self.collection.create_index("event_type")
        self.collection.create_index("timestamp")
        
        logger.debug("SessionMetrics initialisé avec collection: session_metrics")
        
    async def track_creation_time(
        self, 
        duration_seconds: float, 
        user_id: str,
        success: bool,
        error_message: Optional[str] = None        
        ):
        """
        Enregistre une tentative de création de session.
        
        Args:
            user_id: ID de l'utilisateur
            duration_seconds: Temps pris pour créer la session (en secondes)
            success: True si création réussie, False sinon
            error_message: Message d'erreur si échec
        
        Exemple d'utilisation:
            metrics.track_session_creation(
                user_id="66bd41ad...",
                duration_seconds=15.3,
                success=True
            )
        """
        metric_doc = {
                         "user_id": user_id,
            "event_type": "session_creation",
            "timestamp": datetime.utcnow(),
            "duration_ms": duration_seconds * 1000,  # Convertir en millisecondes
            "success": success,
            "error_message": error_message,
            "metadata": {
                "user_id_short": user_id[:8]  # Pour logs plus lisibles
            }
             
         }
        
        try:
            result = self.collection.insert_one(metric_doc)
            
            status = "✅ SUCCESS" if success else "❌ FAILURE"
            logger.info(
                f"[METRIC] Session Creation {status} | "
                f"user={user_id[:8]} | duration={duration_seconds:.2f}s"
            )
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"[METRIC] Erreur lors de l'enregistrement: {e}")
            return None
            
        
        
        
        

