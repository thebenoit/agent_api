"""ua_generator.py
Generate realistic User-Agent strings and coherent HTTP headers at scale.
"""

import random


def weighted_choice(choices):
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w
    return choices[-1][0]


def rand_version(major_min, major_max, minor=(0, 5), build=(0, 9999), patch=(0, 199)):
    major = random.randint(major_min, major_max)
    mi = random.randint(*minor)
    bu = random.randint(*build)
    pa = random.randint(*patch)
    return major, mi, bu, pa


def safari_version_for_webkit():
    version_major = random.choice([15, 16, 17, 18])
    version_minor = random.randint(0, 6)
    webkit_version = "605.1.15"
    return f"{version_major}.{version_minor}", webkit_version


def pick_android_model():
    vendors = {
        "Google": [
            "Pixel 5",
            "Pixel 6",
            "Pixel 6a",
            "Pixel 7",
            "Pixel 7a",
            "Pixel 8",
            "Pixel 8a",
        ],
        "Samsung": [
            "SM-G991B",
            "SM-G996B",
            "SM-G998B",
            "SM-S901B",
            "SM-S906B",
            "SM-S908B",
            "SM-S921B",
            "SM-S926B",
        ],
        "OnePlus": ["KB2003", "IN2013", "LE2113", "CPH2413", "CPH2449"],
        "Xiaomi": ["M2007J3SG", "2201123G", "23013PC75G"],
        "Nothing": ["A063", "A065"],
    }
    brand = weighted_choice([(b, 5) for b in vendors.keys()])
    model = random.choice(vendors[brand])
    return brand, model


def pick_locale():
    locales = [
        ("en-US,en;q=0.9", 60),
        ("en-GB,en;q=0.9", 8),
        ("en-CA,en;q=0.9", 5),
        ("fr-FR,fr;q=0.9,en;q=0.8", 5),
        ("fr-CA,fr;q=0.9,en;q=0.8", 3),
        ("es-ES,es;q=0.9,en;q=0.8", 5),
        ("pt-BR,pt;q=0.9,en;q=0.8", 4),
        ("de-DE,de;q=0.9,en;q=0.8", 4),
        ("zh-CN,zh;q=0.9,en;q=0.8", 4),
        ("it-IT,it;q=0.9,en;q=0.8", 2),
    ]
    return weighted_choice(locales)


def accept_header(browser_family):
    if browser_family in ("Chrome", "Edge", "Opera"):
        return "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    if browser_family == "Firefox":
        return (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        )
    return "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


def upgrade_insecure_requests():
    return "1" if random.random() < 0.9 else None


