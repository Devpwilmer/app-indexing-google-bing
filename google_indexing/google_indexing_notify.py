# -*- coding: utf-8 -*-
"""
Notifica a Google Indexing API que una URL se actualizó o eliminó.

Autenticación (elige una):
  - OAuth (--oauth): tu Gmail propietario en Search Console (recomendado si la
    cuenta de servicio no se puede añadir en Search Console).
  - Cuenta de servicio (--key): JSON de servicio + ese email en Search Console.

Requisitos: proyecto Cloud con Indexing API habilitada; tu dominio verificado
en Search Console con el mismo correo que uses en OAuth.

Instalación:
  pip install -r requirements.txt

Ejemplos:
  python google_indexing\\google_indexing_notify.py --oauth google_indexing\\oauth_client.json "https://tudominio.com/"
  python google_indexing\\google_indexing_notify.py --key ruta-servicio.json "https://tudominio.com/"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OAUTH_CLIENT = SCRIPT_DIR / "oauth_client.json"
DEFAULT_OAUTH_TOKEN = SCRIPT_DIR / "oauth_token.json"

INDEXING_SCOPE = "https://www.googleapis.com/auth/indexing"
INDEXING_SCOPES = [INDEXING_SCOPE]
PUBLISH_URL = "https://indexing.googleapis.com/v3/urlNotifications:publish"


def get_access_token_service_account(key_path: Path) -> str:
    creds = service_account.Credentials.from_service_account_file(
        str(key_path),
        scopes=INDEXING_SCOPES,
    )
    creds.refresh(Request())
    if not creds.token:
        raise RuntimeError("No se obtuvo token OAuth2.")
    return creds.token


def get_access_token_oauth(
    client_secrets_path: Path,
    token_path: Path,
    *,
    use_console: bool = False,
) -> str:
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds: Credentials | None = None
    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(
            str(token_path),
            INDEXING_SCOPES,
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secrets_path.is_file():
                raise FileNotFoundError(
                    f"No existe el cliente OAuth: {client_secrets_path}",
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path),
                INDEXING_SCOPES,
            )
            if use_console:
                print(
                    "Modo consola: abre el enlace, inicia sesión con "
                    "tu Gmail de Search Console y pega el código aquí.",
                    file=sys.stderr,
                )
                creds = flow.run_console()
            else:
                print(
                    "Se abrirá el navegador. Inicia sesión con el Gmail "
                    "propietario de tu sitio en Search Console.",
                    file=sys.stderr,
                )
                creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    if not creds.token:
        raise RuntimeError("No se obtuvo token OAuth2.")
    return creds.token


def notify_url(
    token: str,
    url: str,
    *,
    deleted: bool,
    timeout: float = 30.0,
) -> tuple[int, dict]:
    body = {
        "url": url.strip(),
        "type": "URL_DELETED" if deleted else "URL_UPDATED",
    }
    r = requests.post(
        PUBLISH_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body),
        timeout=timeout,
    )
    try:
        payload = r.json() if r.text else {}
    except json.JSONDecodeError:
        payload = {"raw": r.text[:500]}
    return r.status_code, payload


def load_urls_from_file(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Envía notificaciones URL_UPDATED / URL_DELETED a Google Indexing API.",
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="URLs completas (https://...)",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        help="Archivo de texto: una URL por línea (# comentario)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Usar URL_DELETED en lugar de URL_UPDATED",
    )
    auth = parser.add_mutually_exclusive_group()
    auth.add_argument(
        "--oauth",
        nargs="?",
        const=str(DEFAULT_OAUTH_CLIENT),
        metavar="CLIENT_JSON",
        help=(
            "OAuth con tu Gmail (cliente OAuth de escritorio). "
            f"Por defecto: {DEFAULT_OAUTH_CLIENT.name}"
        ),
    )
    auth.add_argument(
        "--key",
        type=Path,
        help="JSON de cuenta de servicio (alternativa a --oauth)",
    )
    parser.add_argument(
        "--token",
        type=Path,
        default=DEFAULT_OAUTH_TOKEN,
        help=f"Donde guardar el token OAuth (por defecto {DEFAULT_OAUTH_TOKEN.name})",
    )
    parser.add_argument(
        "--oauth-console",
        action="store_true",
        help="OAuth pegando código manual (si el navegador da access_denied)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Segundos entre peticiones al enviar muchas URLs (por defecto 0.2)",
    )
    args = parser.parse_args()

    urls: list[str] = list(args.urls)
    if args.file:
        if not args.file.is_file():
            print(f"No existe el archivo: {args.file}", file=sys.stderr)
            return 2
        urls.extend(load_urls_from_file(args.file))
    urls = [u for u in urls if u]

    if not urls:
        print("Indica al menos una URL o --file.", file=sys.stderr)
        return 2

    try:
        if args.oauth is not None:
            client_path = Path(args.oauth)
            token = get_access_token_oauth(
                client_path,
                args.token,
                use_console=args.oauth_console,
            )
        else:
            key_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            key_path = args.key or (Path(key_env) if key_env else None)
            if not key_path or not key_path.is_file():
                if DEFAULT_OAUTH_CLIENT.is_file():
                    token = get_access_token_oauth(
                        DEFAULT_OAUTH_CLIENT,
                        args.token,
                        use_console=args.oauth_console,
                    )
                else:
                    print(
                        "Indica --oauth (Gmail) o --key (cuenta de servicio).",
                        file=sys.stderr,
                    )
                    return 2
            else:
                token = get_access_token_service_account(key_path)
    except Exception as e:
        print(f"Error de autenticación: {e}", file=sys.stderr)
        return 1

    ok = 0
    errors = 0
    for i, url in enumerate(urls):
        if i > 0 and args.delay > 0:
            time.sleep(args.delay)
        status, payload = notify_url(token, url, deleted=args.delete)
        if status == 200:
            ok += 1
            print(f"OK {status} {url}")
        else:
            errors += 1
            print(f"ERR {status} {url} -> {payload}", file=sys.stderr)

    print(f"Resumen: {ok} correctas, {errors} con error.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
