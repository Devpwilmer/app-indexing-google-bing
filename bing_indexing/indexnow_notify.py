# -*- coding: utf-8 -*-
"""
Envía URLs a buscadores vía IndexNow (Bing, Yandex y otros participantes).

Documentación: https://www.indexnow.org/documentation

Requisitos en tu dominio (Shopify u otro):
  1. Generar clave en Bing Webmaster Tools → IndexNow.
  2. Publicar un archivo en la raíz del sitio, por ejemplo:
       https://tudominio.com/TU_CLAVE.txt
     El archivo debe contener solo la clave (texto UTF-8).
  3. Copiar config.example.json → config.json y rellenar host, key, key_location.

Instalación:
  pip install -r requirements.txt

Ejemplos:
  python fetch_sitemap_and_notify.py
  python indexnow_notify.py "https://tudominio.com/blogs/articulo"
  python indexnow_notify.py --file urls.txt
  python indexnow_notify.py --config mi_config.json "https://tudominio.com/"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "config.json"
INDEXNOW_POST_URL = "https://api.indexnow.org/IndexNow"
INDEXNOW_GET_URL = "https://www.bing.com/indexnow"


def load_config(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"No existe {path}. Copia config.example.json → config.json y rellena tu clave.",
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in ("host", "key", "key_location"):
        if not data.get(field) or "PEGA_AQUI" in str(data.get(field, "")):
            raise ValueError(f"Falta o no está configurado el campo '{field}' en {path}")
    return data


def host_matches_url(host: str, url: str) -> bool:
    parsed = urlparse(url)
    netloc = (parsed.netloc or "").lower().removeprefix("www.")
    return netloc == host.lower().removeprefix("www.")


def submit_post(
    host: str,
    key: str,
    key_location: str,
    url_list: list[str],
    *,
    timeout: float = 60.0,
) -> tuple[int, str]:
    body = {
        "host": host,
        "key": key,
        "keyLocation": key_location,
        "urlList": url_list,
    }
    r = requests.post(
        INDEXNOW_POST_URL,
        headers={"Content-Type": "application/json; charset=utf-8"},
        data=json.dumps(body),
        timeout=timeout,
    )
    return r.status_code, r.text.strip()[:500]


def submit_get_single(
    key: str,
    key_location: str,
    url: str,
    *,
    timeout: float = 30.0,
) -> tuple[int, str]:
    r = requests.get(
        INDEXNOW_GET_URL,
        params={"url": url, "key": key, "keyLocation": key_location},
        timeout=timeout,
    )
    return r.status_code, r.text.strip()[:500]


def load_urls_from_file(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def explain_status(code: int) -> str:
    return {
        200: "OK - URLs enviadas correctamente",
        202: "Aceptado - en cola",
        400: "Peticion invalida (revisa JSON/URLs)",
        403: "Prohibido - clave invalida o archivo .txt no accesible en keyLocation",
        422: "URL no pertenece al host o keyLocation no coincide",
        429: "Demasiadas peticiones - espera y reintenta",
    }.get(code, "Código no documentado — revisa respuesta")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Notifica URLs nuevas/actualizadas vía IndexNow (Bing Webmaster).",
    )
    parser.add_argument("urls", nargs="*", help="URLs completas https://tudominio.com/...")
    parser.add_argument("--file", "-f", type=Path, help="Una URL por línea")
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=DEFAULT_CONFIG,
        help="config.json con host, key, key_location",
    )
    parser.add_argument(
        "--get",
        action="store_true",
        help="Enviar solo 1 URL por GET (en lugar de POST por lote)",
    )
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(e, file=sys.stderr)
        return 2

    host = str(cfg["host"]).strip()
    key = str(cfg["key"]).strip()
    key_location = str(cfg["key_location"]).strip()

    urls: list[str] = list(args.urls)
    if args.file:
        if not args.file.is_file():
            print(f"No existe: {args.file}", file=sys.stderr)
            return 2
        urls.extend(load_urls_from_file(args.file))
    urls = [u for u in urls if u]

    if not urls:
        print("Indica al menos una URL o --file.", file=sys.stderr)
        return 2

    for u in urls:
        if not host_matches_url(host, u):
            print(f"URL fuera del host '{host}': {u}", file=sys.stderr)
            return 2

    if args.get:
        if len(urls) != 1:
            print("--get solo admite una URL.", file=sys.stderr)
            return 2
        status, body = submit_get_single(key, key_location, urls[0])
        print(f"HTTP {status} - {explain_status(status)}")
        if body:
            print(body)
        return 0 if status in (200, 202) else 1

    # IndexNow: hasta 10.000 URLs por POST; enviamos en lotes de 100
    batch_size = 100
    errors = 0
    for i in range(0, len(urls), batch_size):
        batch = urls[i : i + batch_size]
        status, body = submit_post(host, key, key_location, batch)
        print(f"Lote {i // batch_size + 1}: {len(batch)} URL(s) -> HTTP {status} - {explain_status(status)}")
        if body:
            print(f"  {body}")
        if status not in (200, 202):
            errors += 1

    print(f"Resumen: {len(urls)} URL(s) enviadas, {errors} lote(s) con error.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
