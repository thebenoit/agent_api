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
    UndetectedAdapter,
    ProxyConfig,
    RoundRobinProxyStrategy,
    CacheMode,
)
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
import random
from models.fb_sessions import FacebookSessionModel
from schemas.fb_session import FacebookSession


class SessionsManager:
    def __init__(self):

        self.driver = os.getenv("DRIVER_PATH")
        self.user_id = "66bd41ade6e37be2ef4b4fc2"  # User ID fixe
        self.fb_session_model = FacebookSessionModel()

        self.mongo = MongoClient(os.getenv("MONGO_URI"))
        # self.fb_sessions = self.db["fb_sessions"]

        # self.proxies = {
        #     "http": os.getenv("PROXIES_URL"),
        #     "https": os.getenv("PROXIES_URL"),
        # }

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

        proxy_options = {}

        self.chrome_options = uc.ChromeOptions()
        self.chrome_options.add_argument("--ignore-ssl-errors=yes")
        self.chrome_options.add_argument("--ignore-certificate-errors")

        service = Service(self.driver)

        # seleniumwire options
        self.sw_options = {"enable_har": True, "proxy": self.proxies}

        # self.driver = uc.Chrome(
        #     service=service,
        #     options=chrome_options,
        #     seleniumwire_options=sw_options
        # )

    def get_session_info(self, url):
        self.driver.get(url)
        time.sleep(15)

    @staticmethod
    def extract_request_headers_from_result(result):
        graphql_data = []
        if not result or not getattr(result, "network_requests", None):
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
            # Extraire le body/payload de la requête
            if isinstance(req, dict):
                return (
                    req.get("request_body")
                    or req.get("body")
                    or (req.get("request") or {}).get("body")
                )
            return getattr(req, "request_body", None) or getattr(req, "body", None)

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
        url="https://www.facebook.com/marketplace/montreal/propertyrentals?exact=false&latitude=45.50889&longitude=-73.63167&radius=7&locale=fr_CA",
    ):
        try:

            undetected_adapter = UndetectedAdapter()

            self.proxy_strategy = RoundRobinProxyStrategy(self.proxies)

            browser_config = BrowserConfig(
                headless=True,
                verbose=True,
                # proxy=f"http://{os.getenv("PROXIES_URL")}",
                # proxy_config=self.proxy_config,
                extra_args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
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
                browser_adapter=undetected_adapter,
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
                    await asyncio.sleep(10)
                    reqs = self.extract_request_headers_from_result(result)
                    if reqs:
                        self._save_session_to_db(reqs, "initial_load")
                    else:
                        print("[crawl] No GraphQL requests found on initial load")

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
                            if reqs_after:
                                self._save_session_to_db(reqs_after, "after_modal")
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
                                            reqs_zoom, f"after_zoom_{i}"
                                        )
                            except Exception:
                                print(f"[zoom {i}/{times}] step failed (ignored)")

                    await perform_zoom_in(times=3, delay_ms=1000)

                else:
                    print("Crawler failed to load the page: ", result.error_message)

                # Final pass on initial load result for specific GraphQL endpoint
                if result and getattr(result, "network_requests", None):
                    try:
                        graphql_requests = []
                        for req in result.network_requests:
                            url_value = None
                            if isinstance(req, dict):
                                url_value = req.get("url")
                            else:
                                url_value = getattr(req, "url", None)
                            if (
                                isinstance(url_value, str)
                                and "graphql" in url_value.lower()
                                and "marketplace_rentals_map_view_stories"
                                in url_value.lower()
                            ):
                                graphql_requests.append(req)
                        if graphql_requests:
                            self._dump_response_to_json(
                                graphql_requests,
                                result.session_id,
                                "network_requests_graphql",
                            )
                        else:
                            print(
                                "[crawl] No GraphQL network requests found in final filter"
                            )
                    except Exception:
                        print(
                            "[crawl] Failed to filter GraphQL network requests; skipping write"
                        )
                else:
                    print("[crawl] No network requests found")

        except Exception as e:
            print("Error initializing crawler strategy:", e)
            return None

            print("crawler strategy initialized...")

    def extract_payload_from_crawl_data(self, requests_data):
        """Extrait payload et variables depuis les données du crawl"""
        try:
            for req_data in requests_data:
                body = req_data.get("body")
                if body:
                    # Si body est une string URL-encoded
                    if isinstance(body, str):
                        from urllib.parse import parse_qsl

                        parsed = dict(parse_qsl(body))

                        if "variables" in parsed:
                            variables = json.loads(parsed["variables"])

                            # Construire payload complet
                            payload = {
                                "doc_id": parsed.get("doc_id", "29956693457255409"),
                                "fb_api_req_friendly_name": parsed.get(
                                    "fb_api_req_friendly_name",
                                    "CometMarketplaceRealEstateMapStoryQuery",
                                ),
                                "variables": parsed["variables"],
                            }

                            # Ajouter autres champs si présents
                            for key, value in parsed.items():
                                if key not in payload:
                                    payload[key] = value

                            print(
                                f"[payload] Payload extrait depuis crawl: doc_id={payload.get('doc_id', 'N/A')}"
                            )
                            return payload, variables

            # Fallback vers payload de base si rien trouvé
            print("[payload] Aucun payload trouvé dans crawl, utilisation du fallback")
            base_variables = {
                "buyLocation": {"latitude": 45.50889, "longitude": -73.63167},
                "categoryIDArray": [1468271819871448],
                "numericVerticalFields": [],
                "numericVerticalFieldsBetween": [],
                "priceRange": [0, 214748364700],
                "radius": 7000,
                "stringVerticalFields": [],
            }

            base_payload = {
                "doc_id": "29956693457255409",
                "fb_api_req_friendly_name": "CometMarketplaceRealEstateMapStoryQuery",
                "variables": json.dumps(base_variables),
            }

            return base_payload, base_variables

        except Exception as e:
            print(f"[payload] Erreur extraction: {e}")
            return {}, {}

    def _save_session_to_db(self, requests_data, step_label):
        """
        Sauvegarde les données de session dans la base de données.

        Arguments:
        - requests_data: Les données des requêtes GraphQL capturées
        - step_label: Le label de l'étape (initial_load, after_modal, after_zoom_1, etc.)
        """
        try:
            if not requests_data:
                return

            # Extraire headers et payload depuis les données du crawl
            first_request = requests_data[0] if requests_data else {}
            headers = first_request.get("headers", {})

            # Extraire payload et variables depuis les vraies requêtes capturées
            payload, variables = self.extract_payload_from_crawl_data(requests_data)

            print(
                f"[DB] Payload extrait pour {step_label}: doc_id={payload.get('doc_id', 'N/A')}"
            )

            # Créer session avec les vraies données
            session_data = FacebookSession(
                user_id=self.user_id,
                cookies={},
                headers=headers,
                user_agent=headers.get("user-agent", ""),
                payload=payload,
                variables=variables,
                doc_id=payload.get("doc_id", "29956693457255409"),
                x_fb_lsd=headers.get("x-fb-lsd", ""),
                active=True,
            )

            # Vérifier si une session existe déjà
            existing_session = self.fb_session_model.get_session(self.user_id)

            if existing_session:
                # Mettre à jour la session existante
                updates = {
                    "headers": headers,
                    "user_agent": headers.get("user-agent", ""),
                    "x_fb_lsd": headers.get("x-fb-lsd", ""),
                    "payload": payload,
                    "variables": variables,
                    "last_used": time.time(),
                }
                self.fb_session_model.update_session(self.user_id, updates)
                print(f"[DB] Session mise à jour pour {step_label}")
            else:
                # Créer une nouvelle session
                session_id = self.fb_session_model.save_session(session_data)
                print(f"[DB] Nouvelle session créée: {session_id} pour {step_label}")

        except Exception as exc:
            print(f"[DB] Erreur lors de la sauvegarde: {exc}")
            return

    async def crawlai_get_req(
        self,
        url="https://www.facebook.com/marketplace/montreal/propertyrentals?exact=false&latitude=45.50889&longitude=-73.63167&radius=7&locale=fr_CA",
    ):

        async with AsyncWebCrawler() as crawler:
            config1 = CrawlerRunConfig(
                wait_for="css.login-modal",
                js_only=True,
                headless=False,
                js_code="""
                 document.querySelector('.login-modal .close-button').click();
                """,
                proxies=self.proxies,
            )
            # Introduce a random delay between 1 and 3 seconds
            delay = random.uniform(1, 3)
            await asyncio.sleep(delay)
            await crawler.arun(url, config=config1)

    def get_first_req(
        self,
        url="https://www.facebook.com/marketplace/montreal/propertyrentals?exact=false&latitude=45.50889&longitude=-73.63167&radius=7&locale=fr_CA",
    ):
        try:
            self.driver.get(url)
            # allow the page to load fully including any JavaScript that triggers API requests
            time.sleep(15)

            # get first request through selenium to get the headers and first results
            for request in self.driver.requests:
                try:
                    # if request is a response
                    if request.response:
                        # if request is a graphql request
                        if "graphql" in request.url:
                            print("graphql request found")
                            try:
                                # decode the response body
                                resp_body = decode(
                                    request.response.body,
                                    request.response.headers.get(
                                        "Content-Encoding", "identity"
                                    ),
                                )
                                # convert the response body to a json object
                                resp_body = json.loads(resp_body)

                                # if the response body contains the data we want
                                if (
                                    "marketplace_rentals_map_view_stories"
                                    in resp_body["data"]["viewer"]
                                ):
                                    print("marketplace_rentals_map_view_stories found")

                                    try:
                                        # Write all the data to a single structured file
                                        facebook_data = {
                                            "request_headers": dict(
                                                request.headers.__dict__["_headers"]
                                            ),
                                            "request_body": str(request.body),
                                            "response_body": resp_body,
                                        }

                                        with open(
                                            "facebook_graphql_data.json",
                                            "w",
                                            encoding="utf-8",
                                        ) as f:
                                            json.dump(
                                                facebook_data,
                                                f,
                                                indent=2,
                                                ensure_ascii=False,
                                            )

                                        print(
                                            "Structured data written to: facebook_graphql_data.json"
                                        )
                                        self.driver.quit()
                                        # return the headers, body, and response body
                                        return (
                                            request.headers.__dict__["_headers"],
                                            request.body,
                                            resp_body,
                                        )
                                    except (IOError, OSError) as e:
                                        print(f"Error writing to file: {e}")
                                        # Return data even if file writing fails

                                        return (
                                            request.headers.__dict__["_headers"],
                                            request.body,
                                            resp_body,
                                        )
                            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                print(f"Error decoding response body: {e}")
                                continue
                            except (KeyError, TypeError) as e:
                                print(f"Error accessing response data structure: {e}")
                                continue
                except Exception as e:
                    print(f"Error processing request: {e}")
                    continue

            print("No matching request found")
            return None

        except Exception as e:
            print(f"Error during driver navigation or request processing: {e}")
            return None

    def put_session_on_db():
        headers, body, resp_body = self.get_first_req()


# session_manager = SessionsManager()
