import os
import sys
import json
import logging
import time
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
import redis
from rq import Worker, Queue, get_current_job
import signal
import multiprocessing
from datetime import datetime

multiprocessing.set_start_method("spawn", force=True)

# Ajouter le chemin du projet
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.tools.searchFacebook import SearchFacebook
from agents.tools.googlePlaces import GooglePlaces
from services.search_service import SearchService

load_dotenv()

os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(process)d - %(thread)d - %(message)s",
)
logger = logging.getLogger(__name__)


class ScrapingWorker:
    """
    Working RQ avec ThreadPoolExecutor pour gérer 50-100 requêtes/seconde.
    utilise des threads pour le scraping concurrentet des processus pour l'isolation
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

        self.max_workers = int(
            os.getenv("MAX_WORKER_THREADS", 20)
        )  # 20 threads par worker
        self.thread_pool = ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="scraper"
        )

        # Outils de scraping
        self.facebook_scraper = None
        self.google_places = None
        self.search_service = SearchService()

        # Métriques de performance
        self.jobs_processed = 0
        self.jobs_failed = 0
        self.start_time = time.time()

        # Gestion des signaux pour arrêt propre
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """
        Arrêt propre du worker
        """
        logger.info(f"Signal {signum} reçu. Arrêt en cours...")
        self.thread_pool.shutdown(wait=True)
        sys.exit(0)

    def _publish_event(self, job_id: str, event: str, payload: dict):
        """
        Publie un événement SSE sur le canal Redis du job
        """
        try:
            channel = f"sse:job:{job_id}"
            data = json.dumps({"event": event, "payload": payload}, default=str)
            self.redis_client.publish(channel, data)
        except Exception as e:
            logger.warning(f"[{job_id}] publish_event error: {e}")

    def _init_scraper(self):
        """
        Initialise les scrapers
        """
        try:
            if self.facebook_scraper is None:
                self.facebook_scraper = SearchFacebook()
            if self.google_places is None:
                self.google_places = GooglePlaces()
            logger.info("Scrapers initialisés avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des scrapers: {e}")
            raise

    def scrape_listings(
        self, search_params: dict[str, Any], user_id: str
    ) -> List[dict[str, Any]]:
        """
        Fonction de scraping qui sera exécutée par les workers RQ
        """
        start_time = time.time()
        rq_job = get_current_job()
        job_id = rq_job.id if rq_job else f"{user_id[:8]}_{int(time.time())}"

        try:
            logger.info(f"Worker démarré pour user {user_id[:8]}")
            self._publish_event(job_id, "start", {"message": "Démarrage du scraping"})
            self._init_scraper()

            city = search_params.get("city", "")
            min_bedrooms = search_params.get("min_bedrooms", 1)
            max_bedrooms = search_params.get("max_bedrooms", 5)
            min_price = search_params.get("min_price", 0)
            max_price = search_params.get("max_price", 10000)
            location_near = search_params.get("location_near", [])
            enrich_top_k = search_params.get("enrich_top_k", 3)

            logger.info(f"[{job_id}] Recherche de Google Places {city}")
            places_results = self.google_places.execute(city, location_near)

            if not places_results.get("places"):
                error_msg = f"Aucune place trouvée pour {city}"
                error_payload = {
                    "error": error_msg,
                    "message": "Aucun lieu trouvé pour cette ville",
                    "timestamp": datetime.now().isoformat(),
                    "retry_possible": True,
                }
                self._publish_event(job_id, "error", error_payload)
                raise Exception(error_msg)

            import random

            selected_place = random.choice(places_results["places"])
            lat = selected_place["location"]["latitude"]
            lon = selected_place["location"]["longitude"]

            self._publish_event(
                job_id, "progress", {"message": f"Coordonnées trouvées"}
            )

            # 2. Scraping Facebook avec ThreadPoolExecutor
            logger.info(f"[{job_id}] Coordonnées: lat={lat}, lon={lon}")

            logger.info(f"[{job_id}] Début scraping Facebook")

            # Utiliser le ThreadPool pour le scraping concurrent
            future = self.thread_pool.submit(
                self._scrape_facebook_sync,
                lat,
                lon,
                min_price,
                max_price,
                min_bedrooms,
                max_bedrooms,
                user_id,
                enrich_top_k,
            )

            try:
                listings = future.result(
                    timeout=60
                )  # timeout 25s pour laisser 5s de marge
                logger.info(f"[{job_id}] Scraping terminé: {len(listings)} listings")

                # Mettre en cache le résultat
                cache_key = self.search_service._generate_cache_key(search_params)
                self.redis_client.setex(
                    cache_key,
                    300,  # TTL 5 minutes
                    json.dumps(listings),
                )

                # Nettoyer de la clé job
                job_key = f"job:{cache_key}"
                self.redis_client.delete(job_key)

                self.jobs_processed += 1
                elapsed = time.time() - start_time
                logger.info(f"[{job_id}] Job terminé en {elapsed:.2f}s")
                payload = {
                    "status": "success",
                    "listings": listings,
                    "processing_time": elapsed,
                    "coordinates": {"lat": lat, "lon": lon},
                }
                self._publish_event(job_id, "completed", payload)

                return {
                    "status": "success",
                    "listings": listings,
                    "count": len(listings),
                    "processing_time": elapsed,
                    "coordinates": {"lat": lat, "lon": lon},
                }
            except Exception as e:
                logger.error(f"[{job_id}] Timeout ou erreur scraping {e}")
                self.jobs_failed += 1
                logger.error(f"[{job_id}] Erreur scraping: {e}")
                error_payload = {
                    "error": str(e),
                    "message": "Erreur lors du scraping Facebook",
                    "timestamp": datetime.now().isoformat(),
                    "retry_possible": True,
                }
                self._publish_event(job_id, "error", error_payload)
                raise
        except Exception as e:
            self.jobs_failed += 1
            logger.error(f"[{job_id}] Erreur fatale: {e}")
            error_payload = {
                "error": str(e),
                "message": "Erreur fatale lors du scraping",
                "timestamp": datetime.now().isoformat(),
                "retry_possible": False,
            }
            self._publish_event(job_id, "error", error_payload)
            raise

    def _scrape_facebook_sync(
        self,
        lat: float,
        lon: float,
        min_price: float,
        max_price: float,
        min_bedrooms: int,
        max_bedrooms: int,
        user_id: str,
        enrich_top_k: int,
    ) -> List[dict[str, Any]]:
        """
        Scraping Facebook de manière synchrone (appelé par ThreadPoolExecutor).
        cette méthode s'exécute dans un thread séparé
        """
        try:
            # créer un event loop pour ce thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Exécuter le scraping asynchrone
                result = loop.run_until_complete(
                    self.facebook_scraper.execute_async(
                        lat,
                        lon,
                        min_price,
                        max_price,
                        min_bedrooms,
                        max_bedrooms,
                        user_id,
                        [],
                        top_k=enrich_top_k,
                    )
                )
                return result or []

            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Erreur dans _scrape_facebook_sync: {e}")
            error_payload = {
                "error": str(e),
                "message": "Erreur lors du scraping Facebook asynchrone",
                "timestamp": datetime.now().isoformat(),
                "retry_possible": True,
            }
            self._publish_event(job_id, "error", error_payload)
            return []

    def get_metrics(self) -> dict[str, Any]:
        """
        Retourne les métriques de performance du worker
        """
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": uptime,
            "jobs_processed": self.jobs_processed,
            "jobs_failed": self.jobs_failed,
            "success_rate": (
                (self.jobs_processed / (self.jobs_processed + self.jobs_failed)) * 100
                if (self.jobs_processed + self.jobs_failed) > 0
                else 0
            ),
            "jobs_per_second": self.jobs_processed / uptime if uptime > 0 else 0,
            "max_workers": self.max_workers,
            "worker_pid": os.getpid(),
        }


def scrape_listings_job(
    search_params: dict[str, Any], user_id: str
) -> List[dict[str, Any]]:
    """
    Fonction standalone pour RQ - crée une instance et appelle la méthode
    Cette fonction peut être appelée directement par RQ sans passer par la classe
    """
    try:
        worker_instance = ScrapingWorker()
        return worker_instance.scrape_listings(search_params, user_id)
    except Exception as e:
        logger.error(f"Erreur dans scrape_listings_job: {e}")
        raise


def start_worker():
    """
    Point d'entrée pour démarrer un worker RQ
    cette fonction est appelée par RQ pour chaque processus worker.
    """

    try:
        # Configuration Redis
        redis_url = os.getenv("REDIS_URL")

        # Créer la queue directement (plus besoin de Connection)
        queue = Queue("scraping", connection=redis.from_url(redis_url))

        # Créer et démarrer le worker
        worker = Worker([queue], connection=redis.from_url(redis_url))

        logger.info(f"Worker démarré avec PID {os.getpid()}")
        logger.info(f"Ecoute la queue: {queue.name}")

        # Nouvelle API RQ 2.5 - plus de paramètres incompatibles
        worker.work(
            with_scheduler=True,
            max_jobs=1000,  # Max jobs par worker avant redémarrage
        )

    except Exception as e:
        logger.error(f"Erreur fatale du worker: {e}")
        # Publier un événement d'erreur pour le démarrage du worker
        try:
            redis_client = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
            job_id = f"worker_startup_{int(time.time())}"
            error_payload = {
                "error": str(e),
                "message": "Erreur fatale lors du démarrage du worker",
                "timestamp": datetime.now().isoformat(),
                "retry_possible": False,
            }
            channel = f"sse:job:{job_id}"
            data = json.dumps({"event": "error", "payload": error_payload}, default=str)
            redis_client.publish(channel, data)
        except Exception as publish_error:
            logger.error(f"Erreur lors de la publication de l'événement d'erreur de démarrage: {publish_error}")
        sys.exit(1)


if __name__ == "__main__":
    start_worker()