class UserAgentGenerator:
    def __init__(self, chrome_major=(120, 130), firefox_major=(110, 130)):
        self.chrome_major = chrome_major
        self.firefox_major = firefox_major

    def gen(self):
        platform = weighted_choice(
            [
                ("Windows", 40),
                ("Android", 28),
                ("iOS", 15),
                ("macOS", 14),
                ("Linux", 3),
            ]
        )
        if platform == "Windows":
            browser = weighted_choice([("Chrome", 66), ("Edge", 22), ("Firefox", 12)])
            return self.windows(browser)
        if platform == "Android":
            browser = weighted_choice([("Chrome", 88), ("Firefox", 7), ("Opera", 5)])
            return self.android(browser)
        if platform == "iOS":
            browser = weighted_choice([("Safari", 75), ("Chrome", 20), ("Firefox", 5)])
            return self.ios(browser)
        if platform == "macOS":
            browser = weighted_choice([("Safari", 55), ("Chrome", 35), ("Firefox", 10)])
            return self.macos(browser)
        if platform == "Linux":
            browser = weighted_choice([("Chrome", 70), ("Firefox", 30)])
            return self.linux(browser)

    def windows(self, browser):
        win_ver = random.choice(
            [
                ("10.0", "Win64; x64"),
                ("10.0", "WOW64"),
                ("10.0", "Win64; x64"),
                ("10.0", "WOW64"),
                ("11.0", "Win64; x64"),
                ("11.0", "Win64; x64"),
            ]
        )
        nt, arch = win_ver
        if browser in ("Chrome", "Edge", "Opera"):
            major, mi, bu, pa = rand_version(
                *self.chrome_major, minor=(0, 1), build=(0, 9999), patch=(0, 199)
            )
            base = f"Mozilla/5.0 (Windows NT {nt}; {arch}) AppleWebKit/537.36 (KHTML, like Gecko)"
            if browser == "Chrome":
                ua = f"{base} Chrome/{major}.0.{bu}.{pa} Safari/537.36"
                brand = "Google Chrome"
                sec_ch = {
                    "sec-ch-ua": f'"Chromium";v="{major}", "{brand}";v="{major}", ";Not A Brand";v="99"',
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-ch-ua-mobile": "?0",
                }
            elif browser == "Edge":
                ua = f"{base} Chrome/{major}.0.{bu}.{pa} Safari/537.36 Edg/{major}.0.{bu}.{pa}"
                sec_ch = {
                    "sec-ch-ua": f'"Chromium";v="{major}", "Microsoft Edge";v="{major}", ";Not A Brand";v="99"',
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-ch-ua-mobile": "?0",
                }
            else:
                ua = f"{base} Chrome/{major}.0.{bu}.{pa} Safari/537.36 OPR/{major}.0.{bu}.{pa}"
                sec_ch = {
                    "sec-ch-ua": f'"Chromium";v="{major}", "Opera";v="{major}", ";Not A Brand";v="99"',
                    "sec-ch-ua-platform": '"Windows"',
                    "sec-ch-ua-mobile": "?0",
                }
            headers = self.common_headers("Chrome", platform="Windows", sec_ch=sec_ch)
            headers["User-Agent"] = ua
            return headers
        major = random.randint(*self.firefox_major)
        rv = f"{major}.0"
        ua = f"Mozilla/5.0 (Windows NT {nt}; {arch}; rv:{rv}) Gecko/20100101 Firefox/{rv}"
        headers = self.common_headers("Firefox", platform="Windows", sec_ch=None)
        headers["User-Agent"] = ua
        return headers

    def macos(self, browser):
        mac_major_minor = random.choice(["12_7", "13_6", "14_3", "14_5", "15_0"])
        if browser in ("Chrome", "Opera"):
            major, mi, bu, pa = rand_version(*self.chrome_major, minor=(0, 1))
            base = "Mozilla/5.0 (Macintosh; Intel Mac OS X {ver}) AppleWebKit/537.36 (KHTML, like Gecko)"
            ua = f"{base.format(ver=mac_major_minor)} Chrome/{major}.0.{bu}.{pa} Safari/537.36"
            brand = "Google Chrome" if browser == "Chrome" else "Opera"
            sec_ch = {
                "sec-ch-ua": f'"Chromium";v="{major}", "{brand}";v="{major}", ";Not A Brand";v="99"',
                "sec-ch-ua-platform": '"macOS"',
                "sec-ch-ua-mobile": "?0",
            }
            headers = self.common_headers("Chrome", platform="macOS", sec_ch=sec_ch)
            headers["User-Agent"] = ua
            return headers
        if browser == "Firefox":
            major = random.randint(*self.firefox_major)
            rv = f"{major}.0"
            ua = f"Mozilla/5.0 (Macintosh; Intel Mac OS X {mac_major_minor}; rv:{rv}) Gecko/20100101 Firefox/{rv}"
            headers = self.common_headers("Firefox", platform="macOS", sec_ch=None)
            headers["User-Agent"] = ua
            return headers
        vers, webkit = safari_version_for_webkit()
        ua = (
            f"Mozilla/5.0 (Macintosh; Intel Mac OS X {mac_major_minor}) "
            f"AppleWebKit/{webkit} (KHTML, like Gecko) Version/{vers} Safari/{webkit}"
        )
        headers = self.common_headers("Safari", platform="macOS", sec_ch=None)
        headers["User-Agent"] = ua
        return headers

    def ios(self, browser):
        ios_ver = random.choice(["15_7_8", "16_6_1", "17_4_1", "17_5", "18_0"])
        device = random.choice(["iPhone", "iPad"])
        vers, webkit = safari_version_for_webkit()
        mobile_token = "Mobile/15E148"
        base = f"Mozilla/5.0 ({device}; CPU {device} OS {ios_ver} like Mac OS X) AppleWebKit/{webkit} (KHTML, like Gecko)"
        if browser == "Safari":
            ua = f"{base} Version/{vers} {mobile_token} Safari/{webkit}"
        elif browser == "Chrome":
            major, mi, bu, pa = rand_version(*self.chrome_major, minor=(0, 1))
            ua = f"{base} CriOS/{major}.0.{bu}.{pa} Version/{vers} {mobile_token} Safari/{webkit}"
        else:
            ff_major = random.randint(*self.firefox_major)
            ua = f"{base} FxiOS/{ff_major}.0 Version/{vers} {mobile_token} Safari/{webkit}"
        headers = self.common_headers("Safari", platform="iOS", sec_ch=None)
        headers["User-Agent"] = ua
        return headers

    def android(self, browser):
        android_ver = random.choice(["9", "10", "11", "12", "13", "14"])
        brand, model = pick_android_model()
        if browser in ("Chrome", "Opera"):
            major, mi, bu, pa = rand_version(*self.chrome_major, minor=(0, 1))
            base = f"Mozilla/5.0 (Linux; Android {android_ver}; {model}) AppleWebKit/537.36 (KHTML, like Gecko)"
            if browser == "Chrome":
                ua = f"{base} Chrome/{major}.0.{bu}.{pa} Mobile Safari/537.36"
                brand_name = "Google Chrome"
                sec_ch = {
                    "sec-ch-ua": f'"Chromium";v="{major}", "{brand_name}";v="{major}", ";Not A Brand";v="99"',
                    "sec-ch-ua-platform": '"Android"',
                    "sec-ch-ua-mobile": "?1",
                }
            else:
                ua = f"{base} Chrome/{major}.0.{bu}.{pa} Mobile Safari/537.36 OPR/{major}.0.{bu}.{pa}"
                sec_ch = {
                    "sec-ch-ua": f'"Chromium";v="{major}", "Opera";v="{major}", ";Not A Brand";v="99"',
                    "sec-ch-ua-platform": '"Android"',
                    "sec-ch-ua-mobile": "?1",
                }
            headers = self.common_headers("Chrome", platform="Android", sec_ch=sec_ch)
            headers["User-Agent"] = ua
            return headers
        ff_major = random.randint(*self.firefox_major)
        ua = f"Mozilla/5.0 (Android {android_ver}; Mobile; rv:{ff_major}.0) Gecko/20100101 Firefox/{ff_major}.0"
        headers = self.common_headers("Firefox", platform="Android", sec_ch=None)
        headers["User-Agent"] = ua
        return headers

    def linux(self, browser):
        distro = random.choice(
            [
                "X11; Linux x86_64",
                "X11; Ubuntu; Linux x86_64",
                "X11; Fedora; Linux x86_64",
            ]
        )
        if browser == "Chrome":
            major, mi, bu, pa = rand_version(*self.chrome_major, minor=(0, 1))
            ua = f"Mozilla/5.0 ({distro}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{major}.0.{bu}.{pa} Safari/537.36"
            sec_ch = {
                "sec-ch-ua": f'"Chromium";v="{major}", "Google Chrome";v="{major}", ";Not A Brand";v="99"',
                "sec-ch-ua-platform": '"Linux"',
                "sec-ch-ua-mobile": "?0",
            }
            headers = self.common_headers("Chrome", platform="Linux", sec_ch=sec_ch)
            headers["User-Agent"] = ua
            return headers
        else:
            major = random.randint(*self.firefox_major)
            rv = f"{major}.0"
            ua = f"Mozilla/5.0 ({distro}; rv:{rv}) Gecko/20100101 Firefox/{rv}"
            headers = self.common_headers("Firefox", platform="Linux", sec_ch=None)
            headers["User-Agent"] = ua
            return headers

    def common_headers(self, browser_family, platform, sec_ch):
        headers = {
            "Accept": accept_header(browser_family),
            "Accept-Language": pick_locale(),
            "Connection": "keep-alive",
        }
        uir = upgrade_insecure_requests()
        if uir:
            headers["Upgrade-Insecure-Requests"] = uir
        if sec_ch:
            headers.update(
                {
                    "sec-ch-ua": sec_ch["sec-ch-ua"],
                    "sec-ch-ua-mobile": sec_ch["sec-ch-ua-mobile"],
                    "sec-ch-ua-platform": sec_ch["sec-ch-ua-platform"],
                }
            )
        return headers


