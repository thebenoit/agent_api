import os
import sys
from dotenv import load_dotenv

# Ajouter le chemin du projet
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()


def test_debug():
    """Test de debug pour identifier l'erreur exacte"""

    try:
        print("1. Test d'import de SearchService...")
        from services.search_service import SearchService

        print("✅ Import réussi")

        print("2. Test de création de SearchService...")
        search_service = SearchService()
        print("✅ SearchService créé")

        print("3. Test de _generate_cache_key...")
        search_params = {
            "city": "Montreal",
            "min_bedrooms": 1,
            "max_bedrooms": 3,
            "min_price": 800,
            "max_price": 2000,
            "location_near": ["Downtown"],
            "enrich_top_k": 3,
        }

        cache_key = search_service._generate_cache_key(search_params)
        print(f"✅ Cache key générée: {cache_key}")

        print("4. Test de création de queue...")
        queue = search_service.scraping_queue
        print(f"✅ Queue créée: {queue}")

        print("5. Test d'envoi de job...")
        user_id = "66c7b62e7cd43356cfcd27d1"
        user_ip = "127.0.0.1"

        # Test de la méthode search_listings
        import asyncio

        result = asyncio.run(
            search_service.search_listings(search_params, user_ip, user_id)
        )
        print(f"✅ Job envoyé avec succès: {result}")

    except Exception as e:
        print(f"❌ Erreur à l'étape: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_debug()
