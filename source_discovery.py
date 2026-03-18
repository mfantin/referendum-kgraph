"""
Source Discovery Engine: automatically finds and validates new data sources
for the Italian referendum knowledge graph.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import feedparser
import requests

import config

logger = logging.getLogger(__name__)

DISCOVERY_TIMEOUT = 8  # seconds per request


@dataclass
class DiscoveredSource:
    name: str
    url: str
    source_type: str  # "rss", "news_api", "social"
    language: str
    reliability: float
    article_count: int = 0
    relevant_count: int = 0
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "new"  # "new", "validated", "active", "failed"
    error: Optional[str] = None


# --- Candidate feeds to discover ---
CANDIDATE_FEEDS = [
    # Italian newspapers
    {"name": "AGI Politica", "url": "https://www.agi.it/politica/rss", "lang": "it", "reliability": 0.8},
    {"name": "Adnkronos", "url": "https://www.adnkronos.com/rss/politica", "lang": "it", "reliability": 0.75},
    {"name": "Rainews", "url": "https://www.rainews.it/rss/politica", "lang": "it", "reliability": 0.85},
    {"name": "HuffPost Italia", "url": "https://www.huffingtonpost.it/feeds/index.xml", "lang": "it", "reliability": 0.7},
    {"name": "Fanpage Politica", "url": "https://www.fanpage.it/feed/politica/", "lang": "it", "reliability": 0.65},
    {"name": "Open Online", "url": "https://www.open.online/feed/", "lang": "it", "reliability": 0.7},
    {"name": "Domani", "url": "https://www.editorialedomani.it/rss", "lang": "it", "reliability": 0.75},
    {"name": "Il Post", "url": "https://www.ilpost.it/feed/", "lang": "it", "reliability": 0.8},
    {"name": "Linkiesta", "url": "https://www.linkiesta.it/feed/", "lang": "it", "reliability": 0.7},
    {"name": "Formiche.net", "url": "https://formiche.net/feed/", "lang": "it", "reliability": 0.7},
    {"name": "La Stampa Politica", "url": "https://www.lastampa.it/politica/rss.xml", "lang": "it", "reliability": 0.8},
    {"name": "Il Messaggero", "url": "https://www.ilmessaggero.it/rss/politica.xml", "lang": "it", "reliability": 0.75},
    {"name": "Il Giornale", "url": "https://www.ilgiornale.it/feed.xml", "lang": "it", "reliability": 0.65},
    {"name": "Libero", "url": "https://www.liberoquotidiano.it/rss.xml", "lang": "it", "reliability": 0.6},
    # International
    {"name": "Reuters World", "url": "https://www.reutersagency.com/feed/", "lang": "en", "reliability": 0.9},
    {"name": "The Guardian Europe", "url": "https://www.theguardian.com/world/europe-news/rss", "lang": "en", "reliability": 0.85},
    {"name": "Politico EU", "url": "https://www.politico.eu/feed/", "lang": "en", "reliability": 0.85},
    {"name": "France24 Europe", "url": "https://www.france24.com/en/europe/rss", "lang": "en", "reliability": 0.8},
    {"name": "DW Europe", "url": "https://rss.dw.com/xml/rss-en-eu", "lang": "en", "reliability": 0.8},
    {"name": "Al Jazeera Europe", "url": "https://www.aljazeera.com/xml/rss/all.xml", "lang": "en", "reliability": 0.75},
    {"name": "EUobserver", "url": "https://euobserver.com/rss.xml", "lang": "en", "reliability": 0.8},
    # Google News (always works)
    {"name": "Google News IT - Referendum", "url": "https://news.google.com/rss/search?q=referendum+italia+2026&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.7},
    {"name": "Google News IT - Nordio", "url": "https://news.google.com/rss/search?q=riforma+nordio+referendum&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.7},
    {"name": "Google News IT - Separazione Carriere", "url": "https://news.google.com/rss/search?q=separazione+carriere+magistratura&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.7},
    {"name": "Google News EN - Italy Referendum", "url": "https://news.google.com/rss/search?q=italy+referendum+2026&hl=en&gl=US&ceid=US:en", "lang": "en", "reliability": 0.7},
    # Reddit (RSS available for any subreddit)
    {"name": "Reddit r/italy", "url": "https://www.reddit.com/r/italy/search.rss?q=referendum&sort=new&restrict_sr=on", "lang": "it", "reliability": 0.5},
    {"name": "Reddit r/europe", "url": "https://www.reddit.com/r/europe/search.rss?q=italy+referendum&sort=new&restrict_sr=on", "lang": "en", "reliability": 0.45},
]


def _validate_feed(url: str, timeout: int = DISCOVERY_TIMEOUT) -> tuple[bool, int, str]:
    """
    Validate an RSS feed URL. Returns (is_valid, entry_count, error_msg).
    """
    try:
        feed = feedparser.parse(
            url,
            request_headers={"User-Agent": "ReferendumKG/1.0 (Research Tool)"},
        )
        if feed.bozo and not feed.entries:
            err = str(getattr(feed, "bozo_exception", "Unknown error"))[:100]
            return False, 0, f"Parse error: {err}"

        return True, len(feed.entries), ""

    except Exception as e:
        return False, 0, str(e)[:100]


def _count_relevant(url: str, language: str = "it") -> int:
    """Count how many entries in a feed are relevant to the referendum."""
    try:
        feed = feedparser.parse(
            url,
            request_headers={"User-Agent": "ReferendumKG/1.0 (Research Tool)"},
        )
        keywords = config.REFERENDUM_KEYWORDS_IT if language == "it" else config.REFERENDUM_KEYWORDS_EN
        count = 0
        for entry in feed.entries:
            text = (getattr(entry, "title", "") + " " + getattr(entry, "summary", "")).lower()
            if any(kw in text for kw in keywords):
                count += 1
        return count
    except Exception:
        return 0


def discover_sources(
    existing_urls: set[str] | None = None,
    max_new: int = 20,
) -> list[DiscoveredSource]:
    """
    Discover and validate new data sources not already in config.
    Returns list of validated DiscoveredSource objects.
    """
    if existing_urls is None:
        existing_urls = {f["url"] for f in config.RSS_FEEDS.values()}

    discovered = []

    for candidate in CANDIDATE_FEEDS:
        if len(discovered) >= max_new:
            break

        url = candidate["url"]

        # Skip if already known
        if url in existing_urls:
            continue

        is_valid, entry_count, error = _validate_feed(url)

        source = DiscoveredSource(
            name=candidate["name"],
            url=url,
            source_type="rss",
            language=candidate["lang"],
            reliability=candidate["reliability"],
            article_count=entry_count,
            status="validated" if is_valid else "failed",
            error=error if not is_valid else None,
        )

        if is_valid and entry_count > 0:
            source.relevant_count = _count_relevant(url, candidate["lang"])
            source.status = "active" if source.relevant_count > 0 else "validated"
            discovered.append(source)

    # Sort: active sources with relevant articles first
    discovered.sort(
        key=lambda s: (s.status == "active", s.relevant_count, s.reliability),
        reverse=True,
    )

    return discovered


def fetch_from_discovered(source: DiscoveredSource) -> list[dict]:
    """
    Fetch articles from a discovered source.
    Returns list of raw article dicts compatible with data_fetcher.
    """
    try:
        feed = feedparser.parse(
            source.url,
            request_headers={"User-Agent": "ReferendumKG/1.0 (Research Tool)"},
        )
        articles = []
        for entry in feed.entries:
            articles.append({
                "title": getattr(entry, "title", ""),
                "summary": getattr(entry, "summary", getattr(entry, "description", "")),
                "link": getattr(entry, "link", ""),
                "source": source.name,
                "published_parsed": getattr(entry, "published_parsed", None),
            })
        return articles
    except Exception as e:
        logger.error(f"Error fetching {source.name}: {e}")
        return []


def get_discovery_stats(discovered: list[DiscoveredSource]) -> dict:
    """Get summary statistics of discovered sources."""
    active = [s for s in discovered if s.status == "active"]
    validated = [s for s in discovered if s.status == "validated"]
    failed = [s for s in discovered if s.status == "failed"]

    total_articles = sum(s.article_count for s in discovered)
    total_relevant = sum(s.relevant_count for s in discovered)

    return {
        "total_discovered": len(discovered),
        "active": len(active),
        "validated": len(validated),
        "failed": len(failed),
        "total_articles": total_articles,
        "total_relevant": total_relevant,
        "sources_by_language": {
            "it": len([s for s in discovered if s.language == "it"]),
            "en": len([s for s in discovered if s.language == "en"]),
        },
    }
