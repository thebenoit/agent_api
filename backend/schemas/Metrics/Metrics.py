from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
from ...database_manager import mongo_manager
import redis
import logging

logger = logging.getLogger(__name__)

class Metrics(ABC):
    """
    Classe abstraite de base pour tous les collectors de métriques.
    
    Chaque type de metric (Session, User, Performance) hérite de cette classe. 
    """
    
    def __init__(self):
        """
        """
      
        
        