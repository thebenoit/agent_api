import os
import sys
import asyncio
import logging
import time
import argparse
from typing import Any, List, Dict

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("test_search_facebook_async")


def ensure_env_loaded() -> None:
    if load_dotenv is not None:
        load_dotenv()
    else:
        logger.warning(
            "python-dotenv non disponible; variables d'environnement non chargées depuis .env"
        )


def validate_environment() -> None:
    missing: List[str] = []
    for key in ["DRIVER_PATH", "PROXIES_URL"]:
        if not os.getenv(key):
            missing.append(key)
    if missing:
        logger.warning(
            "Variables d'environnement manquantes: %s. Le test tentera de continuer mais risque d'échouer.",
            ", ".join(missing),
        )
    har_path = os.path.join(os.getcwd(), "data", "facebook.har")
    if not os.path.exists(har_path):
        logger.info(
            "HAR introuvable à %s. Le scraper essaiera d'en générer un via Selenium (peut être lent).",
            har_path,
        )
    else:
        logger.info("HAR trouvé: %s", har_path)


async def run_test(
    lat: float,
    lon: float,
    min_price: int,
    max_price: int,
    min_bed: int,
    max_bed: int,
    top_k: int,
) -> List[Dict[str, Any]]:
    start = time.time()
    logger.info(
        "Démarrage test execute_async | lat=%.5f lon=%.5f prix=[%s,%s] chambres=[%s,%s] top_k=%s",
        lat,
        lon,
        min_price,
        max_price,
        min_bed,
        max_bed,
        top_k,
    )

    # Import tardif pour voir plus clairement les erreurs d'import
    try:
        from agents.tools.searchFacebook import SearchFacebook
    except Exception as e:
        logger.exception("Erreur d'import de SearchFacebook: %s", e)
        raise

    try:
        sf = SearchFacebook()
        logger.info("Instance SearchFacebook initialisée")
    except Exception as e:
        logger.exception("Échec initialisation SearchFacebook: %s", e)
        raise

    try:
        results = await sf.execute_async(
            lat,
            lon,
            min_price,
            max_price,
            min_bed,
            max_bed,
            top_k=top_k,
        )
        elapsed = time.time() - start
        logger.info(
            "execute_async terminé en %.2fs avec %d éléments",
            elapsed,
            len(results) if isinstance(results, list) else -1,
        )
        return results
    except asyncio.TimeoutError:
        logger.error("Timeout global lors de l'appel execute_async")
        raise
    except Exception as e:
        logger.exception("Erreur pendant execute_async: %s", e)
        raise


def print_results(results: List[Dict[str, Any]], limit: int) -> None:
    if not isinstance(results, list):
        logger.error("Résultats inattendus (type=%s): %s", type(results), results)
        return
    logger.info("Affichage des %d premiers résultats", min(limit, len(results)))
    for idx, item in enumerate(results[:limit]):
        try:
            title = item.get("title")
            price = item.get("price")
            url = item.get("url")
            desc = item.get("description")
            images = item.get("images") or []
            logger.info("[%d] %s | %s | %s", idx + 1, title, price, url)
            if desc:
                logger.info(
                    "     description: %s",
                    (desc[:140] + "...") if len(desc) > 140 else desc,
                )
            logger.info("     images: %d", len(images))
        except Exception as e:
            logger.exception("Erreur d'affichage pour l'item %d: %s", idx + 1, e)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test async SearchFacebook.execute_async"
    )
    parser.add_argument(
        "--lat", type=float, default=45.5017, help="Latitude (default: Montréal)"
    )
    parser.add_argument(
        "--lon", type=float, default=-73.5673, help="Longitude (default: Montréal)"
    )
    parser.add_argument("--min_price", type=int, default=1000, help="Prix min (CAD)")
    parser.add_argument("--max_price", type=int, default=3000, help="Prix max (CAD)")
    parser.add_argument("--min_bed", type=int, default=1, help="Chambres min")
    parser.add_argument("--max_bed", type=int, default=3, help="Chambres max")
    parser.add_argument(
        "--top_k", type=int, default=3, help="Nombre de listings à enrichir"
    )
    parser.add_argument(
        "--print", dest="to_print", action="store_true", help="Afficher les résultats"
    )
    return parser.parse_args()


async def main() -> None:
    ensure_env_loaded()
    validate_environment()
    args = parse_args()
    try:
        results = await run_test(
            lat=args.lat,
            lon=args.lon,
            min_price=args.min_price,
            max_price=args.max_price,
            min_bed=args.min_bed,
            max_bed=args.max_bed,
            top_k=args.top_k,
        )
    except Exception:
        logger.error("Le test a échoué. Voir les logs ci-dessus pour les détails.")
        sys.exit(1)

    if args.to_print:
        print_results(results, limit=args.top_k)

    # Exit code based on results presence
    if isinstance(results, list) and results:
        logger.info("Test réussi: %d résultats retournés", len(results))
        sys.exit(0)
    else:
        logger.warning("Test terminé sans résultats")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
