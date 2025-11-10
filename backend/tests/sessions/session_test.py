import os
import sys
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, backend_dir)
import asyncio
import pytest
from datetime import datetime
from typing import Dict, Optional
# Ajouter le chemin du projet à sys.path


from sessionManager import SessionsManager
from services.search_service import SearchService

import logging

logger = logging.getLogger(__name__)

    
async def test():
    manager = SessionsManager()
    
    logger.info("Starting session creation test for user: test_user_125")
    
    result = await manager.create_session_for_user("test_user_125")
    
    logger.info(f"Session creation result: {result}")
    
    # Voir les métriques
    logger.info("Retrieving metrics summary for the last hour")
    summary = await manager.metrics.get_metrics_summary(hours=1)
    logger.info(f"Metrics summary: {summary}")

asyncio.run(test())