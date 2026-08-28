import re
import json
import threading

_instance = None
_lock = threading.Lock()

_TIMEOUT = 15

class NovaInboxChecker:
    pass

def get_novainboxchecker():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaInboxChecker()
    return _instance

def get_outlook_token(session):
    try:
        r = session.get(
            "https://login.live.com/oauth20_authorize.srf?client_id=00000000480728C5"
            "&response_type=token&scope=service::outlook.office365.com::MBI_SSL"
            "&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0"},
            timeout=_TIMEOUT,
            allow_redirects=True,
        )
        m = re.search(r"access_token=([^&]+)", str(r.url))
        if m:
            from urllib.parse import unquote
            return unquote(m.group(1))
    except Exception:
        pass
    return None

def build_search_payload(keyword):
    return {
        "requests": [
            {
                "entityRequests": [
                    {
                        "entityType": "Message",
                        "query": {
                            "queryString": keyword,
                        },
                        "from": 0,
                        "size": 1,
                    }
                ],
                "cvid": "nova_search",
                "scenario": {"name": "staticbrowse"},
            }
        ]
    }

def parse_search_response(response):
    try:
        data = response.json()
        results = data.get("value", [])
        for r in results:
            hits = r.get("hitsContainers", [])
            for h in hits:
                return h.get("total", 0)
    except Exception:
        pass
    return 0

def search_inbox(session, keywords, delegate_token):
    hits = {}
    outlook_token = get_outlook_token(session)
    if not outlook_token:
        return hits
    for kw in keywords:
        try:
            payload = build_search_payload(kw)
            r = session.post(
                "https://substrate.office.com/search/api/v1/suggestions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {outlook_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                count = parse_search_response(r)
                if count > 0:
                    hits[kw] = count
        except Exception:
            pass
    return hits
