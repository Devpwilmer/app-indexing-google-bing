# -*- coding: utf-8 -*-
"""
App web local para envio masivo de URLs a Google Indexing API e IndexNow (Bing).

  cd indexing_web
  pip install -r requirements.txt
  python app.py

Abre http://127.0.0.1:5055
"""
from __future__ import annotations

import os

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from config_store import (
    OAUTH_REDIRECT_PATH,
    create_google_oauth_flow,
    get_config_for_ui,
    save_bing_config,
    save_google_oauth_client,
    save_google_oauth_token,
    save_google_service_account,
    save_sitemap_pref,
    set_google_auth_mode,
)
from services import (
    config_status,
    load_sitemap_urls,
    parse_urls,
    submit_bing,
    submit_both,
    submit_google,
)

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "local-indexing-web-dev-only",
)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.after_request
def no_cache_html(response):
    if response.content_type and "text/html" in response.content_type:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


@app.get("/")
def index():
    oauth_msg = request.args.get("oauth")
    tab = request.args.get("tab", "send")
    return render_template("index.html", oauth_msg=oauth_msg, initial_tab=tab)


@app.get("/api/status")
def api_status():
    return jsonify(config_status())


@app.get("/api/config")
def api_config_get():
    return jsonify(get_config_for_ui())


@app.post("/api/config/bing")
def api_config_bing():
    data = request.get_json(silent=True) or {}
    try:
        result = save_bing_config(
            host=str(data.get("host", "")),
            key=str(data.get("key", "")),
            key_location=str(data.get("key_location", "")),
            json_text=str(data.get("json", "")),
        )
        return jsonify({**result, "status": config_status()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/config/sitemap")
def api_config_sitemap():
    data = request.get_json(silent=True) or {}
    try:
        url = save_sitemap_pref(str(data.get("sitemap_url", "")))
        return jsonify({"ok": True, "sitemap_url": url, "status": config_status()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.post("/api/config/google")
def api_config_google():
    data = request.get_json(silent=True) or {}
    try:
        mode = data.get("mode")
        if mode:
            set_google_auth_mode(str(mode))

        if data.get("oauth_client"):
            save_google_oauth_client(str(data["oauth_client"]))
        if data.get("oauth_token"):
            save_google_oauth_token(str(data["oauth_token"]))
        if data.get("service_account"):
            save_google_service_account(str(data["service_account"]))

        return jsonify({"ok": True, "status": config_status()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.get("/api/config/google/authorize")
def api_google_authorize():
    try:
        redirect_uri = url_for("oauth2callback", _external=True)
        flow = create_google_oauth_flow(redirect_uri)
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        session["google_oauth_state"] = state
        return redirect(auth_url)
    except Exception as e:
        return redirect(f"/?tab=config&oauth=error&msg={e}")


@app.get(OAUTH_REDIRECT_PATH)
def oauth2callback():
    if request.args.get("error"):
        msg = request.args.get("error_description") or request.args.get("error")
        return redirect(f"/?tab=config&oauth=error&msg={msg}")

    state = session.pop("google_oauth_state", None)
    if not state:
        return redirect("/?tab=config&oauth=error&msg=sesion+OAuth+expirada")

    try:
        redirect_uri = url_for("oauth2callback", _external=True)
        flow = create_google_oauth_flow(redirect_uri)
        flow.state = state
        flow.fetch_token(authorization_response=request.url)
        from config_store import DEFAULT_OAUTH_TOKEN  # noqa: WPS433

        DEFAULT_OAUTH_TOKEN.write_text(flow.credentials.to_json(), encoding="utf-8")
        set_google_auth_mode("oauth")
        return redirect("/?tab=config&oauth=ok")
    except Exception as e:
        return redirect(f"/?tab=config&oauth=error&msg={e}")


@app.post("/api/parse")
def api_parse():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    urls = parse_urls(text)
    return jsonify({"count": len(urls), "urls": urls})


@app.post("/api/sitemap")
def api_sitemap():
    data = request.get_json(silent=True) or {}
    sitemap_url = data.get("sitemap_url", "").strip()
    if not sitemap_url:
        sitemap_url = config_status()["sitemap_default"]
    try:
        urls = load_sitemap_urls(sitemap_url)
        return jsonify({"ok": True, "count": len(urls), "urls": urls, "sitemap": sitemap_url})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/submit")
def api_submit():
    data = request.get_json(silent=True) or {}
    engine = data.get("engine", "both")
    urls = data.get("urls") or parse_urls(data.get("text", ""))
    if not urls:
        return jsonify({"ok": False, "error": "No hay URLs validas"}), 400

    delay = float(data.get("delay", 0.2))
    if engine == "google":
        result = {"engine": "google", **submit_google(urls, delay=delay)}
    elif engine == "bing":
        result = {"engine": "bing", **submit_bing(urls)}
    elif engine == "both":
        result = {"engine": "both", **submit_both(urls, delay=delay)}
    else:
        return jsonify({"ok": False, "error": "engine debe ser google, bing o both"}), 400

    return jsonify(result)


if __name__ == "__main__":
    print("Indexacion masiva -> http://127.0.0.1:5055")
    print("Configura APIs en la pestaña del navegador o en google_indexing/ y bing_indexing/")
    app.run(host="127.0.0.1", port=5055, debug=True, use_reloader=False)
