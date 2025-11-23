# tests/test_workflow_enqueue.py

import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

import asyncio
from services.search_service import SearchService
from schemas.Metrics.WorkflowMetrics import get_workflow_metrics
import time

async def test_enqueue_tracking():
    """Test que les jobs enqueued sont bien trackés"""
    
    print("\n" + "="*60)
    print("🧪 TEST: Job Enqueue Tracking")
    print("="*60 + "\n")
    
    service = SearchService()
    metrics = get_workflow_metrics()
    
    # 1. Créer une recherche
    search_params = {
        "city": "Montreal",
        "min_bedrooms": 1,
        "max_bedrooms": 3,
        "min_price": 1000,
        "max_price": 2000,
        "location_near": [],
        "enrich_top_k": 4
    }
    
    print("1️⃣ Création d'un job de recherche...")
    result = await service.search_listings(
        search_params=search_params,
        user_ip="127.0.0.1",
        user_id="66bd41ade6e37be2ef4b4fc2"
    )
    
    job_id = result.get("job_id")
    print(f"   Job ID: {job_id}\n")
    print(f"   Status: {result.get('status')}\n")
    
    # 2. Attendre un peu que le buffer flush
    print("2️⃣ Attente du flush du buffer (6 secondes)...")
    time.sleep(6)
    
    # 3. Vérifier que la métrique est en DB
    print("\n3️⃣ Vérification dans MongoDB...")
    db_metric = metrics.collection.find_one({
        "job_id": job_id,
        "event_type": "job_enqueued"
    })
    
    if db_metric:
        print("   ✅ Métrique trouvée en DB !")
        print(f"   Job ID: {db_metric['job_id']}")
        print(f"   User ID: {db_metric['user_id']}")
        print(f"   Event: {db_metric['event_type']}")
        print(f"   Timestamp: {db_metric['timestamp']}")
        print(f"   Metadata: {db_metric['metadata']}")
    else:
        print("   ❌ Métrique NON trouvée en DB")
    
    # 4. Stats buffer
    print(f"\n4️⃣ État du buffer:")
    print(f"   Taille actuelle: {len(metrics._buffer)} métriques")
    
    print("\n" + "="*60)
    print("✅ Test terminé!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_enqueue_tracking())