# Nova Checker Free Version | V0.2

## Features

- **Hotmail / Outlook account checker** — full capture on valid logins
- **Multi-login method support** — Spykii fresh PPFT, Outlook MSAL, static configs, fallback SFTAG
- **Minecraft checker** — detects whether the account has Minecraft
- **Hypixel checker** — verifies Hypixel access / stats
- **DonutSMP checker** — optional, requires API key in config
- **Microsoft Rewards points** — captures current points balance
- **Payment method detection** — flags accounts with saved payment info
- **Subscription detection** — detects active subscriptions on the account
- **Xbox Games library** — captures owned Xbox / Game Pass titles
- **OptiFine cape check** — detects if the account has an OptiFine cape
- **Name change availability** — flags whether a Minecraft name change is available
- **Country detection** — captures account region
- **Inbox scanner** — optional keyword scan (Steam, PayPal, crypto, Roblox, etc.)
- **Proxy support** — loads from `proxy.txt`, rotates and marks failed proxies
- **Multi-threaded** — configurable thread count (default 150)
- **CPM tracking** — live checks-per-minute stat in title bar
- **Deduplication on write** — no duplicate entries across result files
- **Cookie saving** — saves session cookies for valid hits
- **Sorted result output** — Hits / 2FA / Locked / NoVal / Bad / Countries / Games / Inboxes
- **Configurable via `config.ini`** — no hardcoded values, fully ini-driven
- **Rate limiter built-in** — handles 429s gracefully without crashing threads