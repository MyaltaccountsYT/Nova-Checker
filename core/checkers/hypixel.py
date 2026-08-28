import re
import threading

_instance = None
_lock = threading.Lock()

_TIMEOUT = 13
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"

_RE_NAME      = re.compile(r'(?<=content="Plancke" /><meta property="og:locale" content="en_US" /><meta property="og:description" content=").+?(?=")', re.S)
_RE_TITLE     = re.compile(r'<title>(.+?)\s*\|\s*Plancke</title>', re.IGNORECASE)
_RE_LEVEL     = re.compile(r'(?<=Level:</b> ).+?(?=<br/><b>)')
_RE_FIRST     = re.compile(r'(?<=<b>First login: </b>).+?(?=<br/><b>)')
_RE_LAST      = re.compile(r'(?<=<b>Last login: </b>).+?(?=<br/>)')
_RE_BW_STARS  = re.compile(r'(?<=<li><b>Level:</b> ).+?(?=</li>)')
_RE_RANK      = re.compile(r'\[(VIP\+?|MVP\+\+?|YOUTUBE|ADMIN|MOD|HELPER)\]\s*(\S+)', re.IGNORECASE)

class NovaHypixelChecker:
    pass

def get_novahypixelchecker():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaHypixelChecker()
    return _instance

def get_plancke_page(session, username, proxy=None):
    kwargs = dict(
        headers={
            'User-Agent': _UA,
            'Accept-Encoding': 'gzip, deflate',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
        verify=False,
        timeout=(5, _TIMEOUT),
    )
    if proxy:
        kwargs['proxies'] = proxy
    try:
        r = session.get(f'https://plancke.io/hypixel/player/stats/{username}', **kwargs)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None

def get_hypixel_stats(session, username, proxy=None):
    tx = get_plancke_page(session, username, proxy)
    if not tx:
        return {}
    result = {}

    m = _RE_TITLE.search(tx)
    if m:
        raw = m.group(1)
        if 'View player,' not in raw and 'not found' not in raw.lower() and 'plancke' not in raw.lower():
            result['display_name'] = raw
    if 'display_name' not in result:
        m = _RE_NAME.search(tx)
        if m:
            raw = m.group()
            if 'View player,' not in raw and 'not found' not in raw.lower():
                result['display_name'] = raw
    if 'display_name' not in result:
        m = _RE_RANK.search(tx)
        if m:
            result['display_name'] = m.group(0)

    m = _RE_LEVEL.search(tx)
    if m:
        try:
            result['level'] = float(m.group())
        except ValueError:
            pass

    m = _RE_FIRST.search(tx)
    if m:
        result['first_login'] = m.group()

    m = _RE_LAST.search(tx)
    if m:
        result['last_login'] = m.group()

    m = _RE_BW_STARS.search(tx)
    if m:
        try:
            result['bw_stars'] = int(m.group())
        except ValueError:
            pass

    return result

def format_hypixel_capture(stats):
    parts = []
    if stats.get('display_name'):
        parts.append(f"Rank: {stats['display_name']}")
    if stats.get('level'):
        parts.append(f"Lvl: {stats['level']:.0f}")
    if stats.get('bw_stars'):
        parts.append(f"BW: {stats['bw_stars']}")
    if stats.get('first_login'):
        parts.append(f"First: {stats['first_login']}")
    if stats.get('last_login'):
        parts.append(f"Last: {stats['last_login']}")
    return ' | '.join(parts) if parts else None
