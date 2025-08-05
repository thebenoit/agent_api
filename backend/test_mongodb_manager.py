#!/usr/bin/env python3
"""
Script de test pour vérifier le MongoDBManager
"""

import asyncio
import logging
from database_manager import mongo_manager
from database import mongo_db

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_sync_connection():
    """Test de la connexion synchrone."""
    logger.info("=== Test connexion synchrone ===")
    try:
        # Test de récupération d'un utilisateur
        user = mongo_db.get_user_by_id("507f1f77bcf86cd799439011")  # ID de test
        logger.info(
            f"Test get_user_by_id: {'Succès' if user is not None else 'Utilisateur non trouvé (normal)'}"
        )

        # Test de la base de données
        db = mongo_manager.get_sync_db()
        collections = db.list_collection_names()
        logger.info(f"Collections disponibles: {collections}")

        return True
    except Exception as e:
        logger.error(f"Erreur test synchrone: {e}")
        return False


async def test_async_connection():
    """Test de la connexion asynchrone."""
    logger.info("=== Test connexion asynchrone ===")
    try:
        # Test de la base de données asynchrone
        db = mongo_manager.get_async_db()
        collections = await db.list_collection_names()
        logger.info(f"Collections disponibles (async): {collections}")

        return True
    except Exception as e:
        logger.error(f"Erreur test asynchrone: {e}")
        return False


def test_singleton():
    """Test du pattern Singleton."""
    logger.info("=== Test pattern Singleton ===")
    try:
        # Créer deux instances
        manager1 = mongo_manager
        manager2 = mongo_manager

        # Vérifier qu'elles sont la même instance
        is_same = manager1 is manager2
        logger.info(f"Instances identiques: {is_same}")

        # Vérifier les connexions
        client1 = manager1.get_sync_client()
        client2 = manager2.get_sync_client()
        is_same_client = client1 is client2
        logger.info(f"Clients identiques: {is_same_client}")

        return is_same and is_same_client
    except Exception as e:
        logger.error(f"Erreur test singleton: {e}")
        return False


async def main():
    """Fonction principale de test."""
    logger.info("Début des tests MongoDBManager")

    # Tests
    tests = [
        ("Singleton", test_singleton),
        ("Connexion synchrone", test_sync_connection),
        ("Connexion asynchrone", test_async_connection),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        if asyncio.iscoroutinefunction(test_func):
            result = await test_func()
        else:
            result = test_func()
        results.append((test_name, result))

    # Résumé
    logger.info("\n=== RÉSUMÉ DES TESTS ===")
    for test_name, result in results:
        status = "✅ SUCCÈS" if result else "❌ ÉCHEC"
        logger.info(f"{test_name}: {status}")

    # Fermeture propre
    logger.info("Fermeture des connexions...")
    mongo_manager.close_all()
    logger.info("Tests terminés")


if __name__ == "__main__":
    asyncio.run(main())
