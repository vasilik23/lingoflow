"""Small, fail-safe reader for explicitly published official Polish RSS feeds."""

from email.utils import parsedate_to_datetime
import ssl
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from django.core.cache import cache

import certifi


FEEDS = (
    {
        "name": "Główny Urząd Statystyczny",
        "url": "https://stat.gov.pl/rss/pl/5438/8.xml",
        "host": "stat.gov.pl",
        "category": "economy",
        "category_label": "Экономика",
    },
    {
        "name": "RMF24",
        "url": "https://www.rmf24.pl/fakty/polityka/feed",
        "host": "www.rmf24.pl",
        "category": "politics",
        "category_label": "Политика",
    },
    {
        "name": "Polsat Sport",
        "url": "https://www.polsatsport.pl/rss/wszystkie.xml",
        "host": "www.polsatsport.pl",
        "category": "sport",
        "category_label": "Спорт",
    },
    {
        "name": "RMF24 Kultura",
        "url": "https://www.rmf24.pl/kultura/feed",
        "host": "www.rmf24.pl",
        "category": "culture",
        "category_label": "Культура и медиа",
    },
)
CATEGORIES = (
    {"id": "politics", "label": "Политика"},
    {"id": "sport", "label": "Спорт"},
    {"id": "culture", "label": "Культура и медиа"},
    {"id": "economy", "label": "Экономика"},
)
CATEGORY_IDS = frozenset(category["id"] for category in CATEGORIES)
CACHE_KEY = "polskiflow:official-news:v2"
MAX_RESPONSE_BYTES = 512_000
ITEMS_PER_FEED = 3
HTTPS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def latest_official_news(limit: int = 12, category: str | None = None) -> list[dict]:
    cached = cache.get(CACHE_KEY)
    if cached is None:
        items = []
        for feed in FEEDS:
            feed_items = _load_feed(feed)
            feed_items.sort(key=lambda item: item["published_sort"], reverse=True)
            items.extend(feed_items[:ITEMS_PER_FEED])
        items.sort(key=lambda item: item["published_sort"], reverse=True)
        cached = items
        cache.set(CACHE_KEY, cached, 15 * 60)
    if category in CATEGORY_IDS:
        cached = [item for item in cached if item["category"] == category]
    return cached[: max(1, min(limit, 12))]


def _load_feed(feed: dict) -> list[dict]:
    try:
        request = Request(feed["url"], headers={"User-Agent": "LingoFlow/1.0 RSS reader"})
        with urlopen(request, timeout=4, context=HTTPS_CONTEXT) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            return []
        root = ElementTree.fromstring(body)
    except (OSError, ValueError, ElementTree.ParseError):
        return []
    result = []
    for node in root.findall(".//item")[:12]:
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        published = (node.findtext("pubDate") or "").strip()
        parsed = urlparse(link)
        if not title or parsed.scheme != "https" or parsed.hostname != feed["host"]:
            continue
        result.append(
            {
                "title": title[:240],
                "url": link,
                "source": feed["name"],
                "category": feed["category"],
                "category_label": feed["category_label"],
                "published": _display_date(published),
                "published_sort": _timestamp(published),
            }
        )
    return result


def _timestamp(value: str) -> float:
    try:
        return parsedate_to_datetime(value).timestamp()
    except (TypeError, ValueError, OverflowError):
        return 0


def _display_date(value: str) -> str:
    try:
        date = parsedate_to_datetime(value)
        return date.strftime("%d.%m.%Y")
    except (TypeError, ValueError, OverflowError):
        return ""
