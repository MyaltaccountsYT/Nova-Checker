import time
import threading

_instance = None
_lock = threading.Lock()

class NovaRateLimiter:
    def __init__(self):
        self._request_times = []
        self._backoff = 0
        self._limiter_lock = threading.Lock()
        self._consecutive_429 = 0

def get_novaratelimiter():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaRateLimiter()
    return _instance

def wait_if_needed():
    rl = get_novaratelimiter()
    with rl._limiter_lock:
        if rl._backoff > 0:
            time.sleep(rl._backoff)

def record_request(success=True):
    rl = get_novaratelimiter()
    with rl._limiter_lock:
        rl._request_times.append(time.time())
        if len(rl._request_times) > 1000:
            rl._request_times = rl._request_times[-500:]
        if success:
            rl._consecutive_429 = 0
            rl._backoff = max(0, rl._backoff - 0.1)

def handle_429(response):
    rl = get_novaratelimiter()
    with rl._limiter_lock:
        rl._consecutive_429 += 1
        rl._backoff = min(30, 2 ** rl._consecutive_429)
    time.sleep(rl._backoff)
