import os
import json
import logging
import redis

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self):
        """
        Initialise le client Redis pour publier les événements SSE.
        """
        redis_url = os.getenv("REDIS_URL", "")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

    def publish(self, job_id: str, event: str, payload: dict) -> None:
        """
        Publie un événement SSE sur le canal Redis du job donné.
        """
        channel = f"sse:job:{job_id}"
        try:
            message = json.dumps({"event": event, "payload": payload}, default=str)
            self.redis_client.publish(channel, message)
        except Exception as e:
            logger.warning(f"[{job_id}] publish_event error: {e}")
