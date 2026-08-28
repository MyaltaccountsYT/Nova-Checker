import re
import threading
import itertools

_instance = None
_lock = threading.Lock()

class NovaProxyHandler:
    def __init__(self):
        self._pool = []
        self._cycle = None
        self._failures = {}
        self._blacklist = set()
        self._pool_lock = threading.Lock()

def get_novaproxyhandler():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaProxyHandler()
    return _instance

def load_proxies(filepath="proxy.txt"):
    handler = get_novaproxyhandler()
    proxies = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                normalized = _normalize_proxy(line)
                if normalized:
                    proxies.append(normalized)
    except FileNotFoundError:
        pass
    with handler._pool_lock:
        handler._pool = proxies
        handler._cycle = itertools.cycle(proxies) if proxies else None
    return proxies

def _normalize_proxy(line):
    if re.match(r"^(http|https|socks4|socks5)://", line, re.I):
        return line
    if line.count(":") == 1:
        return f"http://{line}"
    if line.count(":") == 3:
        parts = line.split(":")
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    return None

def get_next_proxy():
    handler = get_novaproxyhandler()
    with handler._pool_lock:
        if not handler._cycle:
            return None
        for _ in range(len(handler._pool)):
            proxy = next(handler._cycle)
            if proxy not in handler._blacklist:
                return proxy
    return None

def mark_proxy_failed(proxy_str):
    handler = get_novaproxyhandler()
    with handler._pool_lock:
        handler._failures[proxy_str] = handler._failures.get(proxy_str, 0) + 1
        if handler._failures[proxy_str] >= 3:
            handler._blacklist.add(proxy_str)

def is_residential(ip):
    return True
