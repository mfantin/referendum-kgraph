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
# --- Multi-agent discovery: each "agent" scans from a different angle ---

# Agent 1: Italian mainstream media
_AGENT_ITALIAN_MEDIA = [
    {"name": "AGI Politica", "url": "https://www.agi.it/politica/rss", "lang": "it", "reliability": 0.8},
    {"name": "Adnkronos Politica", "url": "https://www.adnkronos.com/rss/politica", "lang": "it", "reliability": 0.75},
    {"name": "Rainews Politica", "url": "https://www.rainews.it/rss/politica", "lang": "it", "reliability": 0.85},
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
    {"name": "Quotidiano.net", "url": "https://www.quotidiano.net/rss/politica.xml", "lang": "it", "reliability": 0.7},
    {"name": "TPI News", "url": "https://www.tpi.it/feed", "lang": "it", "reliability": 0.65},
    {"name": "Today.it Politica", "url": "https://www.today.it/rss/politica.xml", "lang": "it", "reliability": 0.6},
    {"name": "Avvenire", "url": "https://www.avvenire.it/rss/politica", "lang": "it", "reliability": 0.75},
    {"name": "Il Manifesto", "url": "https://ilmanifesto.it/feed", "lang": "it", "reliability": 0.65},
]

# Agent 2: International & European media
_AGENT_INTERNATIONAL = [
    {"name": "Reuters World", "url": "https://www.reutersagency.com/feed/", "lang": "en", "reliability": 0.9},
    {"name": "The Guardian Europe", "url": "https://www.theguardian.com/world/europe-news/rss", "lang": "en", "reliability": 0.85},
    {"name": "Politico EU", "url": "https://www.politico.eu/feed/", "lang": "en", "reliability": 0.85},
    {"name": "France24 Europe", "url": "https://www.france24.com/en/europe/rss", "lang": "en", "reliability": 0.8},
    {"name": "DW Europe", "url": "https://rss.dw.com/xml/rss-en-eu", "lang": "en", "reliability": 0.8},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "lang": "en", "reliability": 0.75},
    {"name": "EUobserver", "url": "https://euobserver.com/rss.xml", "lang": "en", "reliability": 0.8},
    {"name": "The Local Italy", "url": "https://www.thelocal.it/feed/", "lang": "en", "reliability": 0.75},
    {"name": "Euractiv", "url": "https://www.euractiv.com/feed/", "lang": "en", "reliability": 0.8},
    {"name": "ANSA English", "url": "https://www.ansa.it/english/news/politics_rss.xml", "lang": "en", "reliability": 0.85},
    {"name": "NPR World", "url": "https://feeds.npr.org/1004/rss.xml", "lang": "en", "reliability": 0.8},
    {"name": "AP News", "url": "https://rsshub.app/apnews/topics/world-news", "lang": "en", "reliability": 0.9},
    {"name": "Le Monde Europe", "url": "https://www.lemonde.fr/europe/rss_full.xml", "lang": "fr", "reliability": 0.85},
    {"name": "El Pais International", "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/english.elpais.com/portada", "lang": "en", "reliability": 0.8},
]

