"""
Fetcher dati affluenza dal Ministero dell'Interno (eligendo.it).
Scrapes the official turnout page for the 2026 constitutional referendum.
Falls back to data extracted from news articles if eligendo is unavailable.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "ReferendumKG/1.0 (research project)"}
_TIMEOUT = 15

# Eligendo.it base URLs (patterns from past referendums)
# Real URL pattern from Ministero dell'Interno (eligendo)
ELIGENDO_URLS = [
    # Votanti (affluenza) - Italia, tutte le ripartizioni
    "https://elezioni.interno.gov.it/risultati/20260322/referendum/votanti/italia",
    "https://elezioni.interno.gov.it/risultati/20260323/referendum/votanti/italia",
    # Ripartizioni specifiche (01 = Nord-Ovest, etc.)
    "https://elezioni.interno.gov.it/risultati/20260322/referendum/votanti/italia/01",
    "https://elezioni.interno.gov.it/risultati/20260323/referendum/votanti/italia/01",
    # Fallback: vecchio pattern
    "https://elezioni.interno.gov.it/referendum/affluenza/20260322",
    "https://elezioni.interno.gov.it/referendum/affluenza/20260323",
]

# Official detection times for Italian referendums
RILEVAZIONE_TIMES = ["12:00", "19:00", "23:00", "15:00"]


@dataclass
class RilevazioneAffluenza:
    """Single turnout reading at a specific time."""
    timestamp: datetime
    percentuale: float  # e.g. 38.5
    ora_rilevazione: str  # e.g. "12:00"
    fonte: str = "Ministero dell'Interno"
    dettaglio: str = ""  # e.g. "Dato provvisorio", region breakdown


@dataclass
class AffluenzaData:
    """Complete turnout data collection."""
    rilevazioni: list[RilevazioneAffluenza] = field(default_factory=list)
    ultima_rilevazione: Optional[RilevazioneAffluenza] = None
    fonte: str = "Ministero dell'Interno - eligendo.it"
    last_fetch: Optional[datetime] = None
    error: Optional[str] = None


def _try_fetch_eligendo() -> list[RilevazioneAffluenza]:
    """Try to scrape turnout data from eligendo.it."""
    rilevazioni = []

    for url in ELIGENDO_URLS:
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Pattern 1: Table with turnout data
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    text = " ".join(c.get_text(strip=True) for c in cells)

                    # Look for percentage patterns like "38,5%" or "38.5%"
                    pct_match = re.search(r"(\d{1,2}[.,]\d{1,2})\s*%", text)
                    time_match = re.search(r"(\d{1,2}[:.]\d{2})", text)

                    if pct_match:
                        pct = float(pct_match.group(1).replace(",", "."))
                        ora = time_match.group(1).replace(".", ":") if time_match else "N/D"

                        if 0 < pct < 100:
                            rilevazioni.append(RilevazioneAffluenza(
                                timestamp=datetime.now(timezone.utc),
                                percentuale=pct,
                                ora_rilevazione=ora,
                                fonte="Ministero dell'Interno (eligendo.it)",
                                dettaglio=text[:200],
                            ))

            # Pattern 2: Div-based layout (newer eligendo versions)
            affluenza_divs = soup.find_all("div", class_=re.compile(r"affluenza|turnout|percentuale", re.I))
            for div in affluenza_divs:
                text = div.get_text(strip=True)
                pct_match = re.search(r"(\d{1,2}[.,]\d{1,2})\s*%", text)
                if pct_match:
                    pct = float(pct_match.group(1).replace(",", "."))
                    time_match = re.search(r"ore?\s*(\d{1,2}[:.]\d{2})", text)
                    ora = time_match.group(1).replace(".", ":") if time_match else "N/D"

                    if 0 < pct < 100:
                        rilevazioni.append(RilevazioneAffluenza(
                            timestamp=datetime.now(timezone.utc),
                            percentuale=pct,
                            ora_rilevazione=ora,
                            fonte="Ministero dell'Interno (eligendo.it)",
                            dettaglio=text[:200],
                        ))

            # Pattern 3: JSON API endpoint
            if "application/json" in resp.headers.get("Content-Type", ""):
                data = resp.json()
                if isinstance(data, dict):
                    for key in ["affluenza", "turnout", "percentuale"]:
                        if key in data:
                            val = data[key]
                            if isinstance(val, (int, float)) and 0 < val < 100:
                                rilevazioni.append(RilevazioneAffluenza(
                                    timestamp=datetime.now(timezone.utc),
                                    percentuale=float(val),
                                    ora_rilevazione="N/D",
                                    fonte="Ministero dell'Interno (API)",
                                ))

        except Exception as e:
            logger.debug(f"Eligendo fetch failed for {url}: {e}")
            continue

    return rilevazioni


def _extract_affluenza_from_articles(articles) -> list[RilevazioneAffluenza]:
    """
    Extract turnout data mentioned in news articles.
    Looks for patterns like "affluenza al 38,5% alle ore 12:00"
    """
    ELIGENDO_URL = "https://elezioni.interno.gov.it/risultati/20260322/referendum/votanti/italia"

    rilevazioni = []
    seen = set()

    patterns = [
        # "affluenza al 38,5%" or "affluenza del 38,5%"
        r"affluenza\s+(?:al|del|pari\s+al?)\s*(\d{1,2}[.,]\d{1,2})\s*%",
        # "affluenza 38,5%" direct
        r"affluenza\s*[:\-]?\s*(\d{1,2}[.,]\d{1,2})\s*%",
        # "ha votato il 38,5%"
        r"(?:ha\s+)?votato\s+il\s+(\d{1,2}[.,]\d{1,2})\s*%",
        # "turnout at 38.5%"
        r"turnout\s+(?:at|of)\s+(\d{1,2}[.,]\d{1,2})\s*%",
        # "quorum" related
        r"(\d{1,2}[.,]\d{1,2})\s*%\s*(?:di\s+)?(?:affluenza|votanti|partecipazione)",
    ]

    # Time patterns — broader search
    time_patterns = [
        r"(?:alle?\s+)?ore\s+(\d{1,2}[:.]\d{2})",
        r"(?:delle?\s+)?ore\s+(\d{1,2}[:.]\d{2})",
        r"(?:entro\s+le\s+)?(\d{1,2}[:.]\d{2})",
        r"rilevazione\s+(?:delle?\s+)?(\d{1,2}[:.]\d{2})",
    ]

    # Map known percentages to standard reporting times
    KNOWN_TIMES = {12: "12:00", 19: "19:00", 23: "23:00", 15: "15:00"}

    for article in articles:
        text = (article.title + " " + article.summary).lower()

        if "affluenza" not in text and "turnout" not in text and "votato" not in text:
            continue

        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                pct = float(match.group(1).replace(",", "."))
                if not (1 < pct < 95):  # sanity check
                    continue

                # Try to find associated time in broader context (100 chars)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]

                ora = None
                for tp in time_patterns:
                    time_match = re.search(tp, context)
                    if time_match:
                        ora = time_match.group(1).replace(".", ":")
                        break

                # If no time found, infer from article publication time
                if not ora:
                    pub_hour = article.published.hour
                    # Map to nearest standard reporting time
                    if pub_hour <= 13:
                        ora = "12:00"
                    elif pub_hour <= 20:
                        ora = "19:00"
                    elif pub_hour <= 23:
                        ora = "23:00"
                    else:
                        ora = "15:00"

                key = f"{pct}_{ora}"
                if key in seen:
                    continue
                seen.add(key)

                rilevazioni.append(RilevazioneAffluenza(
                    timestamp=article.published,
                    percentuale=pct,
                    ora_rilevazione=ora,
                    fonte=f"Ministero dell'Interno (via {article.source})",
                    dettaglio=f"{article.title[:120]} | Fonte dati: {ELIGENDO_URL}",
                ))

    return rilevazioni


def fetch_affluenza(articles=None) -> AffluenzaData:
    """
    Fetch turnout data from all available sources.
    Priority: 1) eligendo.it, 2) news articles
    """
    data = AffluenzaData()

    # Try official source first
    try:
        official = _try_fetch_eligendo()
        data.rilevazioni.extend(official)
    except Exception as e:
        logger.warning(f"Eligendo fetch error: {e}")

    # Extract from articles as supplement/fallback
    if articles:
        try:
            from_articles = _extract_affluenza_from_articles(articles)
            # Add article-sourced data, avoiding duplicates
            seen_pcts = {(r.percentuale, r.ora_rilevazione) for r in data.rilevazioni}
            for r in from_articles:
                if (r.percentuale, r.ora_rilevazione) not in seen_pcts:
                    data.rilevazioni.append(r)
                    seen_pcts.add((r.percentuale, r.ora_rilevazione))
        except Exception as e:
            logger.warning(f"Article affluenza extraction error: {e}")

    # Sort by time
    data.rilevazioni.sort(key=lambda r: r.ora_rilevazione)

    if data.rilevazioni:
        data.ultima_rilevazione = data.rilevazioni[-1]

    data.last_fetch = datetime.now(timezone.utc)

    return data
