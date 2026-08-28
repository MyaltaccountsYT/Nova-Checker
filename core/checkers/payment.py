import re
import threading

_instance = None
_lock = threading.Lock()

_UA_ANDROID = "Mozilla/5.0 (Linux; Android 9; SM-G9880 Build/PQ3A.190705.003; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36"
_TIMEOUT = 15

class NovaPaymentChecker:
    pass

def get_novapaymentchecker():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = NovaPaymentChecker()
    return _instance

def _payment_headers(delegate_token):
    return {
        "User-Agent": _UA_ANDROID,
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
        "Authorization": f'MSADELEGATE1.0="{delegate_token}"',
        "Content-Type": "application/json",
        "Host": "paymentinstruments.mp.microsoft.com",
        "Origin": "https://account.microsoft.com",
        "Referer": "https://account.microsoft.com/",
    }

def get_payment_instruments(session, delegate_token):
    if not delegate_token:
        return []
    try:
        r = session.get(
            "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx"
            "?status=active,removed&language=en-US",
            headers=_payment_headers(delegate_token),
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, list) else data.get("items", [])
    except Exception:
        pass
    return []

def get_payment_methods(session, delegate_token):
    items = get_payment_instruments(session, delegate_token)
    methods = []
    for item in items:
        fam = item.get("paymentMethodFamily", "")
        if "credit_card" in fam.lower() or "debit" in fam.lower():
            name = item.get("accountHolderName") or item.get("name") or ""
            disp = (item.get("display") or {}).get("name", "")
            last4_m = re.search(r'(\d{4})$', str(item.get("lastFourDigits", item.get("display", {}).get("name", ""))))
            last4 = last4_m.group(1) if last4_m else ""
            card_str = f"{name} | {disp}{(' | ****' + last4) if last4 else ''}".strip(" |")
            if not card_str:
                card_str = disp or "CC Linked"
            methods.append({"type": "credit_card", "display": card_str})
        elif "paypal" in fam.lower():
            email_acc = item.get("accountHolderEmail") or item.get("emailAddress") or ""
            methods.append({"type": "paypal", "display": email_acc or "PayPal"})
    return methods

def get_billing_address(session, delegate_token):
    items = get_payment_instruments(session, delegate_token)
    for item in items:
        addr = item.get("address") or {}
        if addr:
            return addr
    return {}

def get_account_balance(session, delegate_token):
    items = get_payment_instruments(session, delegate_token)
    for item in items:
        b = item.get("balance") or item.get("availableBalance") or item.get("creditBalance")
        if b and str(b) not in ("0", "0.0", "0.00"):
            cur = item.get("currencyCode") or item.get("currency") or "USD"
            return f"{b} {cur}"
    return "0"
