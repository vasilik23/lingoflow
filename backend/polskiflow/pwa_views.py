import json

from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static


PWA_SHELL_VERSION = "v30"
PWA_CACHE_VERSION = f"polskiflow-shell-{PWA_SHELL_VERSION}"


def web_app_manifest(_request):
    icon_url = f'{static("polskiflow/favicon.svg")}?shell={PWA_SHELL_VERSION}'
    manifest = {
        "id": "/",
        "name": "PolskiFlow",
        "short_name": "PolskiFlow",
        "description": "Практика польского языка от A1 до C2",
        "lang": "ru",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f7f6fb",
        "theme_color": "#6d4aff",
        "icons": [
            {
                "src": icon_url,
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "any",
            },
            {
                "src": icon_url,
                "sizes": "any",
                "type": "image/svg+xml",
                "purpose": "maskable",
            },
        ],
    }
    response = HttpResponse(
        json.dumps(manifest, ensure_ascii=False),
        content_type="application/manifest+json",
    )
    response["Cache-Control"] = "public, max-age=3600"
    return response


def service_worker(_request):
    offline_url = f"/offline/?shell={PWA_SHELL_VERSION}"
    public_assets = [
        f'{static("polskiflow/app.css")}?shell={PWA_SHELL_VERSION}',
        f'{static("polskiflow/favicon.svg")}?shell={PWA_SHELL_VERSION}',
    ]
    source = f'''"use strict";

const CACHE_NAME = {json.dumps(PWA_CACHE_VERSION)};
const OFFLINE_URL = {json.dumps(offline_url)};
// This allowlist contains only public, versioned static assets. User data,
// authenticated HTML, auth/API responses and lesson results are never cached.
const PUBLIC_ASSETS = {json.dumps(public_assets)};
const PRECACHE_URLS = [OFFLINE_URL, ...PUBLIC_ASSETS];

self.addEventListener("install", (event) => {{
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
}});

self.addEventListener("activate", (event) => {{
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
}});

self.addEventListener("fetch", (event) => {{
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Navigations always go to the network. Their responses may contain private
  // account data, so the worker never writes them to Cache Storage.
  if (request.mode === "navigate") {{
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }}

  const cacheKey = `${{url.pathname}}${{url.search}}`;
  if (PUBLIC_ASSETS.includes(cacheKey)) {{
    event.respondWith(caches.match(request).then((cached) => cached || fetch(request)));
  }}
}});
'''
    response = HttpResponse(source, content_type="text/javascript; charset=utf-8")
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Service-Worker-Allowed"] = "/"
    return response


def offline_shell(request):
    response = render(request, "offline.html")
    response["Cache-Control"] = "public, max-age=0, must-revalidate"
    return response
