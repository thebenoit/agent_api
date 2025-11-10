import os
import sys
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, backend_dir)

import asyncio
from sessionManager import SessionsManager
from agents.tools.searchFacebook import SearchFacebook
from schemas.Metrics.SessionMetrics import SessionMetrics
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_search_metrics_end_to_end():
    
    logger.info("\n" + "="*60)
    logger.info("🧪 TEST: Metrics End-to-End")
    logger.info("="*60 + "\n")
    
    test_user_id = "66bd41ade6e37be2ef4b4fc2"  # Ton vrai user
    metrics = SessionMetrics()
    
    logger.info("1️⃣ Création de session...")
    manager = SessionsManager()
    session_created = await manager.create_session_for_user(test_user_id)
    logger.info(f"   Résultat: {'✅ Créée' if session_created else '❌ Échec'}\n")
    
    logger.info("2️⃣ Exécution d'une recherche...")
    searcher = SearchFacebook()
    try:
        listings = await searcher.scrape(
            lat=45.5044,
            lon=-73.5761,
            query={
                "minBudget": 100000,
                "maxBudget": 200000,
                "minBedrooms": 1,
                "maxBedrooms": 3
            },
            user_id=test_user_id,
            job_id="test_metrics_123"
        )
        logger.info(f"   Résultat: ✅ {len(listings)} listings trouvés\n")
    except Exception as e:
        logger.info(f"   Résultat: ❌ Erreur: {str(e)[:100]}\n")
        
    logger.info("3️⃣ Résumé des métriques (dernière heure):")
    logger.info("-" * 60)
    summary = await metrics.get_metrics_summary(hours=1)
    
    if summary:
        # Métriques de création de sessions
        session_metrics = summary.get("session_creation", {})
        logger.info(f"\n📊 CRÉATION DE SESSIONS:")
        logger.info(f"   Total: {session_metrics.get('total', 0)}")
        logger.info(f"   Succès: {session_metrics.get('success_count', 0)}")
        logger.info(f"   Échecs: {session_metrics.get('failure_count', 0)}")
        logger.info(f"   Taux succès: {session_metrics.get('success_rate', 0):.1f}%")
        logger.info(f"   Durée moyenne: {session_metrics.get('avg_duration_seconds', 0):.2f}s")
        
        # Métriques de recherches
        search_metrics = summary.get("search_execution", {})
        logger.info(f"\n🔍 RECHERCHES:")
        logger.info(f"   Total: {search_metrics.get('total', 0)}")
        logger.info(f"   Succès: {search_metrics.get('success_count', 0)}")
        logger.info(f"   Échecs: {search_metrics.get('failure_count', 0)}")
        logger.info(f"   Taux succès: {search_metrics.get('success_rate', 0):.1f}%")
        logger.info(f"   Durée moyenne: {search_metrics.get('avg_duration_seconds', 0):.2f}s")
    
    logger.info("\n" + "="*60)
    logger.info("✅ Test terminé!")
    logger.info("="*60)

if __name__ == "__main__":
    asyncio.run(test_search_metrics_end_to_end())
    