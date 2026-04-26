"""Web skill — open URLs and search the user's default browser."""
from __future__ import annotations

import logging
import webbrowser
from typing import Any
from urllib.parse import quote_plus

from config.settings import WEBSITE_SHORTCUTS

logger = logging.getLogger(__name__)

_SEARCH_ENGINES = {
    "google":  "https://www.google.com/search?q={}",
    "youtube": "https://www.youtube.com/results?search_query={}",
    "bing":    "https://www.bing.com/search?q={}",
    "ddg":     "https://duckduckgo.com/?q={}",
}


def looks_like_url(text: str) -> bool:
    t = text.strip()
    if " " in t or len(t) > 100:
        return False
    return t.startswith(("http://", "https://")) or "." in t


def open_url(target: str) -> dict[str, Any]:
    key = target.strip().lower()
    if key in WEBSITE_SHORTCUTS:
        url = WEBSITE_SHORTCUTS[key]
        label = key
    elif target.startswith(("http://", "https://")):
        url = target
        label = target
    else:
        url = f"https://{target}"
        label = target
    webbrowser.open(url, new=2)
    return {"ok": True, "message": f"Opened {url}",
            "speak": f"Opening {label}."}


def search(query: str, engine: str = "google") -> dict[str, Any]:
    query = query.strip()
    if not query:
        return {"ok": False, "speak": "What should I search for?"}
    template = _SEARCH_ENGINES.get(engine.lower(), _SEARCH_ENGINES["google"])
    url = template.format(quote_plus(query))
    webbrowser.open(url, new=2)
    pretty = "YouTube" if engine.lower() == "youtube" else engine.capitalize()
    return {"ok": True, "message": f"Searched {pretty} for {query}",
            "speak": f"Searching {pretty} for {query}."}
