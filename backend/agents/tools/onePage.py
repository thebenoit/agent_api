from agents.tools.base_tool import BaseTool
from agents.tools.bases.base_scraper import BaseScraper
import os
import re
import logging
from bs4 import BeautifulSoup
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    RoundRobinProxyStrategy,
    ProxyConfig,
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
                    "name": "Description_candidates",
                    "selector": "div[role='main'] span[dir='auto']",
                    "type": "text",
                },
                {
                    "name": "sous_titre_details",
                    "selector": "div.xwib8y2",
                    "type": "nested_list",
                    "fields": [
                        {
                            "name": "sous_titre",
                            "selector": "div, span.x193iq5w.xeuugli.x13faqbe.x1vvkbs.xlh3980.xvmahel.x1n0sxbx.x1lliihq.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i.x1fgarty.x1943h6x.x4zkp8e.x3x7a5m.x6prxxf.xvq8zen.xo1l8bm.xzsf02u.x1yc453h",
                            "type": "text",
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
                            # Cibler uniquement la galerie/carrousel du listing
                            "name": "gallery",
                            "selector": (
                                "[aria-roledescription='carousel'], "
                                "[aria-label*='Carousel'], "
                                "[aria-label*='Carrousel'], "
                                "[aria-label*='Photos'], "
                                "[aria-label*='Miniature'], "
                                "div[role='region'][aria-label*='Photos']"
                            ),
                            "type": "nested_list",
                            "fields": [
                                {
                                    "name": "src",
                                    "selector": "img",
                                    "type": "attribute",
                                    "attribute": "src",
                                },
                                {
                                    "name": "alt",
                                    "selector": "img",
                                    "type": "attribute",
                                    "attribute": "alt",
                                },
                            ],
                        },
                    ],
                },
            ],
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

    async def fetch_page(
        self,
        url: str,
        *,
        return_raw_html: bool = False,
        return_extracted_raw: bool = False,
    ):
        logger = logging.getLogger(__name__)
        logger.info("[OnePage.fetch_page] start url=%s", url)

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

            if not result.success:
                logger.warning("[OnePage.fetch_page] échec result.success=False")
                return {}

            extracted = getattr(result, "extracted_content", None)
            if extracted is None:
                logger.warning("[OnePage.fetch_page] pas de extracted_content")
                return {}

            # Normalisation du contenu extrait pour unifier la sortie
            try:
                if isinstance(extracted, str):
                    import json

                    extracted = json.loads(extracted)
            except Exception as e:
                logger.exception("[OnePage.fetch_page] erreur parsing JSON: %s", e)
                # retourne brut si non JSON
                if return_extracted_raw:
                    out = {"raw": extracted}
                    if return_raw_html:
                        out["html"] = result.html
                    return out
                else:
                    return {"html": result.html} if return_raw_html else {}

            def is_image_url(url: str) -> bool:
                if not isinstance(url, str):
                    return False
                ul = url.lower()
                return (
                    any(ext in ul for ext in [".jpg", ".jpeg", ".png", ".webp"]) or
                    "safe_image.php" in ul
                )

            def to_images_list(images_node, title=None):
                """Normalise la structure extraite par JsonCssExtractionStrategy et filtre par titre.

                Args:
                    images_node: La structure d'images extraite
                    title: Si fourni, ne garde que les images dont l'alt correspond au titre

                Attend typiquement une structure du type:
                images: [ { gallery: [ {src, alt}, ... ] } ]

                Mais gère aussi les anciens formats (thumbnails) et
                une liste directe de {src, alt}.
                """
                normalized = []
                if isinstance(images_node, dict):
                    images_node = [images_node]
                if isinstance(images_node, list):
                    for entry in images_node:
                        if not isinstance(entry, dict):
                            continue
                        # Nouveau format: gallery
                        gallery = entry.get("gallery")
                        if isinstance(gallery, dict):
                            gallery = [gallery]
                        if isinstance(gallery, list):
                            for item in gallery:
                                if isinstance(item, dict):
                                    src = item.get("src")
                                    alt = item.get("alt")
                                    if src and is_image_url(src):
                                        # Vérifie si l'alt correspond au titre si un titre est fourni
                                        if title is None or (alt and alt.strip().lower() == title.strip().lower()):
                                            normalized.append({"src": src, "alt": alt})

                        # Ancien format: thumbnails
                        thumbs = entry.get("thumbnails")
                        if isinstance(thumbs, dict):
                            thumbs = [thumbs]
                        if isinstance(thumbs, list):
                            for t in thumbs:
                                if isinstance(t, dict):
                                    src = t.get("src")
                                    alt = t.get("alt")
                                    if src and is_image_url(src):
                                        if title is None or (alt and alt.strip().lower() == title.strip().lower()):
                                            normalized.append({"src": src, "alt": alt})

                        # Si l'entrée est déjà un dict {src, alt}
                        if entry.get("src") and is_image_url(entry.get("src")):
                            src = entry.get("src")
                            alt = entry.get("alt")
                            if title is None or (alt and alt.strip().lower() == title.strip().lower()):
                                normalized.append({
                                    "src": src,
                                    "alt": alt,
                                })
                return normalized

            description = None
            if isinstance(extracted, dict):
                # Prendre la plus longue chaîne plausible comme description
                candidates = extracted.get("Description_candidates")
                if isinstance(candidates, list) and candidates:
                    texts = []
                    for d in candidates:
                        if isinstance(d, str) and d.strip():
                            texts.append(d.strip())
                        elif isinstance(d, dict):
                            txt = d.get("text") or d.get("value")
                            if isinstance(txt, str) and txt.strip():
                                texts.append(txt.strip())
                    if texts:
                        # Heuristique: choisir la chaîne la plus longue > 60 caractères
                        texts_sorted = sorted(texts, key=lambda s: len(s), reverse=True)
                        for t in texts_sorted:
                            if len(t) >= 60:
                                description = t
                                break
                        if description is None:
                            description = texts_sorted[0]

                images = to_images_list(extracted.get("images"), title=description)
            else:
                images = []

            # Fallback HTML parse si rien trouvé
            if not description or not images:
                try:
                    soup = BeautifulSoup(result.html, "html.parser")
                    if not description:
                        main = soup.select_one("div[role='main']") or soup
                        span_texts = [
                            s.get_text(strip=True)
                            for s in main.select("span[dir='auto']")
                            if s.get_text(strip=True)
                        ]
                        if span_texts:
                            span_texts.sort(key=lambda s: len(s), reverse=True)
                            for t in span_texts:
                                if len(t) >= 60:
                                    description = t
                                    break
                            if description is None:
                                description = span_texts[0]

                    if not images:
                        # Restreindre la recherche au conteneur de galerie/carrousel
                        main = soup.select_one("div[role='main']") or soup
                        # Chercher une vraie galerie
                        gallery = main.select_one(
                            "[aria-roledescription='carousel'], "
                            "[aria-label*='Carousel'], "
                            "[aria-label*='Carrousel'], "
                            "[aria-label*='Photos'], "
                            "div[role='region'][aria-label*='Photos']"
                        )

                        # Ou bien, Facebook utilise souvent des 'Miniature N'
                        thumbnails = main.select("[aria-label*='Miniature']")

                        imgs = []
                        if gallery:
                            scopes = [gallery]
                        elif thumbnails:
                            scopes = thumbnails
                        else:
                            scopes = [main]

                        for scope in scopes:
                            for img in scope.select("img"):
                                src = img.get("src")
                                if not src and img.get("srcset"):
                                    # prendre la plus grande dans srcset
                                    try:
                                        parts = [p.strip() for p in img.get("srcset").split(",")]
                                        if parts:
                                            src = parts[-1].split(" ")[0]
                                    except Exception:
                                        pass
                                if src and is_image_url(src):
                                    alt = img.get("alt")
                                    imgs.append({"src": src, "alt": alt})
                        # dédoublonner par src
                        seen = set()
                        images = []
                        for im in imgs:
                            if im["src"] not in seen:
                                images.append(im)
                                seen.add(im["src"])
                except Exception as e:
                    logger.exception(
                        "[OnePage.fetch_page] fallback HTML parse error: %s", e
                    )

            out = {
                "description": description,
                "images": images,
            }
            if return_raw_html:
                out["html"] = result.html
            if return_extracted_raw:
                out["raw_extracted"] = extracted
            logger.info(
                "[OnePage.fetch_page] ok desc_len=%d images=%d",
                len(out.get("description") or ""),
                len(out.get("images") or []),
            )
            return out