def generate_headers_batch(n=1000, seed=None):
    if seed is not None:
        random.seed(seed)
    gen = UserAgentGenerator()
    return [gen.gen() for _ in range(n)]


def generate_complete_headers(seed=None):
    """
    Génère un ensemble complet de headers HTTP cohérents.

    Cette fonction génère des headers réalistes avec:
    - User-Agent correspondant à un navigateur réel
    - Headers Accept adaptés au type de navigateur
    - Headers sec-ch-ua cohérents (pour navigateurs Chromium)
    - Accept-Language avec distribution géographique réaliste
    - Autres headers de sécurité appropriés

    Args:
        seed (int, optional): Graine pour la génération aléatoire (pour reproductibilité)

    Returns:
        dict: Dictionnaire contenant tous les headers HTTP

    Exemple:
        >>> headers = generate_complete_headers()
        >>> print(headers)
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9...',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'sec-ch-ua': '"Chromium";v="125", "Google Chrome";v="125"...',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    """
    if seed is not None:
        random.seed(seed)
    gen = UserAgentGenerator()
    return gen.gen()


def generate_single_user_agent(seed=None):
    """
    Génère uniquement le User-Agent string.

    Cette fonction est un raccourci pour obtenir seulement la chaîne User-Agent
    sans les autres headers. Utilise generate_complete_headers() en interne
    pour garantir la cohérence.

    Args:
        seed (int, optional): Graine pour la génération aléatoire (pour reproductibilité)

    Returns:
        str: Une chaîne User-Agent réaliste

    Exemple:
        >>> ua = generate_single_user_agent()
        >>> print(ua)
        Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.78 Safari/537.36
    """
    headers = generate_complete_headers(seed)
    return headers["User-Agent"]


