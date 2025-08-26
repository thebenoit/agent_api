# server.py
import os
import uvicorn

# from agents.ian import graph
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from langchain_core.messages import HumanMessage, AIMessage
from fastapi.responses import StreamingResponse
from auth.middleware import auth_middleware
from database import mongo_db
import json
from agents.graph import IanGraph
from schemas import ChatRequest
from database_manager import mongo_manager
import atexit
import logging
import asyncio

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
    return await auth_middleware(request, call_next)


# class ChatRequest(BaseModel):
#     message: str

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
        "http://localhost:4000",  # Express server
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
        redis_url = os.getenv("REDIS_URL")
        r = redis.from_url(redis_url, decode_responses=True)
        pubsub = r.pubsub()
        channel = f"sse:job:{job_id}"
        pubsub.subscribe(channel)

        async def event_generator():
            try:
                while True:
                    message = pubsub.get_message(timeout=10.0)
                    if message and message.get("type") == "message":
                        data = message.get("data", "")
                        yield f"data: {data}\n\n"
                    await asyncio.sleep(0.05)
            finally:
                try:
                    pubsub.unsubscribe(channel)
                    pubsub.close()
                except Exception as e:
                    pass
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de job_events: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
        



@app.get("/user/info")
async def get_user_info(req: Request):
    """Récupère les informations de l'utilisateur authentifié"""
    return {
        "user_id": req.state.user_id,
        "thread_id": req.state.thread_id,
        "user": req.state.user,
    }
    
    



# ... existing code ...


@app.post("/chat")
async def chat(request: ChatRequest, req: Request):
    try:
        # get the user message
        # user_message = request.messages

        user_info = mongo_db.get_user_by_id(req.state.user_id)
        if user_info is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Utilisateur non trouvé",
                    "message": "L'utilisateur n'existe plus dans la base de données",
                },
            )


        # Utiliser le thread_id de l'utilisateur authentifié
        config = {"configurable": {"thread_id": user_info["_id"]}}

        agent_response = await agent._get_response(
            messages=request.messages,
            session_id=user_info["_id"],
            user_id=user_info["_id"],
        )


        return {"response": agent_response}
    except NotImplementedError as e:
        logger.error(f"Erreur NotImplementedError: {e}")
        return JSONResponse(
            status_code=501,
            content={
                "error": "Fonctionnalité non implémentée",
                "message": "Cette fonctionnalité n'est pas encore disponible",
                "details": str(e),
            },
        )
    except Exception as e:
        logger.error(f"Erreur générale: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Erreur interne du serveur",
                "message": "Une erreur s'est produite lors du traitement de votre demande",
                "details": "Veuillez réessayer plus tard",
            },
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
        )
