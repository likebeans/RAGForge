from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


def normalize_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    base_url = base_url.strip()
    if not base_url:
        return None

    parsed = urlparse(base_url)
    if parsed.scheme:
        return base_url

    trimmed = base_url.lstrip("/")
    parsed = urlparse(f"http://{trimmed}")
    host = parsed.hostname or ""

    scheme = "https"
    try:
        ip_addr = ipaddress.ip_address(host)
        if ip_addr.is_private or ip_addr.is_loopback:
            scheme = "http"
    except ValueError:
        if host in {"localhost"}:
            scheme = "http"

    return f"{scheme}://{trimmed}"
