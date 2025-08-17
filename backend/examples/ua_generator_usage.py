#!/usr/bin/env python3
"""
Exemples d'utilisation du générateur de User-Agent et headers HTTP.

Ce fichier démontre les différentes façons d'utiliser les fonctions
du module ua_generator selon vos besoins spécifiques.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ua_generator import (
    generate_complete_headers,
    generate_single_user_agent,
    generate_requests_session_headers,
    generate_headers_batch,
)


def example_1_basic_user_agent():
    """Exemple 1: Génération d'un User-Agent simple"""
    print("=== Exemple 1: User-Agent simple ===")

    ua = generate_single_user_agent()
    print(f"User-Agent généré: {ua}")
    print()


def example_2_complete_headers():
    """Exemple 2: Headers HTTP complets et cohérents"""
    print("=== Exemple 2: Headers complets ===")

    headers = generate_complete_headers()
    print("Headers générés:")
    for key, value in headers.items():
        print(f"  {key}: {value}")
    print()


def example_3_requests_integration():
    """Exemple 3: Intégration avec requests"""
    print("=== Exemple 3: Intégration avec requests ===")

    try:
        import requests

        # Génération des headers optimisés pour requests
        headers = generate_requests_session_headers()

        print("Headers pour requests:")
        for key, value in headers.items():
            print(f"  {key}: {value}")

        # Utilisation avec requests.Session
        session = requests.Session()
        session.headers.update(headers)

        print("\nSession configurée avec les headers générés.")
        print("Prêt pour faire des requêtes avec une identité réaliste!")

        # Exemple de requête (commenté pour éviter les appels réseau)
        # response = session.get('https://httpbin.org/headers')
        # print("Réponse:", response.json())

    except ImportError:
        print(
            "Module 'requests' non disponible. Installez-le avec: pip install requests"
        )
    print()


def example_4_reproducible_generation():
    """Exemple 4: Génération reproductible avec seed"""
    print("=== Exemple 4: Génération reproductible ===")

    # Même seed = même résultat
    seed = 42

    ua1 = generate_single_user_agent(seed=seed)
    ua2 = generate_single_user_agent(seed=seed)

    print(f"UA avec seed {seed} (1ère fois): {ua1}")
    print(f"UA avec seed {seed} (2ème fois): {ua2}")
    print(f"Identiques: {ua1 == ua2}")

    # Seed différent = résultat différent
    ua3 = generate_single_user_agent(seed=123)
    print(f"UA avec seed 123: {ua3}")
    print(f"Différent du précédent: {ua1 != ua3}")
    print()


def example_5_batch_generation():
    """Exemple 5: Génération en lot pour les tests de charge"""
    print("=== Exemple 5: Génération en lot ===")

    # Génération de 5 ensembles de headers
    batch = generate_headers_batch(n=5, seed=456)

    print("5 ensembles de headers générés:")
    for i, headers in enumerate(batch, 1):
        user_agent = headers.get("User-Agent", "N/A")
        platform = "Unknown"
        if "Windows" in user_agent:
            platform = "Windows"
        elif "Android" in user_agent:
            platform = "Android"
        elif "Macintosh" in user_agent:
            platform = "macOS"
        elif "iPhone" in user_agent or "iPad" in user_agent:
            platform = "iOS"
        elif "Linux" in user_agent:
            platform = "Linux"

        browser = "Unknown"
        if "Chrome/" in user_agent and "Edg/" not in user_agent:
            browser = "Chrome"
        elif "Edg/" in user_agent:
            browser = "Edge"
        elif "Firefox/" in user_agent:
            browser = "Firefox"
        elif "Safari/" in user_agent and "Chrome/" not in user_agent:
            browser = "Safari"

        print(f"  {i}. {browser} sur {platform}")
    print()


def example_6_facebook_scraping_scenario():
    """Exemple 6: Scénario de scraping Facebook"""
    print("=== Exemple 6: Scénario de scraping Facebook ===")

    # Génération de headers pour simuler un utilisateur réel
    headers = generate_complete_headers(seed=789)

    print("Configuration pour scraping Facebook:")
    print("Headers de base:")
    for key, value in headers.items():
        print(f"  {key}: {value}")

    # Headers additionnels spécifiques à Facebook
    facebook_headers = headers.copy()
    facebook_headers.update(
        {
            "Referer": "https://www.facebook.com/",
            "Origin": "https://www.facebook.com",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "cache-control": "max-age=0",
        }
    )

    print("\nHeaders enrichis pour Facebook:")
    additional_keys = [
        "Referer",
        "Origin",
        "sec-fetch-dest",
        "sec-fetch-mode",
        "sec-fetch-site",
        "cache-control",
    ]
    for key in additional_keys:
        if key in facebook_headers:
            print(f"  {key}: {facebook_headers[key]}")

    print("\nCes headers simulent un navigateur réel accédant à Facebook.")
    print()


def main():
    """Fonction principale qui exécute tous les exemples"""
    print("🔧 Démonstration du générateur de User-Agent et headers HTTP\n")

    example_1_basic_user_agent()
    example_2_complete_headers()
    example_3_requests_integration()
    example_4_reproducible_generation()
    example_5_batch_generation()
    example_6_facebook_scraping_scenario()

    print("✅ Tous les exemples ont été exécutés avec succès!")
    print("\n💡 Conseils d'utilisation:")
    print("- Utilisez generate_single_user_agent() pour un simple User-Agent")
    print("- Utilisez generate_complete_headers() pour des headers complets")
    print("- Utilisez generate_requests_session_headers() avec requests")
    print("- Utilisez des seeds pour la reproductibilité en tests")
    print("- Générez en lot pour les tests de charge")


if __name__ == "__main__":
    main()
