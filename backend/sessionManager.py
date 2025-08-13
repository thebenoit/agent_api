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


class SessionsManager:
    def __init__(self):

        self.driver = os.getenv("DRIVER_PATH")

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
            print("No proxy config found in environment. Set PROXY_SERVER, PROXY_USERNAME, PROXY_PASSWORD env variables!")
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

    async def init_undetected_crawler(
        self,
        url="https://www.facebook.com/marketplace/montreal/propertyrentals?exact=false&latitude=45.50889&longitude=-73.63167&radius=7&locale=fr_CA",
    ):
        try:

            undetected_adapter = UndetectedAdapter()

            self.proxy_strategy = RoundRobinProxyStrategy(self.proxies)

            browser_config = BrowserConfig(
                headless=False,
                verbose=True,
                
                # proxy=f"http://{os.getenv("PROXIES_URL")}",
                #proxy_config=self.proxy_config,
                extra_args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )

            crawler_config = CrawlerRunConfig(
                # url=url,
                capture_network_requests=True,
                wait_for_images=True,
                cache_mode=CacheMode.BYPASS,
                proxy_rotation_strategy=self.proxy_strategy,
                # simulate_user=True,
            )

            crawler_strategy = AsyncPlaywrightCrawlerStrategy(
                browser_config=browser_config,
                browser_adapter=undetected_adapter,
            )

            async with AsyncWebCrawler(
                crawler_strategy=crawler_strategy, config=browser_config
            ) as crawler:

                result = await crawler.arun(url=url, config=crawler_config)

                if result.success:
                    print("Session: \n", result.session_id, "\n")
                    # print("HEADERS: \n", result.response_headers[:10], "\n")
                    self._dump_response_to_json(
                        result.response_headers, result.session_id, "response_headers"
                    )
                else:
                    print("Crawler failed to load the page: ", result.error_message)
                if result.network_requests:
                    # Filter only GraphQL requests
                    try:
                        graphql_requests = []
                        for req in result.network_requests:
                            # Support dict-like or object-like entries
                            url_value = None
                            if isinstance(req, dict):
                                url_value = req.get("url")
                            else:
                                url_value = getattr(req, "url", None)

                            if (
                                isinstance(url_value, str)
                                and "graphql" in url_value.lower()
                            ):
                                graphql_requests.append(req)

                        if graphql_requests:
                            self._dump_response_to_json(
                                graphql_requests,
                                result.session_id,
                                "network_requests_graphql",
                            )
                        else:
                            print("No GraphQL network requests found")
                    except Exception as _:
                        print(
                            "Failed to filter GraphQL network requests; skipping write"
                        )
                else:
                    print("No network requests found")

        except Exception as e:
            print("Error initializing crawler strategy:", e)
            return None

            print("crawler strategy initialized...")

    def _dump_response_to_json(self, data, session_id, label):
        """
        Persist the provided data into a JSON file under the local `data` directory.

        Arguments:
        - data: The Python object to serialize. Non-serializable objects are coerced to strings.
        - session_id: Identifier included in the filename for traceability. If falsy, a timestamp is used.
        - label: Logical label for the content (e.g., "response_headers", "network_requests").
        """
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)

            safe_session_id = str(session_id) if session_id else str(int(time.time()))
            file_name = f"{label}_{safe_session_id}.json"
            file_path = os.path.join(data_dir, file_name)

            payload = {
                "session_id": session_id,
                "label": label,
                "data": data,
            }

            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2, default=str)

            print(f"Wrote JSON to: {file_path}")
        except Exception as exc:
            print(f"Failed to write JSON to data directory: {exc}")
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
