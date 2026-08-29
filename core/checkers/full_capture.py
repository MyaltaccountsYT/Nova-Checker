import os
import json
import threading

_instance = None
_lock = threading.Lock()
_file_lock = threading.Lock()
_seen_cache: dict = {}


class NovaFileHandler:
    def __init__(self):
        self._result_dir = None


def get_novafilehandler():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaFileHandler()
    return _instance


def read_combos(filepath="accs.txt"):
    seen = set()
    combos = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if ":" not in line:
                    continue
                if line.lower() not in seen:
                    seen.add(line.lower())
                    combos.append(line)
    except FileNotFoundError:
        pass
    return combos


def get_result_directory():
    handler = get_novafilehandler()
    if handler._result_dir:
        return handler._result_dir
    with _lock:
        if handler._result_dir:
            return handler._result_dir
        base = "results"
        os.makedirs(base, exist_ok=True)
        n = 1
        while True:
            candidate = os.path.join(base, f"R{n}")
            if not os.path.exists(candidate):
                os.makedirs(candidate)
                for sub in ["Countries", "Games", "Inboxes", "Cookies"]:
                    os.makedirs(os.path.join(candidate, sub), exist_ok=True)
                handler._result_dir = candidate
                return candidate
            n += 1


def write_with_dedup(filepath, content):
    with _file_lock:
        if filepath not in _seen_cache:
            _seen_cache[filepath] = set()
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        _seen_cache[filepath] = {l.strip() for l in f}
                except Exception:
                    pass
        if content.strip() in _seen_cache[filepath]:
            return
        _seen_cache[filepath].add(content.strip())
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(content if content.endswith("\n") else content + "\n")


def append_line(filepath, line):
    with _file_lock:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(line if line.endswith("\n") else line + "\n")


def save_cookies(email, session, result_dir):
    cookies = [{"name": c.name, "value": c.value, "domain": c.domain, "path": c.path} for c in session.cookies]
    safe_email = email.replace("@", "_at_").replace(".", "_")
    path = os.path.join(result_dir, "Cookies", f"{safe_email}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _file_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)