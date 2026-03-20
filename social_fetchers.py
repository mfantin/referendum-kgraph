"""
Direct social platform fetchers: Reddit JSON, Telegram scraping,
Bluesky public API, Mastodon public API.

All methods work without API keys, using only public endpoints.
"""

import re
import time
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

import config
from data_fetcher import (
    Article,
    FeedStatus,
    compute_relevance,
    analyze_sentiment,
    extract_entities,
    extract_poll_numbers,
    _clean_html,
)

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "ReferendumKG/1.0 (research project)"}
_TIMEOUT = getattr(config, "SOCIAL_FETCH_TIMEOUT", 10)
_RATE_DELAY = getattr(config, "SOCIAL_RATE_LIMIT_DELAY", 2.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_engagement(value: float, scale: float = 500.0) -> float:
    """Normalize an engagement metric (upvotes, views, likes) to 0-1 range."""
    if value <= 0:
        return 0.0
    return round(min(1.0, value / scale), 3)


def _make_article(
    title: str,
    summary: str,
    source: str,
    url: str,
    published: datetime,
    language: str,
    platform: str,
    engagement: Optional[float] = None,
) -> Optional[Article]:
    """Build an Article if it passes the relevance threshold."""
    relevance = compute_relevance(title, summary, language)
    if relevance < 0.05:
        return None

    full_text = title + " " + summary
    sentiment_score, sentiment_dir = analyze_sentiment(full_text)
    politicians, parties = extract_entities(full_text)
    poll_data = extract_poll_numbers(full_text)

    return Article(
        title=title,
        summary=summary[:500],
        source=source,
        url=url,
        published=published,
        relevance=relevance,
        sentiment_score=sentiment_score,
        sentiment_direction=sentiment_dir,
        mentioned_entities=politicians,
        mentioned_parties=parties,
        poll_data=poll_data,
        language=language,
        platform=platform,
        engagement_score=engagement,
    )


# ---------------------------------------------------------------------------
# 1. Reddit JSON API
# ---------------------------------------------------------------------------

def fetch_reddit(
    searches: Optional[dict] = None,
) -> tuple[list[Article], list[FeedStatus]]:
    """
    Fetch posts from Reddit using the public JSON API (.json suffix).
    Returns richer data than RSS: score, num_comments, full selftext.
    """
    if searches is None:
        searches = getattr(config, "REDDIT_SEARCHES", {})

    articles: list[Article] = []
    statuses: list[FeedStatus] = []
    seen_urls: set[str] = set()

    for subreddit, sub_config in searches.items():
        queries = sub_config.get("queries", [])
        lang = sub_config.get("lang", "it")
        reliability = sub_config.get("reliability", 0.5)

        for query in queries:
            source_name = f"Reddit {subreddit}: {query}"
            status = FeedStatus(
                name=source_name,
                url=f"https://www.reddit.com/{subreddit}/search.json?q={query}",
            )

            try:
                url = (
                    f"https://www.reddit.com/{subreddit}/search.json"
                    f"?q={requests.utils.quote(query)}&sort=new&restrict_sr=on&limit=25"
                )
                resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()

                children = data.get("data", {}).get("children", [])
                status.article_count = len(children)

                for child in children:
                    post = child.get("data", {})
                    permalink = f"https://www.reddit.com{post.get('permalink', '')}"
                    if permalink in seen_urls:
                        continue
                    seen_urls.add(permalink)

                    title = post.get("title", "")
                    selftext = post.get("selftext", "")[:1000]
                    score = post.get("score", 0)
                    num_comments = post.get("num_comments", 0)
                    created = post.get("created_utc", 0)

                    published = datetime.fromtimestamp(created, tz=timezone.utc) if created else datetime.now(timezone.utc)
                    engagement = _normalize_engagement(score + num_comments * 2, scale=500)

                    article = _make_article(
                        title=title,
                        summary=_clean_html(selftext) if selftext else title,
                        source=f"Reddit {subreddit}",
                        url=permalink,
                        published=published,
                        language=lang,
                        platform="reddit",
                        engagement=engagement,
                    )
                    if article:
                        articles.append(article)

                status.relevant_count = len([a for a in articles if a.source == f"Reddit {subreddit}"])
                status.success = True

            except requests.exceptions.RequestException as e:
                status.error = f"Network error: {str(e)[:80]}"
            except Exception as e:
                status.error = f"Error: {str(e)[:80]}"

            status.last_fetch = datetime.now(timezone.utc)
            statuses.append(status)

            # Rate limit: Reddit requires ~2s between unauthenticated requests
            time.sleep(_RATE_DELAY)

    return articles, statuses


# ---------------------------------------------------------------------------
# 2. Telegram public channel scraper
# ---------------------------------------------------------------------------

def fetch_telegram(
    channels: Optional[dict] = None,
) -> tuple[list[Article], list[FeedStatus]]:
    """
    Scrape public Telegram channels via t.me/s/ (no auth needed).
    Extracts message text, timestamps, and view counts.
    """
    if channels is None:
        channels = getattr(config, "TELEGRAM_CHANNELS", {})

    articles: list[Article] = []
    statuses: list[FeedStatus] = []

    for channel_id, ch_config in channels.items():
        label = ch_config.get("label", channel_id)
        lang = ch_config.get("lang", "it")
        source_name = f"Telegram @{channel_id}"
        page_url = f"https://t.me/s/{channel_id}"

        status = FeedStatus(name=source_name, url=page_url)

        try:
            resp = requests.get(page_url, headers=_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            messages = soup.select("div.tgme_widget_message_bubble")
            status.article_count = len(messages)

            for msg in messages:
                # Extract text
                text_el = msg.select_one("div.tgme_widget_message_text")
                if not text_el:
                    continue
                text = _clean_html(text_el.get_text(separator=" "))
                if not text or len(text) < 15:
                    continue

                # Extract timestamp
                time_el = msg.select_one("time.datetime")
                if not time_el:
                    time_el = msg.select_one("a.tgme_widget_message_date > time")
                published = datetime.now(timezone.utc)
                if time_el and time_el.get("datetime"):
                    try:
                        published = datetime.fromisoformat(
                            time_el["datetime"].replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                # Extract link
                link_el = msg.select_one("a.tgme_widget_message_date")
                link = link_el["href"] if link_el and link_el.get("href") else page_url

                # Extract view count
                views_el = msg.select_one("span.tgme_widget_message_views")
                views = 0
                if views_el:
                    views_text = views_el.get_text().strip().upper()
                    try:
                        if "K" in views_text:
                            views = int(float(views_text.replace("K", "")) * 1000)
                        elif "M" in views_text:
                            views = int(float(views_text.replace("M", "")) * 1_000_000)
                        else:
                            views = int(views_text)
                    except (ValueError, TypeError):
                        views = 0

                engagement = _normalize_engagement(views, scale=10000)

                # Use first ~80 chars as "title", rest as summary
                title = text[:80].rsplit(" ", 1)[0] + "..." if len(text) > 80 else text
                summary = text

                article = _make_article(
                    title=title,
                    summary=summary,
                    source=source_name,
                    url=link,
                    published=published,
                    language=lang,
                    platform="telegram",
                    engagement=engagement,
                )
                if article:
                    articles.append(article)

            status.relevant_count = len([a for a in articles if a.source == source_name])
            status.success = True

        except requests.exceptions.RequestException as e:
            status.error = f"Network error: {str(e)[:80]}"
        except Exception as e:
            status.error = f"Error: {str(e)[:80]}"

        status.last_fetch = datetime.now(timezone.utc)
        statuses.append(status)

    return articles, statuses


# ---------------------------------------------------------------------------
# 3. Bluesky public API
# ---------------------------------------------------------------------------

def fetch_bluesky(
    queries: Optional[list[str]] = None,
) -> tuple[list[Article], list[FeedStatus]]:
    """
    Search Bluesky posts via the public AT Protocol API (no auth needed).
    Endpoint: public.api.bsky.app/xrpc/app.bsky.feed.searchPosts
    """
    if queries is None:
        queries = getattr(config, "BLUESKY_QUERIES", [])

    reliability = getattr(config, "BLUESKY_RELIABILITY", 0.4)
    articles: list[Article] = []
    statuses: list[FeedStatus] = []
    seen_uris: set[str] = set()

    for query in queries:
        source_name = f"Bluesky: {query}"
        api_url = (
            f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
            f"?q={requests.utils.quote(query)}&limit=25&sort=latest"
        )
        status = FeedStatus(name=source_name, url=api_url)

        try:
            resp = requests.get(api_url, headers=_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            posts = data.get("posts", [])
            status.article_count = len(posts)

            for post in posts:
                uri = post.get("uri", "")
                if uri in seen_uris:
                    continue
                seen_uris.add(uri)

                record = post.get("record", {})
                text = record.get("text", "")
                if not text:
                    continue

                # Build web permalink
                author = post.get("author", {})
                handle = author.get("handle", "unknown")
                # URI format: at://did:plc:.../app.bsky.feed.post/rkey
                rkey = uri.rsplit("/", 1)[-1] if "/" in uri else ""
                permalink = f"https://bsky.app/profile/{handle}/post/{rkey}"

                # Parse timestamp
                created_at = record.get("createdAt", "")
                published = datetime.now(timezone.utc)
                if created_at:
                    try:
                        published = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                # Engagement
                like_count = post.get("likeCount", 0)
                repost_count = post.get("repostCount", 0)
                reply_count = post.get("replyCount", 0)
                engagement = _normalize_engagement(
                    like_count + repost_count * 2 + reply_count, scale=200
                )

                # Detect language (prefer Italian)
                langs = record.get("langs", [])
                lang = "it" if "it" in langs else ("en" if "en" in langs else "it")

                title = text[:80].rsplit(" ", 1)[0] + "..." if len(text) > 80 else text

                article = _make_article(
                    title=title,
                    summary=text,
                    source="Bluesky",
                    url=permalink,
                    published=published,
                    language=lang,
                    platform="bluesky",
                    engagement=engagement,
                )
                if article:
                    articles.append(article)

            status.relevant_count = len(posts)
            status.success = True

        except requests.exceptions.RequestException as e:
            status.error = f"Network error: {str(e)[:80]}"
        except Exception as e:
            status.error = f"Error: {str(e)[:80]}"

        status.last_fetch = datetime.now(timezone.utc)
        statuses.append(status)

    return articles, statuses


# ---------------------------------------------------------------------------
# 4. Mastodon public tag timeline API
# ---------------------------------------------------------------------------

def fetch_mastodon(
    instances: Optional[dict] = None,
) -> tuple[list[Article], list[FeedStatus]]:
    """
    Fetch public tag timelines from Mastodon instances (no auth needed).
    Endpoint: /api/v1/timelines/tag/{hashtag}
    """
    if instances is None:
        instances = getattr(config, "MASTODON_SEARCHES", {})

    articles: list[Article] = []
    statuses: list[FeedStatus] = []
    seen_urls: set[str] = set()

    for instance, inst_config in instances.items():
        tags = inst_config.get("tags", [])
        lang = inst_config.get("lang", "it")

        for tag in tags:
            source_name = f"Mastodon {instance}: #{tag}"
            api_url = f"https://{instance}/api/v1/timelines/tag/{tag}?limit=20"
            status = FeedStatus(name=source_name, url=api_url)

            try:
                resp = requests.get(api_url, headers=_HEADERS, timeout=_TIMEOUT)
                resp.raise_for_status()
                toots = resp.json()

                if not isinstance(toots, list):
                    status.error = "Unexpected API response format"
                    status.last_fetch = datetime.now(timezone.utc)
                    statuses.append(status)
                    continue

                status.article_count = len(toots)

                for toot in toots:
                    toot_url = toot.get("url", "")
                    if toot_url in seen_urls:
                        continue
                    seen_urls.add(toot_url)

                    content_html = toot.get("content", "")
                    text = _clean_html(content_html)
                    if not text or len(text) < 10:
                        continue

                    # Parse timestamp
                    created_at = toot.get("created_at", "")
                    published = datetime.now(timezone.utc)
                    if created_at:
                        try:
                            published = datetime.fromisoformat(
                                created_at.replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            pass

                    # Engagement
                    favs = toot.get("favourites_count", 0)
                    reblogs = toot.get("reblogs_count", 0)
                    replies = toot.get("replies_count", 0)
                    engagement = _normalize_engagement(
                        favs + reblogs * 2 + replies, scale=100
                    )

                    account = toot.get("account", {})
                    display_name = account.get("display_name", "")
                    title = text[:80].rsplit(" ", 1)[0] + "..." if len(text) > 80 else text

                    article = _make_article(
                        title=title,
                        summary=text,
                        source=f"Mastodon @{display_name}@{instance}" if display_name else f"Mastodon {instance}",
                        url=toot_url,
                        published=published,
                        language=lang,
                        platform="mastodon",
                        engagement=engagement,
                    )
                    if article:
                        articles.append(article)

                status.relevant_count = len([a for a in articles if source_name in a.source or instance in a.source])
                status.success = True

            except requests.exceptions.RequestException as e:
                status.error = f"Network error: {str(e)[:80]}"
            except Exception as e:
                status.error = f"Error: {str(e)[:80]}"

            status.last_fetch = datetime.now(timezone.utc)
            statuses.append(status)

    return articles, statuses


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def fetch_all_social() -> tuple[list[Article], list[FeedStatus]]:
    """
    Run all direct social fetchers and return combined results.
    Gracefully handles failures on individual platforms.
    """
    all_articles: list[Article] = []
    all_statuses: list[FeedStatus] = []

    fetchers = [
        ("Reddit", fetch_reddit),
        ("Telegram", fetch_telegram),
        ("Bluesky", fetch_bluesky),
        ("Mastodon", fetch_mastodon),
    ]

    for name, fetcher in fetchers:
        try:
            arts, stats = fetcher()
            all_articles.extend(arts)
            all_statuses.extend(stats)
            logger.info(f"[Social] {name}: {len(arts)} articles from {len(stats)} sources")
        except Exception as e:
            logger.error(f"[Social] {name} fetcher failed: {e}")
            all_statuses.append(FeedStatus(
                name=f"{name} (failed)",
                url="",
                last_fetch=datetime.now(timezone.utc),
                success=False,
                error=str(e)[:100],
            ))

    return all_articles, all_statuses


def get_social_stats(articles: list[Article]) -> dict:
    """Get breakdown of social articles by platform."""
    platforms: dict[str, dict] = {}
    for a in articles:
        if a.platform == "rss":
            continue
        p = a.platform
        if p not in platforms:
            platforms[p] = {
                "count": 0,
                "si": 0,
                "no": 0,
                "neutral": 0,
                "avg_engagement": 0.0,
                "total_engagement": 0.0,
            }
        platforms[p]["count"] += 1
        platforms[p][a.sentiment_direction.lower()] = platforms[p].get(a.sentiment_direction.lower(), 0) + 1
        if a.engagement_score:
            platforms[p]["total_engagement"] += a.engagement_score

    for p, stats in platforms.items():
        if stats["count"] > 0:
            stats["avg_engagement"] = round(stats["total_engagement"] / stats["count"], 3)

    return platforms
