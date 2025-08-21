import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from redis import Redis
from rq import Queue, get_current_job
from rq.job import Job

from models.redisConfig import RedisConfig
from agents.tools.searchFacebook import SearchFacebook
from agents.tools.googlePlaces import GooglePlaces

logger = logging.getLogger(__name__)


class SearchService:
    """Service de recherche avec cache Redis et queue RQ"""

    def __init__(self):
        self.config = RedisConfig()
        self.redis_client = self.config.get_redis_client()
        self.scraping_queue = self.config.get_scraping_queue()
