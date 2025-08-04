import os
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import jwt
from typing import Optional
from database import mongo_db

# Configuration du logging - Désactiver les logs PyMongo
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Désactiver les logs de debug de PyMongo
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
logging.getLogger("pymongo.connection").setLevel(logging.WARNING)
logging.getLogger("pymongo.server").setLevel(logging.WARNING)
logging.getLogger("pymongo.pool").setLevel(logging.WARNING)


async def auth_middleware(request: Request, call_next):
    """middleware to authenticate the user"""
    logger.info(f"=== DÉBUT MIDDLEWARE AUTH ===")
    logger.info(f"URL: {request.url}")
    logger.info(f"Méthode: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")

    try:
        secret_key = os.getenv("SECRET_KEY")
        logger.info(f"SECRET_KEY configurée: {'Oui' if secret_key else 'Non'}")

        if not secret_key:
            logger.error("SECRET_KEY non configurée")
            raise HTTPException(status_code=500, detail="SECRET_KEY non configurée")

        # Extraire le token du header Authorisation
        auth_header = request.headers.get("Authorization")
        logger.info(f"Header Authorization: {auth_header}")

        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Token d'authentification manquant ou format incorrect")
            raise HTTPException(
                status_code=401, detail="Token d'authentification manquant"
            )

        token = auth_header.split(" ")[1]
        logger.info(f"Token extrait: {token[:20]}...")

        try:
            # Decode le token
            logger.info("Tentative de décodage du token...")
            decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
            logger.info(f"Token décodé avec succès: {decoded}")

            user_id = decoded.get("user_id")
            logger.info(f"user_id extrait du token: {user_id}")
            logger.info(f"Type de user_id: {type(user_id)}")

            if isinstance(user_id, dict) and "_id" in user_id:
                logger.info(f"user_id['_id']: {user_id['_id']}")
            else:
                logger.warning(f"user_id n'est pas un dict avec '_id': {user_id}")

            if not user_id:
                logger.error("user_id manquant dans le token décodé")
                raise HTTPException(status_code=401, detail="Token invalide")

            logger.info("Recherche de l'utilisateur dans la base de données...")
            user = mongo_db.get_user_by_id(user_id)
            logger.info(f"Utilisateur trouvé: {'Oui' if user else 'Non'}")

            if user:
                logger.info(f"Type de user: {type(user)}")
                logger.info(
                    f"Clés de user: {list(user.keys()) if isinstance(user, dict) else 'N/A'}"
                )

            if not user:
                logger.error(f"Utilisateur non trouvé pour user_id: {user_id}")
                raise HTTPException(status_code=401, detail="Utilisateur non trouvé")

            # 5. Injecter les données dans request.state
            logger.info("Injection des données dans request.state...")
            request.state.user_id = user_id
            logger.info(f"user_id injecté: {request.state.user_id}")

            chat_id = user.get("chatId")
            logger.info(f"chatId extrait: {chat_id}")
            request.state.thread_id = chat_id
            logger.info(f"thread_id injecté: {request.state.thread_id}")

            request.state.user = user
            logger.info(f"user injecté: {type(request.state.user)}")

            # 6. Continuer vers l'endpoint
            logger.info("=== FIN MIDDLEWARE AUTH - CONTINUATION ===")
            return await call_next(request)

        except jwt.InvalidTokenError as e:
            logger.error(f"Erreur de décodage JWT: {e}")
            raise HTTPException(status_code=401, detail="Token invalide")
        except Exception as e:
            logger.error(f"Erreur détaillée: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback complet:", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Erreur d'authentification: {str(e)}"
            )
    except HTTPException:
        logger.info("HTTPException relancée")
        raise
    except Exception as e:
        logger.error(f"Erreur critique dans le middleware: {e}")
        logger.error(f"Traceback complet:", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")
