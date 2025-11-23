from database_manager import mongo_manager
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from Metrics import Metrics
import asyncio
import logging
from collections import deque
import threading
import time

logger = logging.getLogger(__name__)

class SearchMetrics(Metrics):
    """
    Metrics d'une recherche d'appartement de l'utilisateur
    """
    BATCH_SIZE = 100  # Écrire par batch de 100 métriques
    FLUSH_INTERVAL = 5  # Flush toutes les 5 secondes
    MAX_BUFFER_SIZE = 10000  # Si buffer > 10k, flush immédiatement
    
    
    def __inti__(self):
        super().__init__()
        
        self.db = mongo_manager.get_async_client()
        self.collection = self.db["search_metrics"]
        
        self._buffer = deque(maxlen=self.MAX_BUFFER_SIZE)
        self._buffer_lock = threading.Lock()
        
        self._flush_thread = None
        self._stop_flush = threading.Event()
        self._start_flush_thread()
        self._create_indexes()
        
        logger.info(
            "WorkflowMetrics initialisé (batch_size=%d, flush_interval=%ds)",
            self.BATCH_SIZE,
            self.FLUSH_INTERVAL
        )
    