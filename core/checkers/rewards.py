import re
import time
import threading

_instance = None
_lock = threading.Lock()

_UA_BING = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
_TIMEOUT = 15

class NovaRewardsChecker:
    pass

def get_novarewardschecker():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaRewardsChecker()
    return _instance

def get_rewards_points(session):
    pts, ltm = get_rewards_bing_page(session)
    if pts:
        return pts, ltm
    pts, ltm = get_rewards_flyout(session)
    if pts:
        return pts, ltm
    return get_rewards_fallback(session)

def get_rewards_bing_page(session):
    try:
        hdrs = {"User-Agent": _UA_BING, "Pragma": "no-cache", "Accept": "*/*"}
        r = session.get("https://rewards.bing.com/", headers=hdrs, timeout=_TIMEOUT, allow_redirects=True)
        if 'action="https://rewards.bing.com/signin-oidc"' in r.text or 'id="fmHF"' in r.text:
            act_m = re.search(r'action="([^"]+)"', r.text)
            if act_m:
                form_data = {}
                for inp in re.finditer(r'<input type="hidden" name="([^"]+)" id="[^"]+" value="([^"]+)">', r.text):
                    form_data[inp.group(1)] = inp.group(2)
                r = session.post(act_m.group(1), data=form_data, headers=hdrs, timeout=_TIMEOUT, allow_redirects=True)
        all_pts = re.findall(r',\"availablePoints\":(\d+)', r.text)
        if all_pts:
            pts = max(all_pts, key=int)
            if pts != "0":
                ltm_m = re.search(r'"lifetimePoints"\s*:\s*(\d+)', r.text)
                return pts, (ltm_m.group(1) if ltm_m else "0")
    except Exception:
        pass
    return None, None

def get_rewards_flyout(session):
    try:
        session.get(
            "https://www.bing.com/",
            headers={"User-Agent": _UA_BING, "Accept": "text/html", "Referer": "https://www.bing.com/"},
            timeout=_TIMEOUT,
        )
        ts = int(time.time() * 1000)
        rf = session.get(
            f"https://www.bing.com/rewards/panelflyout/getuserinfo?timestamp={ts}",
            headers={
                "User-Agent": _UA_BING,
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "Referer": "https://www.bing.com/",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=_TIMEOUT,
        )
        if rf.status_code == 200:
            d = rf.json()
            if d.get("userInfo", {}).get("isRewardsUser"):
                pts = str(d["userInfo"].get("balance", "0"))
                ltm = str(d["userInfo"].get("lifetimeBalance", "0"))
                return pts, ltm
    except Exception:
        pass
    return None, None

def get_rewards_fallback(session):
    try:
        r = session.get(
            "https://www.bing.com/rewards/panelflyout/getuserinfo?channel=BingFlyout&partnerId=BingRewards",
            headers={"User-Agent": _UA_BING},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            pm = re.search(r'"balance"\s*:\s*(\d+)', r.text)
            lm = re.search(r'"lifetimeBalance"\s*:\s*(\d+)', r.text)
            if pm:
                return pm.group(1), (lm.group(1) if lm else "0")
    except Exception:
        pass
    return None, None
