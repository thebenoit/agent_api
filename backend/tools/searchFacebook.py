from typing import Any
import os
from dotenv import load_dotenv
from seleniumwire import webdriver  # Import from seleniumwire
import sys

# from setuptools._distutils import version as _version
# sys.modules['distutils.version'] = _version
import seleniumwire.undetected_chromedriver as uc
from seleniumwire.undetected_chromedriver import Chrome
from selenium.webdriver.common.by import By
from pymongo import MongoClient
from seleniumwire.utils import decode
from selenium.webdriver.chrome.options import Options
#from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import logging
import sys
from bs4 import BeautifulSoup

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

load_dotenv()

from tools.base_tool import BaseTool
from tools.bases.base_scraper import BaseScraper


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

        proxies = {"http": os.getenv("PROXIES_URL"), "https": os.getenv("PROXIES_URL")}

        proxy_options = {}

        self.chrome_options = uc.ChromeOptions()

        # ignore ssl errors
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--ignore-ssl-errors=yes")
        self.chrome_options.add_argument("--ignore-certificate-errors")

        print(f"Chrome options chargées")

        service = Service(self.driver)

        # seleniumwire options
        sw_options = {"enable_har": True, "proxy": proxies}
        # self.driver = uc.Chrome(
        #     service=service,
        #     options=chrome_options,
        #     seleniumwire_options={"enable_har": True},
        # )

        # self.filtered_har = self.get_har()

        # create a http session
        self.session = (
            requests.Session()
        )  # Permet de réutiliser connexions, cookies et en-têtes entre plusieurs requêtes.
        self.session.proxies.update(proxies)
        # #ignore ssl errors
        self.session.verify = False

        print("les options de sessions sont chargées")

        self.init_session()

        # #close the driver
        # self.driver.close()

        self.max_retries = 3
        self.retry_delay = 10

    def execute(
        self,
        lat: float,
        lon: float,
        minBudget: float,
        maxBudget: float,
        minBedrooms: int,
        maxBedrooms: int,
    ) -> Any:

        self.listings = []

        inputs = {
            "lat": lat,
            "lon": lon,
            "minBudget": minBudget * 10,
            "maxBudget": maxBudget * 10,
            "minBedrooms": minBedrooms,
            "maxBedrooms": maxBedrooms,
        }
        print("inputs: ", inputs)
        # query = {"lat":"40.7128","lon":"-74.0060","bedrooms":2,"minBudget":80000,"maxBudget":100000,"bedrooms":3,"minBedrooms":3,"maxBedrooms":4}
        listings = self.scrape(inputs["lat"], inputs["lon"], inputs)
        if listings:
            # Gérer le cas où marketplace_listing_title peut être une string ou un dict
            title = listings[0]["for_sale_item"]["marketplace_listing_title"]
            if isinstance(title, dict):
                print("listings: ", title.get("text", title))
            else:
                print("listings: ", title)
        else:
            print("Aucune annonce trouvée: ")

        return listings

    ##methode to get the har file from the driver
    def get_har(self):
        print("Lancement du driver")
        self.driver.get(self.url)
        time.sleep(15)
        raw_har = self.driver.har
        # si c'est une chaîne JSON, on la parse
        if isinstance(raw_har, str):
            self.har = json.loads(raw_har)
        else:
            self.har = raw_har

        # Extract headers, payload, url and response body for graphql requests
        filtered_har = {
            "log": {
                "entries": [
                    {
                        "request": {
                            "url": entry["request"]["url"],
                            "headers": entry["request"]["headers"],
                            "method": entry["request"]["method"],
                            "postData": entry["request"].get("postData", {}),
                        },
                        "response": {
                            "content": entry["response"].get("content", {}),
                            "headers": entry["response"].get("headers", []),
                            "status": entry["response"].get("status"),
                            "statusText": entry["response"].get("statusText"),
                            "bodySize": entry["response"].get("bodySize"),
                            "body": entry["response"].get("body", ""),
                        },
                    }
                    for entry in self.har["log"]["entries"]
                    if entry["request"].get("url")
                    == "https://www.facebook.com/api/graphql/"
                ]
            }
        }

        # Write filtered HAR data to file
        with open("data/facebook.har", "w") as f:
            json.dump(filtered_har, f, indent=4)

        return filtered_har

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

    # def fetch_graphql_call(query_url_fragments="/api/graphql/",timeout=10000):

    def get_next_cursor(self, body):
        try:
            # On descend dans data.viewer.marketplace_feed_stories.page_info
            page_info = body["data"]["viewer"]["marketplace_feed_stories"]["page_info"]
            raw_cursor = page_info["end_cursor"]

            # raw_cursor est une chaîne JSON encodée, on la parse si possible
            try:
                return json.loads(raw_cursor)
            except json.JSONDecodeError:
                # print(f"raw_cursor: {raw_cursor}")
                # si ce n'est pas du JSON valide, on retourne la chaîne brute
                return raw_cursor

        except KeyError as e:
            print(f"Erreur d'accès aux données : {e}")
            # on peut logger body pour debug :
            # print(json.dumps(body, indent=2))
            return None

    def parse_payload(self, payload):

        # Decode the data string
        # decoded_str = urllib.parse.unquote(payload.decode())

        # Parse the string into a dictionary
        data_dict = dict(urllib.parse.parse_qsl(payload))

        return data_dict

    def init_session(self):

        headers, payload_to_send, resp_body = self.get_har_entry()

        # si le headers n'est pas trouvé
        if headers is None:
            print("no headers found in har file")
            try:
                print("on récupère le har file")
                # on récupère le har file
                self.har = self.get_har()
                # on récupère les headers, payload et resp_body
                headers, payload_to_send, resp_body = self.get_har_entry()

            except Exception as e:
                print(
                    f"Erreur lors de l'obtention de la première requête : {e} header: {headers}"
                )

        self.next_cursor = self.get_next_cursor(resp_body)

        # self.listings.append(resp_body)

        # load headers to requests Sesssion
        self.load_headers(headers)

        # parse payload to normal format
        self.payload_to_send = self.parse_payload(payload_to_send)

        # update the api name we're using (map api)
        self.payload_to_send["doc_id"] = "29956693457255409"
        self.payload_to_send["fb_api_req_friendly_name"] = (
            "CometMarketplaceRealEstateMapStoryQuery"
        )

        self.variables = json.loads(self.payload_to_send["variables"])
        # self.variables = {"buyLocation":{"latitude":45.4722,"longitude":-73.5848},"categoryIDArray":[1468271819871448],"numericVerticalFields":[],"numericVerticalFieldsBetween":[],"priceRange":[0,214748364700],"radius":2000,"stringVerticalFields":[]}

        # self.driver.close()

    def add_listings(self, body):
        print("cherche les listings...")
        try:
            edges = body["data"]["viewer"]["marketplace_rentals_map_view_stories"][
                "edges"
            ]
            print(f"🔍 Nombre d'edges trouvées: {len(edges)}")

            for node in body["data"]["viewer"]["marketplace_rentals_map_view_stories"][
                "edges"
            ]:
                if (
                    "for_sale_item" in node["node"]
                    and "id" in node["node"]["for_sale_item"]
                ):
                    print("FOR SALE ITEM FOUND")
                    listing_id = node["node"]["for_sale_item"]["id"]
                    # Utiliser listing_id comme _id dans le document
                    # data = node["node"]

                    # Traitement des images
                    listing_photos = []
                    if "listing_photos" in node["node"]["for_sale_item"]:
                        for photo in node["node"]["for_sale_item"]["listing_photos"]:
                            if "image" in photo:
                                # Modifier L"URL pour obtenir l'image en haute qualité
                                original_url = photo["image"]["uri"]
                                # Remplacer les paramètres de taille dans l'URL
                                # hq_url = original_url.split('?')[0] + "?width=1080&height=1080&quality=original"

                                listing_photos.append(
                                    {
                                        "id": photo.get("id", ""),
                                        "uri": original_url,
                                    }
                                )

                    # Extraire et nettoyer le prix pour le convertir en valeur numérique
                    price_numeric = None
                    if (
                        "formatted_price" in node["node"]["for_sale_item"]
                        and "text" in node["node"]["for_sale_item"]["formatted_price"]
                    ):
                        price_text = node["node"]["for_sale_item"]["formatted_price"][
                            "text"
                        ]
                        # Supprimer les espaces, le symbole $ et convertir en nombre
                        price_numeric = self.clean_price(price_text)

                        # Extraire le nombre de chambres et de salles de bain
                    custom_title = node["node"]["for_sale_item"].get("custom_title", "")
                    bedrooms = self.clean_bedrooms(custom_title)
                    bathrooms = self.clean_bathrooms(custom_title)

                    # Au lieu d'ajouter tout le nœud, créez un nouvel objet avec seulement les champs désirés
                    filtered_data = {
                        "_id": listing_id,
                        "scraped_at": time.time(),  # Ajoute un timestamp UNIX
                        "budget": price_numeric,
                        "bedrooms": bedrooms,
                        "bathrooms": bathrooms,
                        "for_sale_item": {
                            "id": node["node"]["for_sale_item"]["id"],
                            "marketplace_listing_title": node["node"][
                                "for_sale_item"
                            ].get("marketplace_listing_title", ""),
                            "formatted_price": node["node"]["for_sale_item"].get(
                                "formatted_price", {}
                            ),
                            "location": node["node"]["for_sale_item"].get(
                                "location", {}
                            ),
                            "custom_title": node["node"]["for_sale_item"].get(
                                "custom_title", ""
                            ),
                            "custom_sub_titles_with_rendering_flags": node["node"][
                                "for_sale_item"
                            ].get("custom_sub_titles_with_rendering_flags", []),
                            "listing_photos": listing_photos,
                            "share_uri": node["node"]["for_sale_item"].get(
                                "share_uri", ""
                            ),
                        },
                    }
                    # Vérifie si l'annonce existe déjà dans la liste
                    listing_exists = False
                    for listing in self.listings:
                        if listing.get("_id") == listing_id:
                            listing_exists = True
                            break

                    if not listing_exists:
                        print("Ajout de data--------->:")
                        # print("filtered_data: \n", filtered_data)
                        self.listings.append(filtered_data)
                # else:
                # print("no for_sale_item found")
        except KeyError as e:
            print(f"Erreur de structure dans le body : {e}")

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

    def initialize_driver(self):
        print("Initialisation du navigateur Chrome")

        """Initialise et retourne une nouvelle instance du navigateur Chrome"""
        try:
            chrome_options = uc.ChromeOptions()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--ignore-ssl-errors=yes")
            chrome_options.add_argument("--ignore-certificate-errors")

            driver_path = os.getenv("DRIVER_PATH")
            service = Service(driver_path)

            return uc.Chrome(
                service=service,
                options=chrome_options,
            )
        except Exception as e:
            print(f"Erreur lors de l'initialisation du navigateur Chrome: {e}")
            return None

    def get_realtorca_url(self, page_number):
        try:
            return f"https://www.realtor.ca/realtor-search-results#province=4&page={page_number}&sort=11-A"
        except Exception as e:
            return None

    def scrape(self, lat, lon, query):
        print("Initialisation de la methode Scrape...")
        for attempt in range(self.max_retries):
            # Méthode pour scraper les données à une position géographique donnée
            try:
                # Met à jour les coordonnées de recherche dans les variables
                self.variables["buyLocation"]["latitude"] = lat
                self.variables["buyLocation"]["longitude"] = lon
                self.variables["priceRange"] = [query["minBudget"], query["maxBudget"]]
                self.variables["numericVerticalFieldsBetween"] = [
                    {
                        "max": query["maxBedrooms"],  # ex: 3
                        "min": query["minBedrooms"],  # ex: 1
                        "name": "bedrooms",
                    }
                ]

                # Convertit les variables en JSON et les ajoute au payload
                self.payload_to_send["variables"] = json.dumps(self.variables)

                #print("headers: ", self.session.headers, "\n")

                # Fait une requête POST à l'API GraphQL de Facebook
                resp_body = self.session.post(
                    "https://www.facebook.com/api/graphql/",
                    data=urllib.parse.urlencode(self.payload_to_send),
                )
                # print(
                # "resp_body: ",
                # dict(list(resp_body.json().items())[:1])
                # )  

                # Vérifie que la réponse contient bien les données d'appartements
                try:
                    while (
                        "marketplace_rentals_map_view_stories"
                        not in resp_body.json()["data"]["viewer"]
                    ):
                        print("pas le bon type de données")  # Affiche une erreur
                        # print(f" resp json {resp_body.json()["data"]["viewer"]}") # Affiche la réponse pour debug
                        # Réessaie la requête
                        resp_body = self.session.post(
                            "https://www.facebook.com/api/graphql/",
                            data=urllib.parse.urlencode(self.payload_to_send),
                        )
                except Exception as e:
                    print(f"Erreur lors de la vérification des données: {e}")
                    raise

                # Ajoute les annonces trouvées à la liste

                # self.listings.append(resp_body.json())
                self.add_listings(resp_body.json())

            except Exception as e:
                print(f"Erreur lors de la tentative {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    sleep_time = self.retry_delay * (attempt + 1) + random.uniform(1, 5)
                    print(f"Nouvelle tentative dans {sleep_time} secondes...")
                    sleep(sleep_time)
                else:
                    print(
                        "Nombre maximum de tentatives atteint, passage au point suivant"
                    )
                    return []

            # Attend 5 secondes entre chaque requête
            print("wait 5 seconds...")
            time.sleep(5)

        # Après la boucle, retourne les résultats
        if self.listings:
            print("length of listings: ", len(self.listings))
            return self.listings  # Retourne toute la liste
        else:
            return []  # Retourne liste vide si aucun résultat