def generate_requests_session_headers(seed=None):
    """
    Génère des headers optimisés pour les sessions requests Python.

    Cette fonction filtre les headers pour ne garder que ceux qui sont
    pertinents lors de l'utilisation avec la bibliothèque requests.
    Certains headers comme 'Connection' sont automatiquement gérés par requests.

    Args:
        seed (int, optional): Graine pour la génération aléatoire (pour reproductibilité)

    Returns:
        dict: Headers optimisés pour requests.Session()

    Exemple:
        >>> import requests
        >>> headers = generate_requests_session_headers()
        >>> session = requests.Session()
        >>> session.headers.update(headers)
        >>> response = session.get('https://example.com')
    """
    headers = generate_complete_headers(seed)

    # Headers pertinents pour requests (on retire Connection qui est géré automatiquement)
    requests_headers = {
        "User-Agent": headers["User-Agent"],
        "Accept": headers["Accept"],
        "Accept-Language": headers["Accept-Language"],
    }

    # Ajouter Upgrade-Insecure-Requests si présent
    if "Upgrade-Insecure-Requests" in headers:
        requests_headers["Upgrade-Insecure-Requests"] = headers[
            "Upgrade-Insecure-Requests"
        ]

    # Ajouter tous les headers sec-ch-* (Client Hints)
    for key, value in headers.items():
        if key.startswith("sec-ch-"):
            requests_headers[key] = value

    return requests_headers
