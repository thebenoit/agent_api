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

    async def search_listings(
        self,
        search_params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        recherche avec cache et queue.
        """
        #1. Vérifier le rate limiting
        if not self.check_rate_limit(user_ip):
            return {
                "status":"rate_limited",
                "message":"Trop de requêtes.Réessayez dans 1 minute",
                "retry_after":60
            }
        #2.Vérfifier le cache Redis
        cache_key = self._generate_cache_key(search_params)
        cached_result = self.redis_client.get(cache_key)
        
        #3. Vérifier si un job est déjà en cours
        job_key = f"job{cache_key}"
        existing_job_id = self.redis_client.get(job_key)
        
        if existing_job_id:
            #Job en cours, retourner le statut
            try:
                job = Job.fetch(existing_job_id,connection=self.redis_client)
                if job.is_finished:
                    
                    result = job.result
                    if result:
                        #Mettre à jour le cache
                        self.redis_client.setex(cache_key, self.cache_ttl, json.dumps(result))
                        self.redis_client.delete(job_key)
                        return {"status":"completed","data":result}
                    else:
                        #job échoué, nettoyer et relancer
                        self.redis_client.delete(job_key)
                elif: job.is_failed:
                    #job échoué, nettoyer et relancer
                    self.redis_client.delete(job_key)
                else:
                    #job en cours
                    return {
                        "status":"processing",
                        "job_id":existing_job_id,
                        "estimated_wait":"10-30 secondes"
                    }
            except Exception as e:
                logger.error(f"Erreur lors de la récupération du job: {e}")
                self.redis_client.delete(job_key)
        
        #créer un nouveau job de scraping
        try:
            # Ajouter le job à la queue RQ
            job = self.scraping_queue.enqueue(
                "workers.scraping_worker.scrape_listings",
                args=(search_params, user_id),
                job_timeout=self.job_timeout,
                retry=self.max_job_attempts,
                retry_backoff=60, #Retry après 1 minute
                result_ttl=300, # Garder le resultat
                failure_ttl=60  # garder l'échec       
            )
            
            #Marquer qu'un jobn est en cours pour cette recherche 
            self.redis_client.setext(job_key,self.job_timeout + 60,job.id)
            
            logger.info(f"Mouveau job crée: {job.id} pour {cache_key}")
            
            return {
                "status":"queued".
                "job_id"job.id,
                "estimated_wait":"10-30 secondes"
                "message":"Recherche en cours. Utilisez le job_id pour vérifier le statut
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la création du job: {e}")
            return {
                "status":"error",
                "message":"Une erreur est survenue lors de la création du job"
                "error":str(e)
            }

        
            