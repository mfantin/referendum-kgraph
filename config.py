"""
Configuration for the Italian Referendum Knowledge Graph tool.
Referendum: Riforma Nordio (separazione carriere magistratura) - 22-23 Marzo 2026
"""

from datetime import datetime

# --- Referendum Info ---
REFERENDUM_DATE_START = datetime(2026, 3, 22, 7, 0)
REFERENDUM_DATE_END = datetime(2026, 3, 23, 15, 0)
REFERENDUM_TITLE = "Referendum Costituzionale - Riforma della Giustizia (Nordio)"
REFERENDUM_DESCRIPTION = (
    "Referendum confermativo sulla riforma costituzionale della giustizia: "
    "separazione delle carriere tra giudici e PM, sdoppiamento del CSM, "
    "sorteggio dei membri laici, Alta Corte disciplinare."
)

# --- RSS Feeds ---
RSS_FEEDS = {
    "ANSA Politica": {
        "url": "https://www.ansa.it/sito/notizie/politica/politica_rss.xml",
        "language": "it",
        "reliability": 0.9,
    },
    "La Repubblica Politica": {
        "url": "https://www.repubblica.it/rss/politica/rss2.0.xml",
        "language": "it",
        "reliability": 0.8,
    },
    "Corriere della Sera Politica": {
        "url": "https://xml2.corriereobjects.it/rss/politica.xml",
        "language": "it",
        "reliability": 0.85,
    },
    "Il Sole 24 Ore": {
        "url": "https://www.ilsole24ore.com/rss/italia.xml",
        "language": "it",
        "reliability": 0.85,
    },
    "Il Fatto Quotidiano": {
        "url": "https://www.ilfattoquotidiano.it/feed/",
        "language": "it",
        "reliability": 0.7,
    },
    "Sky TG24 Politica": {
        "url": "https://tg24.sky.it/rss/tg24_politica.xml",
        "language": "it",
        "reliability": 0.8,
    },
    "BBC Europe": {
        "url": "http://feeds.bbci.co.uk/news/world/europe/rss.xml",
        "language": "en",
        "reliability": 0.9,
    },
    "Euronews": {
        "url": "https://www.euronews.com/rss",
        "language": "en",
        "reliability": 0.8,
    },
}

# --- Keywords for relevance filtering ---
REFERENDUM_KEYWORDS_IT = [
    "referendum", "riforma giustizia", "separazione carriere",
    "riforma nordio", "nordio", "csm", "consiglio superiore magistratura",
    "magistratura", "alta corte disciplinare", "sorteggio csm",
    "confermativo", "riforma costituzionale", "22 marzo", "23 marzo",
    "scheda elettorale", "seggio", "affluenza", "quorum",
    "voto referendum", "campagna referendaria",
]

REFERENDUM_KEYWORDS_EN = [
    "referendum", "italy referendum", "italian referendum",
    "judiciary reform", "separation of careers", "nordio reform",
    "constitutional reform italy", "italian justice reform",
    "csm reform", "magistrate", "prosecutor judge separation",
]

# --- Party Positions ---
PARTY_POSITIONS = {
    "FdI": {
        "name": "Fratelli d'Italia",
        "position": "SI",
        "color": "#003DA5",
        "leader": "Giorgia Meloni",
        "key_figures": ["Giorgia Meloni", "Carlo Nordio"],
        "estimated_support_pct": 28.0,
    },
    "Lega": {
        "name": "Lega",
        "position": "SI",
        "color": "#008C45",
        "leader": "Matteo Salvini",
        "key_figures": ["Matteo Salvini"],
        "estimated_support_pct": 8.5,
    },
    "FI": {
        "name": "Forza Italia",
        "position": "SI",
        "color": "#0087DC",
        "leader": "Antonio Tajani",
        "key_figures": ["Antonio Tajani"],
        "estimated_support_pct": 9.0,
    },
    "NM": {
        "name": "Noi Moderati",
        "position": "SI",
        "color": "#1E3A5F",
        "leader": "Maurizio Lupi",
        "key_figures": ["Maurizio Lupi"],
        "estimated_support_pct": 1.0,
    },
    "PD": {
        "name": "Partito Democratico",
        "position": "NO",
        "color": "#E2001A",
        "leader": "Elly Schlein",
        "key_figures": ["Elly Schlein"],
        "estimated_support_pct": 23.0,
    },
    "M5S": {
        "name": "Movimento 5 Stelle",
        "position": "NO",
        "color": "#FFD700",
        "leader": "Giuseppe Conte",
        "key_figures": ["Giuseppe Conte"],
        "estimated_support_pct": 11.0,
    },
    "AVS": {
        "name": "Alleanza Verdi e Sinistra",
        "position": "NO",
        "color": "#4CAF50",
        "leader": "Nicola Fratoianni",
        "key_figures": ["Nicola Fratoianni", "Angelo Bonelli"],
        "estimated_support_pct": 6.5,
    },
    "Azione": {
        "name": "Azione",
        "position": "SI",
        "color": "#1B3D6D",
        "leader": "Carlo Calenda",
        "key_figures": ["Carlo Calenda"],
        "estimated_support_pct": 3.0,
    },
    "IV": {
        "name": "Italia Viva",
        "position": "SI",
        "color": "#FF6600",
        "leader": "Matteo Renzi",
        "key_figures": ["Matteo Renzi"],
        "estimated_support_pct": 2.5,
    },
}

