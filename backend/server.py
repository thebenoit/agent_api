# server.py
import os
import uvicorn

# from agents.ian import graph
from fastapi import FastAPI, Request
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

agent = IanGraph()

app = FastAPI()


# Ajouter le middleware d'authentification
@app.middleware("http")
async def auth_middleware_wrapper(request: Request, call_next):
    return await auth_middleware(request, call_next)


# class ChatRequest(BaseModel):
#     message: str


class chatResponse(BaseModel):
    response: str
    listings: Optional[List[dict]] = None
    map_data: Optional[dict] = None
    chat_history: Optional[List[dict]] = None


# Route de santé (optionnelle, LangGraph a déjà ses endpoints)
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {"Hello": "World"}


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
            return {"error": "Utilisateur non trouvé"}, 404

        # print("user_info:", user_info)

        # input_data = {"messages": [{"role": "user", "content": user_message}]}

        # Utiliser le thread_id de l'utilisateur authentifié
        config = {"configurable": {"thread_id": user_info["chatId"]}}

        agent_response = await agent._get_response(
            messages=request.messages,
            session_id=user_info["chatId"],
            user_id=user_info["_id"],
        )

        # response = await graph.ainvoke(
        #     input=input_data,
        #     config=config,
        # )

        # response = await graph.ainvoke(input=input_data, config=config)

        ##Ajouter Human Message dans la base de données

        ##Ajouter AI Message dans la base de données

        return {"response": agent_response}
    except NotImplementedError as e:
        print(f"Erreur NotImplementedError: {e}")
        return {"error": "Fonctionnalité non implémentée", "details": str(e)}, 501
    except Exception as e:
        print(f"Erreur générale: {e}")
        return {"error": "Erreur interne du serveur", "details": str(e)}, 500


# Gestionnaire de fermeture propre
@atexit.register
def cleanup():
    """Ferme proprement les connexions MongoDB à la fermeture de l'application."""
    mongo_manager.close_all()
