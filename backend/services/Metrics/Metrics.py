from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
import redis
import logging

logger = logging.getLogger(__name__)

class MetricsCollecotr(ABC):
    """
    Classe abstraite de base pour tous les collectors de métriques.
    
    Chaque type de metric (Session, User, Performance) hérite de cette classe. 
    """
    
    def __init__(self):
        """
        """