# --- Known Polls (pre-seeded) ---
KNOWN_POLLS = [
    {
        "source": "Ipsos",
        "date": "2026-03-10",
        "si_pct": 46.0,
        "no_pct": 54.0,
        "sample_size": 1000,
        "note": "Tra chi ha deciso",
    },
    {
        "source": "SWG",
        "date": "2026-03-08",
        "si_pct": 48.0,
        "no_pct": 52.0,
        "sample_size": 1500,
        "note": "Tra chi ha deciso",
    },
    {
        "source": "EMG",
        "date": "2026-03-05",
        "si_pct": 47.0,
        "no_pct": 53.0,
        "sample_size": 1200,
        "note": "Tra chi ha deciso",
    },
    {
        "source": "Tecnè",
        "date": "2026-03-03",
        "si_pct": 49.0,
        "no_pct": 51.0,
        "sample_size": 1000,
        "note": "Tra chi ha deciso",
    },
    {
        "source": "Euromedia",
        "date": "2026-02-28",
        "si_pct": 45.0,
        "no_pct": 55.0,
        "sample_size": 800,
        "note": "Tra chi ha deciso",
    },
]

# --- Sentiment Lexicon (Italian) ---
SENTIMENT_SI = [
    "approvare", "approva", "approvazione", "favorevole", "favore",
    "sostenere", "sostegno", "riforma necessaria", "modernizzare",
    "efficienza", "efficiente", "giustizia giusta", "cambiamento",
    "separazione necessaria", "imparzialità", "terzietà del giudice",
    "garanzia", "equilibrio dei poteri", "vota sì", "votare sì",
    "a favore", "pro riforma", "migliorare la giustizia",
]

SENTIMENT_NO = [
    "bocciare", "bocciatura", "contrario", "respingere",
    "pericoloso", "pericolo", "rischio", "minaccia",
    "indipendenza magistratura", "attacco alla magistratura",
    "concentrazione poteri", "indebolire", "smantellare",
    "contro la riforma", "vota no", "votare no", "no alla riforma",
    "pm sotto controllo", "giustizia a rischio", "democrazia a rischio",
    "controriforma", "passo indietro",
]

# --- Entity Detection Keywords ---
POLITICIAN_KEYWORDS = {}
for party_id, party_data in PARTY_POSITIONS.items():
    for figure in party_data["key_figures"]:
        POLITICIAN_KEYWORDS[figure.lower()] = {
            "name": figure,
            "party": party_id,
            "position": party_data["position"],
        }

PARTY_KEYWORDS = {}
for party_id, party_data in PARTY_POSITIONS.items():
    PARTY_KEYWORDS[party_data["name"].lower()] = party_id
    PARTY_KEYWORDS[party_id.lower()] = party_id

# --- Visualization ---
COLOR_SI = "#2ecc71"
COLOR_NO = "#e74c3c"
COLOR_NEUTRAL = "#95a5a6"
COLOR_PARTY = "#3498db"
COLOR_POLITICIAN = "#9b59b6"
COLOR_POLL = "#f39c12"
COLOR_ARTICLE = "#1abc9c"
COLOR_TOPIC = "#e67e22"

NODE_COLORS = {
    "outcome_si": COLOR_SI,
    "outcome_no": COLOR_NO,
    "party_si": "#27ae60",
    "party_no": "#c0392b",
    "politician": COLOR_POLITICIAN,
    "poll": COLOR_POLL,
    "article": COLOR_ARTICLE,
    "topic": COLOR_TOPIC,
    "referendum": "#2c3e50",
}

# --- Refresh & Cache ---
DEFAULT_REFRESH_SECONDS = 300
CACHE_TTL_SECONDS = 300
MAX_ARTICLES = 200
GRAPH_LAYOUT_SEED = 42

# --- Prediction Weights ---
SIGNAL_WEIGHTS = {
    "polls": 0.45,
    "party_strength": 0.25,
    "media_sentiment": 0.20,
    "momentum": 0.10,
}

# Historical referendum poll error (Italy 2016: ~13 points)
HISTORICAL_POLL_ERROR = 0.13
