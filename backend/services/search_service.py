import os
import asyncio
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from redis import Redis
import redis
from rq import Queue, get_current_job
from rq.job import Job

from config.redisConfig import RedisConfig
from agents.tools.searchFacebook import SearchFacebook
from agents.tools.googlePlaces import GooglePlaces

logger = logging.getLogger(__name__)


class SearchService:
    """Service de recherche avec cache Redis et queue RQ"""

    def __init__(self):
        # Configuration Redis
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

        # Configuration des queues
        self.scraping_queue = Queue("scraping", connection=self.redis_client)
        self.cache_ttl = int(os.getenv("CACHE_TTL", 300))  # 5 minutes
        self.max_job_attempts = int(os.getenv("MAX_JOB_ATTEMPTS", 3))
        self.job_timeout = int(os.getenv("JOB_TIMEOUT", 90))

        # Rate limiting
        self.rate_limit_window = 60  # 1 minute
        self.max_requests_per_window = 100  # 100 requêtes par minute par IP

    def _generate_cache_key(self, search_params: Dict[str, Any]) -> str:
        """
        Génère une clé de cache normalisée et idempotente.
        CRUCIAL pour la production : évite le scraping répété.
        """
        # Normaliser les paramètres pour l'idempotence
        # Normaliser les paramètres pour l'idempotence
        location_near = search_params.get("location_near", [])
        if location_near is None:
            location_near = []

        normalized = {
            "city": str(search_params.get("city", "")).lower().strip(),
            "min_bedrooms": int(search_params.get("min_bedrooms", 0)),
            "max_bedrooms": int(search_params.get("max_bedrooms", 0)),
            "min_price": int(search_params.get("min_price", 0)),
            "max_price": int(search_params.get("max_price", 0)),
            "location_near": sorted([str(x).lower().strip() for x in location_near]),
            "enrich_top_k": int(search_params.get("enrich_top_k", 4)),
        }

        # Hash SHA-256 pour une clé unique et sécurisée
        params_str = json.dumps(normalized, sort_keys=True)
        return f"search_results:{hashlib.sha256(params_str.encode()).hexdigest()}"

    def _check_rate_limit(self, user_ip: str) -> bool:
        """
        Vérifie le rate limiting par IP.
        PROTECTION contre le spam et la surcharge.
        """
        key = f"rate_limit:{user_ip}"
        current_count = self.redis_client.get(key)

        if current_count is None:
            # Première requête dans la fenêtre
            self.redis_client.setex(key, self.rate_limit_window, 1)
            return True

        current_count = int(current_count)
        if current_count >= self.max_requests_per_window:
            logger.warning(f"Rate limit dépassé pour IP: {user_ip}")
            return False

        # Incrémenter le compteur
        self.redis_client.incr(key)
        return True

    async def search_listings(
        self, search_params: Dict[str, Any], user_ip: str, user_id: str
    ) -> Dict[str, Any]:
        """
        Recherche principale avec cache et queue.
        NON-BLOQUANT pour FastAPI - retourne immédiatement.
        """

        # 1. Vérifier le rate limiting
        # if not self._check_rate_limit(user_ip):
        #     return {
        #         "status": "rate_limited",
        #         "message": "Trop de requêtes. Réessayez dans 1 minute.",
        #         "retry_after": 60,
        #     }

        # 2. Vérifier le cache Redis
        cache_key = self._generate_cache_key(search_params)
        # cached_result = self.redis_client.get(cache_key)

        # if cached_result:
        #     logger.info(f"Cache hit pour {cache_key}")
        #     return {
        #         "status": "cached",
        #         "data": json.loads(cached_result),
        #         "cached_at": datetime.now().isoformat(),
        #     }

        # # 3. Vérifier si un job est déjà en cours
        job_key = f"job:{cache_key}"
        # existing_job_id = self.redis_client.get(job_key)

        # if existing_job_id:
            # Job en cours, retourner le statut
            # try:
            #     job = Job.fetch(existing_job_id, connection=self.redis_client)
            #     if job.is_finished:
            #         # Job terminé, récupérer le résultat
            #         result = job.result
            #         if result:
            #             # Mettre en cache et nettoyer
            #             self.redis_client.setex(
            #                 cache_key, self.cache_ttl, json.dumps(result)
            #             )
            #             self.redis_client.delete(job_key)
            #             return {"status": "completed", "data": result}
            #         else:
            #             # Job échoué, nettoyer et relancer
            #             self.redis_client.delete(job_key)
            #     elif job.is_failed:
            #         # Job échoué, nettoyer et relancer
            #         self.redis_client.delete(job_key)
            #     else:
            #         # Job en cours
            #         return {
            #             "status": "processing",
            #             "job_id": existing_job_id,
            #             "estimated_wait": "10-30 secondes",
            #         }
            # except Exception as e:
            #     logger.error(f"Erreur lors de la récupération du job: {e}")
            #     self.redis_client.delete(job_key)

        # 4. Créer un nouveau job de scraping
        try:
            # Ajouter le job à la queue RQ
            job = self.scraping_queue.enqueue(
                "workers.scraping_workers.scrape_listings_job",
                args=(search_params, user_id),
                job_timeout=self.job_timeout,
                # retry=self.max_job_attempts,
                retry_backoff=60,  # Retry après 1 minute
                result_ttl=300,  # Garder le résultat 5 minutes
                failure_ttl=60,  # Garder l'échec 1 minute
            )

            # Marquer qu'un job est en cours pour cette recherche
            self.redis_client.setex(job_key, self.job_timeout + 60, job.id)

            logger.info(f"Nouveau job créé: {job.id} pour {cache_key}")

            return {
                "status": "queued",
                "job_id": job.id,
                "estimated_wait": "10-30 secondes",
                "message": "Recherche en cours. Utilisez le job_id pour vérifier le statut.",
            }

        except Exception as e:
            logger.error(f"Erreur lors de la création du job: {e}")
            return {
                "status": "error",
                "message": "Erreur lors de la création du job de recherche",
                "error": str(e),
            }

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Vérifie le statut d'un job de scraping.
        Permet au frontend de poller le statut.
        """
        try:
            job = Job.fetch(job_id, connection=self.redis_client)

            if job.is_finished:
                result = job.result
                if result:
                    return {
                        "status": "completed",
                        "data": result,
                        "completed_at": (
                            job.ended_at.isoformat() if job.ended_at else None
                        ),
                    }
                else:
                    return {"status": "failed", "error": "Job terminé sans résultat"}

            elif job.is_failed:
                return {
                    "status": "failed",
                    "error": str(job.exc_info),
                    "attempts": job.meta.get("retry", 0),
                }
            elif job.is_started:
                return {
                    "status": "processing",
                    "started_at": job.started_at.isoformat(),
                }

            else:
                return {"status": "queued", "created_at": job.created_at.isoformat()}

        except Exception as e:
            logger.error(f"Erreur lors de la vérification du job {job_id}: {e}")
            return {"status": "error", "error": str(e)}

    def cleanup_expired_jobs(self):
        """
        Nettoie les jobs expirés et les clés de cache.
        Maintenance pour éviter l'accumulation de données.
        """
        try:
            # Nettoyer les clés de job expirées
            job_keys = self.redis_client.keys("job:*")
            for key in job_keys:
                if not self.redis_client.exists(key):
                    self.redis_client.delete(key)

            logger.info(f"Nettoyage terminé. {len(job_keys)} clés vérifiées.")

        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
