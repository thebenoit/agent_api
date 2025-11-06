from database import mongo_db
import asyncio
import jwt
import os
import requests
import time
import logging
from typing import List
# Configuration des logs
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_session_id(user_id):
    logger.info(f"Début création session_id pour user_id: {user_id}")
    start_time = time.time()

    logger.info("Connexion à la base de données...")
    user = await mongo_db.get_user_by_id(user_id)
    db_time = time.time() - start_time
    logger.info(f"Récupération utilisateur terminée en {db_time:.2f}s")

    if user:
        logger.info("Utilisateur trouvé, création du JWT...")
        session_id = jwt.encode(
            {"user_id": user_id}, os.getenv("SECRET_KEY"), algorithm="HS256"
        )
        total_time = time.time() - start_time
        logger.info(f"Session ID créé en {total_time:.2f}s {session_id}")
        return session_id
    else:
        logger.warning("Utilisateur non trouvé")
        return None


async def decode_session_id(session_id):
    logger.info("Début décodage session_id")
    start_time = time.time()

    try:
        payload = jwt.decode(session_id, os.getenv("SECRET_KEY"), algorithms=["HS256"])
        decode_time = time.time() - start_time
        logger.info(f"Session ID décodé en {decode_time:.2f}s")
        return payload["user_id"]
    except jwt.InvalidTokenError as e:
        logger.error(f"Token invalide ou modifié {e}")
        return None
    
async def update_chat_history(chat_id: str, chat_history: List[dict],who:str):
    await mongo_db.update_chat_history(chat_id, chat_history,who)


async def test_user_text_chat():
    logger.info("=== DÉBUT DU TEST ===")
    start_time = time.time()

    user_id = "66bd41ade6e37be2ef4b4fc2"
    logger.info(f"Test avec user_id: {user_id}")

    # Création du session_id
    session_start = time.time()
    session_id = await create_session_id(user_id)
    session_time = time.time() - session_start
    logger.info(f"Création session_id terminée en {session_time:.2f}s")

    if not session_id:
        logger.error("Impossible de créer session_id, arrêt du test")
        return

    chat_request = {
        "system_prompt": "You are a helpful assistant that can answer questions and help with tasks.",
        "message": "je cherche un appartement a Montreal",
        "session_id": session_id,
    }

    user_id = await decode_session_id(session_id)
    logger.info(f"User ID décodé: {user_id}")

    logger.info("Préparation de la requête HTTP...")
    logger.info(f"URL: http://localhost:8000/chat")
    logger.info(f"Headers: Authorization: Bearer {session_id}...")

    # Test de connexion au serveur
    logger.info("Test de connexion au serveur...")
    try:
        test_response = requests.get("http://localhost:8000/")
        logger.info(f"Connexion serveur OK - Status: {test_response.status_code}")
    except requests.exceptions.ConnectionError:
        logger.error("ERREUR: Impossible de se connecter au serveur sur localhost:8000")
        logger.error("Assurez-vous que le serveur est démarré avec: python3 server.py")
        return
    except requests.exceptions.Timeout:
        logger.error("ERREUR: Timeout lors de la connexion au serveur")
        return

    # Requête principale
    logger.info("Envoi de la requête POST...")
    request_start = time.time()

    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json=chat_request,
            headers={"Authorization": f"Bearer {session_id}"},
            #timeout=30,  # Timeout de 30 secondes
        )
        request_time = time.time() - request_start
        logger.info(
            f"Réponse reçue en {request_time:.2f}s - Status: {response.status_code}"
        )

        if response.status_code == 200:
            logger.info("Réponse JSON:")
            print(response.json())
        else:
            logger.error(f"Erreur HTTP {response.status_code}: {response.text}")

    except requests.exceptions.Timeout:
        logger.error("ERREUR: Timeout lors de la requête POST (30s)")
    except requests.exceptions.ConnectionError:
        logger.error("ERREUR: Connexion perdue pendant la requête")
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")

    total_time = time.time() - start_time
    logger.info(f"=== FIN DU TEST - Temps total: {total_time:.2f}s ===")


async def main():
    logger.info("Démarrage du programme de test")
    await create_session_id("66bd41ade6e37be2ef4b4fc2")
    #await update_chat_history("688bb77bf5435fe5e7f62218", [{"role": "user", "content": "je cherche un appartement a Montreal"}],'user')


if __name__ == "__main__":
    asyncio.run(main())
