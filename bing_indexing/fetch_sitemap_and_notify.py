# -*- coding: utf-8 -*-
"""
Lee todas las URLs del sitemap de tu sitio y las envia a IndexNow (Bing).

Un solo comando:
  python fetch_sitemap_and_notify.py

Opciones:
  python fetch_sitemap_and_notify.py --dry-run
  python fetch_sitemap_and_notify.py --sitemap https://tudominio.com/sitemap.xml
  python fetch_sitemap_and_notify.py --save urls_from_sitemap.txt
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import requests

from indexnow_notify import (
    DEFAULT_CONFIG,
    SCRIPT_DIR,
    explain_status,
    host_matches_url,
    load_config,
    submit_post,
)

DEFAULT_SITEMAP = "https://tudominio.com/sitemap.xml"
DEFAULT_SAVE = SCRIPT_DIR / "urls_from_sitemap.txt"


def _locs(xml: str) -> list[str]:
    return [unquote(m.group(1)) for m in re.finditer(r"<loc>(.*?)</loc>", xml, re.I)]


def _fetch_xml(url: str, *, timeout: float = 60.0) -> str:
    url = url.replace("&amp;", "&")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def fetch_urls_from_sitemap(sitemap_url: str, *, timeout: float = 60.0) -> list[str]:
    """Recorre sitemap index y sitemaps hijos; devuelve URLs unicas en orden."""
    root_xml = _fetch_xml(sitemap_url, timeout=timeout)
    entries = _locs(root_xml)

    all_urls: list[str] = []
    for entry in entries:
        entry = entry.replace("&amp;", "&")
        if entry.endswith(".xml") or "sitemap" in entry.lower() and ".xml" in entry:
            try:
                child_xml = _fetch_xml(entry, timeout=timeout)
                child_locs = _locs(child_xml)
                if child_locs and child_locs[0].endswith(".xml"):
                    for nested in child_locs:
                        all_urls.extend(_locs(_fetch_xml(nested, timeout=timeout)))
                else:
                    all_urls.extend(child_locs)
            except requests.RequestException as e:
                print(f"AVISO: no se pudo leer {entry}: {e}", file=sys.stderr)
        else:
            all_urls.append(entry)

    seen: set[str] = set()
    unique: list[str] = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def save_urls(path: Path, urls: list[str], sitemap_url: str) -> None:
    lines = [f"# Generado desde {sitemap_url}", f"# Total: {len(urls)}", ""]
    lines.extend(urls)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def submit_batches(
    host: str,
    key: str,
    key_location: str,
    urls: list[str],
    *,
    batch_size: int = 100,
) -> int:
    errors = 0
    for i in range(0, len(urls), batch_size):
        batch = urls[i : i + batch_size]
        status, body = submit_post(host, key, key_location, batch)
        n = i // batch_size + 1
        print(f"Lote {n}: {len(batch)} URL(s) -> HTTP {status} - {explain_status(status)}")
        if body:
            print(f"  {body}")
        if status not in (200, 202):
            errors += 1
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sitemap -> IndexNow (Bing): obtiene URLs y las notifica.",
    )
    parser.add_argument(
        "--sitemap",
        default=DEFAULT_SITEMAP,
        help=f"URL del sitemap index (default: {DEFAULT_SITEMAP})",
    )
    parser.add_argument("--config", "-c", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--save",
        type=Path,
        default=DEFAULT_SAVE,
        help="Guardar lista de URLs en este archivo",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="No escribir archivo de URLs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo listar URLs, sin enviar a IndexNow",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="URLs por peticion POST (max 10000)",
    )
    args = parser.parse_args()

    print(f"Leyendo sitemap: {args.sitemap}")
    try:
        urls = fetch_urls_from_sitemap(args.sitemap)
    except requests.RequestException as e:
        print(f"Error al leer sitemap: {e}", file=sys.stderr)
        return 1

    print(f"URLs encontradas: {len(urls)}")

    if not args.no_save:
        save_urls(args.save, urls, args.sitemap)
        print(f"Lista guardada: {args.save}")

    if args.dry_run:
        for u in urls[:10]:
            print(f"  {u}")
        if len(urls) > 10:
            print(f"  ... y {len(urls) - 10} mas")
        return 0

    try:
        cfg = load_config(args.config)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(e, file=sys.stderr)
        return 2

    host = str(cfg["host"]).strip()
    key = str(cfg["key"]).strip()
    key_location = str(cfg["key_location"]).strip()

    filtered = [u for u in urls if host_matches_url(host, u)]
    skipped = len(urls) - len(filtered)
    if skipped:
        print(f"Omitidas {skipped} URL(s) fuera de host '{host}'", file=sys.stderr)
    if not filtered:
        print("No hay URLs para enviar.", file=sys.stderr)
        return 2

    errors = submit_batches(host, key, key_location, filtered, batch_size=args.batch_size)
    print(f"Resumen: {len(filtered)} URL(s) enviadas, {errors} lote(s) con error.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
