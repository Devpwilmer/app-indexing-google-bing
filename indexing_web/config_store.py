# -*- coding: utf-8 -*-
"""Guardar y cargar credenciales de Google y Bing para la app web."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOOGLE_DIR = ROOT / "google_indexing"
BING_DIR = ROOT / "bing_indexing"

DEFAULT_OAUTH_CLIENT = GOOGLE_DIR / "oauth_client.json"
DEFAULT_OAUTH_TOKEN = GOOGLE_DIR / "oauth_token.json"
SERVICE_ACCOUNT_FILE = GOOGLE_DIR / "service_account.json"
AUTH_MODE_FILE = GOOGLE_DIR / "google_auth_mode.txt"
DEFAULT_CONFIG = BING_DIR / "config.json"
PREFS_FILE = Path(__file__).resolve().parent / "prefs.json"

INDEXING_SCOPES = ["https://www.googleapis.com/auth/indexing"]
OAUTH_REDIRECT_PATH = "/oauth2callback"


def _read_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


GENERIC_SITEMAP = "https://tudominio.com/sitemap.xml"


def get_sitemap_default() -> str:
    """URL por defecto del sitemap (prefs del usuario o plantilla genérica)."""
    prefs = _read_json(PREFS_FILE)
    if isinstance(prefs, dict):
        url = str(prefs.get("sitemap_url", "")).strip()
        if url:
            return url
    return GENERIC_SITEMAP


def save_sitemap_pref(url: str) -> str:
    url = url.strip()
    if not url:
        if PREFS_FILE.is_file():
            PREFS_FILE.unlink()
        return GENERIC_SITEMAP
    if not url.startswith("http"):
        raise ValueError("La URL del sitemap debe empezar por https://")
    prefs: dict = {}
    if PREFS_FILE.is_file():
        existing = _read_json(PREFS_FILE)
        if isinstance(existing, dict):
            prefs = existing
    prefs["sitemap_url"] = url
    _write_json(PREFS_FILE, prefs)
    return url


def get_google_auth_mode() -> str:
    if AUTH_MODE_FILE.is_file():
        mode = AUTH_MODE_FILE.read_text(encoding="utf-8").strip()
        if mode in ("oauth", "service_account"):
            return mode
    if SERVICE_ACCOUNT_FILE.is_file() and not DEFAULT_OAUTH_TOKEN.is_file():
        return "service_account"
    return "oauth"


def set_google_auth_mode(mode: str) -> None:
    if mode not in ("oauth", "service_account"):
        raise ValueError("mode debe ser oauth o service_account")
    AUTH_MODE_FILE.write_text(mode, encoding="utf-8")


def google_ready() -> bool:
    mode = get_google_auth_mode()
    if mode == "service_account":
        return SERVICE_ACCOUNT_FILE.is_file()
    return DEFAULT_OAUTH_CLIENT.is_file() and DEFAULT_OAUTH_TOKEN.is_file()


def bing_ready() -> bool:
    if not DEFAULT_CONFIG.is_file():
        return False
    try:
        from indexnow_notify import load_config  # noqa: WPS433

        load_config(DEFAULT_CONFIG)
        return True
    except Exception:
        return False


def config_status() -> dict:
    bing_cfg = _read_json(DEFAULT_CONFIG) if DEFAULT_CONFIG.is_file() else {}
    host = str((bing_cfg or {}).get("host", ""))
    return {
        "google": {
            "mode": get_google_auth_mode(),
            "oauth_client": DEFAULT_OAUTH_CLIENT.is_file(),
            "oauth_token": DEFAULT_OAUTH_TOKEN.is_file(),
            "service_account": SERVICE_ACCOUNT_FILE.is_file(),
            "ready": google_ready(),
        },
        "bing": {
            "config": DEFAULT_CONFIG.is_file(),
            "host": host,
            "ready": bing_ready(),
        },
        "sitemap_default": None,  # filled by services
    }


def get_config_for_ui() -> dict:
    bing = {"host": "", "key": "", "key_location": ""}
    raw_bing = _read_json(DEFAULT_CONFIG)
    if isinstance(raw_bing, dict):
        bing = {
            "host": str(raw_bing.get("host", "")),
            "key": str(raw_bing.get("key", "")),
            "key_location": str(raw_bing.get("key_location", "")),
        }

    oauth_client_text = ""
    if DEFAULT_OAUTH_CLIENT.is_file():
        oauth_client_text = DEFAULT_OAUTH_CLIENT.read_text(encoding="utf-8")

    oauth_token_text = ""
    if DEFAULT_OAUTH_TOKEN.is_file():
        oauth_token_text = DEFAULT_OAUTH_TOKEN.read_text(encoding="utf-8")

    service_account_text = ""
    if SERVICE_ACCOUNT_FILE.is_file():
        service_account_text = SERVICE_ACCOUNT_FILE.read_text(encoding="utf-8")

    return {
        "google": {
            "mode": get_google_auth_mode(),
            "oauth_client": oauth_client_text,
            "oauth_token": oauth_token_text,
            "service_account": service_account_text,
            "ready": google_ready(),
        },
        "bing": {**bing, "ready": bing_ready()},
        "sitemap_url": get_sitemap_default(),
    }


def save_bing_config(
    *,
    host: str = "",
    key: str = "",
    key_location: str = "",
    json_text: str = "",
) -> dict:
    if json_text.strip():
        data = json.loads(json_text)
        if not isinstance(data, dict):
            raise ValueError("El JSON de Bing debe ser un objeto")
        host = str(data.get("host", host)).strip()
        key = str(data.get("key", key)).strip()
        key_location = str(data.get("key_location", key_location)).strip()

    host = host.strip().removeprefix("https://").removeprefix("http://").split("/")[0]
    key = key.strip()
    key_location = key_location.strip()

    if not host or not key:
        raise ValueError("Indica host y clave IndexNow")
    if "PEGA_AQUI" in key.upper():
        raise ValueError("Sustituye la clave de ejemplo por la tuya de Bing Webmaster")

    if not key_location:
        key_location = f"https://{host}/{key}.txt"

    _write_json(DEFAULT_CONFIG, {"host": host, "key": key, "key_location": key_location})
    return {"ok": True, "host": host, "key_location": key_location}


def save_google_oauth_client(text: str) -> None:
    text = text.strip()
    if not text:
        raise ValueError("Pega el JSON del cliente OAuth de Google Cloud")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("JSON invalido")
    if "installed" not in data and "web" not in data:
        raise ValueError('El JSON debe ser cliente OAuth de escritorio ("installed") o web')
    _write_json(DEFAULT_OAUTH_CLIENT, data)


def save_google_oauth_token(text: str) -> None:
    text = text.strip()
    if not text:
        raise ValueError("Pega el JSON del token OAuth o usa Autorizar con Google")
    data = json.loads(text)
    if not isinstance(data, dict) or "token" not in data:
        raise ValueError('Token invalido: debe ser el contenido de oauth_token.json')
    _write_json(DEFAULT_OAUTH_TOKEN, data)


def save_google_service_account(text: str) -> None:
    text = text.strip()
    if not text:
        raise ValueError("Pega el JSON de la cuenta de servicio")
    data = json.loads(text)
    if not isinstance(data, dict) or data.get("type") != "service_account":
        raise ValueError("No parece un JSON de cuenta de servicio de Google")
    _write_json(SERVICE_ACCOUNT_FILE, data)


def create_google_oauth_flow(redirect_uri: str):
    from google_auth_oauthlib.flow import Flow

    if not DEFAULT_OAUTH_CLIENT.is_file():
        raise FileNotFoundError(
            "Primero guarda el cliente OAuth (JSON de Google Cloud Console)",
        )
    return Flow.from_client_secrets_file(
        str(DEFAULT_OAUTH_CLIENT),
        scopes=INDEXING_SCOPES,
        redirect_uri=redirect_uri,
    )
