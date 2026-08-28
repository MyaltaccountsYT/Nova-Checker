import re
import time
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_instance = None
_lock = threading.Lock()

DONUT_API_URL = 'https://api.donutsmp.net/v1/stats/'
_TIMEOUT = 20

class NovaDonutChecker:
    pass

def get_novadonutchecker():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaDonutChecker()
    return _instance

def _make_donut_session():
    s = requests.Session()
    retry = Retry(
        total=3, backoff_factor=0.75,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET'],
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount('https://', adapter)
    s.mount('http://', adapter)
    s.verify = False
    return s

def _format_seconds(total_seconds):
    try:
        total_seconds = int(total_seconds)
    except Exception:
        return str(total_seconds)
    if total_seconds < 0:
        total_seconds = 0
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:    parts.append(f'{days}d')
    if hours:   parts.append(f'{hours}h')
    if minutes: parts.append(f'{minutes}m')
    return ' '.join(parts) if parts else '0m'

def _parse_ban_info(ban_text):
    info = {}
    if not ban_text or not isinstance(ban_text, str):
        return info
    m = re.search(r'Ban ID: ([A-Za-z0-9]+)', ban_text)
    if m:
        info['ban_id'] = m.group(1)
    if 'Permanently' in ban_text or 'permanently' in ban_text:
        info['duration'] = 'Permanently'
    else:
        m2 = re.search(r'\[([^\]]+)\]', ban_text)
        if m2:
            info['duration'] = m2.group(1)
    if 'Suspicious activity' in ban_text:
        info['reason'] = 'Suspicious activity'
    return info

def check_donut_smp(username, proxy_list=None, api_key=None):
    if not username or username == 'N/A':
        return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    session = _make_donut_session()

    proxy_candidates = []
    if proxy_list:
        import random
        for _ in range(min(4, len(proxy_list))):
            p = random.choice(proxy_list)
            if p and p not in proxy_candidates:
                proxy_candidates.append(p)
    proxy_candidates.append(None)

    valid_proxies = []
    for p in proxy_candidates:
        pdict = {'http': p, 'https': p} if p else None
        try:
            r = session.get(
                'https://api.donutsmp.net/index.html',
                headers=headers, proxies=pdict, verify=False, timeout=10,
            )
            if r.status_code == 200:
                valid_proxies.append(pdict)
        except Exception:
            pass
    if not valid_proxies:
        valid_proxies = [None]

    response = None
    for idx, pdict in enumerate(valid_proxies):
        try:
            r = session.get(
                f'{DONUT_API_URL}{username}',
                headers=headers, proxies=pdict, verify=False, timeout=_TIMEOUT,
            )
            time.sleep(0.3 * (idx + 1))
            if r.status_code in (200, 401, 404, 429):
                response = r
                break
        except Exception:
            continue

    if response is None or response.status_code != 200:
        return None

    try:
        data = response.json()
    except Exception:
        return None

    stats_data = None
    if isinstance(data, dict) and 'result' in data and isinstance(data['result'], dict):
        stats_data = data['result']

    if not isinstance(stats_data, dict):
        return None

    result = {'username': username}
    for field in ('broken_blocks', 'deaths', 'kills', 'mobs_killed', 'money',
                  'money_made_from_sell', 'money_spent_on_shop', 'placed_blocks'):
        if stats_data.get(field):
            result[field] = stats_data[field]

    if stats_data.get('playtime'):
        raw = stats_data['playtime']
        result['playtime_raw'] = raw
        result['playtime_fmt'] = _format_seconds(raw)

    return result

def format_donut_capture(donut_data):
    if not donut_data:
        return None
    parts = []
    if donut_data.get('money'):
        parts.append(f"Money: {donut_data['money']}")
    if donut_data.get('kills'):
        parts.append(f"Kills: {donut_data['kills']}")
    if donut_data.get('deaths'):
        parts.append(f"Deaths: {donut_data['deaths']}")
    if donut_data.get('playtime_fmt'):
        parts.append(f"Playtime: {donut_data['playtime_fmt']}")
    if donut_data.get('mobs_killed'):
        parts.append(f"Mobs: {donut_data['mobs_killed']}")
    return ' | '.join(parts) if parts else None

def save_donut_stats(email, password, username, donut_data, ban_status, result_dir):
    import os
    if not donut_data:
        return
    lines = [
        f'{email}:{password}',
        f'Username: {username}',
    ]
    for field in ('broken_blocks', 'deaths', 'kills', 'mobs_killed',
                  'money', 'money_made_from_sell', 'money_spent_on_shop', 'placed_blocks'):
        if donut_data.get(field):
            lines.append(f'{field}: {donut_data[field]}')
    if donut_data.get('playtime_raw'):
        raw = donut_data['playtime_raw']
        fmt = donut_data.get('playtime_fmt', str(raw))
        lines.append(f'playtime: {raw} ({fmt})')
    if ban_status and ban_status not in ('False', None):
        lines.append('banned: true')
        info = _parse_ban_info(str(ban_status))
        if info.get('ban_id'):      lines.append(f"ban_id: {info['ban_id']}")
        if info.get('duration'):    lines.append(f"ban_duration: {info['duration']}")
    else:
        lines.append('banned: false')
    if len(lines) > 2:
        path = os.path.join(result_dir, 'donut_stats.txt')
        with open(path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            f.write('\n' + '=' * 50 + '\n')
