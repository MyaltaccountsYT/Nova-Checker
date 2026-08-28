import re
import json
import threading

_instance = None
_lock = threading.Lock()

_SFTAG_URL = (
    "https://login.live.com/oauth20_authorize.srf"
    "?client_id=00000000402B5328"
    "&redirect_uri=https://login.live.com/oauth20_desktop.srf"
    "&scope=service::user.auth.xboxlive.com::MBI_SSL"
    "&display=touch&response_type=token&locale=en"
)

_UA_EDGE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"

class NovaTokenExtractor:
    def __init__(self):
        self._cache = {}
        self._cache_lock = threading.Lock()

def get_novatokenextractor():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaTokenExtractor()
    return _instance

def extract_auth_params(session):
    for _ in range(3):
        try:
            r = session.get(
                _SFTAG_URL,
                headers={
                    "User-Agent": _UA_EDGE,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=15,
                allow_redirects=True,
            )
            t = r.text
            url_post = ppft = None

            m = re.search(r'ServerData\s*=\s*({.*?});', t, re.DOTALL)
            if m:
                try:
                    sd = json.loads(m.group(1))
                    url_post = sd.get("urlPost")
                    sft = sd.get("sFTTag", "")
                    pm = re.search(r'name="PPFT".*?value="([^"]+)"', sft)
                    if pm:
                        ppft = pm.group(1)
                except Exception:
                    pass

            if not url_post:
                mu = re.search(r'"urlPost"\s*:\s*"([^"]+)"', t)
                if mu:
                    url_post = mu.group(1).replace("\\u0026", "&").replace("&amp;", "&")

            if not ppft:
                mp = re.search(r'name="PPFT"[^>]+value="([^"]+)"', t, re.DOTALL) or \
                     re.search(r'"sFT"\s*:\s*"([^"]+)"', t)
                if mp:
                    ppft = mp.group(1)

            if url_post and ppft:
                return url_post, ppft
        except Exception:
            pass
    return None, None

def extract_ppft(html):
    for pat in [
        r'name="PPFT"[^>]+value="([^"]+)"',
        r'"sFT"\s*:\s*"([^"]+)"',
    ]:
        m = re.search(pat, html, re.DOTALL)
        if m:
            return m.group(1)
    return None

def extract_urlpost(html):
    m = re.search(r'"urlPost"\s*:\s*"([^"]+)"', html)
    if m:
        return m.group(1).replace("\\u0026", "&").replace("&amp;", "&")
    return None
