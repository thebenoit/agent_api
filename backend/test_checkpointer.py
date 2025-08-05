#!/usr/bin/env python3
"""
Test spécifique pour le checkpointer MongoDB
"""

import asyncio
import logging
from database_manager import mongo_manager
from database import mongo_db

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_checkpointer():
    """Test du checkpointer sans fermer les connexions."""
    logger.info("=== Test checkpointer ===")
    try:
        # Test de la connexion normale
        db = mongo_manager.get_sync_db()
        collections = db.list_collection_names()
        logger.info(f"Collections avant checkpointer: {len(collections)}")

        # Créer le checkpointer
        checkpointer = await mongo_manager.get_checkpointer()
        logger.info("Checkpointer créé avec succès")

        # Vérifier que la connexion est toujours active
        collections_after = db.list_collection_names()
        logger.info(f"Collections après checkpointer: {len(collections_after)}")

        # Vérifier que les connexions sont identiques
        is_same = collections == collections_after
        logger.info(f"Connexions identiques: {is_same}")

        return True
    except Exception as e:
        logger.error(f"Erreur test checkpointer: {e}")
        return False


async def test_multiple_operations():
    """Test de multiples opérations sans conflit."""
    logger.info("=== Test opérations multiples ===")
    try:
        # Opération 1: Récupération utilisateur
        user = mongo_db.get_user_by_id("507f1f77bcf86cd799439011")
        logger.info("Opération 1: Récupération utilisateur ✅")

        # Opération 2: Création checkpointer
        checkpointer = await mongo_manager.get_checkpointer()
        logger.info("Opération 2: Création checkpointer ✅")

        # Opération 3: Récupération historique
        history = mongo_db.get_chat_history("507f1f77bcf86cd799439011")
        logger.info("Opération 3: Récupération historique ✅")

        # Opération 4: Vérification connexion
        db = mongo_manager.get_sync_db()
        collections = db.list_collection_names()
        logger.info(
            f"Opération 4: Vérification connexion ✅ ({len(collections)} collections)"
        )

        return True
    except Exception as e:
        logger.error(f"Erreur test opérations multiples: {e}")
        return False


async def main():
    """Fonction principale de test."""
    logger.info("Début des tests checkpointer")

    # Tests
    tests = [
        ("Checkpointer", test_checkpointer),
        ("Opérations multiples", test_multiple_operations),
    ]

    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        result = await test_func()
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
