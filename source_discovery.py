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

# Agent 4: Reddit – Italian community & politics
_AGENT_SOCIAL_REDDIT_IT = [
    {"name": "Reddit r/italy referendum", "url": "https://www.reddit.com/r/italy/search.rss?q=referendum&sort=new&restrict_sr=on", "lang": "it", "reliability": 0.5},
    {"name": "Reddit r/italy nordio", "url": "https://www.reddit.com/r/italy/search.rss?q=nordio+OR+magistratura&sort=new&restrict_sr=on", "lang": "it", "reliability": 0.45},
    {"name": "Reddit r/italy separazione carriere", "url": "https://www.reddit.com/r/italy/search.rss?q=separazione+carriere+OR+riforma+giustizia&sort=new&restrict_sr=on", "lang": "it", "reliability": 0.45},
    {"name": "Reddit r/italy voto marzo", "url": "https://www.reddit.com/r/italy/search.rss?q=voto+marzo+OR+scheda+elettorale+OR+seggio&sort=new&restrict_sr=on", "lang": "it", "reliability": 0.4},
    {"name": "Reddit r/italypolitics", "url": "https://www.reddit.com/r/italypolitics/new.rss", "lang": "it", "reliability": 0.4},
    {"name": "Reddit r/italypolitics referendum", "url": "https://www.reddit.com/r/italypolitics/search.rss?q=referendum+OR+nordio+OR+giustizia&sort=new&restrict_sr=on", "lang": "it", "reliability": 0.45},
    {"name": "Reddit r/Italia referendum", "url": "https://www.reddit.com/r/Italia/search.rss?q=referendum+OR+nordio+OR+voto&sort=new&restrict_sr=on", "lang": "it", "reliability": 0.4},
]

# Agent 5: Reddit – International & European subs
_AGENT_SOCIAL_REDDIT_INT = [
    {"name": "Reddit r/europe italy referendum", "url": "https://www.reddit.com/r/europe/search.rss?q=italy+referendum&sort=new&restrict_sr=on", "lang": "en", "reliability": 0.45},
    {"name": "Reddit r/europe italian justice", "url": "https://www.reddit.com/r/europe/search.rss?q=italian+justice+reform+OR+nordio&sort=new&restrict_sr=on", "lang": "en", "reliability": 0.4},
    {"name": "Reddit r/worldnews italy", "url": "https://www.reddit.com/r/worldnews/search.rss?q=italy+referendum&sort=new&restrict_sr=on", "lang": "en", "reliability": 0.45},
    {"name": "Reddit r/geopolitics italy", "url": "https://www.reddit.com/r/geopolitics/search.rss?q=italy+referendum+OR+italian+reform&sort=new&restrict_sr=on", "lang": "en", "reliability": 0.4},
    {"name": "Reddit r/law italy", "url": "https://www.reddit.com/r/law/search.rss?q=italy+judiciary+OR+italian+justice&sort=new&restrict_sr=on", "lang": "en", "reliability": 0.4},
    {"name": "Reddit r/EuropeanFederalists italy", "url": "https://www.reddit.com/r/EuropeanFederalists/search.rss?q=italy+referendum+OR+italian&sort=new&restrict_sr=on", "lang": "en", "reliability": 0.35},
]

# Agent 6: Social Blogs, Forum & Community voices (via RSS/Atom)
_AGENT_SOCIAL_BLOGS = [
    # Italian political blogs & opinion platforms with RSS
    {"name": "Il Fatto Blog", "url": "https://www.ilfattoquotidiano.it/blog/feed/", "lang": "it", "reliability": 0.45},
    {"name": "Micromega", "url": "https://www.micromega.net/feed/", "lang": "it", "reliability": 0.5},
    {"name": "Valigia Blu", "url": "https://www.valigiablu.it/feed/", "lang": "it", "reliability": 0.55},
    {"name": "Lavoce.info", "url": "https://lavoce.info/feed/", "lang": "it", "reliability": 0.6},
    {"name": "Il Grand Continent IT", "url": "https://legrandcontinent.eu/it/feed/", "lang": "it", "reliability": 0.55},
    {"name": "Termometro Politico", "url": "https://www.termometropolitico.it/feed", "lang": "it", "reliability": 0.5},
    {"name": "Scenari Economici", "url": "https://scenarieconomici.it/feed/", "lang": "it", "reliability": 0.45},
    {"name": "Phastidio", "url": "https://phastidio.net/feed/", "lang": "it", "reliability": 0.5},
    {"name": "Startmag", "url": "https://www.startmag.it/feed/", "lang": "it", "reliability": 0.5},
]

