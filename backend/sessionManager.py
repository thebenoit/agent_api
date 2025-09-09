import os
import time
import json
import requests
from pymongo import MongoClient
import seleniumwire.undetected_chromedriver as uc
from seleniumwire import webdriver as sw
from seleniumwire.utils import decode
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from seleniumwire.undetected_chromedriver import ChromeOptions
from urllib.parse import urlparse
import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    # UndetectedAdapter,
    ProxyConfig,
    RoundRobinProxyStrategy,
    CacheMode,
)
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
import random
from models.fb_sessions import FacebookSessionModel
from schemas.fb_session import FacebookSession


class SessionsManager:
    """
    Gestionnaire de session pour facebook marketplace
    créer une session pour un utilisateur
    """

    def __init__(self):
        self.driver = os.getenv("DRIVER_PATH")
        self.user_id = "66bd41ade6e37be2ef4b4fc2"  # User ID fixe
        self.fb_session_model = FacebookSessionModel()

        self.mongo = MongoClient(os.getenv("MONGO_URI"))

        self.proxies = ProxyConfig.from_env()  # ProxyConfig.from_env()
        # eg: export PROXIES="ip1:port1:username1:password1,ip2:port2:username2:password2"
        if not self.proxies:
            print("No proxies found in environment. Set PROXIES env variable!")
            return

        self.proxy_config = ProxyConfig(
            server=os.getenv("PROXY_SERVER"),
            username=os.getenv("PROXY_USERNAME"),
            password=os.getenv("PROXY_PASSWORD"),
        )

        if not self.proxy_config:
            print(
                "No proxy config found in environment. Set PROXY_SERVER, PROXY_USERNAME, PROXY_PASSWORD env variables!"
            )
            return

        # Charger les villes depuis le fichier JSON
        self.cities = self._load_cities()

    def _load_cities(self):
        """Charge les villes depuis le fichier cities.json"""
        try:
            cities_path = os.path.join(os.path.dirname(__file__), "data", "cities.json")
            with open(cities_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("cities", [])
        except Exception as e:
            print(f"Erreur lors du chargement des villes: {e}")
            # Fallback vers Montreal si erreur
            return [
                {
                    "name": "Montreal",
                    "country": "Canada",
                    "locale": "fr_CA",
                    "latitude": 45.5044,
                    "longitude": -73.5761,
                    "region": "Quebec",
                }
            ]

    def _select_city_for_user(self, user_id: str):
        """Sélectionne une ville de manière déterministe basée sur l'user_id"""
        if not self.cities:
            return None

        # Utiliser l'user_id comme seed pour la sélection déterministe
        import hashlib

        user_hash = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        city_index = user_hash % len(self.cities)

        selected_city = self.cities[city_index]
        print(
            f"[City] Ville sélectionnée pour {user_id[:8]}: {selected_city['name']}, {selected_city['country']}"
        )
        return selected_city

    def _generate_facebook_marketplace_url(self, city_data):
        """Génère l'URL Facebook Marketplace pour une ville donnée"""
        base_url = "https://www.facebook.com/marketplace"

        radius = random.randint(10, 100)

        # Construire l'URL avec le format standard
        url = f"{base_url}/{city_data['name'].lower()}/propertyrentals"
        url += f"?exact=false"
        url += f"&latitude={city_data['latitude']}"
        url += f"&longitude={city_data['longitude']}"
        url += f"&radius={radius}"
        # url += f"&locale={city_data['locale']}"
        url += f"&locale=fr_CA"

        return url

    def generate_user_agent(self, user_id: str):
        """
        Génère un User-Agent cohérent pour un utilisateur.
        Si user_id est fourni, utilise un seed pour la reproductibilité.
        """
        from services.ua_generator import generate_complete_headers
        import hashlib

        if user_id:
            rnd_seed = random.randint(8, 16)
            # Seed reproductible basé sur l'user_id
            hash_part = int(hashlib.md5(user_id.encode()).hexdigest()[12], 16)
            time_part = int(time.time() * 1000) % 1000000
            seed = hash_part + time_part
            return generate_complete_headers(seed=seed)
        else:
            # Headers aléatoires pour compatibilité avec code existant
            return generate_complete_headers()

    def generate_user_specific_coordinates(self, user_id: str):
        """
        Génère des coordonnées légèrement variées pour chaque utilisateur
        basées sur la ville sélectionnée pour cet utilisateur.
        """
        import hashlib

        # Sélectionner la ville pour cet utilisateur
        city_data = self._select_city_for_user(user_id)
        if not city_data:
            # Fallback vers Montreal si pas de ville trouvée
            base_lat, base_lon = 45.50889, -73.63167
        else:
            base_lat, base_lon = city_data["latitude"], city_data["longitude"]

        # Seed basé sur l'user_id pour reproductibilité
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest()[:12], 16)

        # Variation de ±0.002 degré (environ 200m)
        lat_variation = ((user_hash % 2000) / 1000000) - 0.001
        lon_variation = (((user_hash // 2000) % 2000) / 1000000) - 0.001

        return {
            "latitude": base_lat + lat_variation,
            "longitude": base_lon + lon_variation,
        }

    @staticmethod
    def extract_request_headers_from_result(result):
        graphql_data = []
        if not result or not getattr(result, "network_requests", None):
            print("return req headers results: ")
            return graphql_data

        def get_req_headers(req):
            if isinstance(req, dict):
                return (
                    req.get("request_headers")
                    or req.get("headers")
                    or (req.get("request") or {}).get("headers")
                )
            h = getattr(req, "request_headers", None) or getattr(req, "headers", None)
            if h:
                return h
            request_obj = getattr(req, "request", None)
            return getattr(request_obj, "headers", None) if request_obj else None

        def get_req_body(req):
            if isinstance(req, dict):
                body = (
                    req.get("request_body")
                    or req.get("body")
                    or (req.get("request") or {}).get("body")
                    or req.get("post_data")
                )
            else:
                body = (
                    getattr(req, "request_body", None)
                    or getattr(req, "body", None)
                    or getattr(req, "post_data", None)
                )
            if isinstance(body, (bytes, bytearray)):
                try:
                    body = body.decode("utf-8", errors="ignore")
                except Exception:
                    body = None
            return body

        for req in result.network_requests:
            u = req.get("url") if isinstance(req, dict) else getattr(req, "url", None)
            if isinstance(u, str) and "graphql" in u.lower():
                headers = get_req_headers(req)
                body = get_req_body(req)

                if headers:
                    graphql_data.append(
                        {
                            "url": u,
                            "headers": headers,
                            "body": body,  # Ajouter le body pour extraire payload/variables
                        }
                    )
        return graphql_data

    async def init_undetected_crawler(
        self,
        user_id: str = None,
        url=None,
    ):
        try:

            if url is None:
                coords = self.generate_user_specific_coordinates(user_id)
                city_data = self._select_city_for_user(user_id)
                url = self._generate_facebook_marketplace_url(city_data)
                print(
                    f"[User {user_id[:8]}] URL générée avec coordonnées personnalisées"
                )

            # browser_headers = self.generate_user_agent(user_id)
            # print("browser_headers: ", browser_headers,"\n")
            # user_agent = browser_headers["User-Agent"]

            # undetected_adapter = UndetectedAdapter()
            self.proxy_strategy = RoundRobinProxyStrategy(self.proxies)

            browser_config = BrowserConfig(
                headless=True,
                verbose=True,
                # user_agent=user_agent,
                user_agent_mode="random",
                extra_args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    # f"--user-agent={user_agent}",
                ],
            )

            # Keep a persistent session to run JS steps (close modal, map nudges) in the same tab
            session_identifier = f"fb_session_{int(time.time())}"
            print(f"[crawl] starting session: {session_identifier} url={url}")

            crawler_config = CrawlerRunConfig(
                # url=url,
                capture_network_requests=True,
                wait_for_images=True,
                cache_mode=CacheMode.BYPASS,
                proxy_rotation_strategy=self.proxy_strategy,
                scan_full_page=True,
                session_id=session_identifier,
                # simulate_user=True,
            )

            crawler_strategy = AsyncPlaywrightCrawlerStrategy(
                browser_config=browser_config,
                # browser_adapter=undetected_adapter,
            )

            async with AsyncWebCrawler(
                crawler_strategy=crawler_strategy, config=browser_config
            ) as crawler:

                print("[crawl] initial load...")
                result = await crawler.arun(url=url, config=crawler_config)

                if result.success:
                    total_reqs = (
                        len(result.network_requests or [])
                        if hasattr(result, "network_requests")
                        else 0
                    )
                    total_graphql = 0
                    if getattr(result, "network_requests", None):
                        for _r in result.network_requests:
                            u = (
                                _r.get("url")
                                if isinstance(_r, dict)
                                else getattr(_r, "url", None)
                            )
                            if isinstance(u, str) and "graphql" in u.lower():
                                total_graphql += 1
                    print(
                        f"[crawl] initial load ok: network_requests={total_reqs} graphql={total_graphql}"
                    )
                    # Give the page extra time to fully settle before interacting
                    print(
                        "[crawl] waiting ~10s for page to fully settle before actions..."
                    )
                    rnd_sleep = random.randint(7, 20)
                    await asyncio.sleep(rnd_sleep)
                    reqs = self.extract_request_headers_from_result(result)
                    if reqs:
                        # self._save_session_to_db(reqs, "initial_load", user_id)
                        print("[crawl] GraphQL requests found on initial load:")
                    else:
                        print("[crawl] No GraphQL requests found on initial load")
                        # return None

                    # Try to close the login modal (X/labels/Escape)
                    print("[modal] attempting to close modal (X/labels/Escape)...")
                    close_modal_config = CrawlerRunConfig(
                        session_id=session_identifier,
                        js_only=True,
                        js_code="""
                        (function () {
                          const tryClick = (sel) => {
                            const el = document.querySelector(sel);
                            if (el) { el.click(); return true; }
                            return false;
                          };
                          const selectors = [
                            'div[role="dialog"] [aria-label*="Fermer" i]',
                            'div[role="dialog"] [aria-label*="Close" i]',
                            '[data-testid="x_close_button"]',
                            'button[aria-label*="Fermer" i]',
                            'button[aria-label*="Close" i]'
                          ];
                          for (const s of selectors) { if (tryClick(s)) return; }
                          const buttons = Array.from(document.querySelectorAll('div[role="dialog"] button, div[role="dialog"] [role="button"]'));
                          for (const b of buttons) {
                            const label = (b.getAttribute('aria-label') || b.textContent || '').trim();
                            if (/^(fermer|close|dismiss)$/i.test(label)) { b.click(); return; }
                          }
                          document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', keyCode: 27, bubbles: true }));
                        })();
                        """,
                        wait_for="js:() => true",
                        capture_network_requests=True,
                    )

                    try:
                        modal_result = await crawler.arun(
                            url=url, config=close_modal_config
                        )
                        if modal_result and getattr(
                            modal_result, "network_requests", None
                        ):
                            m_total = (
                                len(modal_result.network_requests or [])
                                if hasattr(modal_result, "network_requests")
                                else 0
                            )
                            m_graphql = 0
                            for _r in modal_result.network_requests or []:
                                u = (
                                    _r.get("url")
                                    if isinstance(_r, dict)
                                    else getattr(_r, "url", None)
                                )
                                if isinstance(u, str) and "graphql" in u.lower():
                                    m_graphql += 1
                            print(
                                f"[modal] step executed: network_requests={m_total} graphql={m_graphql}"
                            )
                            reqs_after = self.extract_request_headers_from_result(
                                modal_result
                            )
                            # if reqs_after:
                            # self._save_session_to_db(
                            #     reqs_after, "after_modal", user_id
                            # )
                    except Exception:
                        print("[modal] step failed (ignored)")

                    # Click Zoom In (+) multiple times with short waits
                    async def perform_zoom_in(times: int = 3, delay_ms: int = 1000):
                        print(f"[zoom] clicking + {times}x, delay ~{delay_ms}ms")
                        for i in range(1, times + 1):
                            zoom_in_cfg = CrawlerRunConfig(
                                session_id=session_identifier,
                                js_only=True,
                                js_code="""
                                (function () {
                                  const q = (sel) => document.querySelector(sel);
                                  const selectors = [
                                    '[aria-label*="Zoom avant" i][role="button"]',
                                    'div[aria-label*="Zoom avant" i][role="button"]',
                                    '[aria-label*="Zoom in" i][role="button"]',
                                    'button[aria-label*="Zoom In" i]',
                                    'button[aria-label*="Zoom avant" i]'
                                  ];
                                  let btn = null;
                                  for (const s of selectors) { btn = q(s); if (btn) break; }
                                  if (!btn) return;
                                  try { btn.scrollIntoView({ block: 'center', inline: 'center' }); } catch (e) {}
                                  const rect = btn.getBoundingClientRect();
                                  const x = rect.left + rect.width / 2;
                                  const y = rect.top + rect.height / 2;
                                  const fire = (type) => btn.dispatchEvent(new MouseEvent(type, { bubbles: true, clientX: x, clientY: y }));
                                  const firePtr = (type) => btn.dispatchEvent(new PointerEvent(type, { bubbles: true, clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse', isPrimary: true }));
                                  firePtr('pointerover'); fire('mouseover');
                                  firePtr('pointerdown'); fire('mousedown');
                                  btn.click();
                                  firePtr('pointerup'); fire('mouseup');
                                })();
                                """,
                                wait_for=f"js:() => new Promise(r => setTimeout(() => r(true), {delay_ms}))",
                                capture_network_requests=True,
                            )
                            try:
                                zoom_result = await crawler.arun(
                                    url=url, config=zoom_in_cfg
                                )
                                if zoom_result and getattr(
                                    zoom_result, "network_requests", None
                                ):
                                    reqs_zoom = (
                                        self.extract_request_headers_from_result(
                                            zoom_result
                                        )
                                    )
                                    z_total = (
                                        len(zoom_result.network_requests or [])
                                        if hasattr(zoom_result, "network_requests")
                                        else 0
                                    )
                                    z_graphql = 0
                                    for _r in zoom_result.network_requests or []:
                                        u = (
                                            _r.get("url")
                                            if isinstance(_r, dict)
                                            else getattr(_r, "url", None)
                                        )
                                        if (
                                            isinstance(u, str)
                                            and "graphql" in u.lower()
                                        ):
                                            z_graphql += 1
                                    print(
                                        f"[zoom {i}/{times}] executed: network_requests={z_total} graphql={z_graphql} headers_dumped={len(reqs_zoom) if reqs_zoom else 0}"
                                    )
                                    if reqs_zoom:
                                        self._save_session_to_db(
                                            reqs_zoom, f"after_zoom_{i}", user_id
                                        )
                            except Exception:
                                print(f"[zoom {i}/{times}] step failed (ignored)")

                    rnd_delay = random.randint(1000, 3000)
                    await perform_zoom_in(times=3, delay_ms=rnd_delay)
                    return result

                else:
                    print("Crawler failed to load the page: ", result.error_message)
                    return None

        except Exception as e:
            print("Error initializing crawler strategy:", e)
            return None

    def extract_payload_from_crawl_data(self, requests_data):
        try:
            for req_data in requests_data:
                body = req_data.get("body")
                # 1) Normaliser en str
                if isinstance(body, (bytes, bytearray)):
                    try:
                        body = body.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                if not isinstance(body, str) or not body:
                    continue

                from urllib.parse import parse_qsl

                parsed = dict(parse_qsl(body))

                # Besoin au minimum de variables + doc_id
                if "variables" not in parsed:
                    continue

                # variables doit être JSON valide (string JSON)
                try:
                    variables = json.loads(parsed["variables"])
                except Exception:
                    # parfois double-encodé -> unquote puis json.loads
                    from urllib.parse import unquote

                    try:
                        variables = json.loads(unquote(parsed["variables"]))
                        parsed["variables"] = unquote(parsed["variables"])
                    except Exception:
                        continue

                # doc_id présent ? (sinon on skip, on NE met PAS un faux default)
                if "doc_id" not in parsed:
                    continue

                # Construire le payload EXACT de cette requête
                payload = {
                    "doc_id": parsed["doc_id"],
                    # s'il manque fb_api_req_friendly_name dans le body,
                    # on le prend du header x-fb-friendly-name si dispo
                    "fb_api_req_friendly_name": parsed.get("fb_api_req_friendly_name")
                    or req_data.get("headers", {}).get("x-fb-friendly-name", ""),
                    "variables": parsed["variables"],  # JSON string, pas re-encodée
                }
                # Conserver les autres clés body utiles
                for k, v in parsed.items():
                    if k not in payload:
                        payload[k] = v

                headers = req_data.get("headers", {})
                return {"headers": headers, "payload": payload, "variables": variables}

            # Rien de bon trouvé
            return None
        except Exception as e:
            print(f"[payload] Erreur extraction: {e}")
            return None

    def _save_session_to_db(self, requests_data, step_label, user_id: str):
        try:
            if not requests_data:
                return
            extracted = self.extract_payload_from_crawl_data(requests_data)
            if not extracted:
                print("[DB] Aucun payload exploitable")
                return

            headers = extracted["headers"] or {}
            payload = extracted["payload"] or {}
            variables = extracted["variables"] or {}

            session_data = FacebookSession(
                user_id=user_id,
                cookies={},  # tu peux aussi récupérer les cookies si crawl4ai les expose
                headers=headers,
                user_agent=headers.get("user-agent", ""),
                payload=payload,
                variables=variables,
                doc_id=payload.get("doc_id", ""),
                x_fb_lsd=headers.get("x-fb-lsd", ""),
                active=True,
            )

            existing_session = self.fb_session_model.get_session(user_id)
            if existing_session:
                updates = {
                    "headers": headers,
                    "user_agent": headers.get("user-agent", ""),
                    "x_f_b_lsd": headers.get(
                        "x-fb-lsd", ""
                    ),  # garde la même clé si tu en as une
                    "payload": payload,
                    "variables": variables,
                    "last_used": time.time(),
                }
                self.fb_session_model.update_session(user_id, updates)
            else:
                self.fb_session_model.save_session(session_data)
        except Exception as exc:
            print(f"[DB] Erreur lors de la sauvegarde: {exc}")

    async def create_session_for_user(
        self, user_id: str, force_refresh: bool = False
    ) -> bool:
        """
        API pour créer ou mettre a jour une session
        """
        try:
            if not force_refresh:
                existing_session = self.fb_session_model.get_session(user_id)
                if existing_session:
                    return True

            print(f"[user {user_id[:8]}] Création de session...")
            success = await self.init_undetected_crawler(user_id)

            if success:
                print(f"[user {user_id[:8]}] Session contient quelque chose")
                return True
            else:
                print(f"[user {user_id[:8]}] Erreur lors de la création de la session")
                return False

        except Exception as e:
            print(
                f"[user {user_id[:8]}] Erreur lors de la création/mise à jour de la session: {e}"
            )
            return False
        
    

    def put_session_on_db():
        headers, body, resp_body = self.get_first_req()


# session_manager = SessionsManager()
