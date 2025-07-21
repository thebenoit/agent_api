from tools.base_tool import BaseTool
from tools.bases.base_scraper import BaseScraper
import os
import re
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    RoundRobinProxyStrategy,
    ProxyConfig,
    JsonCssExtractionStrategy,
    JsonCssExtractionStrategy,
)


class OnePage(BaseTool, BaseScraper):
    def __init__(self):
        super().__init__()

        self.proxy_configs = ProxyConfig.from_env()
        self.user_agent = None
        self.headers = None
        self.payload_to_send = None
        self.cookies = None
        ignore_ssl_errors = True

        self.schema = {
            "name": "Facebook Images",
            "baseSelector": "body",
            "fields": [
                
                    {
                        "name": "Description", 
                        "selector": "div.xz9dl7a > div[aria-hidden='false'] > span[dir='auto']",
                        "type": "text"
                    },
                
                {
                 
                     "name":"sous_titre_details",
                     "selector":"div.xwib8y2",
                     "type":"nested_list",
                     "fields":[
                         { "name":"sous_titre",
                         "selector":"div, span.x193iq5w.xeuugli.x13faqbe.x1vvkbs.xlh3980.xvmahel.x1n0sxbx.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x4zkp8e.x3x7a5m.x6prxxf.xvq8zen.xo1l8bm.xzsf02u.x1yc453h",
                         "type":"text"
                         }
                     ],
                
                },
                # {
                #     "name":"Details",
                #     "selector":"div.xwib8y2",
                #     "type":"nested_list",
                #     "fields":[
                #        { "name":"un_detail",
                #         "selector":"div, span.x193iq5w.xeuugli.x13faqbe.x1vvkbs.xlh3980.xvmahel.x1n0sxbx.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x4zkp8e.x3x7a5m.x6prxxf.xvq8zen.xo1l8bm.xzsf02u.x1yc453h",
                #         "type":"text"
                #        }
                #     ],
                    
                # },
                {
                    "name": "images",
                    "selector": "div[role='main']",
                    "type": "nested_list",
                    "fields": [
 
                        {
                            "name": "thumbnails",
                            "selector": "div[aria-label*='Thumbnail']",
                            "type": "nested_list",
                            "fields": [
                                {
                                    "name": "src",
                                    "selector": "img",
                                    "type": "attribute",
                                    "attribute": "src"
                                },
                                {
                                    "name": "alt",
                                    "selector": "img",
                                    "type": "attribute",
                                    "attribute": "alt"
                                }
                            ]
                        },

                    ]
                }
            ]
        
        }

    @property
    def name(self):
        return "one_page"

    @property
    def description(self):
        return "fetch deeply one page(or multiple in a concurrent way)"

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

    def execute(self, url: str):
        return "allo"

    def scrape(self, url: str):
        return "allo"

    async def fetch_page(self, url: str):

        # load proxies and create rotation strategy
        proxy_strategy = None
        if self.proxy_configs:
            proxy_strategy = RoundRobinProxyStrategy(self.proxy_configs)
        else:
            print(
                "⚠️  Aucun proxy configuré. Définissez la variable d'environnement PROXIES_URL"
            )

        browser_config = BrowserConfig(
            verbose=True,
            headless=True,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            extra_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            # cookies = {
            #     "datr": "Kt1aaJzfABZM7avRtLfDCUmV",
            #     "sb": "Kt1aaD5JktL8FtgYs3lBovg6",
            #     "wd": "1440x788"
            # }
        )

        # Dans la configuration, décommentez et utilisez le schema
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            wait_for_images=True,
            proxy_rotation_strategy=proxy_strategy,
            excluded_tags=["form", "header", "footer"],
            keep_data_attributes=True,  # ✅ Changé à True pour garder data-attributes
            remove_overlay_elements=True,
            js_code=[
                "await new Promise(resolve => setTimeout(resolve, 5000));",
                "window.scrollTo(0, document.body.scrollHeight);",
                "await new Promise(resolve => setTimeout(resolve, 2000));",
                "document.querySelectorAll('[role=\"button\"]').forEach(btn => { if(btn.textContent.includes('See more') || btn.textContent.includes('Voir plus')) btn.click(); });",
            ],
            extraction_strategy=JsonCssExtractionStrategy(self.schema),  # ✅ Décommenté
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=config)

            if result.success:
                print("📄 HTML Length:", len(result.html))
                # print("success: ", result.markdown[])
                # 3. Vérifier les données extraites
                if hasattr(result, "extracted_content"):
                    print("🎯 Extracted data:", result.extracted_content)
                else:
                    print("⚠️ No extracted content found")
            if result.error_message:
                print("erreur")
