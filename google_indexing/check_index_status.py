# -*- coding: utf-8 -*-
"""
Comprueba si URLs están indexadas en Google (Search Console URL Inspection API).

La Indexing API NO devuelve estado de indexación; solo notifica cambios.
Este script usa la API de inspección de Search Console.

Requiere: Search Console API habilitada en el proyecto Cloud, propiedad
Tu dominio verificado en Search Console, OAuth con scope webmasters.readonly.

Primera vez (o si pide permisos nuevos):
  del oauth_token.json
  python check_index_status.py URL1 URL2 URL3 --oauth

Ejemplo:
  python check_index_status.py https://tudominio.com/ https://tudominio.com/pagina --oauth
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OAUTH_CLIENT = SCRIPT_DIR / "oauth_client.json"
# Token aparte: el de Indexing API no incluye scope de Search Console.
DEFAULT_OAUTH_TOKEN = SCRIPT_DIR / "oauth_token_search_console.json"

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
INSPECT_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
SITE_URL = "https://tudominio.com/"


def get_credentials(token_path: Path, client_path: Path, *, use_console: bool) -> Credentials:
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds: Credentials | None = None
    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
            if use_console:
                print("Modo consola: abre el enlace y pega el código.", file=sys.stderr)
                creds = flow.run_console()
            else:
                print("Autoriza en el navegador (Search Console).", file=sys.stderr)
                creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def inspect_url(creds: Credentials, page_url: str, site_url: str = SITE_URL) -> dict:
    creds.refresh(Request())
    body = {"inspectionUrl": page_url, "siteUrl": site_url}
    r = requests.post(
        INSPECT_URL,
        headers={
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body),
        timeout=60,
    )
    if r.status_code != 200:
        return {"error": r.status_code, "body": r.text[:800]}
    return r.json()


def summarize(result: dict) -> str:
    if "error" in result:
        return f"Error API: {result['error']} — {result.get('body', '')[:200]}"

    ins = result.get("inspectionResult", {})
    idx = ins.get("indexStatusResult", {})
    verdict = idx.get("verdict", "—")
    coverage = idx.get("coverageState", "—")
    indexing = idx.get("indexingState", "—")
    crawled = idx.get("lastCrawlTime", "—")
    page_fetch = idx.get("pageFetchState", "—")
    google_canonical = idx.get("googleCanonical", "—")
    user_canonical = idx.get("userCanonical", "—")

    indexed = verdict in ("PASS", "NEUTRAL") and "indexed" in coverage.lower()

    lines = [
        f"  Veredicto: {verdict}",
        f"  Cobertura: {coverage}",
        f"  Estado indexación: {indexing}",
        f"  Último rastreo: {crawled}",
        f"  Fetch: {page_fetch}",
        f"  Canónica Google: {google_canonical}",
    ]
    if user_canonical and user_canonical != "—":
        lines.append(f"  Canónica usuario: {user_canonical}")
    lines.append(f"  ¿Indexada (resumen): {'Sí' if indexed else 'No / revisar'}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspecciona indexación en Google Search Console.")
    parser.add_argument("urls", nargs="+", help="Hasta varias URLs a comprobar")
    parser.add_argument("--oauth", action="store_true", help="Usar oauth_client.json")
    parser.add_argument("--oauth-console", action="store_true")
    parser.add_argument("--site", default=SITE_URL, help=f"siteUrl GSC (default {SITE_URL})")
    parser.add_argument("--token", type=Path, default=DEFAULT_OAUTH_TOKEN)
    parser.add_argument("--client", type=Path, default=DEFAULT_OAUTH_CLIENT)
    args = parser.parse_args()

    if not args.client.is_file():
        print(f"No existe {args.client}", file=sys.stderr)
        return 2

    try:
        creds = get_credentials(args.token, args.client, use_console=args.oauth_console)
    except Exception as e:
        print(f"Auth: {e}", file=sys.stderr)
        return 1

    print(f"Propiedad Search Console: {args.site}\n")
    for url in args.urls:
        print(f"URL: {url}")
        try:
            data = inspect_url(creds, url, args.site)
            print(summarize(data))
        except Exception as e:
            print(f"  Error: {e}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
