import os
from typing import Optional
from redis import Redis
from rq import Queue
from dotenv import load_dotenv

load_dotenv()


class RedisConfig:

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.cache_ttl = int(os.getenv("CACHE_TTL", 400))
        self.max_job_attempts = int(os.getenv("MAX_JOB_ATTEMPTS", 3))
        self.job_timeout = int(os.getenv("JOB_TIMEOUT", 30))

    def get_redis_client(self) -> Redis:
        """Retourne le client Redis."""
        return Redis.from_url(self.redis_url, decode_responses=True)

    def get_scraping_queue(self) -> Queue:
        """Retourne la queue Redis."""
        redis_client = self.get_redis_client()
        return Queue("scraping", connection=redis_client)

    def get_cache_key(self, search_params: dict) -> str:
        """Retourne la clé de cache pour les paramètres de recherche."""
        import hashlib
        import json

        normalized = {
            "city": search_params.get("city", "").lower().strip(),
            "min_bedrooms": search_params.get("min_bedrooms", 0),
            "max_bedrooms": search_params.get("max_bedrooms", 0),
            "min_price": search_params.get("min_price", 0),
            "max_price": search_params.get("max_price", 0),
            "location_near": sorted(search_params.get("location_near", [])),
            "enrich_top_k": search_params.get("enrich_top_k", 4),
        }

        params_str = json.dumps(normalized, sort_keys=True)
        return f"search_results:{hashlib.sha256(params_str.encode()).hexdigest()}"
