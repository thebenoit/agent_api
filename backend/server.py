# server.py
import os
import uvicorn
from agents.ian import graph
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional, List
from langchain_core.messages import HumanMessage, AIMessage
from fastapi.responses import StreamingResponse
from auth.middleware import auth_middleware
from database import mongo_db
import json

app = FastAPI()


# Ajouter le middleware d'authentification
@app.middleware("http")
async def auth_middleware_wrapper(request: Request, call_next):
    return await auth_middleware(request, call_next)


class ChatRequest(BaseModel):
    system_prompt: str
    message: str
    session_id: str
    # chat_history: Optional[List[dict]] = None


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


@app.post("/chat")
async def chat(request: ChatRequest, req: Request):
    # get the user message
    user_message = request.message

    user_info = await mongo_db.get_user_by_id(req.state.user_id)
    if user_info is None:
        return {"error": "Utilisateur non trouvé"}, 404
    
    input_data = {
         "messages": [{"role": "user", "content": user_message}]
    }
    # Utiliser le thread_id de l'utilisateur authentifié
    config = {"configurable": {"thread_id": user_info["chatId"]}}

    response = await graph.ainvoke(
        input=input_data,
        config=config,
    )


    return {"response": response}

