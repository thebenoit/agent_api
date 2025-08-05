#!/usr/bin/env python3
"""
Test d'intégration du graph avec MongoDB
"""

import asyncio
import logging
from database_manager import mongo_manager
from agents.graph import IanGraph
from schemas import Message

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_graph_creation():
    """Test de création du graph."""
    logger.info("=== Test création du graph ===")
    try:
        # Créer l'agent
        agent = IanGraph()
        logger.info("Agent créé avec succès")

        # Créer le graph
        graph = await agent.create_graph()
        logger.info("Graph créé avec succès")

        return graph is not None
    except Exception as e:
        logger.error(f"Erreur création graph: {e}")
        return False


async def test_graph_invocation():
    """Test d'invocation du graph."""
    logger.info("=== Test invocation du graph ===")
    try:
        # Créer l'agent
        agent = IanGraph()
        logger.info("Agent créé avec succès")

        # Créer un message de test
        test_message = Message(
            role="user", content="Bonjour, je cherche un appartement à Montréal"
        )

        # Tester l'invocation
        response = await agent._get_response(
            messages=[test_message],
            session_id="test_session_123",
            user_id="test_user_123",
        )

        logger.info(f"Réponse reçue: {response}")
        return True
    except Exception as e:
        logger.error(f"Erreur invocation graph: {e}")
        return False


async def test_multiple_invocations():
    """Test de multiples invocations."""
    logger.info("=== Test multiples invocations ===")
    try:
        # Créer l'agent
        agent = IanGraph()
        logger.info("Agent créé avec succès")

        # Test 1
        message1 = Message(role="user", content="Je cherche un 2 chambres")
        response1 = await agent._get_response(
            messages=[message1], session_id="test_session_1", user_id="test_user_1"
        )
        logger.info("Invocation 1 réussie")

        # Test 2
        message2 = Message(role="user", content="Quels sont les prix?")
        response2 = await agent._get_response(
            messages=[message2], session_id="test_session_2", user_id="test_user_2"
        )
        logger.info("Invocation 2 réussie")

        return True
    except Exception as e:
        logger.error(f"Erreur multiples invocations: {e}")
        return False


async def main():
    """Fonction principale de test."""
    logger.info("Début des tests d'intégration graph")

    # Tests
    tests = [
        ("Création graph", test_graph_creation),
        ("Invocation graph", test_graph_invocation),
        ("Multiples invocations", test_multiple_invocations),
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
