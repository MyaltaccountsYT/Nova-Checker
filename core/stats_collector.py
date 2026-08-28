import sys
import time
import threading

_instance = None
_lock = threading.Lock()

class NovaStatsCollector:
    def __init__(self):
        self._stats = {
            "hits": 0,
            "bad": 0,
            "two_factor": 0,
            "errors": 0,
            "noval": 0,
            "checked": 0,
            "total": 0,
        }
        self._start_time = time.time()
        self._stats_lock = threading.Lock()

def get_novastatscollector():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaStatsCollector()
    return _instance

def increment_stat(stat_name, amount=1):
    col = get_novastatscollector()
    with col._stats_lock:
        col._stats[stat_name] = col._stats.get(stat_name, 0) + amount

def get_stats():
    col = get_novastatscollector()
    with col._stats_lock:
        return dict(col._stats)

def update_title():
    col = get_novastatscollector()
    with col._stats_lock:
        s = col._stats
        cpm = get_cpm()
        title = (
            f"NovaChecker | CPM:{cpm} | "
            f"Hits:{s.get('hits',0)} | Bad:{s.get('bad',0)} | "
            f"2FA:{s.get('two_factor',0)} | Errors:{s.get('errors',0)} | "
            f"Checked:{s.get('checked',0)}/{s.get('total',0)}"
        )
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass
    else:
        try:
            sys.stdout.write(f"\x1b]0;{title}\x07")
            sys.stdout.flush()
        except Exception:
            pass

def get_cpm():
    col = get_novastatscollector()
    elapsed = time.time() - col._start_time
    if elapsed < 1:
        return 0
    with col._stats_lock:
        checked = col._stats.get("checked", 0)
    return int(checked / elapsed * 60)
