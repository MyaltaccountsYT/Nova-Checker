import threading

_instance = None
_lock = threading.Lock()

_UA_EDGE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
_UA_ANDROID = "Mozilla/5.0 (Linux; Android 9; SM-G9880 Build/PQ3A.190705.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36"
_TIMEOUT = 15

class NovaXboxChecker:
    pass

def get_novaxboxchecker():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaXboxChecker()
    return _instance

def get_xbox_authenticate(session, rps_token):
    try:
        r = session.post(
            "https://user.auth.xboxlive.com/user/authenticate",
            json={
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName": "user.auth.xboxlive.com",
                    "RpsTicket": rps_token,
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType": "JWT",
            },
            headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": _UA_EDGE},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json().get("Token")
    except Exception:
        pass
    return None

def get_xsts_token(session, user_token):
    try:
        r = session.post(
            "https://xsts.auth.xboxlive.com/xsts/authorize",
            json={
                "Properties": {"SandboxId": "RETAIL", "UserTokens": [user_token]},
                "RelyingParty": "http://xboxlive.com",
                "TokenType": "JWT",
            },
            headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": _UA_EDGE},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def get_title_history(session, xuid, xsts_token):
    games = []
    xhdrs = {
        "Authorization": xsts_token,
        "Accept": "application/json",
        "Accept-Language": "en-US",
        "x-xbl-contract-version": "2",
        "User-Agent": _UA_EDGE,
    }
    for url in [
        f"https://titlehub.xboxlive.com/users/xuid({xuid})/titles/titleHistory/decoration/detail?maxItems=200",
        f"https://achievements.xboxlive.com/users/xuid({xuid})/history/titles?maxItems=200",
    ]:
        try:
            r = session.get(url, headers=xhdrs, timeout=_TIMEOUT)
            if r.status_code != 200:
                continue
            data = r.json()
            titles = data.get("titles", [])
            for t in titles:
                if not isinstance(t, dict):
                    continue
                name = t.get("name") or t.get("titleName", "Unknown")
                tid = str(t.get("titleId") or t.get("id", ""))
                if name and name != "Unknown":
                    games.append({"name": name, "titleId": tid})
            if games:
                break
        except Exception:
            continue
    return games

def get_owned_games(session, rps_token):
    if not rps_token:
        return []
    user_token = get_xbox_authenticate(session, rps_token)
    if not user_token:
        return []
    xsts_data = get_xsts_token(session, user_token)
    if not xsts_data:
        return []
    uhs = xsts_data.get("DisplayClaims", {}).get("xui", [{}])[0].get("uhs", "")
    xuid = xsts_data.get("DisplayClaims", {}).get("xui", [{}])[0].get("xid", "")
    xbl3 = f'XBL3.0 x={uhs};{xsts_data.get("Token","")}'
    if not uhs or not xuid:
        return []
    return get_title_history(session, xuid, xbl3)

def get_game_pass_status(session, delegate_token):
    if not delegate_token:
        return []
    subs = []
    try:
        r = session.get(
            "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentTransactions",
            headers={
                "User-Agent": _UA_ANDROID,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Authorization": f'MSADELEGATE1.0="{delegate_token}"',
                "Content-Type": "application/json",
                "Host": "paymentinstruments.mp.microsoft.com",
                "Origin": "https://account.microsoft.com",
                "Referer": "https://account.microsoft.com/",
            },
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            for s in data.get("subscriptions", []):
                n = s.get("title") or s.get("productName") or s.get("name")
                if n:
                    subs.append(n)
    except Exception:
        pass
    return subs
