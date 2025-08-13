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
    logger.info(f"Cookies: {request.cookies}")

    if request.method == "OPTIONS":
        logger.info("Requête OPTIONS détectée - passage direct au middleware suivant")
        return await call_next(request)

    try:
        secret_key = os.getenv("SECRET_KEY")
        logger.info(f"SECRET_KEY configurée: {'Oui' if secret_key else 'Non'}")

        if not secret_key:
            logger.error("SECRET_KEY non configurée")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Erreur de configuration",
                    "message": "SECRET_KEY non configurée",
                    "details": "Le serveur n'est pas correctement configuré",
                },
            )

        # Extraire le token du header Authorisation OU du cookie
        auth_header = request.headers.get("Authorization")
        session_cookie = request.cookies.get("session_id")

        logger.info(f"Header Authorization: {auth_header}")
        logger.info(
            f"Cookie session_id: {session_cookie[:20] if session_cookie else 'Non trouvé'}..."
        )

        # Déterminer la source du token
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Vérifier si le token du header est vide ou null
            if token and token.lower() != "null" and token.strip() != "":
                logger.info("Token extrait du header Authorization")
            elif session_cookie:
                token = session_cookie
                logger.info("Token extrait du cookie session_id (header vide)")
            else:
                logger.warning("Token d'authentification manquant")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Authentification requise",
                        "message": "Token d'authentification manquant",
                        "details": "Veuillez vous connecter",
                    },
                )
        elif session_cookie:
            token = session_cookie
            logger.info("Token extrait du cookie session_id")
        else:
            logger.warning("Token d'authentification manquant")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentification requise",
                    "message": "Token d'authentification manquant",
                    "details": "Veuillez vous connecter",
                },
            )

        logger.info(f"Token extrait: {token[:20]}...")

        try:
            # Decode le token
            logger.info("Tentative de décodage du token...")
            decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
            logger.info(f"Token décodé avec succès: {decoded}")

            # Changement de user_id vers userId pour correspondre au frontend
            user_id = decoded.get("userId")
            logger.info(f"userId extrait du token: {user_id}")
            logger.info(f"Type de userId: {type(user_id)}")

            if isinstance(user_id, dict) and "_id" in user_id:
                logger.info(f"user_id['_id']: {user_id['_id']}")
            else:
                logger.warning(f"user_id n'est pas un dict avec '_id': {user_id}")

            if not user_id:
                logger.error("user_id manquant dans le token décodé")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Token invalide",
                        "message": "Le token ne contient pas d'identifiant utilisateur valide",
                        "details": "Veuillez vous reconnecter pour obtenir un nouveau token",
                    },
                )

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
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Utilisateur non trouvé",
                        "message": "L'utilisateur associé à ce token n'existe plus",
                        "details": "Veuillez vous reconnecter",
                    },
                )

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

        except jwt.ExpiredSignatureError as e:
            logger.error(f"Token expiré: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token expiré",
                    "message": "Votre session a expiré",
                    "details": "Veuillez vous reconnecter pour obtenir un nouveau token",
                },
            )
        except jwt.InvalidSignatureError as e:
            logger.error(f"Signature du token invalide: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token invalide",
                    "message": "Le token d'authentification est corrompu",
                    "details": "Veuillez vous reconnecter pour obtenir un nouveau token",
                },
            )
        except jwt.DecodeError as e:
            logger.error(f"Erreur de décodage JWT: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token invalide",
                    "message": "Le format du token d'authentification est incorrect",
                    "details": "Veuillez vous reconnecter pour obtenir un nouveau token",
                },
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"Token JWT invalide: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token invalide",
                    "message": "Le token d'authentification est invalide",
                    "details": "Veuillez vous reconnecter pour obtenir un nouveau token",
                },
            )
        except Exception as e:
            logger.error(
                f"Erreur inattendue lors du décodage: {type(e).__name__}: {str(e)}"
            )
            logger.error(f"Traceback complet:", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Erreur d'authentification",
                    "message": "Une erreur s'est produite lors de l'authentification",
                    "details": "Veuillez réessayer plus tard",
                },
            )
    except Exception as e:
        logger.error(f"Erreur critique dans le middleware: {e}")
        logger.error(f"Traceback complet:", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Erreur interne du serveur",
                "message": "Une erreur inattendue s'est produite",
                "details": "Veuillez réessayer plus tard",
            },
        )
