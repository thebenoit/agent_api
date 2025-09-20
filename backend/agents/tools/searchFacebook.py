from typing import Any
import asyncio
import os
from dotenv import load_dotenv
from utils import event_publisher
from seleniumwire import webdriver  # Import from seleniumwire
import sys
from models.fb_sessions import FacebookSessionModel

# from setuptools._distutils import version as _version
# sys.modules['distutils.version'] = _version
import undetected_chromedriver as uc
from undetected_chromedriver import Chrome
from selenium.webdriver.common.by import By
from pymongo import MongoClient
from seleniumwire.utils import decode
from selenium.webdriver.chrome.options import Options

# from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import logging
import sys
from bs4 import BeautifulSoup
from utils.event_publisher import EventPublisher


# rotating ip library
from requests_ip_rotator import ApiGateway
import urllib3

# # other
import requests
import json
import time
import random
import urllib
import urllib.parse
from time import sleep
import httpx

load_dotenv()

from agents.tools.base_tool import BaseTool
from agents.tools.bases.base_scraper import BaseScraper
from agents.tools.onePage import OnePage
import logging

logger = logging.getLogger(__name__)


class SearchFacebook(BaseTool, BaseScraper):

    @property
    def name(self) -> str:
        return "search_facebook"

    @property
    def description(self) -> str:
        return "Search in facebook marketplace for a listing according to the user's request(query)"

    def __init__(self):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("initialisation du scraper facebook...")

        self.url = "https://www.facebook.com/marketplace/montreal/propertyrentals"
        ##change according to the computer install here: https://googlechromelabs.github.io/chrome-for-testing/#stable
        self.driver = os.getenv("DRIVER_PATH")
        self.har = None
        self.filtered_har = None
        self.listings = []
        self.seen_listing_ids = set()

        self.max_retries = 3
        self.retry_delay = 10
        self.event_publisher = EventPublisher()

    def execute(
        self,
        lat: float,
        lon: float,
        minBudget: float,
        maxBudget: float,
        minBedrooms: int,
        maxBedrooms: int,
        user_id: str,
        job_id,
    ) -> Any:

        self.listings = []
        self.seen_listing_ids = set()

        inputs = {
            "lat": lat,
            "lon": lon,
            "minBudget": minBudget * 100,
            "maxBudget": maxBudget * 100,
            "minBedrooms": minBedrooms,
            "maxBedrooms": maxBedrooms,
        }

        self.event_publisher.publish(
            job_id,
            "progress",
            {
                "status": "user_pref",
                "message": "preferences du user",
                "input": input,
            },
        )

        print("inputs: ", inputs)
        # query = {"lat":"40.7128","lon":"-74.0060","bedrooms":2,"minBudget":80000,"maxBudget":100000,"bedrooms":3,"minBedrooms":3,"maxBedrooms":4}
        listings = asyncio.run(
            self.scrape(inputs["lat"], inputs["lon"], inputs, user_id, job_id)
        )
        if not listings:
            listings = []
            print("Aucune annonce trouvée: ")
            # print("listings: ", listings)

        return listings

    async def execute_async(
        self,
        lat: float,
        lon: float,
        minBudget: float,
        maxBudget: float,
        minBedrooms: int,
        maxBedrooms: int,
        user_id: str,
        listings: list,
        job_id: str,
        *,
        top_k: int = 5,
        concurrency: int = 3,
        timeout_sec: float = 90.0,
        **kwargs,
    ) -> Any:
        logger.info(
            "[execute_async] start lat=%.5f lon=%.5f price=[%s,%s] beds=[%s,%s] top_k=%s conc=%s timeout=%ss",
            lat,
            lon,
            minBudget,
            maxBudget,
            minBedrooms,
            maxBedrooms,
            top_k,
            concurrency,
            timeout_sec,
        )

        # Exécuter la collecte synchrone existante dans un thread
        def _run_sync():
            return self.execute(
                lat,
                lon,
                minBudget,
                maxBudget,
                minBedrooms,
                maxBedrooms,
                user_id,
                job_id,
            )

        listings = await asyncio.to_thread(_run_sync)
        logger.info(
            "[execute_async] base listings récupérés: %d",
            len(listings) if isinstance(listings, list) else -1,
        )

        # if progress:
        #     progress("progress", {"count": len(listings)})

        if not listings:
            return []

        self.event_publisher.publish(
            job_id,
            "progress",
            {"status": "processing", "message": f"{len(listings)} listings"},
        )

        onepage = OnePage()
        sem = asyncio.Semaphore(concurrency)

        async def enrich(item: dict) -> dict:
            # Gestion intelligente de l'URL selon le type de listing
            url = None

            # Pour les listings du feed
            if item.get("listing_type") == "feed":
                url = item.get("for_sale_item", {}).get("share_uri")
                if not url:
                    # Construire l'URL à partir de l'ID
                    listing_id = item.get("_id")
                    if listing_id:
                        url = f"https://www.facebook.com/marketplace/item/{listing_id}/"

            else:
                # Pour les listings de la carte (ancienne structure)
                url = item.get("for_sale_item", {}).get("share_uri") or (
                    f"https://www.facebook.com/marketplace/item/{item.get('_id','')}"
                    if item.get("_id")
                    else None
                )

            if not url:
                item["onepage"] = {"error": True, "reason": "no url"}
                logger.warning(
                    "[enrich] aucun URL pour _id=%s title=%s type=%s",
                    item.get("_id"),
                    item.get("for_sale_item", {}).get("marketplace_listing_title")
                    or item.get("title"),
                    item.get("listing_type", "unknown"),
                )
                return item

            try:
                start = asyncio.get_event_loop().time()
                logger.debug(
                    "[enrich] start _id=%s url=%s type=%s",
                    item.get("_id"),
                    url,
                    item.get("listing_type", "unknown"),
                )

                # On publie uniquement les champs titre, image et url selon la structure demandée.
                self.event_publisher.publish(
                    job_id,
                    "progress",
                    {
                        "status": "listing_loading",
                        "message": "Démarage du fetch de la page",
                        "title": item.get("title")
                        or item.get("for_sale_item", {}).get(
                            "marketplace_listing_title"
                        ),
                        "image": item.get("primary_image"),
                        "url": url,
                    },
                )

                async with sem:
                    data = await asyncio.wait_for(
                        onepage.fetch_page(url, job_id), timeout=timeout_sec
                    )

                # self.event_publisher.publish(
                #     job_id,
                #     "progress",
                #     {
                #         "status": "listing_loading",
                #         "message": f"Fetch de la page réussi",
                #         "titre":f"{data.get("description", "") or ""}",
                #         "image":f"{(data.get("images", [None])[0] if data.get("images") else None)}",
                #         "data":data,
                #         "url": url,

                #     },
                # )
                # Fusion dans la structure de sortie
                item.setdefault("details", {})
                if isinstance(data, dict):
                    if data.get("description"):
                        item["details"]["description"] = data["description"]
                    if data.get("images"):
                        item["details"]["images"] = data["images"]
                item["details"]["source_url"] = url
                elapsed = asyncio.get_event_loop().time() - start
                images_count = len(item["details"].get("images", []))

                desc_len = len(item["details"].get("description", "") or "")
                logger.info(
                    "[enrich] ok _id=%s in %.2fs images=%d desc_len=%d type=%s",
                    item.get("_id"),
                    elapsed,
                    images_count,
                    desc_len,
                    item.get("listing_type", "unknown"),
                )
            except Exception as e:
                item["onepage"] = {"error": True, "reason": str(e)}
                logger.exception(
                    "[enrich] erreur _id=%s url=%s type=%s: %s",
                    item.get("_id"),
                    url,
                    item.get("listing_type", "unknown"),
                    e,
                )

                self.event_publisher.publish(
                    job_id,
                    "Error",
                    {
                        "status": "Error",
                        "message": f"Erreur lors de la recherche d'appartement ",
                    },
                )
            return item

        targets = listings[: top_k if top_k > 0 else 0]
        logger.info(
            "[execute_async] enrich targets: %s",
            [t.get("_id") for t in targets],
        )
        if targets:
            enriched = await asyncio.gather(*(enrich(li) for li in targets))
            listings[: len(enriched)] = enriched
            logger.info("[execute_async] enrich terminé: %d items", len(enriched))

        # Optionnel: normaliser la structure retournée
        logger.debug("[execute_async] normalisation de la sortie...")

        normalized = [
            self.normalize_item(x)
            for x in listings[: top_k if top_k > 0 else len(listings)]
        ]
        if normalized:
            sample = {
                "id": normalized[0].get("id"),
                "title": normalized[0].get("title"),
                "price": normalized[0].get("price"),
                "bedrooms": normalized[0].get("bedrooms"),
                "bathrooms": normalized[0].get("bathrooms"),
                "url": normalized[0].get("url"),
            }

            self.event_publisher.publish(
                job_id,
                "progress",
                {"message": f"{sample.get('title')}", "sample": sample},
            )
            logger.info("[execute_async] normalized sample: %s", sample)
            logger.info("[execute_async] normalized: %s", normalized)
        logger.debug(
            "[execute_async] normalized count=%d ids=%s",
            len(normalized),
            [n.get("id") for n in normalized],
        )
        return normalized

    def load_fb_headers(self, headers, session):
        # dict: simple
        if isinstance(headers, dict):
            session.headers.update(headers)

        # liste: [(k, v)] ou [{"name": k, "value": v}]
        elif isinstance(headers, list):
            for h in headers:
                if isinstance(h, (list, tuple)) and len(h) == 2:
                    k, v = h
                    session.headers[k] = v
                elif isinstance(h, dict) and "name" in h:
                    session.headers[h["name"]] = h.get("value", "")

        else:
            raise TypeError("headers doit être un dict ou une liste")

        additional_headers = {
            "x-fb-lsd": headers.get("x-fb-lsd", ""),  # Token de sécurité
            "x-asbd-id": headers.get("x-asbd-id", "359341"),  # ID app Facebook
            "sec-ch-prefers-color-scheme": "light",
            "sec-ch-ua": '"Chromium";v="135", "Not_A Brand";v="8", "Google Chrome";v="135"',
            "sec-ch-ua-full-version-list": '"Not.A/Brand";v="99.0.0.0", "Chromium";v="136.0.7103.25"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"10.0"',
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "fr-FR,fr;q=0.9,en;q=0.8",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "te": "trailers",
        }

        # override si besoin
        session.headers.update(
            additional_headers
            # {"x-fb-friendly-name": "CometMarketplaceRealEstateMapStoryQuery"}
        )

        # 🆕 Log des headers chargés pour debug
        print(f"[Headers] Headers chargés: {len(session.headers)} headers")
        if "cookie" in session.headers:
            cookie_header = session.headers["cookie"]
            cookie_count = len(cookie_header.split(";"))
            print(f"[Headers] Cookies dans session: {cookie_count} cookies")

            # 🆕 Vérifier la qualité des cookies
            important_cookies = ["c_user", "xs", "fr", "datr", "sb"]
            found_important = [
                name for name in important_cookies if name in cookie_header
            ]

            if found_important:
                print(f"[Headers] ✅ Cookies importants trouvés: {found_important}")
            else:
                print("[Headers] ⚠️ Aucun cookie important trouvé dans la session")
        else:
            print("[Headers] ⚠️ Aucun cookie trouvé dans les headers de session")

        return session

    def load_headers(self, headers):
        # Cette méthode charge les en-têtes HTTP dans la session

        # Pour chaque paire clé-valeur dans les en-têtes fournis
        for key, value in headers:
            # Met à jour les en-têtes de la session avec la nouvelle paire clé-valeur
            self.session.headers.update({key: value})

        # Ajoute un en-tête spécifique pour identifier le type de requête Facebook
        # Cet en-tête indique qu'on utilise l'API de recherche immobilière sur la carte
        self.session.headers.update(
            {"x-fb-friendly-name": "CometMarketplaceRealEstateMapStoryQuery"}
        )

    def parse_payload(self, payload):
        # Vérifier si payload est déjà un dictionnaire
        if isinstance(payload, dict):
            return payload

        # Si c'est une chaîne, la parser
        if isinstance(payload, str):
            # Decode the data string if it's bytes
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")

            # Parse the string into a dictionary
            data_dict = dict(urllib.parse.parse_qsl(payload))
            return data_dict

        # Si c'est un autre type, essayer de le convertir en dict
        try:
            return dict(payload)
        except (TypeError, ValueError):
            print(f"Warning: Impossible de parser le payload de type {type(payload)}")
            return {}

    def init_session(
        self, user_id, session, lat, lon, minBudget, maxBudget, minBedrooms, maxBedrooms
    ):
        logger.info("init_session")

        headers, payload, resp_body = FacebookSessionModel().init_fb_session(user_id)

        # si le headers n'est pas trouvé
        if headers is None:
            logger.info("no headers found in doc\n")
            try:
                logger.info("on récupère le headers\n")

                return None, None, None

            except Exception as e:
                logger.info(
                    f"Erreur lors de l'obtention de la première requête : {e} header: {headers}\n"
                )

        self.load_fb_headers(headers, session)

        # parse payload to normal format
        payload = self.parse_payload(payload)

        # update the api name we're using (map api)
        # payload["doc_id"] = "29956693457255409"
        # payload["fb_api_req_friendly_name"] = "CometMarketplaceRealEstateMapStoryQuery"
        if payload.get("fb_api_req_friendly_name"):
            session.headers["x-fb-friendly-name"] = payload["fb_api_req_friendly_name"]

        variables = json.loads(payload["variables"])
        variables["radius"] = 4000
        variables["buyLocation"]["latitude"] = lat
        variables["buyLocation"]["longitude"] = lon
        variables["priceRange"] = [minBudget, maxBudget]
        variables["numericVerticalFieldsBetween"] = [
            {
                "max": maxBedrooms,  # ex: 3
                "min": minBedrooms,  # ex: 1
                "name": "bedrooms",
            }
        ]
        payload["variables"] = json.dumps(variables)

        return headers, payload, variables

    def add_feed_listings(self, body,job_id):
        """
        Traite les données du feed marketplace et extrait les informations importantes des listings.
        Structure: data.viewer.marketplace_feed_stories.edges

        Args:
            body (dict): Corps de la réponse GraphQL contenant les listings du feed
        """
        print("🔍 Recherche des listings dans le feed marketplace...")

        listings = []

        try:
            # Accéder aux edges du feed
            edges = body["data"]["viewer"]["marketplace_feed_stories"]["edges"]
            print(f"✅ Nombre d'edges trouvées(feed): {len(edges)}")

            for edge in edges:
                node = edge["node"]

                # Vérifier que c'est bien un listing
                if (
                    node.get("__typename") == "MarketplaceFeedListingStory"
                    and node.get("story_type") == "LISTING"
                    and "listing" in node
                ):
                    logger.info(f"Listing trouvée!")
                    listing = node["listing"]
                    listing_id = listing.get("id")

                    # Extraction des informations essentielles
                    title = listing.get("marketplace_listing_title", "")
                    price_info = listing.get("listing_price", {})
                    price_text = price_info.get("formatted_amount", "")
                    price_numeric = price_info.get("amount", "")

                    # Localisation
                    location_info = listing.get("location", {}).get(
                        "reverse_geocode", {}
                    )
                    city = location_info.get("city", "")
                    state = location_info.get("state", "")

                    # Chambres et salles de bain
                    custom_title = listing.get("custom_title", "")
                    bedrooms = self.clean_bedrooms(custom_title)
                    bathrooms = self.clean_bathrooms(custom_title)

                    # Image principale
                    primary_photo = listing.get("primary_listing_photo", {})
                    image_uri = ""
                    if primary_photo and "image" in primary_photo:
                        image_uri = primary_photo["image"].get("uri", "")

                    # Sous-titres (adresse)
                    subtitles = []
                    custom_subtitles = listing.get(
                        "custom_sub_titles_with_rendering_flags", []
                    )
                    for subtitle_obj in custom_subtitles:
                        if "subtitle" in subtitle_obj:
                            subtitles.append(subtitle_obj["subtitle"])

                    # Construction de l'objet listing filtré
                    filtered_data = {
                        "_id": listing_id,
                        "scraped_at": time.time(),
                        "title": title,
                        "price": {"formatted": price_text, "numeric": price_numeric},
                        "bedrooms": bedrooms,
                        "bathrooms": bathrooms,
                        "location": {
                            "city": city,
                            "state": state,
                            "full_address": (
                                " - ".join(subtitles)
                                if subtitles
                                else f"{city}, {state}"
                            ),
                        },
                        "primary_image": image_uri,
                        "custom_title": custom_title,
                        "listing_type": "feed",  # Pour distinguer du type map
                        "for_sale_item": {
                            "id": listing_id,
                            "marketplace_listing_title": title,
                            "formatted_price": price_info,
                            "location": listing.get("location", {}),
                            "custom_title": custom_title,
                            "custom_sub_titles_with_rendering_flags": custom_subtitles,
                            "listing_photos": [{"uri": image_uri}] if image_uri else [],
                            "share_uri": f"https://www.facebook.com/marketplace/item/{listing_id}/",
                        },
                    }

                    # print("filtered_data: ", filtered_data)

                    # Ajout à la liste des listings
                    listings.append(filtered_data)
                    self.event_publisher.publish(job_id,"progress",
                        {
                        "status":"listing_loading",
                        "title":title,
                        "image":image_uri,
                        "url":f"https://www.facebook.com/marketplace/item/{listing_id}/"  
                        }                
                                        ) 
                    logger.info(f"✅ Listing ajouté: {title} - {price_text} - {city}")

                else:
                    print(
                        f"⚠️ Type de node non reconnu: {node.get('__typename')} - {node.get('story_type')}"
                    )
            return listings

        except KeyError as e:
            print(f"❌ Erreur de structure dans le body: {e}")
            print(
                f"Clés disponibles: {list(body.get('data', {}).get('viewer', {}).keys())}"
            )
        except Exception as e:
            print(f"❌ Erreur lors du traitement des listings: {e}")

    def normalize_item(self, item: dict) -> dict:
        """Normalise une annonce brute en un objet simple et uniformisé.

        Retourne un dictionnaire avec les clés: id, title, price, bedrooms,
        bathrooms, url, images, description, source.
        """
        try:
            for_sale = item.get("for_sale_item", {}) or {}
            details = item.get("details", {}) or {}

            # Gestion intelligente du titre selon le type de listing
            title = ""
            if item.get("listing_type") == "feed":
                # Pour les listings du feed, utiliser le titre direct
                title = item.get("title", "") or for_sale.get(
                    "marketplace_listing_title", ""
                )
            else:
                # Pour les listings de la carte, utiliser la structure existante
                title = for_sale.get("marketplace_listing_title", "") or item.get(
                    "title", ""
                )

            # Gestion intelligente du prix selon le type de listing
            price = ""
            if item.get("listing_type") == "feed":
                # Pour les listings du feed, utiliser la structure price.formatted
                price_info = item.get("price", {})
                if isinstance(price_info, dict):
                    price = price_info.get("formatted", "")
                else:
                    price = str(price_info) if price_info else ""
            else:
                # Pour les listings de la carte, utiliser la structure existante
                price = (for_sale.get("formatted_price", {}) or {}).get(
                    "text"
                ) or item.get("budget", "")

            # Gestion intelligente de l'URL
            url = for_sale.get("share_uri")
            if not url and item.get("_id"):
                # Construire l'URL si elle n'existe pas
                url = f"https://www.facebook.com/marketplace/item/{item.get('_id')}/"

            normalized = {
                "id": item.get("_id"),
                "title": title,
                "price": price,
                "bedrooms": item.get("bedrooms"),
                "bathrooms": item.get("bathrooms"),
                "url": url,
                "images": details.get("images", []) or [],
                "description": details.get("description"),
                "source": "facebook",
                "listing_type": item.get(
                    "listing_type", "unknown"
                ),  # Ajouter le type pour debug
            }
            logger.debug("[normalize_item] %s", normalized)
            return normalized
        except Exception as e:
            logger.exception("[normalize_item] erreur: %s", e)
            return {
                "id": item.get("_id"),
                "title": None,
                "price": None,
                "bedrooms": item.get("bedrooms"),
                "bathrooms": item.get("bathrooms"),
                "url": None,
                "images": [],
                "description": None,
                "source": "facebook",
                "listing_type": item.get("listing_type", "unknown"),
                "error": str(e),
            }

    def clean_bathrooms(self, custom_title):
        """
        Extrait le nombre de salles de bain à partir du titre personnalisé
        Format typique: "X lits · Y salle de bain"

        Args:
            custom_title (str): Titre personnalisé de l'annonce

        Returns:
            float or None: Nombre de salles de bain ou None si non trouvé
        """
        try:
            if not custom_title:
                return None

            # Recherche le nombre (entier ou décimal) avant "salle de bain" ou "bath"
            import re

            match = re.search(
                r"(\d+(?:\.\d+)?)\s*(?:salle de bain|salles de bain|bath|baths)",
                custom_title.lower(),
            )
            if match:
                return float(match.group(1))  # Utilise float() au lieu de int()
            return None
        except:
            return None

    def clean_bedrooms(self, custom_title):
        """
        Extrait le nombre de chambres à partir du titre personnalisé
        Format typique: "X lits · Y salle de bain"

        Args:
            custom_title (str): Titre personnalisé de l'annonce

        Returns:
            int or None: Nombre de chambres ou None si non trouvé
        """
        try:
            if not custom_title:
                return None

            # Recherche le nombre avant "lits" ou "lit"
            import re

            match = re.search(
                r"(\d+)\s*(?:lit|lits|chambre|chambres|bed|beds)", custom_title.lower()
            )
            if match:
                return int(match.group(1))
            return None
        except:
            return None

    def clean_price(self, price):
        try:
            # Supprime tous les caractères non numériques sauf le point
            cleaned = "".join(char for char in price if char.isdigit() or char == ".")
            return float(cleaned)
        except:
            return None

    def getpageInfo(self, id: str):
        """function to get the page info of a listing with the elp of id"""
        try:
            page_driver = self.initialize_driver()

        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            return None

        page_info = {
            "title": "",
            "price": "",
            "bedrooms": "",
            "bathrooms": "",
            "description": "",
            "images": [],
            "url": "",
            "location": "",
        }

        url = f"https://www.facebook.com/marketplace/item/{id}/?ref=category_feed&locale=fr_CA"

        print("Recherche de l'annonce spécifique... ")
        print("url: ", url)
        page_driver.get(url)
        print("wait 5 seconds...")
        time.sleep(5)
        try:
            # Cherche le bouton X pour fermer le modal
            close_button = page_driver.find_element(
                By.CSS_SELECTOR, "[aria-label='Fermer']"
            )
            close_button.click()
            print("modal fermé...")

        except:
            print("Pas de modal à fermer")

        print("wait 5 seconds...")
        time.sleep(5)

        html_content = page_driver.page_source

        # Pretty print the HTML with proper indentation
        soup = BeautifulSoup(html_content, "html.parser")

        print("get le titre")
        # title = soup.find("span", class_="f4").text

        # # Extraction du titre
        title_element = soup.find("h1", class_=lambda c: c and "x1heor9g" in c)
        if title_element:
            page_info["title"] = title_element.text.strip()
            print("title", page_info["title"], "\n")

        # print("title: ", title)
        page_driver.quit()

        return page_info

    async def scrape(self, lat, lon, query, user_id: str, job_id, progress=None):
        print("Initialisation de fb_graphql_call...")

        for attempt in range(self.max_retries):
            try:
                # Créer une nouvelle session pour chaque tentative
                session = requests.Session()

                proxies = {
                    "http": os.getenv("PROXIES_URL"),
                    "https": os.getenv("PROXIES_URL"),
                }
                session.proxies.update(proxies)
                print("proxies updated... done")
                session.verify = False
                print("query: ", query)
                minBudget = query["minBudget"] or 0
                maxBudget = query["maxBudget"] or 0
                minBedrooms = query["minBedrooms"] or 0
                maxBedrooms = query["maxBedrooms"] or 0

                # Initialiser la session Facebook
                headers, payload, variables = self.init_session(
                    user_id,
                    session,
                    lat,
                    lon,
                    minBudget,
                    maxBudget,
                    minBedrooms,
                    maxBedrooms,
                )

                if headers is None or payload is None:
                    logger.info(
                        f"Session non initialisée pour user {user_id}, tentative {attempt + 1}"
                    )
                    if attempt < self.max_retries - 1:
                        sleep_time = (
                            self.retry_delay + (attempt + 1) + random.uniform(1, 5)
                        )
                        logger.info(f"Nouvelle tentative dans {sleep_time} secondes...")
                        time.sleep(sleep_time)
                        continue
                    else:
                        raise RuntimeError(
                            "Impossible d'initialiser la session Facebook"
                        )

                # Faire la requête POST initiale
                resp_body = session.post(
                    "https://www.facebook.com/api/graphql/",
                    data=urllib.parse.urlencode(payload),
                )
                logger.info(
                    f"[DEBUG] GraphQL Response status={resp_body.status_code}\n"
                )

                # Vérifier que la réponse contient les bonnes données avec boucle while
                try:
                    retry_count = 0
                    max_inner_retries = 3

                    while (
                        "marketplace_rentals_map_view_stories"
                        not in resp_body.json().get("data", {}).get("viewer", {})
                        and "marketplace_feed_stories"
                        not in resp_body.json().get("data", {}).get("viewer", {})
                        and retry_count < max_inner_retries
                    ):
                        print(
                            f"Pas le bon type de données, tentative interne {retry_count + 1}/{max_inner_retries}"
                        )

                        # Réessayer la requête
                        resp_body = session.post(
                            "https://www.facebook.com/api/graphql/",
                            data=urllib.parse.urlencode(payload),
                        )
                        retry_count += 1

                        # Petit délai entre les tentatives internes
                        time.sleep(2)

                    # Vérifier si on a finalement obtenu les bonnes données
                    if (
                        "marketplace_rentals_map_view_stories"
                        not in resp_body.json().get("data", {}).get("viewer", {})
                        and "marketplace_feed_stories"
                        not in resp_body.json().get("data", {}).get("viewer", {})
                    ):
                        logger.info(
                            "Impossible d'obtenir les données valides après toutes les tentatives internes"
                        )
                        raise RuntimeError(
                            "Données invalides après tentatives internes"
                        )

                    logger.info("Données GraphQL récupérées avec succès")

                    # Traiter les données selon leur type
                    response_data = resp_body.json()
                    viewer_data = response_data.get("data", {}).get("viewer", {})

                    if "marketplace_feed_stories" in viewer_data:
                        logger.info("📰 Traitement des données du feed")

                        listings = self.add_feed_listings(response_data,job_id)
                    else:
                        logger.info("⚠️ Type de données non reconnu")

                    if not listings and attempt < self.max_retries - 1:
                        logger.info(
                            f"Aucune annonce trouvée (tentative {attempt+1}), "
                            f"nouvelle tentative dans {self.retry_delay}s"
                        )
                        time.sleep(self.retry_delay)
                        continue
                    logger.info(f"Listings récupérés: {len(listings)}")
                    return listings

                except Exception as e:
                    logger.info(f"Erreur lors de la vérification des données: {e}")
                    raise

            except KeyError as e:
                logger.error(f"Clé manquante dans la session pour user {user_id}: {e}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.retry_delay + (attempt + 1) + random.uniform(1, 5)
                    logger.info(f"Nouvelle tentative dans {sleep_time} secondes...")
                    time.sleep(sleep_time)
                else:
                    raise RuntimeError(f"Invalid session data: missing key {e}")

            except Exception as e:
                print(f"Erreur lors de la tentative {attempt + 1}: {e}")

                if attempt < self.max_retries - 1:
                    self.event_publisher.publish(
                        job_id,
                        "error",
                        {
                            "message": f"erreur lors de la tentative {attempt} je vais reéssayer "
                        },
                    )
                    sleep_time = self.retry_delay + (attempt + 1) + random.uniform(1, 5)
                    print(f"Nouvelle tentative dans {sleep_time} secondes...")
                    time.sleep(sleep_time)

                else:
                    print("Nombre maximum de tentatives atteint")
                    raise RuntimeError(f"Unexpected error during GraphQL call: {e}")

            # Délai entre les tentatives principales
            if attempt < self.max_retries - 1:
                print("Attente 5 secondes avant la prochaine tentative...")
                time.sleep(5)

        # Si on arrive ici, toutes les tentatives ont échoué
        raise RuntimeError("Toutes les tentatives de fb_graphql_call ont échoué")
