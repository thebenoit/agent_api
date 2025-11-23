from database_manager import mongo_manager
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .Metrics import Metrics
import asyncio
import logging
from collections import deque
import threading
import time

logger = logging.getLogger("agent_api.backend.schemas.Metrics.WorkflowMetrics")
logger.setLevel(logging.INFO)
# Optional: configure handler if running as script/test standalone
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    
    
class WorkflowMetrics(Metrics):
    """
    Métriques workflow production-ready avec écriture asynchrone et batching.
    
    Optimisé pour des milliers de requêtes/seconde :
    - Écriture async (non-bloquante)
    - Batching automatique (réduit charge DB)
    - Buffer en mémoire (résilient)
    """
    
    BATCH_SIZE = 100 # Écrire par batch de 100 métriques
    FLUSH_INTERVAL = 5 # flush toutes les 5 secondes
    MAX_BUFFER_SIZE = 10000 #si buffer > 10k, flush immédiatement
    
    def __init__(self):
        super().__init__()
        
        # Connexion MongoDB
        self.db = mongo_manager.get_sync_db()
        self.collection = self.db["workflow_metrics"]
        
        self._buffer = deque(maxlen=self.MAX_BUFFER_SIZE)
        self._buffer_lock = threading.Lock()
        
         # 🆕 Background thread pour flush automatique
        self._flush_thread = None
        self._stop_flush = threading.Event()
        self._start_flush_thread()
        
        # Créer les index pour performance
        self._create_indexes()
        
        logger.info(
            "WorkflowMetrics initialisé (batch_size=%d, flush_interval=%ds)",
            self.BATCH_SIZE,
            self.FLUSH_INTERVAL
        )
        
    def _create_indexes(self):
        """
        Créer les index MongoDB pour requêtes rapides.
        CRITIQUE pour performance avec gros volume !
        """
        
        try:
            # Index pour recherche par job_id (très fréquent)
            self.collection.create_index("job_id")
            
            # Index pour recherche par user_id
            self.collection.create_index("user_id")
            
            # Index pour recherche par timestamp (pour résumés)
            self.collection.create_index("timestamp")
            
            
            # 🆕 TTL Index : Auto-suppression après 30 jours
            # Évite que la collection grossisse indéfiniment
            self.collection.create_index(
                "timestamp",
                expireAfterSeconds=30 * 24 * 60 * 60  # 30 jours
            )
            
            logger.info("✅ Index MongoDB créés avec succès")
                  
        except Exception as e:
            logger.error(f"❌ Erreur création index: {e}")
            
            
    def _start_flush_thread(self):
        """
        Démarre un thread background qui flush le buffer périodiquement.
        """
        
        if self._flush_thread is None or not self._flush_thread.is_alive():
            self._stop_flush.clear()
            self._flush_thread = threading.Thread(
                target=self._flush_loop,
                daemon=True,
                name="metrics-flusher"
            )
            
            self._flush_thread.start()
            logger.info("Thread de flush démarré")
            
            
    def _flush_loop(self):
        """
        Boucle qui flush le buffer toutes les N secondes.
        Tourne en background, n'impacte pas le flow principal.
        """
        while not self._stop_flush.is_set():
            try:
                # Attendre FLUSH_INTERVAL secondes
                self._stop_flush.wait(self.FLUSH_INTERVAL)
                
                # Flush le buffer
                if len(self._buffer) > 0:
                    self._flush_buffer()
                    
            except Exception as e:
                logger.error(f"❌ Erreur dans flush loop: {e}", exc_info=True)
                
                
    def _flush_buffer(self):
        """
        Vide le buffer en écrivant toutes les métriques en DB.
        Utilise insert_many pour performance (1 requête au lieu de N).
        """
        
        with self._buffer_lock:
            if not self._buffer:
                return
            
            #copier le buffer et le vider
            metrics_to_write = list(self._buffer)
            self._buffer.clear()
            
        if not metrics_to_write:
            return
        
        try:
            start = time.time()
            
            # 🚀 insert_many = beaucoup plus rapide que N x insert_one
            result = self.collection.insert_many(metrics_to_write,ordered=False)
            
            duration = time.time() - start
            logger.info(
                f"📊 [FLUSH] {len(metrics_to_write)} métriques écrites en {duration:.3f}s"  
            )
        except Exception as e:
            logger.error(
                f"❌ Erreur lors du flush de {len(metrics_to_write)} métriques: {e}",
                exc_info=True
            )
            # En cas d'erreur, remettre dans le buffer (retry)
            with self._buffer_lock:
                self._buffer.extendleft(reversed(metrics_to_write))
                
                
    def _add_to_buffer(self, metric_doc: Dict[str, Any]):
        """
        Ajoute une métrique au buffer (non-bloquant).
        Si buffer plein, flush immédiatement.
        """
        
        with self._buffer_lock:
            self._buffer.append(metric_doc)
            buffer_size = len(self._buffer)
            
            if buffer_size >= self.MAX_BUFFER_SIZE:
                logger.warning(
                    f"⚠️ Buffer plein ({buffer_size}), flush immédiat"
                )
                self._flush_buffer()
                
                
    def track_job_enqueued(
        self,
        job_id,
        user_id: str,
        search_params: Dict[str,Any]
    ):
        """
        Track quand un job est ajouté à la queue Redis.
        
        NON-BLOQUANT : Retourne immédiatement, écriture en background.
        """
        metric_doc = {
            "job_id": job_id,
            "user_id": user_id,
            "event_type": "job_enqueued",
            "timestamp": datetime.now(),
            "metadata": {
                "city": search_params.get("city"),
                "min_price": search_params.get("min_price"),
                "max_price": search_params.get("max_price"),
                "min_bedrooms": search_params.get("min_bedrooms"),
                "max_bedrooms": search_params.get("max_bedrooms"),
            }
        } 
        
        # Ajouter au buffer (retour immédiat)
        self._add_to_buffer(metric_doc)
        
        logger.debug(f"[METRIC] Job enqueued: {job_id[:12]}")
        
        
    def track_worker_started(
        self,
        job_id: str,
        user_id: str,
        queue_wait_seconds: float
    ):
        """
        Track quand un worker commence à traiter un job.
        Le queue_wait_seconds indique combien de temps le job a attendu.
        """
        metric_doc = {
            "job_id": job_id,
            "user_id": user_id,
            "event_type": "worker_started",
            "timestamp": datetime.now(),
            "duration_ms": queue_wait_seconds * 1000,
            "metadata": {
                "queue_wait_seconds": round(queue_wait_seconds, 3)
            }
        }
        
        self._add_to_buffer(metric_doc)
        
        logger.debug(
            f"[METRIC] Worker started: {job_id[:12]} (wait: {queue_wait_seconds:.2f}s)"
        )
        
    def track_session_check(
        self,
        job_id: str,
        user_id: str,
        session_existed: bool,
        session_created: bool,
        duration_seconds: float
    ):
        """
        Track la vérification/création de session.
        """
        metric_doc = {
            "job_id": job_id,
            "user_id": user_id,
            "event_type": "session_check",
            "timestamp": datetime.now(),
            "duration_ms": duration_seconds * 1000,
            "success": True,  # Si on arrive ici, c'est un succès
            "metadata": {
                "session_existed": session_existed,
                "session_created": session_created,
                "duration_seconds": round(duration_seconds, 3)
            }
        }
        
        self._add_to_buffer(metric_doc)
        
        status = "existed" if session_existed else ("created" if session_created else "failed")
        logger.debug(
            f"[METRIC] Session check: {job_id[:12]} ({status}, {duration_seconds:.2f}s)"
        )
        
    def track_google_places(
        self,
        job_id: str,
        user_id: str,
        success: bool,
        places_count: int,
        duration_seconds: float,
        error_message: Optional[str] = None
    ):
        """
        Track l'appel à l'API Google Places.
        """
        metric_doc = {
            "job_id": job_id,
            "user_id": user_id,
            "event_type": "google_places",
            "timestamp": datetime.utcnow(),
            "duration_ms": duration_seconds * 1000,
            "success": success,
            "error_message": error_message,
            "metadata": {
                "places_count": places_count,
                "duration_seconds": round(duration_seconds, 3)
            }
        }
        
        self._add_to_buffer(metric_doc)
        
        status = f"✅ {places_count} places" if success else f"❌ {error_message}"
        logger.debug(f"[METRIC] Google Places: {job_id[:12]} ({status})")
        

    def track_onepage_enrich(
        self,
        job_id: str,
        user_id: str,
        total_count: int,
        enriched_count: int,
        failed_count: int,
        duration_seconds: float
    ):
        """
        Track l'enrichissement des listings via OnePage.
        """
        metric_doc = {
            "job_id": job_id,
            "user_id": user_id,
            "event_type": "onepage_enrich",
            "timestamp": datetime.utcnow(),
            "duration_ms": duration_seconds * 1000,
            "success": enriched_count > 0,
            "metadata": {
                "total_count": total_count,
                "enriched_count": enriched_count,
                "failed_count": failed_count,
                "success_rate": (enriched_count / total_count * 100) if total_count > 0 else 0,
                "duration_seconds": round(duration_seconds, 3)
            }
        }
        
        self._add_to_buffer(metric_doc)
        
        logger.debug(
            f"[METRIC] OnePage: {job_id[:12]} ({enriched_count}/{total_count} enriched)"
        )
        
    def track_job_completed(
        self,
        job_id: str,
        user_id: str,
        total_duration_seconds: float,
        success: bool,
        listings_count: int = 0,
        error_message: Optional[str] = None
    ):
        """
        Track la complétion d'un job (succès ou échec).
        C'est la métrique END-TO-END la plus importante.
        """
        metric_doc = {
            "job_id": job_id,
            "user_id": user_id,
            "event_type": "job_completed",
            "timestamp": datetime.now(),
            "duration_ms": total_duration_seconds * 1000,
            "success": success,
            "error_message": error_message,
            "metadata": {
                "listings_count": listings_count,
                "total_duration_seconds": round(total_duration_seconds, 3)
            }
        }
        
        self._add_to_buffer(metric_doc)
        
        status = f"✅ {listings_count} listings" if success else f"❌ {error_message}"
        logger.info(
            f"[METRIC] Job completed: {job_id[:12]} ({status}, {total_duration_seconds:.2f}s)"
        )
        
    def shutdown(self):
        """
        Arrêt propre : flush le buffer avant de quitter.
        À appeler avant d'arrêter l'application.
        """
        logger.info("🛑 Shutdown WorkflowMetrics...")
        
        # Arrêter le thread de flush
        self._stop_flush.set()
        if self._flush_thread:
            self._flush_thread.join(timeout=10)
        
        # Flush final
        self._flush_buffer()
        
        logger.info("✅ WorkflowMetrics shutdown complete")
            
            
# 🆕 Instance globale (singleton pattern pour production)
_workflow_metrics_instance = None

def get_workflow_metrics() -> WorkflowMetrics:
    """
    Retourne l'instance singleton de WorkflowMetrics.
    Évite de créer plusieurs threads de flush.
    """
    global _workflow_metrics_instance
    if _workflow_metrics_instance is None:
        _workflow_metrics_instance = WorkflowMetrics()
    return _workflow_metrics_instance
            
            
        
        
        
        
        
        