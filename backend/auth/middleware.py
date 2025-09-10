import os
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import jwt
from typing import Optional
from database import mongo_db
import time

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Désactiver les logs de debug de PyMongo
logging.getLogger("pymongo").setLevel(logging.WARNING)

async def auth_middleware(request: Request, call_next):
    """middleware to authenticate the user"""
    logger.info(f"=== DÉBUT MIDDLEWARE AUTH ===")
    logger.info(f"URL: {request.url}")
    logger.info(f"Méthode: {request.method}")

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
                },
            )

        # 🆕 AMÉLIORATION : Chercher le token dans plusieurs endroits avec priorité
        token = None
        token_source = "unknown"
        
        print("DEBUG cookies:", request.headers.get("cookie"))
        
        # 1. D'abord dans le header Authorization (priorité haute)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            token_source = "authorization_header"
            logger.info("Token trouvé dans le header Authorization")
        
        # 2. Sinon dans le cookie access_token (nouveau système)
        elif not token:
            access_cookie = request.cookies.get("access_token")
            if access_cookie:
                token = access_cookie
                token_source = "access_cookie"
                logger.info("Token trouvé dans le cookie access_token")
        
        # 3. Enfin dans le cookie session_id (ancien système - compatibilité)
        elif not token:
            session_cookie = request.cookies.get("session_id")
            if session_cookie:
                token = session_cookie
                token_source = "session_cookie"
                logger.info("Token trouvé dans le cookie session_id (mode compatibilité)")

        if not token:
            logger.warning("Aucun token d'authentification trouvé")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentification requise",
                    "message": "Token d'authentification manquant",
                    "details": "Veuillez vous reconnecter",
                },
            )

        try:
            # 🆕 AMÉLIORATION : Validation avancée du token
            if not token or token.strip() == "":
                raise ValueError("Token vide")

            # Décoder le token
            logger.info(f"Token à décoder: '{token[:20]}...' (longueur: {len(token) if token else 0})")
            logger.info(f"Secret key: '{secret_key[:10]}...' (longueur: {len(secret_key) if secret_key else 0})")
            logger.info(f"Tentative de décodage du token depuis {token_source}...")
            decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
            logger.info(f"Token décodé avec succès")

            # 🆕 NOUVEAU : Validation des claims de sécurité
            current_time = int(time.time())
            
            # Vérifier l'expiration
            exp = decoded.get("exp")
            if not exp or current_time > exp:
                logger.error("Token expiré")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Token expiré",
                        "message": "Votre session a expiré",
                        "details": "Veuillez vous reconnecter",
                    },
                )

            #  NOUVEAU : Vérifier l'audience
            aud = decoded.get("audience")
            if not aud or "chat_api" not in aud:
                logger.error(f"Audience invalide: {aud}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": f"Token invalide",
                        "message": "Token non destiné à ce service",
                    },
                )

            #  NOUVEAU : Vérifier le type de token
            token_type = decoded.get("tokenType")
            if token_type != "access":
                logger.error(f"Type de token invalide: {token_type}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Token invalide",
                        "message": "Type de token non autorisé",
                    },
                )

            # Extraire l'ID utilisateur
            user_id = decoded.get("userId") or decoded.get("sub")
            logger.info(f"userId extrait du token: {user_id}")

            if not user_id:
                logger.error("user_id manquant dans le token décodé")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Token invalide",
                        "message": "Le token ne contient pas d'identifiant utilisateur valide",
                    },
                )

            #  NOUVEAU : Vérifier le scope
            scope = decoded.get("scope", "")
            if "chat:read" not in scope:
                logger.error(f"Scope insuffisant: {scope}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Permissions insuffisantes",
                        "message": "Vous n'avez pas les permissions nécessaires",
                    },
                )

            # Rechercher l'utilisateur
            logger.info("Recherche de l'utilisateur dans la base de données...")
            user = mongo_db.get_user_by_id(user_id)
            logger.info(f"Utilisateur trouvé: {'Oui' if user else 'Non'}")

            if not user:
                logger.error(f"Utilisateur non trouvé pour user_id: {user_id}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Utilisateur non trouvé",
                        "message": "L'utilisateur associé à ce token n'existe plus",
                    },
                )

            #  NOUVEAU : Vérifier si l'utilisateur est actif
            if user.get("status") == "inactive":
                logger.error(f"Utilisateur inactif: {user_id}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Compte désactivé",
                        "message": "Votre compte a été désactivé",
                    },
                )

            # Injecter les données dans request.state
            logger.info("Injection des données dans request.state...")
            request.state.user_id = user_id
            request.state.user = user
            
            # Gérer le chatId
            chat_id = user.get("chatId")
            if not chat_id:
                chat_id = f"chat_{user_id}_{int(time.time())}"
                logger.info(f"ChatId créé: {chat_id}")
            
            request.state.thread_id = chat_id
            request.state.token_source = token_source  # 🆕 NOUVEAU : Pour le debug
            logger.info(f"thread_id injecté: {request.state.thread_id}")

            logger.info("=== FIN MIDDLEWARE AUTH - CONTINUATION ===")
            return await call_next(request)

        except jwt.ExpiredSignatureError as e:
            logger.error(f"Token expiré: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token expiré",
                    "message": "Votre session a expiré",
                    "details": "Veuillez vous reconnecter",
                },
            )
        except jwt.InvalidSignatureError as e:
            logger.error(f"Signature du token invalide: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token invalide",
                    "message": "Le token d'authentification est corrompu",
                },
            )
        except jwt.DecodeError as e:
            logger.error(f"Erreur de décodage JWT: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token invalide",
                    "message": "Le format du token d'authentification est incorrect",
                },
            )
        except ValueError as e:
            logger.error(f"Erreur de validation: {e}")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token invalide",
                    "message": str(e),
                },
            )
        except Exception as e:
            logger.error(f"Erreur inattendue lors du décodage: {type(e).__name__}: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Erreur d'authentification",
                    "message": "Une erreur s'est produite lors de l'authentification",
                },
            )
    except Exception as e:
        logger.error(f"Erreur critique dans le middleware: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Erreur interne du serveur",
                "message": "Une erreur inattendue s'est produite",
            },
        )
