import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()


async def test_with_search_service():
    """Test en utilisant SearchService existant"""

    from services.search_service import SearchService

    search_service = SearchService()

    # Paramètres de test
    search_params = {
        "city": "Montreal",
        "min_bedrooms": 1,
        "max_bedrooms": 3,
        "min_price": 800,
        "max_price": 2000,
        "location_near": ["Downtown"],
        "enrich_top_k": 3,
    }

    user_id = "test_user_123"
    user_ip = "127.0.0.1"  # IP de test

    print("🚀 Test avec SearchService...")
    # Utiliser la méthode existante
    result = await search_service.search_listings(search_params, user_ip, user_id)

    print(f"✅ Résultat: {result}")
    return result


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_with_search_service())