# Agent 7: YouTube – direct channel RSS + Google News proxy
_AGENT_SOCIAL_YOUTUBE = [
    # Direct channel RSS feeds (official YouTube Atom feeds, parsed by feedparser)
    {"name": "YT La7 Attualità", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCkTnMJPSjkvPnFJXLMWzMfQ", "lang": "it", "reliability": 0.5},
    {"name": "YT Sky TG24", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC0LlEMGTe2pg1K0gVi2HFKQ", "lang": "it", "reliability": 0.5},
    {"name": "YT Rai News", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCLoNQH9RCndfUGOb2f7E1Ew", "lang": "it", "reliability": 0.5},
    {"name": "YT Breaking Italy", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCRI-Ds5eY70kxWzejMYiMDw", "lang": "it", "reliability": 0.45},
    {"name": "YT Fanpage.it", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCBcfQzk5-Qlvpoql1oCeaJQ", "lang": "it", "reliability": 0.45},
    {"name": "YT Open", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCnsvJeZO4RigQ898WdDNoBw", "lang": "it", "reliability": 0.45},
    # Google News proxy for broader YouTube coverage
    {"name": "YT GNews: referendum youtube", "url": "https://news.google.com/rss/search?q=referendum+nordio+site:youtube.com&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.35},
    {"name": "YT GNews: voto referendum opinioni", "url": "https://news.google.com/rss/search?q=referendum+giustizia+opinioni+site:youtube.com&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.35},
    {"name": "YT GNews: separazione carriere video", "url": "https://news.google.com/rss/search?q=separazione+carriere+magistratura+site:youtube.com&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.3},
]

# Agent 8: Twitter/X buzz via Google News proxy
_AGENT_SOCIAL_TWITTER = [
    {"name": "GNews: referendum su Twitter/X", "url": "https://news.google.com/rss/search?q=referendum+nordio+%22su+twitter%22+OR+%22su+x%22+OR+%22tweet%22&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.35},
    {"name": "GNews: referendum hashtag tendenza", "url": "https://news.google.com/rss/search?q=referendum+hashtag+OR+trending+OR+tendenza+OR+virale&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.35},
    {"name": "GNews: referendum reazioni social", "url": "https://news.google.com/rss/search?q=referendum+italia+%22reazioni+social%22+OR+%22dibattito+online%22+OR+%22social+media%22&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.35},
    {"name": "GNews EN: italy referendum twitter", "url": "https://news.google.com/rss/search?q=italy+referendum+twitter+OR+%22on+X%22+OR+%22social+media%22&hl=en&gl=US&ceid=US:en", "lang": "en", "reliability": 0.35},
]

# Agent 9: Instagram buzz via Google News proxy
_AGENT_SOCIAL_INSTAGRAM = [
    {"name": "GNews: referendum Instagram", "url": "https://news.google.com/rss/search?q=referendum+nordio+%22su+instagram%22+OR+%22instagram%22+OR+%22reel%22+OR+%22story%22&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.3},
    {"name": "GNews: referendum Instagram politici", "url": "https://news.google.com/rss/search?q=referendum+instagram+meloni+OR+schlein+OR+conte+OR+salvini&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.35},
    {"name": "GNews: referendum influencer Instagram", "url": "https://news.google.com/rss/search?q=referendum+influencer+instagram+OR+creator+OR+post+social&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.3},
]

# Agent 10: Facebook buzz via Google News proxy
_AGENT_SOCIAL_FACEBOOK = [
    {"name": "GNews: referendum Facebook", "url": "https://news.google.com/rss/search?q=referendum+nordio+%22su+facebook%22+OR+%22facebook%22+OR+%22pagina+facebook%22&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.3},
    {"name": "GNews: referendum gruppi Facebook", "url": "https://news.google.com/rss/search?q=referendum+%22gruppo+facebook%22+OR+%22condivisioni%22+OR+%22virale+facebook%22&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.3},
    {"name": "GNews: referendum Facebook politici", "url": "https://news.google.com/rss/search?q=referendum+facebook+meloni+OR+schlein+OR+conte+OR+salvini+OR+nordio&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.35},
]

# Agent 11: TikTok buzz via Google News proxy
_AGENT_SOCIAL_TIKTOK = [
    {"name": "GNews: referendum TikTok", "url": "https://news.google.com/rss/search?q=referendum+nordio+%22tiktok%22+OR+%22su+tiktok%22+OR+%22tiktoker%22&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.3},
    {"name": "GNews: referendum TikTok giovani", "url": "https://news.google.com/rss/search?q=referendum+tiktok+giovani+OR+%22generazione+z%22+OR+virale&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.3},
    {"name": "GNews: referendum TikTok politica", "url": "https://news.google.com/rss/search?q=tiktok+politica+italiana+referendum+OR+nordio+OR+voto&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.3},
]

# Agent 12: LinkedIn buzz via Google News proxy
_AGENT_SOCIAL_LINKEDIN = [
    {"name": "GNews: referendum LinkedIn", "url": "https://news.google.com/rss/search?q=referendum+nordio+%22linkedin%22+OR+%22su+linkedin%22&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.35},
    {"name": "GNews: riforma giustizia LinkedIn", "url": "https://news.google.com/rss/search?q=riforma+giustizia+linkedin+OR+%22analisi%22+OR+%22professionisti%22&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.35},
    {"name": "GNews: separazione carriere dibattito professionale", "url": "https://news.google.com/rss/search?q=separazione+carriere+linkedin+OR+avvocati+OR+giuristi+OR+%22ordine+avvocati%22&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.4},
]

# Agent 13: All social platforms – cross-platform engagement
_AGENT_SOCIAL_CROSS = [
    {"name": "GNews: referendum influencer opinion", "url": "https://news.google.com/rss/search?q=referendum+nordio+influencer+OR+creator+OR+tiktoker+OR+youtuber+OR+instagrammer&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.3},
    {"name": "GNews: referendum campagna social", "url": "https://news.google.com/rss/search?q=referendum+%22campagna+social%22+OR+%22comunicazione+politica%22+OR+%22propaganda+digitale%22&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.4},
    {"name": "GNews: referendum fake news disinformazione", "url": "https://news.google.com/rss/search?q=referendum+nordio+%22fake+news%22+OR+disinformazione+OR+bufala+OR+fact-check&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.45},
    {"name": "GNews EN: italy referendum social platforms", "url": "https://news.google.com/rss/search?q=italy+referendum+instagram+OR+tiktok+OR+facebook+OR+linkedin+OR+%22social+media%22&hl=en&gl=US&ceid=US:en", "lang": "en", "reliability": 0.35},
]

# Agent 14: RSSHub bridge (fallback for platforms without direct access)
_AGENT_RSSHUB = [
    {"name": "RSSHub: Telegram Meloni", "url": "https://rsshub.app/telegram/channel/GiorgiaMeloni", "lang": "it", "reliability": 0.3},
    {"name": "RSSHub: Telegram Salvini", "url": "https://rsshub.app/telegram/channel/matteosalviniofficial", "lang": "it", "reliability": 0.3},
    {"name": "RSSHub: Twitter referendum", "url": "https://rsshub.app/twitter/search/referendum%20nordio", "lang": "it", "reliability": 0.25},
    {"name": "RSSHub: Twitter riforma giustizia", "url": "https://rsshub.app/twitter/search/riforma%20giustizia%20referendum", "lang": "it", "reliability": 0.25},
]

# Agent 15: Sentiment & opinion tracking (sondaggi informali, umori, intenzioni di voto)
_AGENT_SOCIAL_SENTIMENT = [
    {"name": "GNews: intenzioni voto referendum", "url": "https://news.google.com/rss/search?q=intenzioni+voto+referendum+2026&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.55},
    {"name": "GNews: umori elettorato referendum", "url": "https://news.google.com/rss/search?q=umori+OR+clima+OR+orientamento+elettorato+referendum&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.5},
    {"name": "GNews: cittadini referendum opinioni", "url": "https://news.google.com/rss/search?q=cittadini+referendum+%22cosa+pensano%22+OR+opinioni+OR+sondaggio+strada&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.4},
    {"name": "GNews: giovani voto referendum", "url": "https://news.google.com/rss/search?q=giovani+voto+referendum+nordio+OR+generazione&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.45},
    {"name": "GNews: astensione referendum 2026", "url": "https://news.google.com/rss/search?q=astensione+OR+astensionismo+referendum+2026&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.5},
    {"name": "GNews: forum referendum discussione", "url": "https://news.google.com/rss/search?q=referendum+nordio+forum+OR+discussione+OR+dibattito+online&hl=it&gl=IT&ceid=IT:it", "lang": "it", "reliability": 0.4},
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

# Social agent feeds (for broader keyword matching)
_ALL_SOCIAL_FEEDS = (
    _AGENT_SOCIAL_REDDIT_IT
    + _AGENT_SOCIAL_REDDIT_INT
    + _AGENT_SOCIAL_BLOGS
    + _AGENT_SOCIAL_YOUTUBE
    + _AGENT_SOCIAL_TWITTER
    + _AGENT_SOCIAL_INSTAGRAM
    + _AGENT_SOCIAL_FACEBOOK
    + _AGENT_SOCIAL_TIKTOK
    + _AGENT_SOCIAL_LINKEDIN
    + _AGENT_SOCIAL_CROSS
    + _AGENT_RSSHUB
    + _AGENT_SOCIAL_SENTIMENT
)
_SOCIAL_URLS = {f["url"] for f in _ALL_SOCIAL_FEEDS}

# All agents combined
CANDIDATE_FEEDS = (
    _AGENT_ITALIAN_MEDIA
    + _AGENT_INTERNATIONAL
    + _AGENT_GOOGLE_NEWS
    + _AGENT_SOCIAL_REDDIT_IT
    + _AGENT_SOCIAL_REDDIT_INT
    + _AGENT_SOCIAL_BLOGS
    + _AGENT_SOCIAL_YOUTUBE
    + _AGENT_SOCIAL_TWITTER
    + _AGENT_SOCIAL_INSTAGRAM
    + _AGENT_SOCIAL_FACEBOOK
    + _AGENT_SOCIAL_TIKTOK
    + _AGENT_SOCIAL_LINKEDIN
    + _AGENT_SOCIAL_CROSS
    + _AGENT_RSSHUB
    + _AGENT_SOCIAL_SENTIMENT
    + _AGENT_INSTITUTIONAL
    + _AGENT_EXIT_POLL
)

# Agent names for dashboard display
DISCOVERY_AGENTS = {
    "Media Italiani": len(_AGENT_ITALIAN_MEDIA),
    "Media Internazionali": len(_AGENT_INTERNATIONAL),
    "Google News": len(_AGENT_GOOGLE_NEWS),
    "Reddit Italia": len(_AGENT_SOCIAL_REDDIT_IT),
    "Reddit Int'l": len(_AGENT_SOCIAL_REDDIT_INT),
    "Blog & Opinioni": len(_AGENT_SOCIAL_BLOGS),
    "YouTube": len(_AGENT_SOCIAL_YOUTUBE),
    "Twitter/X": len(_AGENT_SOCIAL_TWITTER),
    "Instagram": len(_AGENT_SOCIAL_INSTAGRAM),
    "Facebook": len(_AGENT_SOCIAL_FACEBOOK),
    "TikTok": len(_AGENT_SOCIAL_TIKTOK),
    "LinkedIn": len(_AGENT_SOCIAL_LINKEDIN),
    "Cross-platform": len(_AGENT_SOCIAL_CROSS),
    "RSSHub Bridge": len(_AGENT_RSSHUB),
    "Sentiment Voto": len(_AGENT_SOCIAL_SENTIMENT),
    "Fonti Istituzionali": len(_AGENT_INSTITUTIONAL),
    "Exit Poll": len(_AGENT_EXIT_POLL),
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


def _count_relevant(url: str, language: str = "it", is_social: bool = False) -> int:
    """Count how many entries in a feed are relevant to the referendum."""
    try:
        feed = feedparser.parse(
            url,
            request_headers={"User-Agent": "ReferendumKG/1.0 (Research Tool)"},
        )
        keywords = config.REFERENDUM_KEYWORDS_IT if language == "it" else config.REFERENDUM_KEYWORDS_EN
        # Social sources also match on informal/colloquial keywords
        if is_social and language == "it":
            keywords = list(keywords) + getattr(config, "SOCIAL_KEYWORDS_IT", [])
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
            source_type="social" if url in _SOCIAL_URLS else "rss",
            language=candidate["lang"],
            reliability=candidate["reliability"],
            article_count=entry_count,
            status="validated" if is_valid else "failed",
            error=error if not is_valid else None,
        )

        if is_valid and entry_count > 0:
            is_social = url in _SOCIAL_URLS
            source.relevant_count = _count_relevant(url, candidate["lang"], is_social=is_social)
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
