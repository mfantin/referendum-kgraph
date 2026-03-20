"""
Data fetcher: RSS feeds, article filtering, sentiment analysis, entity extraction.
"""

import re
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests

import config

logger = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    summary: str
    source: str
    url: str
    published: datetime
    relevance: float
    sentiment_score: float  # -1.0 (strong NO) to +1.0 (strong SI)
    sentiment_direction: str  # "SI", "NO", "NEUTRAL"
    mentioned_entities: list[str] = field(default_factory=list)
    mentioned_parties: list[str] = field(default_factory=list)
    poll_data: Optional[dict] = None
    language: str = "it"
    platform: str = "rss"  # "rss", "reddit", "telegram", "bluesky", "mastodon", "youtube"
    engagement_score: Optional[float] = None  # normalized 0-1 (upvotes, views, likes)


@dataclass
class FeedStatus:
    name: str
    url: str
    last_fetch: Optional[datetime] = None
    success: bool = False
    article_count: int = 0
    relevant_count: int = 0
    error: Optional[str] = None


def _clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _parse_date(entry) -> datetime:
    """Parse date from a feedparser entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    return datetime.now(timezone.utc)


def compute_relevance(title: str, summary: str, language: str = "it") -> float:
    """Score relevance of an article to the referendum (0.0 - 1.0)."""
    text = (title + " " + summary).lower()
    keywords = config.REFERENDUM_KEYWORDS_IT if language == "it" else config.REFERENDUM_KEYWORDS_EN

    hits = 0
    max_possible = len(keywords)
    for kw in keywords:
        if kw.lower() in text:
            hits += 1

    if max_possible == 0:
        return 0.0

    # Title matches count double
    title_lower = title.lower()
    title_hits = sum(1 for kw in keywords if kw.lower() in title_lower)
    hits += title_hits

    score = min(1.0, hits / max(max_possible * 0.15, 1))
    return round(score, 3)


def _detect_negation(text_lower: str, keyword: str, window: int = 4) -> bool:
    """
    Check if a keyword is preceded by a negation within a word window.
    E.g. "non è una buona riforma" -> negates "buona riforma".
    """
    NEGATIONS = [
        "non", "no", "nessun", "nessuna", "nessuno", "mai", "né", "ne ",
        "senza", "mica", "neppure", "nemmeno", "neanche",
        "not", "no", "never", "neither", "nor", "without",
    ]
    pos = text_lower.find(keyword)
    if pos < 0:
        return False
    # Look at the text before the keyword (up to `window` words back)
    prefix = text_lower[max(0, pos - 60):pos].strip()
    prefix_words = prefix.split()[-window:]
    return any(neg in prefix_words for neg in NEGATIONS)


def analyze_sentiment(text: str) -> tuple[float, str]:
    """
    Analyze sentiment direction (SI vs NO) using keyword matching
    with negation detection. Returns (score, direction) where score is -1.0 to +1.0.
    """
    text_lower = text.lower()

    si_hits = 0
    no_hits = 0

    for kw in config.SENTIMENT_SI:
        if kw in text_lower:
            if _detect_negation(text_lower, kw):
                # Negated SI keyword -> counts as NO signal
                no_hits += 1
            else:
                si_hits += 1

    for kw in config.SENTIMENT_NO:
        if kw in text_lower:
            if _detect_negation(text_lower, kw):
                # Negated NO keyword -> counts as SI signal
                si_hits += 1
            else:
                no_hits += 1

    total = si_hits + no_hits
    if total == 0:
        return 0.0, "NEUTRAL"

    score = (si_hits - no_hits) / total

    # Lower threshold: even a slight lean counts as directional
    if score > 0.05:
        direction = "SI"
    elif score < -0.05:
        direction = "NO"
    else:
        direction = "NEUTRAL"

    # Boost score magnitude when there are many keyword hits
    magnitude_boost = min(2.0, 1.0 + total * 0.1)
    boosted_score = max(-1.0, min(1.0, score * magnitude_boost))

    return round(boosted_score, 3), direction


def extract_entities(text: str) -> tuple[list[str], list[str]]:
    """
    Extract mentioned politicians and parties from text.
    Returns (politicians, parties).
    """
    text_lower = text.lower()
    politicians = []
    parties = []

    for kw, info in config.POLITICIAN_KEYWORDS.items():
        if kw in text_lower:
            politicians.append(info["name"])

    for kw, party_id in config.PARTY_KEYWORDS.items():
        if len(kw) > 2 and kw in text_lower:  # Skip very short abbreviations
            if party_id not in parties:
                parties.append(party_id)

    return politicians, parties


def extract_poll_numbers(text: str) -> Optional[dict]:
    """
    Try to extract poll SI/NO percentages from article text.
    Returns dict with si_pct, no_pct or None.
    """
    text_lower = text.lower()

    # Pattern: "sì XX%" or "si XX%"
    si_match = re.search(r"s[iì]\s*(?:al\s*)?(\d{1,2}[.,]?\d?)\s*%", text_lower)
    no_match = re.search(r"no\s*(?:al\s*)?(\d{1,2}[.,]?\d?)\s*%", text_lower)

    if si_match and no_match:
        try:
            si_pct = float(si_match.group(1).replace(",", "."))
            no_pct = float(no_match.group(1).replace(",", "."))
            if 20 < si_pct < 80 and 20 < no_pct < 80 and abs(si_pct + no_pct - 100) < 5:
                return {"si_pct": si_pct, "no_pct": no_pct, "extracted_from": "article_text"}
        except ValueError:
            pass

    return None


def fetch_single_feed(feed_name: str, feed_config: dict) -> tuple[list[Article], FeedStatus]:
    """Fetch and process a single RSS feed."""
    status = FeedStatus(
        name=feed_name,
        url=feed_config["url"],
    )
    articles = []

    try:
        feed = feedparser.parse(
            feed_config["url"],
            request_headers={"User-Agent": "ReferendumKG/1.0 (Research Tool)"},
        )

        if feed.bozo and not feed.entries:
            status.error = str(feed.bozo_exception)[:100] if hasattr(feed, "bozo_exception") else "Feed parse error"
            status.last_fetch = datetime.now(timezone.utc)
            return articles, status

        language = feed_config.get("language", "it")
        status.article_count = len(feed.entries)

        for entry in feed.entries:
            title = _clean_html(getattr(entry, "title", ""))
            summary = _clean_html(getattr(entry, "summary", getattr(entry, "description", "")))
            link = getattr(entry, "link", "")

            relevance = compute_relevance(title, summary, language)
            if relevance < 0.1:
                continue

            full_text = title + " " + summary
            sentiment_score, sentiment_dir = analyze_sentiment(full_text)
            politicians, parties = extract_entities(full_text)
            poll_data = extract_poll_numbers(full_text)

            article = Article(
                title=title,
                summary=summary[:500],
                source=feed_name,
                url=link,
                published=_parse_date(entry),
                relevance=relevance,
                sentiment_score=sentiment_score,
                sentiment_direction=sentiment_dir,
                mentioned_entities=politicians,
                mentioned_parties=parties,
                poll_data=poll_data,
                language=language,
            )
            articles.append(article)

        status.relevant_count = len(articles)
        status.success = True

    except requests.exceptions.RequestException as e:
        status.error = f"Network error: {str(e)[:80]}"
    except Exception as e:
        status.error = f"Error: {str(e)[:80]}"

    status.last_fetch = datetime.now(timezone.utc)
    return articles, status


def fetch_all_feeds(extra_feeds: dict | None = None) -> tuple[list[Article], list[FeedStatus]]:
    """
    Fetch all configured RSS feeds + any discovered extras + direct social platforms.
    """
    all_articles = []
    all_statuses = []

    # Configured feeds
    for feed_name, feed_config in config.RSS_FEEDS.items():
        articles, status = fetch_single_feed(feed_name, feed_config)
        all_articles.extend(articles)
        all_statuses.append(status)

    # Extra discovered feeds
    if extra_feeds:
        for feed_name, feed_config in extra_feeds.items():
            articles, status = fetch_single_feed(feed_name, feed_config)
            all_articles.extend(articles)
            all_statuses.append(status)

    # Direct social platform fetchers (Reddit JSON, Telegram, Bluesky, Mastodon)
    try:
        from social_fetchers import fetch_all_social
        social_articles, social_statuses = fetch_all_social()
        all_articles.extend(social_articles)
        all_statuses.extend(social_statuses)
    except Exception as e:
        logger.error(f"Social fetchers failed: {e}")

    # Sort by relevance * recency (engagement boosts social content)
    now = datetime.now(timezone.utc)
    all_articles.sort(
        key=lambda a: (
            a.relevance
            * max(0.1, 1.0 - (now - a.published).total_seconds() / 86400)
            * (1.0 + (a.engagement_score or 0.0) * 0.5)
        ),
        reverse=True,
    )

    # Limit to MAX_ARTICLES
    all_articles = all_articles[: config.MAX_ARTICLES]

    return all_articles, all_statuses


def get_all_polls(articles: list[Article]) -> list[dict]:
    """Combine known polls with any extracted from articles."""
    polls = list(config.KNOWN_POLLS)

    seen_sources = {(p["source"], p["date"]) for p in polls}
    for article in articles:
        if article.poll_data:
            key = (article.source, article.published.strftime("%Y-%m-%d"))
            if key not in seen_sources:
                polls.append({
                    "source": article.source,
                    "date": article.published.strftime("%Y-%m-%d"),
                    "si_pct": article.poll_data["si_pct"],
                    "no_pct": article.poll_data["no_pct"],
                    "sample_size": None,
                    "note": "Estratto da articolo",
                })
                seen_sources.add(key)

    polls.sort(key=lambda p: p["date"], reverse=True)
    return polls
