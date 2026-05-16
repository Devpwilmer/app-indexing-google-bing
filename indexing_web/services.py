# -*- coding: utf-8 -*-
"""Servicios que envuelven google_indexing y bing_indexing."""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOOGLE_DIR = ROOT / "google_indexing"
BING_DIR = ROOT / "bing_indexing"

for d in (GOOGLE_DIR, BING_DIR):
    p = str(d)
    if p not in sys.path:
        sys.path.insert(0, p)

from fetch_sitemap_and_notify import (  # noqa: E402
    DEFAULT_SITEMAP,
    fetch_urls_from_sitemap,
)
from config_store import (  # noqa: E402
    DEFAULT_OAUTH_CLIENT,
    DEFAULT_OAUTH_TOKEN,
    SERVICE_ACCOUNT_FILE,
    bing_ready,
    config_status as _config_status_base,
    get_google_auth_mode,
    get_sitemap_default,
    google_ready,
)
from google_indexing_notify import (  # noqa: E402
    get_access_token_oauth,
    get_access_token_service_account,
    notify_url,
)
from indexnow_notify import (  # noqa: E402
    DEFAULT_CONFIG,
    explain_status,
    host_matches_url,
    load_config,
    submit_post,
)

URL_RE = re.compile(r"https?://[^\s,\"'<>]+", re.I)


def parse_urls(text: str) -> list[str]:
    found = URL_RE.findall(text or "")
    seen: set[str] = set()
    out: list[str] = []
    for u in found:
        u = u.rstrip(".,;)")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def config_status() -> dict:
    status = _config_status_base()
    status["sitemap_default"] = get_sitemap_default()
    return status


def get_google_access_token() -> str:
    if get_google_auth_mode() == "service_account":
        if not SERVICE_ACCOUNT_FILE.is_file():
            raise FileNotFoundError(
                "Falta cuenta de servicio. Configurala en la pestaña APIs.",
            )
        return get_access_token_service_account(SERVICE_ACCOUNT_FILE)
    if not DEFAULT_OAUTH_CLIENT.is_file():
        raise FileNotFoundError(
            "Falta cliente OAuth. Configuralo en la pestaña APIs.",
        )
    return get_access_token_oauth(DEFAULT_OAUTH_CLIENT, DEFAULT_OAUTH_TOKEN)


def load_sitemap_urls(sitemap_url: str = DEFAULT_SITEMAP) -> list[str]:
    return fetch_urls_from_sitemap(sitemap_url)


def submit_google(urls: list[str], *, delay: float = 0.2) -> dict:
    if not google_ready():
        return {
            "ok": False,
            "error": "Google no configurado. Abre la pestaña Configurar APIs.",
            "results": [],
        }
    try:
        token = get_google_access_token()
    except Exception as e:
        return {"ok": False, "error": str(e), "results": []}

    results = []
    ok_count = 0
    for i, url in enumerate(urls):
        if i > 0 and delay > 0:
            time.sleep(delay)
        status, payload = notify_url(token, url, deleted=False)
        item = {"url": url, "status": status, "ok": status == 200, "detail": payload}
        results.append(item)
        if status == 200:
            ok_count += 1
    return {
        "ok": ok_count == len(urls),
        "submitted": len(urls),
        "success": ok_count,
        "errors": len(urls) - ok_count,
        "results": results,
    }


def submit_bing(urls: list[str], *, batch_size: int = 100) -> dict:
    if not bing_ready():
        return {
            "ok": False,
            "error": "Bing no configurado. Abre la pestaña Configurar APIs.",
            "batches": [],
        }
    try:
        cfg = load_config(DEFAULT_CONFIG)
    except Exception as e:
        return {"ok": False, "error": str(e), "batches": []}

    host = str(cfg["host"]).strip()
    key = str(cfg["key"]).strip()
    key_location = str(cfg["key_location"]).strip()
    filtered = [u for u in urls if host_matches_url(host, u)]
    skipped = len(urls) - len(filtered)

    batches = []
    errors = 0
    for i in range(0, len(filtered), batch_size):
        batch = filtered[i : i + batch_size]
        status, body = submit_post(host, key, key_location, batch)
        batches.append({
            "batch": i // batch_size + 1,
            "count": len(batch),
            "http_status": status,
            "message": explain_status(status),
            "body": body,
            "ok": status in (200, 202),
        })
        if status not in (200, 202):
            errors += 1

    return {
        "ok": errors == 0 and len(filtered) > 0,
        "submitted": len(filtered),
        "skipped": skipped,
        "batches": batches,
        "batch_errors": errors,
    }


def submit_both(urls: list[str], *, delay: float = 0.2) -> dict:
    return {
        "google": submit_google(urls, delay=delay),
        "bing": submit_bing(urls),
        "url_count": len(urls),
    }
