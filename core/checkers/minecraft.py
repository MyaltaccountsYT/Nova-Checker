import threading

_instance = None
_lock = threading.Lock()

_TIMEOUT = 15

class NovaMinecraftChecker:
    pass

def get_novaminecraftchecker():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaMinecraftChecker()
    return _instance

def check_minecraft_ownership(session, access_token):
    try:
        r = session.get(
            'https://api.minecraftservices.com/entitlements/license?requestId=nova',
            headers={'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            items = r.json().get('items', [])
            has_mc      = any(i.get('name') in ('game_minecraft', 'product_minecraft') for i in items)
            has_gp_pc   = any(i.get('name') == 'product_game_pass_pc' for i in items)
            has_gp_ult  = any(i.get('name') == 'product_game_pass_ultimate' for i in items)
            if has_mc and has_gp_ult:
                return 'Normal Minecraft (with Game Pass Ultimate)'
            if has_mc and has_gp_pc:
                return 'Normal Minecraft (with Game Pass)'
            if has_mc:
                return 'Normal Minecraft'
            if has_gp_ult:
                return 'Xbox Game Pass Ultimate'
            if has_gp_pc:
                return 'Xbox Game Pass (PC)'
    except Exception:
        pass
    return None

def get_minecraft_profile(session, access_token):
    try:
        r = session.get(
            'https://api.minecraftservices.com/minecraft/profile',
            headers={'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            return {
                'name': data.get('name', ''),
                'uuid': data.get('id', ''),
                'capes': [c.get('alias', '') for c in data.get('capes', [])],
            }
    except Exception:
        pass
    return None

def get_name_change_info(session, access_token):
    try:
        r = session.get(
            'https://api.minecraftservices.com/minecraft/profile/namechange',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            return {
                'name_change_allowed': data.get('nameChangeAllowed', False),
                'created_at': data.get('createdAt', ''),
            }
    except Exception:
        pass
    return None

def get_optifine_cape(session, username):
    try:
        r = session.get(
            f'http://s.optifine.net/capes/{username}.png',
            verify=False, timeout=8,
        )
        if 'Not found' in r.text:
            return False
        return True
    except Exception:
        return None
