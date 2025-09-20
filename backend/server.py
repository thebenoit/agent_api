# server.py
import os
import uvicorn

# from agents.ian import graph
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from langchain_core.messages import HumanMessage, AIMessage
from fastapi.responses import StreamingResponse
from auth.middleware import auth_middleware
from middleware.access_control_middleware import access_control_middleware
from database import mongo_db
import json
from agents.graph import IanGraph
from schemas import ChatRequest, Message
from database_manager import mongo_manager
import atexit
import logging
import asyncio
import redis
from rq import Queue
from workers.fb_session_worker import create_fb_session_job
from langchain_core.callbacks.manager import AsyncCallbackManager
from langchain_core.callbacks.base import AsyncCallbackHandler
from bson import ObjectId  # pour sérialiser les ObjectId


# Configuration du logging
logger = logging.getLogger(__name__)

agent = IanGraph()

app = FastAPI()


# Gestionnaire d'exceptions global
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Gestionnaire global pour les HTTPException"""
    logger.error(f"HTTPException capturée: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Erreur HTTP",
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestionnaire global pour toutes les autres exceptions"""
    logger.error(f"Exception non gérée: {type(exc).__name__}: {str(exc)}")
    logger.error("Traceback complet:", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erreur interne du serveur",
            "message": "Une erreur inattendue s'est produite",
            "details": "Veuillez réessayer plus tard",
        },
    )


# Ajouter le middleware d'authentification
@app.middleware("http")
async def auth_middleware_wrapper(request: Request, call_next):
    if (
        request.url.path.startswith("/docs")
        or request.url.path.startswith("/openapi.json")
        or request.url.path.startswith("/fb-session/enqueue")
    ):
        print("docs")
        return await call_next(request)

    return await auth_middleware(request, call_next)


#Middleware pour contrôler l'accès au chat stream
@app.middleware("http")
async def access_control_wrapper(request: Request, call_next):
    return await access_control_middleware(request, call_next)


# class ChatRequest(BaseModel):
#     message: str

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
        "http://localhost:4000",  # Express server
        "https://www.moveout.ai",
        "https://moveout.ai"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class chatResponse(BaseModel):
    response: str
    listings: Optional[List[dict]] = None
    map_data: Optional[dict] = None
    chat_history: Optional[List[dict]] = None


# Route de santé (optionnelle, LangGraph a déjà ses endpoints)
@app.get("/health")
async def health():
    return {"status": "ok"}


@atexit.register
def cleanup():
    """Ferme proprement les connexions MongoDB à la fermeture de l'application."""
    mongo_manager.close_all()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/events/jobs/{job_id}")
async def job_events(job_id: str):
    """
    SSE: écoute les événements du job via Redis Pub/Sub.
    Le worker publie sur: sse:job:{job_id}
    """
    try:
        # connexion à redis
        redis_url = os.getenv("REDIS_URL")
        r = redis.from_url(redis_url, decode_responses=True)

        # Abonnement au channel
        pubsub = r.pubsub()
        channel = f"sse:job:{job_id}"
        pubsub.subscribe(channel)

        async def event_generator():
            try:
                while True:  # Boucle infinie pour écouter les événements
                    # ecoute les messages de redis
                    message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)

                    if message and message.get("type") == "message":
                        raw = message.get("data", "")
                        try:
                            obj = json.loads(raw)            # ton worker publie déjà du JSON
                            event_name = obj.get("event", "message")  # ex: "progress", "completed"
                            # on renvoie un vrai SSE avec un nom d’événement
                            yield f"event: {event_name}\n"
                            yield f"data: {json.dumps(obj)}\n\n"
                        except Exception:
                            # fallback si jamais ce n’est pas du JSON
                            yield f"data: {raw}\n\n"

                    await asyncio.sleep(0.05)
            finally:
                try:
                    
                    pubsub.unsubscribe(channel)
                    pubsub.close()
                except Exception as e:
                    pass

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
    },
)
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de job_events: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")


@app.get("/user/info")
async def get_user_info(req: Request):
    """Récupère les informations de l'utilisateur authentifié"""
    user = req.state.user
    user_serializable = {}
    for key, value in user.items():
        if isinstance(value, ObjectId):
            user_serializable[key] = str(value)
        else:
            user_serializable[key] = value

    return {
        "user_id": req.state.user_id,
        "thread_id": req.state.thread_id,
        "user": user_serializable,
    }


@app.post("/fb-session/enqueue/{user_id}")
async def enqueue_fb_session(user_id: str):
    """
    Enqueue un job RQ pour créer ou rafraîchir la session FB pour user_id
    """
    redis_url = os.getenv("REDIS_URL")
    conn = redis.from_url(redis_url, decode_responses=True)
    queue = Queue("fb_session", connection=conn)
    job = queue.enqueue(create_fb_session_job, user_id)
    return {"enqueued": True, "job_id": job.id}


@app.get("/chat/stream")
async def chat_stream(message: str, req: Request):

    checkpointer_id = req.state.user_id

    msg = Message(role="user", content=message)

    return StreamingResponse(
        agent.get_stream_response([msg], checkpointer_id),
        media_type="text/event-stream",
    )


# Gestionnaire de fermeture propre
@atexit.register
def cleanup():
    """Ferme proprement les connexions MongoDB à la fermeture de l'application."""
    mongo_manager.close_all()


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        access_log=True,
        reload=True,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
