"""Owner-scoped feedback persistence through Supabase RLS."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from django.conf import settings

def load_feedback(token, user_id):
    if not _configured(token): return []
    query = urlencode({"select": "id,category,message,page_url,priority,status,created_at", "user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": "50"})
    try:
        with urlopen(_request(f"user_feedback?{query}", token), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response: rows = json.load(response)
        return rows if isinstance(rows, list) else None
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError): return None

def save_feedback(token, user_id, category, message, page_url, priority="normal"):
    if not _configured(token): return False
    request = _request("user_feedback", token, "POST", {"user_id": user_id, "category": category, "message": message, "page_url": page_url, "priority": priority, "status": "new"})
    try:
        with urlopen(request, timeout=settings.SUPABASE_AUTH_TIMEOUT) as response: return response.status in (200, 201, 204)
    except (HTTPError, URLError, TimeoutError): return False

def _request(path, token, method="GET", payload=None):
    headers = {"apikey": settings.SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}", "Accept": "application/json"}
    if payload is not None: headers.update({"Content-Type": "application/json", "Prefer": "return=minimal"})
    return Request(f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/{path}", data=json.dumps(payload).encode() if payload else None, method=method, headers=headers)

def _configured(token): return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY and token)
