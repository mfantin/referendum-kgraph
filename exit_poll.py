"""
Exit Poll module: detects and aggregates exit poll data from articles.
Activates after voting ends (23 March 2026, 15:00).
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import config
from data_fetcher import Article

logger = logging.getLogger(__name__)


@dataclass
class ExitPollResult:
    source: str
    si_pct: float
    no_pct: float
    timestamp: datetime
    reliability: float = 0.5
    is_projection: bool = False  # True if it's a projection (proiezione), not exit poll
    note: str = ""


def is_exit_poll_time() -> bool:
    """Check if we are past the exit poll availability threshold."""
    now = datetime.now(timezone.utc)
    threshold = config.EXIT_POLL_AVAILABLE_AFTER.replace(tzinfo=timezone.utc)
    return now >= threshold


def extract_exit_poll_data(article: Article) -> Optional[ExitPollResult]:
    """
    Try to extract exit poll SI/NO percentages from an article.
    Only processes articles published after voting ends.
    """
    text = (article.title + " " + article.summary).lower()

    # Check if article mentions exit poll keywords
    has_exit_poll_keyword = any(kw in text for kw in config.EXIT_POLL_KEYWORDS)
    if not has_exit_poll_keyword:
        return None

    # Determine if it's a projection vs exit poll
    is_projection = any(kw in text for kw in [
        "proiezione", "proiezioni", "prime proiezioni",
        "spoglio", "scrutinio", "dati reali",
        "risultati parziali", "dati parziali",
    ])

    # Try to extract percentages - multiple patterns
    si_pct = None
    no_pct = None

    # Pattern 1: "sì XX%" / "no XX%"
    si_match = re.search(r"s[iì]\s*(?:al\s*)?(\d{1,2}[.,]\d?)\s*%", text)
    no_match = re.search(r"no\s*(?:al\s*)?(\d{1,2}[.,]\d?)\s*%", text)

    if si_match and no_match:
        try:
            si_pct = float(si_match.group(1).replace(",", "."))
            no_pct = float(no_match.group(1).replace(",", "."))
        except ValueError:
            pass

    # Pattern 2: "XX% sì" / "XX% no" or "XX% per il sì"
    if si_pct is None:
        si_match2 = re.search(r"(\d{1,2}[.,]\d?)\s*%\s*(?:per il\s*)?s[iì]", text)
        no_match2 = re.search(r"(\d{1,2}[.,]\d?)\s*%\s*(?:per il\s*)?no", text)
        if si_match2 and no_match2:
            try:
                si_pct = float(si_match2.group(1).replace(",", "."))
                no_pct = float(no_match2.group(1).replace(",", "."))
            except ValueError:
                pass

    # Pattern 3: "sì tra XX e YY" (range) -> take midpoint
    if si_pct is None:
        si_range = re.search(r"s[iì]\s*(?:tra|fra|a|al)?\s*(?:il\s*)?(\d{1,2}[.,]?\d?)\s*(?:e|ed|-|/)\s*(?:il\s*)?(\d{1,2}[.,]?\d?)\s*%?", text)
        no_range = re.search(r"no\s*(?:tra|fra|a|al)?\s*(?:il\s*)?(\d{1,2}[.,]?\d?)\s*(?:e|ed|-|/)\s*(?:il\s*)?(\d{1,2}[.,]?\d?)\s*%?", text)
        if si_range and no_range:
            try:
                si_low = float(si_range.group(1).replace(",", "."))
                si_high = float(si_range.group(2).replace(",", "."))
                no_low = float(no_range.group(1).replace(",", "."))
                no_high = float(no_range.group(2).replace(",", "."))
                si_pct = (si_low + si_high) / 2
                no_pct = (no_low + no_high) / 2
            except ValueError:
                pass

    # Pattern 4: "No avanti (49/53%)" or "No 49-53%, Sì 47-51%"
    if si_pct is None:
        no_range2 = re.search(r"no\s*(?:avanti|in vantaggio)?\s*\(?(\d{1,2}[.,]?\d?)\s*[/\-]\s*(\d{1,2}[.,]?\d?)\s*%?\)?", text)
        si_range2 = re.search(r"s[iì]\s*(?:a|al|indietro)?\s*\(?(\d{1,2}[.,]?\d?)\s*[/\-]\s*(\d{1,2}[.,]?\d?)\s*%?\)?", text)
        if si_range2 and no_range2:
            try:
                si_low = float(si_range2.group(1).replace(",", "."))
                si_high = float(si_range2.group(2).replace(",", "."))
                no_low = float(no_range2.group(1).replace(",", "."))
                no_high = float(no_range2.group(2).replace(",", "."))
                si_pct = (si_low + si_high) / 2
                no_pct = (no_low + no_high) / 2
            except ValueError:
                pass

    # Pattern 5: "XX/YY%" near "no" and "ZZ/WW%" near "sì" (loose match)
    if si_pct is None:
        ranges = re.findall(r"(\d{1,2}[.,]?\d?)\s*[/\-]\s*(\d{1,2}[.,]?\d?)\s*%", text)
        if len(ranges) >= 2:
            try:
                # Usually first range is for No (mentioned first in exit polls)
                r1 = ((float(ranges[0][0].replace(",","."))+float(ranges[0][1].replace(",",".")))/2)
                r2 = ((float(ranges[1][0].replace(",","."))+float(ranges[1][1].replace(",",".")))/2)
                # Determine which is SI and which is NO from context
                first_range_pos = text.find(ranges[0][0])
                no_before = text.rfind("no", 0, first_range_pos + 20)
                si_before = text.rfind("s\u00ec", 0, first_range_pos + 20) if "s\u00ec" in text[:first_range_pos+20] else text.rfind("si ", 0, first_range_pos + 20)
                if no_before >= 0 and (si_before < 0 or no_before > si_before):
                    no_pct = r1
                    si_pct = r2
                else:
                    si_pct = r1
                    no_pct = r2
            except (ValueError, IndexError):
                pass

    if si_pct is None or no_pct is None:
        return None

    # Sanity checks
    if not (15 < si_pct < 85 and 15 < no_pct < 85):
        return None
    if abs(si_pct + no_pct - 100) > 10:
        return None

    # Determine source reliability
    reliability = 0.5
    source_lower = article.source.lower() + " " + text
    for known_source in config.EXIT_POLL_SOURCES:
        if known_source.lower().split("(")[0].strip().lower() in source_lower:
            reliability = 0.8
            break

    if is_projection:
        reliability = min(reliability + 0.1, 0.95)  # Projections are more reliable

    # Build note
    note_parts = []
    if is_projection:
        note_parts.append("Proiezione")
    else:
        note_parts.append("Exit poll")
    note_parts.append(f"da {article.source}")

    return ExitPollResult(
        source=article.source,
        si_pct=round(si_pct, 1),
        no_pct=round(no_pct, 1),
        timestamp=article.published,
        reliability=reliability,
        is_projection=is_projection,
        note=" - ".join(note_parts),
    )


# Known exit poll results (hardcoded as fallback when RSS doesn't capture them)
KNOWN_EXIT_POLLS = [
    # Proiezioni reali con dati di spoglio (aggiornati 23/03 ore 17:00+)
    {
        "source": "Consorzio Opinio/Rai (2a proiezione)",
        "si_pct": 46.1,
        "no_pct": 53.9,
        "reliability": 0.95,
        "is_projection": True,
        "note": "2a proiezione Opinio/Rai, copertura 37% (fonte: affaritaliani.it)",
    },
    {
        "source": "Tecnè (2a proiezione Mediaset)",
        "si_pct": 46.0,
        "no_pct": 54.0,
        "reliability": 0.93,
        "is_projection": True,
        "note": "2a proiezione Tecnè: SI 46%, NO 54% (fonte: tgcom24.mediaset.it)",
    },
    {
        "source": "Dati reali spoglio (12.014/61.533 sezioni)",
        "si_pct": 45.62,
        "no_pct": 54.38,
        "reliability": 0.98,
        "is_projection": True,
        "note": "Dati reali scrutinio: SI 45.62%, NO 54.38% su 12.014 sezioni (fonte: quotidiano.net)",
    },
]


def collect_exit_polls(articles: list[Article]) -> list[ExitPollResult]:
    """
    Scan all articles for exit poll data.
    Falls back to KNOWN_EXIT_POLLS if nothing found in articles.
    Returns list of ExitPollResult sorted by reliability and recency.
    """
    if not is_exit_poll_time():
        return []

    results = []
    seen = set()

    for article in articles:
        ep = extract_exit_poll_data(article)
        if ep:
            # Deduplicate by source
            key = (ep.source, round(ep.si_pct))
            if key not in seen:
                results.append(ep)
                seen.add(key)

    # If no exit polls found from articles, use known data
    if not results:
        now = datetime.now(timezone.utc)
        for known in KNOWN_EXIT_POLLS:
            results.append(ExitPollResult(
                source=known["source"],
                si_pct=known["si_pct"],
                no_pct=known["no_pct"],
                timestamp=now,
                reliability=known["reliability"],
                is_projection=known["is_projection"],
                note=known["note"],
            ))

    # Sort: projections first, then by reliability, then by recency
    results.sort(key=lambda r: (r.is_projection, r.reliability, r.timestamp.timestamp()),
                 reverse=True)

    return results


def aggregate_exit_polls(exit_polls: list[ExitPollResult]) -> dict:
    """
    Compute weighted average of exit poll results.
    Returns dict with si_pct, no_pct, confidence, count.
    """
    if not exit_polls:
        return {"si_pct": 50.0, "no_pct": 50.0, "confidence": 0.0, "count": 0}

    total_weight = 0.0
    weighted_si = 0.0

    for ep in exit_polls:
        w = ep.reliability
        weighted_si += ep.si_pct * w
        total_weight += w

    if total_weight == 0:
        return {"si_pct": 50.0, "no_pct": 50.0, "confidence": 0.0, "count": 0}

    si_avg = weighted_si / total_weight
    no_avg = 100.0 - si_avg

    # Confidence grows with number and quality of sources
    confidence = min(0.9, len(exit_polls) * 0.15 + sum(ep.reliability for ep in exit_polls) * 0.1)

    return {
        "si_pct": round(si_avg, 1),
        "no_pct": round(no_avg, 1),
        "confidence": round(confidence, 3),
        "count": len(exit_polls),
    }
