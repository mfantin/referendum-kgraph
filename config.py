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

# Social-media-specific keywords (informal/colloquial language on Reddit, blogs, etc.)
SOCIAL_KEYWORDS_IT = [
    "referendum", "nordio", "separazione carriere", "riforma giustizia",
    "voto", "votare", "seggio", "scheda", "quorum", "affluenza",
    "magistrati", "giudici", "pm", "procuratori",
    "csm", "alta corte", "sorteggio",
    "sì", "no", "astengo", "astensione", "non voto",
    "meloni", "schlein", "conte", "salvini", "tajani", "calenda", "renzi",
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

# --- Sentiment Lexicon (Italian) - expanded ---
SENTIMENT_SI = [
    # Verbi / azioni pro-riforma
    "approvare", "approva", "approvato", "approvazione", "approviamo",
    "sostenere", "sostiene", "sostegno", "sostenuto",
    "votare sì", "vota sì", "voterà sì", "voto favorevole",
    "promuovere", "promuove",
    # Aggettivi / giudizi positivi sulla riforma
    "favorevole", "favore", "a favore", "pro riforma",
    "riforma necessaria", "riforma giusta", "riforma equilibrata",
    "buona riforma", "riforma positiva", "riforma moderna",
    "passo avanti", "passo in avanti", "svolta",
    "modernizzare", "modernizzazione", "innovare", "innovazione",
    "efficienza", "efficiente", "efficacia",
    "migliorare", "miglioramento", "migliorare la giustizia",
    "cambiamento", "rinnovamento", "progresso",
    # Argomenti specifici pro-SI
    "separazione necessaria", "separazione delle carriere",
    "imparzialità", "terzietà", "terzietà del giudice",
    "giudice imparziale", "giudice terzo",
    "garanzia", "garanzie", "garantire",
    "equilibrio dei poteri", "equilibrio",
    "processo giusto", "giusto processo",
    "tutela dei diritti", "diritti dei cittadini",
    "trasparenza", "responsabilità", "accountability",
    "meritocrazia", "professionalità",
    # Posizioni partiti/politici pro-SI
    "centrodestra unito", "governo approva", "meloni sostiene",
    "nordio difende", "la riforma funziona",
    "maggioranza a favore", "coalizione compatta",
    # Sondaggi/trend pro-SI
    "sì in vantaggio", "sì avanti", "cresce il sì",
    "consenso per il sì", "vittoria del sì",
    "sondaggi favorevoli", "trend positivo",
    # Affluenza e partecipazione pro-SI
    "alta affluenza", "affluenza alta", "grande partecipazione",
    "mobilitazione", "elettori ai seggi", "code ai seggi",
    "quorum raggiunto", "partecipazione record",
    # Inglese
    "approve", "support", "in favor", "reform needed",
    "yes vote", "vote yes", "pro reform",
    "high turnout", "strong turnout",
]

SENTIMENT_NO = [
    # Verbi / azioni anti-riforma
    "bocciare", "boccia", "bocciato", "bocciatura", "bocciamo",
    "respingere", "respinto", "respinge",
    "votare no", "vota no", "voterà no", "voto contrario",
    "opporsi", "oppone", "opposizione alla riforma",
    "rigettare", "rigetto", "rifiutare", "rifiuto",
    "abrogare", "abolire", "cancellare",
    # Aggettivi / giudizi negativi
    "contrario", "contrari", "contro la riforma",
    "pericoloso", "pericolosa", "pericolo",
    "rischio", "rischioso", "rischiosa", "a rischio",
    "minaccia", "minacciare", "minaccioso",
    "dannoso", "dannosa", "danno", "danni",
    "negativo", "negativa", "pessimo", "pessima",
    "sbagliato", "sbagliata", "errore", "grave errore",
    "passo indietro", "regressione", "arretramento",
    "controriforma", "stravolgimento",
    # Argomenti specifici anti-riforma
    "indipendenza magistratura", "indipendenza dei magistrati",
    "attacco alla magistratura", "attacco ai magistrati",
    "attacco alla giustizia", "mani sulla giustizia",
    "concentrazione poteri", "concentrazione di potere",
    "indebolire", "indebolimento", "smantellare", "smantellamento",
    "pm sotto controllo", "controllo politico",
    "giustizia a rischio", "democrazia a rischio",
    "stato di diritto a rischio", "colpo alla democrazia",
    "magistratura sotto attacco", "bavaglio",
    "potere esecutivo", "ingerenza politica", "politicizzare",
    "corporativismo", "casta", "privilegio",
    "due binari", "magistrati di serie b",
    # Posizioni partiti/politici anti-riforma
    "opposizione compatta", "schlein contro", "conte contro",
    "pd contrario", "m5s contrario", "sinistra contro",
    "anm contraria", "magistrati contrari",
    # Sondaggi/trend pro-NO
    "no in vantaggio", "no avanti", "cresce il no",
    "consenso per il no", "vittoria del no",
    "affluenza bassa", "astensione", "disaffezione",
    # Affluenza e partecipazione pro-NO
    "bassa affluenza", "affluenza bassa", "scarsa partecipazione",
    "astensionismo", "diserzione", "seggi vuoti", "seggi deserti",
    "boicottare", "boicottaggio", "non voto",
    # Inglese
    "reject", "oppose", "against", "dangerous reform",
    "no vote", "vote no", "anti reform", "threat to democracy",
    "low turnout", "voter apathy",
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
    "social": "#8e44ad",
    "platform": "#2980b9",
    "topic": COLOR_TOPIC,
    "referendum": "#2c3e50",
}

# --- Direct Social Platform Configuration ---
# Reddit: subreddits and search queries (JSON API, no auth needed)
REDDIT_SEARCHES = {
    "r/italy": {
        "queries": [
            "referendum", "nordio", "separazione carriere",
            "riforma giustizia", "voto marzo", "magistratura",
        ],
        "lang": "it",
        "reliability": 0.5,
    },
    "r/italypolitics": {
        "queries": ["referendum", "nordio", "giustizia", "voto"],
        "lang": "it",
        "reliability": 0.45,
    },
    "r/Italia": {
        "queries": ["referendum", "nordio", "voto"],
        "lang": "it",
        "reliability": 0.4,
    },
    "r/europe": {
        "queries": ["italy referendum", "italian justice reform"],
        "lang": "en",
        "reliability": 0.45,
    },
    "r/worldnews": {
        "queries": ["italy referendum"],
        "lang": "en",
        "reliability": 0.4,
    },
}

# Telegram: public channels (scraped from t.me/s/)
TELEGRAM_CHANNELS = {
    "GiorgiaMeloni": {"label": "Giorgia Meloni", "lang": "it", "reliability": 0.55},
    "matteosalviniofficial": {"label": "Matteo Salvini", "lang": "it", "reliability": 0.55},
    "GiuseppeConte_ufficiale": {"label": "Giuseppe Conte", "lang": "it", "reliability": 0.55},
    "foraborsa": {"label": "Fora Borsa (economia)", "lang": "it", "reliability": 0.4},
}

# Bluesky: search queries (public API, no auth)
BLUESKY_QUERIES = [
    "referendum nordio",
    "separazione carriere",
    "riforma giustizia",
    "voto referendum italia",
    "#referendum",
    "#riformanordio",
]
BLUESKY_RELIABILITY = 0.4

# Mastodon: instances and hashtags (public tag timeline API)
MASTODON_SEARCHES = {
    "mastodon.uno": {
        "tags": ["referendum", "riformanordio", "nordio", "separazionecarriere"],
        "lang": "it",
        "reliability": 0.35,
    },
    "mastodon.social": {
        "tags": ["referendum", "riformanordio"],
        "lang": "it",
        "reliability": 0.3,
    },
}

# YouTube: political channels (official RSS, parsed by feedparser)
YOUTUBE_POLITICAL_CHANNELS = {
    "La7 Attualità": "UCkTnMJPSjkvPnFJXLMWzMfQ",
    "Sky TG24": "UC0LlEMGTe2pg1K0gVi2HFKQ",
    "Rai News": "UCLoNQH9RCndfUGOb2f7E1Ew",
    "Breaking Italy": "UCRI-Ds5eY70kxWzejMYiMDw",
    "Fanpage.it": "UCBcfQzk5-Qlvpoql1oCeaJQ",
    "Open": "UCnsvJeZO4RigQ898WdDNoBw",
}

# Social fetcher settings
SOCIAL_FETCH_TIMEOUT = 10
SOCIAL_RATE_LIMIT_DELAY = 2.0  # seconds between Reddit requests

# --- Refresh & Cache ---
DEFAULT_REFRESH_SECONDS = 300
CACHE_TTL_SECONDS = 300
MAX_ARTICLES = 500
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

# --- Exit Poll Configuration ---
EXIT_POLL_AVAILABLE_AFTER = datetime(2026, 3, 23, 15, 0)  # After voting ends

EXIT_POLL_KEYWORDS = [
    "exit poll", "exit-poll", "exitpoll",
    "prime proiezioni", "proiezioni", "proiezione",
    "prime stime", "stima", "stime di voto",
    "risultati parziali", "dati parziali",
    "spoglio", "scrutinio", "primi risultati",
    "consorzio opinio", "opinio", "quorum/youtrend",
    "youtrend", "swg exit", "tecnè exit", "piepoli",
    "instant poll", "primi dati reali",
    "exit poll results", "early results", "preliminary results",
]

EXIT_POLL_SOURCES = [
    "Consorzio Opinio (Rai)",
    "Quorum/YouTrend (Sky TG24)",
    "Tecnè (Rete 4/Mediaset)",
    "SWG (La7)",
    "Istituto Piepoli (Italia 1)",
    "EMG Different",
]

# Weight for exit poll signal (overrides polls when available)
SIGNAL_WEIGHTS_WITH_EXIT_POLL = {
    "exit_poll": 0.50,
    "polls": 0.15,
    "party_strength": 0.10,
    "media_sentiment": 0.15,
    "momentum": 0.10,
}
