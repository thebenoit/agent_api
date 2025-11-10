from database_manager import mongo_manager

from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
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
        self.db = mongo_manager.get_async_db()
        self.collection = self.db["session_metrics"]
        
        logger.debug("SessionMetrics initialisé avec collection: session_metrics")

    async def ensure_indexes(self):
        """
        Crée les index nécessaires pour la collection.
        Doit être appelé au démarrage de l'application.
        """
        await self.collection.create_index("user_id")
        await self.collection.create_index("event_type")
        await self.collection.create_index("timestamp")
        logger.info("Index MongoDB créés pour session_metrics")
        
    async def track_session_creation(
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
            await metrics.track_session_creation(
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
            result = await self.collection.insert_one(metric_doc)
            
            status = "✅ SUCCESS" if success else "❌ FAILURE"
            logger.info(
                f"[METRIC] Session Creation {status} | "
                f"user={user_id[:8]} | duration={duration_seconds:.2f}s"
            )
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"[METRIC] Erreur lors de l'enregistrement: {e}")
            return None
        
    async def track_search_execution(
        self,
        user_id: str,
        duration_seconds: float,
        success: bool,
        listings_count: int = 0,
        error_message: Optional[str] = None,
        retry_count: int = 0            
    ):
        """
        Enregistre une exécution de recherche Facebook.
        
        Args:
            user_id: ID de l'utilisateur
            duration_seconds: Temps total de la recherche
            success: True si recherche réussie, False sinon
            listings_count: Nombre de listings trouvés
            error_message: Message d'erreur si échec
            retry_count: Nombre de tentatives avant succès/échec
        
        Exemple d'utilisation:
            await metrics.track_search_execution(
                user_id="66bd41ad...",
                duration_seconds=8.5,
                success=True,
                listings_count=12,
                retry_count=0
            )
        """
        metric_doc = {
            "user_id": user_id,
            "event_type": "search_execution",
            "timestamp": datetime.utcnow(),
            "duration_ms": duration_seconds * 1000,
            "success": success,
            "error_message": error_message,
            "metadata": {
                "listings_count": listings_count,
                "retry_count": retry_count,
                "user_id_short": user_id[:8]
            }
        }
        try:
            result = await self.collection.insert_one(metric_doc)
            
            status = "✅ SUCCESS" if success else "❌ FAILURE"
            logger.info(
                f"[METRIC] Search {status} | "
                f"user={user_id[:8]} | duration={duration_seconds:.2f}s | "
                f"listings={listings_count} | retries={retry_count}"
            )
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"[METRIC] Erreur lors de l'enregistrement: {e}")
            return None

    async def get_metrics_summary(self, hours: int = 24) -> Dict[str,Any]:
        """
        Récupère un résumé des métriques des dernières X heures.
        Utile pour debugging et monitoring.
        
        Args:
            hours: Nombre d'heures à analyser (défaut: 24h)
        
        Returns:
            Dict avec statistiques: taux de succès, durées moyennes, etc.
        
        Exemple d'utilisation:
            summary = await metrics.get_metrics_summary(hours=24)
            print(f"Taux de succès: {summary['session_creation']['success_rate']}")
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        try:
            recent_metrics = await self.collection.find({
                "timestamp": {"$gte":cutoff_time}
            }).to_list(length=None)
            
            session_creation = [m for m in recent_metrics if m["event_type"] == "session_creation"]
            search_executions = [m for m in recent_metrics if m["event_type"] == "search_execution"]
            
            session_stats = self._calculate_event_stats(session_creation, "session")
            
            search_stats = self._calculate_event_stats(search_executions, "search")
            
            summary = {
                "period_hours": hours,
                "timestamp": datetime.utcnow().isoformat(),
                "session_creation": session_stats,
                "search_execution": search_stats
            }
            
            logger.info(
                f"[METRIC SUMMARY] Last {hours}h | "
                f"Sessions: {session_stats['total']} ({session_stats['success_rate']:.1f}% success) | "
                f"Searches: {search_stats['total']} ({search_stats['success_rate']:.1f}% success)"
            )
            
            return summary
            
        
        except Exception as e:
            logger.error(f"[METRIC] erreur lors du résumé")
            return{}
            
            
    def _calculate_event_stats(self, events: list, event_name: str) -> Dict[str,Any]:
        """
        Helper pour calculer les stats d'un type d'événement.
        (Méthode privée, utilisée par get_metrics_summary)
        """
        
        if not events:
            return {
                "total": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "avg_duration_seconds": 0.0                
            }
            
        total = len(events)
        success_count = sum(1 for e in events if e.get("success"))
        failure_count = total - success_count
        success_rate = (success_count / total * 100) if total > 0 else 0.0
        
        # Durée moyenne (convertir ms en secondes)
        durations = [e.get("duration_ms", 0) / 1000 for e in events if e.get("duration_ms")]
        avg_duration = statistics.mean(durations) if durations else 0.0
        
        return {
            "total": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_rate,
            "avg_duration_seconds": round(avg_duration, 2)            
        }
        
        
        
        
        
