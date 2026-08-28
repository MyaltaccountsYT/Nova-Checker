import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_instance = None
_lock = threading.Lock()

class NovaSessionManager:
    def __init__(self):
        self._pool = []
        self._pool_lock = threading.Lock()

def get_novasessionmanager():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaSessionManager()
    return _instance

def get_session():
    s = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST", "HEAD", "OPTIONS", "PUT", "DELETE"]),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=4,
        pool_maxsize=4,
    )
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.verify = False
    return s

def recycle_session(session):
    clear_cookies(session)
    manager = get_novasessionmanager()
    with manager._pool_lock:
        manager._pool.append(session)

def clear_cookies(session):
    session.cookies.clear()
