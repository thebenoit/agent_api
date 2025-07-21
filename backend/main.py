from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from api.chat import router as chat_router
from api.agents import router as agents_router

# Chargement des variables d'environnement
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    print("🚀 Démarrage du serveur MoveOutAI Backend")
    yield
    print("👋 Arrêt du serveur MoveOutAI Backend")

# Création de l'application FastAPI
app = FastAPI(
    title="MoveOutAI Backend",
    description="API backend pour l'assistant IA de recherche d'appartements",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS pour le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend Next.js
        "http://127.0.0.1:3000",
        "https://your-domain.com"  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes principales
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])

@app.get("/")
async def root():
    """Route de base pour vérifier que l'API fonctionne"""
    return {
        "message": "MoveOutAI Backend API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Vérification de l'état de santé de l'API"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