# Agent 3: Google News multi-query (most reliable for volume)
_AGENT_GOOGLE_NEWS = [
    {"name": "GNews: referendum italia 2026", "url": "https://news.google.com/rss/search?q=referendum+italia+2026&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.7},
    {"name": "GNews: riforma nordio", "url": "https://news.google.com/rss/search?q=riforma+nordio+referendum&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.7},
    {"name": "GNews: separazione carriere", "url": "https://news.google.com/rss/search?q=separazione+carriere+magistratura&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.7},
    {"name": "GNews: CSM riforma", "url": "https://news.google.com/rss/search?q=CSM+riforma+costituzionale&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.65},
    {"name": "GNews: referendum sondaggi", "url": "https://news.google.com/rss/search?q=referendum+sondaggi+marzo+2026&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.7},
    {"name": "GNews: voto referendum giustizia", "url": "https://news.google.com/rss/search?q=voto+referendum+giustizia+marzo&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.65},
    {"name": "GNews: referendum si no", "url": "https://news.google.com/rss/search?q=referendum+%22si%22+%22no%22+riforma&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.65},
    {"name": "GNews: affluenza referendum", "url": "https://news.google.com/rss/search?q=affluenza+referendum+2026&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.65},
    {"name": "GNews EN: italy referendum", "url": "https://news.google.com/rss/search?q=italy+referendum+2026&hl=en&gl=US&ceid=US:en", "lang": "en", "reliability": 0.7},
    {"name": "GNews EN: italy justice reform", "url": "https://news.google.com/rss/search?q=italy+justice+reform+vote&hl=en&gl=US&ceid=US:en", "lang": "en", "reliability": 0.65},
    {"name": "GNews EN: italy constitutional", "url": "https://news.google.com/rss/search?q=italy+constitutional+referendum+march&hl=en&gl=US&ceid=US:en", "lang": "en", "reliability": 0.65},
]

# Agent 4: Social media & community
_AGENT_SOCIAL = [
    {"name": "Reddit r/italy referendum", "url": "https://www.reddit.com/r/italy/search.rss?q=referendum&sort=new&restrict_sr=on", "lang": "it", "reliability": 0.5},
    {"name": "Reddit r/italy nordio", "url": "https://www.reddit.com/r/italy/search.rss?q=nordio+OR+magistratura&sort=new&restrict_sr=on", "lang": "it", "reliability": 0.45},
    {"name": "Reddit r/europe italy", "url": "https://www.reddit.com/r/europe/search.rss?q=italy+referendum&sort=new&restrict_sr=on", "lang": "en", "reliability": 0.45},
    {"name": "Reddit r/italypolitics", "url": "https://www.reddit.com/r/italypolitics/new.rss", "lang": "it", "reliability": 0.4},
    {"name": "Reddit r/worldnews italy", "url": "https://www.reddit.com/r/worldnews/search.rss?q=italy+referendum&sort=new&restrict_sr=on", "lang": "en", "reliability": 0.45},
]

# Agent 5: Legal & institutional sources
_AGENT_INSTITUTIONAL = [
    {"name": "Camera dei Deputati News", "url": "https://www.camera.it/leg19/1132", "lang": "it", "reliability": 0.95},
    {"name": "ANM (magistrati)", "url": "https://www.associazionemagistrati.it/feed", "lang": "it", "reliability": 0.7},
    {"name": "Altalex", "url": "https://www.altalex.com/rss", "lang": "it", "reliability": 0.75},
    {"name": "Diritto.it", "url": "https://www.diritto.it/feed/", "lang": "it", "reliability": 0.7},
    {"name": "Questione Giustizia", "url": "https://www.questionegiustizia.it/rss.xml", "lang": "it", "reliability": 0.75},
]

# Agent 6: Exit Poll & Results (active after voting ends)
_AGENT_EXIT_POLL = [
    {"name": "GNews: exit poll referendum", "url": "https://news.google.com/rss/search?q=exit+poll+referendum+2026&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.8},
    {"name": "GNews: prime proiezioni referendum", "url": "https://news.google.com/rss/search?q=proiezioni+referendum+risultati+2026&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.8},
    {"name": "GNews: risultati referendum giustizia", "url": "https://news.google.com/rss/search?q=risultati+referendum+giustizia+nordio&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.8},
    {"name": "GNews: spoglio referendum 2026", "url": "https://news.google.com/rss/search?q=spoglio+scrutinio+referendum+2026&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.8},
    {"name": "GNews: affluenza referendum 23 marzo", "url": "https://news.google.com/rss/search?q=affluenza+referendum+23+marzo+2026&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.75},
    {"name": "GNews: consorzio opinio exit poll", "url": "https://news.google.com/rss/search?q=consorzio+opinio+exit+poll+referendum&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.85},
    {"name": "GNews: youtrend proiezioni referendum", "url": "https://news.google.com/rss/search?q=youtrend+quorum+proiezioni+referendum&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.85},
    {"name": "GNews: tecnè swg exit poll", "url": "https://news.google.com/rss/search?q=tecn%C3%A8+OR+swg+OR+piepoli+exit+poll+referendum&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.8},
    {"name": "GNews EN: italy referendum exit poll", "url": "https://news.google.com/rss/search?q=italy+referendum+exit+poll+results+2026&hl=en&gl=US&ceid=US:en", "lang": "en", "reliability": 0.75},
    {"name": "GNews EN: italy referendum results", "url": "https://news.google.com/rss/search?q=italy+constitutional+referendum+results&hl=en&gl=US&ceid=US:en", "lang": "en", "reliability": 0.75},
]

# All agents combined
CANDIDATE_FEEDS = (
    _AGENT_ITALIAN_MEDIA
    + _AGENT_INTERNATIONAL
    + _AGENT_GOOGLE_NEWS
    + _AGENT_SOCIAL
    + _AGENT_INSTITUTIONAL
    + _AGENT_EXIT_POLL
)

# Agent names for dashboard display
DISCOVERY_AGENTS = {
    "Media Italiani": len(_AGENT_ITALIAN_MEDIA),
    "Media Internazionali": len(_AGENT_INTERNATIONAL),
    "Google News (multi-query)": len(_AGENT_GOOGLE_NEWS),
    "Social & Community": len(_AGENT_SOCIAL),
    "Fonti Istituzionali": len(_AGENT_INSTITUTIONAL),
    "Exit Poll & Risultati": len(_AGENT_EXIT_POLL),
}


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
    max_new: int = 50,
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
