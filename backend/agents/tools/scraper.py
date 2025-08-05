import sys
import os
from tools.base_tool import BaseTool
from tools.bases.base_scraper import BaseScraper
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    RoundRobinProxyStrategy,
)
from dotenv import load_dotenv
load_dotenv()


class Scraper(BaseTool, BaseScraper):
    def __init__(self):
        super().__init__()
        
        print("initialisation du scraper...")
        
        proxies = {"http": os.getenv("PROXIES_URL"), "https": os.getenv("PROXIES_URL")}
        use_persistent_context = True  
        #don't see the window 
        headless = True
        ignore_ssl_errors = True
        cookies = None
        headers = None
        
        
        browser_config = BrowserConfig(
            headless=headless,
            ignore_ssl_errors=ignore_ssl_errors,
            proxies=proxies,
        )
        
        
        
    def name(self):
        return "scraper"
    
    def description(self):
        return "scrape a page"
    
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
        
        
        
        
        
        
        
        