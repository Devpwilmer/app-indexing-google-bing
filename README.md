# Indexación masiva · Google y Bing

Herramienta **gratuita y local** (en tu PC) para avisar a **Google** y **Bing** cuando publicas o actualizas páginas en tu web. Ideal para **Shopify**, WordPress o cualquier sitio con URLs públicas.

> Esta carpeta es la **plantilla para GitHub**. No incluye claves ni datos de nadie.  
> Tu copia de trabajo con tus archivos secretos puede estar en otra carpeta (por ejemplo `Automatizacion`).

---

## Qué hace

1. Pegas URLs (o cargas el **sitemap** de tu tienda).
2. Pulsas **Google**, **Bing** o **Ambos**.
3. Los buscadores **reciben el aviso** (no garantiza indexación al instante, pero acelera el proceso).

Todo se ejecuta en **http://127.0.0.1:5055** — solo en tu ordenador, no se publica en internet.

---

## Qué necesitas antes

| Requisito | Para qué |
|-----------|----------|
| **Python 3.10+** | [python.org](https://www.python.org/downloads/) — al instalar, marca *Add Python to PATH* |
| **Google Search Console** | Tu dominio verificado (ej. `https://tudominio.com`) |
| **Google Cloud** | Proyecto con **Indexing API** activada + cliente OAuth |
| **Bing Webmaster Tools** | Tu sitio añadido + clave **IndexNow** |
| **Archivo en tu web** | Un `.txt` en la raíz con la clave IndexNow (en Shopify: Archivos + redirección) |

---

## Instalación (primera vez)

### 1. Descarga el proyecto

```text
git clone https://github.com/TU_USUARIO/app-indexing-google-bing.git
cd app-indexing-google-bing
```

(O descarga el ZIP desde GitHub y descomprímelo.)

### 2. Instala las dependencias

Abre **PowerShell** o **CMD** en la carpeta del proyecto:

```powershell
cd indexing_web
pip install -r requirements.txt
pip install -r ..\google_indexing\requirements.txt
pip install -r ..\bing_indexing\requirements.txt
```

### 3. Arranca la aplicación

**Opción A — doble clic:**  
`iniciar_indexacion_web.bat`

**Opción B — terminal:**

```powershell
cd indexing_web
python app.py
```

Abre en el navegador: **http://127.0.0.1:5055**

---

## Configurar tus APIs (pestaña «Configurar APIs»)

Hazlo **una sola vez** por dominio. Los datos se guardan **solo en tu PC**.

### Bing (IndexNow)

1. En [Bing Webmaster Tools](https://www.bing.com/webmasters) → **IndexNow** → genera una clave.
2. Sube a tu web un archivo `TU_CLAVE.txt` que contenga **solo la clave** (ej. `https://tudominio.com/abc123.txt`).
3. En la app → **Configurar APIs** → sección **Bing**:
   - **Host:** `tudominio.com` (sin `https://`)
   - **Clave:** la de Bing
   - **URL del archivo:** la URL pública del `.txt`
4. **Guardar Bing**

O copia `bing_indexing/config.example.json` → `bing_indexing/config.json` y rellénalo a mano.

### Google (Indexing API)

1. En [Google Cloud Console](https://console.cloud.google.com/) crea un proyecto y activa **Indexing API**.
2. Crea credenciales **OAuth** tipo *Aplicación de escritorio*.
3. Descarga el JSON y pégalo en la app (campo *Cliente OAuth*), **o** renómbralo a `oauth_client.json` dentro de `google_indexing/`.
4. En el mismo JSON, en Google Cloud añade esta **URI de redirección** (si usas el botón de la app):  
   `http://127.0.0.1:5055/oauth2callback`
5. Pulsa **Autorizar con Google** e inicia sesión con el Gmail que es **propietario** del sitio en Search Console.
6. **Guardar Google**

**Alternativa:** cuenta de servicio (JSON) — solo si la tienes añadida como usuario en Search Console.

---

## Uso diario

1. Arranca la app (`python app.py` o el `.bat`).
2. Pestaña **Enviar URLs**.
3. Pega enlaces, sube un `.txt` / `.csv`, o **Cargar sitemap** (en Shopify suele ser `https://tudominio.com/sitemap.xml`).
4. Pulsa **Google**, **Bing** o **Ambos**.
5. Revisa el panel **Resultado** (códigos **200** o **202** = recibido).

**Cuotas orientativas:** Google ~200 avisos/día; si tienes muchas URLs, reparte en varios días.

---

## Estructura del proyecto

```text
app-indexing-google-bing/
├── README.md                 ← esta guía
├── iniciar_indexacion_web.bat
├── indexing_web/               ← aplicación web (empieza aquí)
├── google_indexing/            ← scripts Google + plantillas OAuth
└── bing_indexing/              ← scripts Bing + config.example.json
```

---

## Shopify (resumen)

- El sitemap se actualiza al publicar productos, blogs o páginas.
- URL típica del sitemap: `https://tudominio.com/sitemap.xml`
- Para páginas nuevas “descubiertas pero no indexadas”, envíalas con esta herramienta y enlázalas desde el blog o la home.

---

## Problemas frecuentes

| Problema | Qué hacer |
|----------|-----------|
| La página no abre | ¿Sigue abierta la ventana negra con `python app.py`? |
| Google en ámbar | Completa OAuth en **Configurar APIs** |
| Bing 403 | Revisa que el `.txt` de la clave se abra en el navegador |
| «No hay URLs válidas» | Usa URLs completas con `https://` |

---

## Créditos

Herramienta desarrollada por **Wilmer Méndez**.  
Si te fue útil, puedes seguirme en [LinkedIn](https://pe.linkedin.com/in/wilmermendez).

---

## Licencia

Uso libre para proyectos personales y comerciales. Sin garantía. Respeta las políticas de Google y Bing.
