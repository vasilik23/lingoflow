"""Owner-scoped learning collections through the Supabase Data API."""

import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


def load_collections(token, user_id):
    collections = _get("learning_collections", "id,name,created_at", token, user_id, "created_at.asc")
    items = _get("learning_collection_items", "id,collection_id,content_type,content_id,created_at", token, user_id, "created_at.asc")
    return None if collections is None or items is None else (collections, items)


def load_collection_summaries(token, user_id):
    return _get("learning_collections", "id,name", token, user_id, "created_at.asc")


def create_collection(token, user_id, name):
    return _write("learning_collections", token, "POST", {"id": str(uuid.uuid4()), "user_id": user_id, "name": name}, "return=minimal")


def delete_collection(token, user_id, collection_id):
    query = urlencode({"id": f"eq.{collection_id}", "user_id": f"eq.{user_id}"})
    return _write(f"learning_collections?{query}", token, "DELETE", prefer="return=minimal")


def rename_collection(token, user_id, collection_id, name):
    query = urlencode({"id": f"eq.{collection_id}", "user_id": f"eq.{user_id}"})
    return _write(f"learning_collections?{query}", token, "PATCH", {"name": name}, "return=minimal")


def add_collection_item(token, user_id, collection_id, content_type, content_id):
    return _write("learning_collection_items", token, "POST", {"id": str(uuid.uuid4()), "collection_id": collection_id, "user_id": user_id, "content_type": content_type, "content_id": content_id}, "resolution=ignore-duplicates,return=minimal")


def delete_collection_item(token, user_id, item_id):
    query = urlencode({"id": f"eq.{item_id}", "user_id": f"eq.{user_id}"})
    return _write(f"learning_collection_items?{query}", token, "DELETE", prefer="return=minimal")


def _get(table, fields, token, user_id, order):
    if not _configured(token): return None
    query = urlencode({"select": fields, "user_id": f"eq.{user_id}", "order": order, "limit": "500"})
    try:
        with urlopen(_request(f"{table}?{query}", token), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response: rows = json.load(response)
        return rows if isinstance(rows, list) else None
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError): return None


def _write(path, token, method, payload=None, prefer=None):
    if not _configured(token): return False
    try:
        with urlopen(_request(path, token, method, payload, prefer), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response: return response.status in (200, 201, 204)
    except (HTTPError, URLError, TimeoutError): return False


def _request(path, token, method="GET", payload=None, prefer=None):
    headers = {"apikey": settings.SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}", "Accept": "application/json"}
    if payload is not None: headers["Content-Type"] = "application/json"
    if prefer: headers["Prefer"] = prefer
    return Request(f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/{path}", data=json.dumps(payload).encode() if payload is not None else None, method=method, headers=headers)


def _configured(token): return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY and token)
