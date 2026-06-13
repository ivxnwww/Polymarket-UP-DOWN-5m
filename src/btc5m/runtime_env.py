from __future__ import annotations

import os


_PROXY_ENV_VARS = [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
]

_BROKEN_PROXY_MARKERS = (
    "127.0.0.1:9",
    "localhost:9",
)


def sanitize_proxy_environment() -> list[str]:
    """Remove clearly broken loopback proxy variables for direct market feeds.

    The local environment used for this project can inject placeholder proxies
    such as 127.0.0.1:9, which make requests/websocket connections fail before
    the application even reaches the exchanges. Only obviously invalid loopback
    proxies are removed; real proxy setups are preserved.
    """
    removed: list[str] = []
    for key in _PROXY_ENV_VARS:
        value = os.environ.get(key)
        if not value:
            continue
        normalized = value.strip().lower()
        if any(marker in normalized for marker in _BROKEN_PROXY_MARKERS):
            os.environ.pop(key, None)
            removed.append(key)
    return removed
