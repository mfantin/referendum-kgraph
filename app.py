"""
Italian Referendum Knowledge Graph - Live Prediction Dashboard
Referendum Costituzionale: Riforma della Giustizia (Nordio) - 22-23 Marzo 2026

Animazione live ogni secondo | Source discovery automatico | Mobile-friendly
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timezone
import streamlit.components.v1 as components

import config
from data_fetcher import fetch_all_feeds, get_all_polls
from kg_builder import build_graph, graph_to_plotly, get_graph_stats
from predictor import predict
from source_discovery import discover_sources, get_discovery_stats

# --- Page Config ---
st.set_page_config(
    page_title="Referendum KG - Predizione Live",
    page_icon="\U0001f1ee\U0001f1f9",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Auto-refresh via JS (zero external dependencies) ---
# Countdown updates every second client-side; full data reload at configured interval
_JS_AUTOREFRESH = """
<script>
(function() {
    // Live countdown update (every second, client-side only)
    function updateCountdown() {
        var el = document.getElementById('live-countdown');
        if (!el) return;
        var target = new Date('2026-03-22T07:00:00Z').getTime();
        var end = new Date('2026-03-23T15:00:00Z').getTime();
        var now = Date.now();
        if (now > end) {
            el.innerHTML = '\\u{1F534} VOTO CONCLUSO';
        } else if (now > target) {
            var rem = Math.floor((end - now) / 1000);
            var h = Math.floor(rem / 3600);
            var m = Math.floor((rem %% 3600) / 60);
            var s = rem %% 60;
            el.innerHTML = '<span class="live-dot"></span> VOTAZIONE IN CORSO - ' +
                String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
        } else {
            var rem = Math.floor((target - now) / 1000);
            var d = Math.floor(rem / 86400);
            var h = Math.floor((rem %% 86400) / 3600);
            var m = Math.floor((rem %% 3600) / 60);
            var s = rem %% 60;
            el.innerHTML = '\\u{1F7E1} ' + d + 'g ' +
                String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0') + ' al voto';
        }
        // Update clock
        var clk = document.getElementById('live-clock');
        if (clk) clk.textContent = new Date().toLocaleTimeString('it-IT');
    }
    setInterval(updateCountdown, 1000);
    updateCountdown();

    // Full page reload for data refresh (configurable)
    var refreshMs = %d;
    if (refreshMs > 0) {
        setTimeout(function(){ window.parent.location.reload(); }, refreshMs);
    }
})();
</script>
"""
tick = int(datetime.now().timestamp())

# --- Custom CSS (mobile-responsive) ---
st.markdown("""
<style>
    /* Mobile-first responsive */
    @media (max-width: 768px) {
        .block-container { padding: 0.5rem 0.8rem !important; }
        .main-header h1 { font-size: 1.1rem !important; }
        .main-header p { font-size: 0.8rem !important; }
        div[data-testid="stMetric"] { padding: 0.4rem !important; }
        div[data-testid="stMetric"] label { font-size: 0.75rem !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    }
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 0.8rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.6rem; }
    .main-header p { color: #a8d8ea; margin: 0.2rem 0 0 0; font-size: 0.9rem; }
    .countdown-live {
        display: inline-block;
        background: rgba(255,255,255,0.12);
        border-radius: 8px;
        padding: 0.3rem 0.8rem;
        font-weight: bold;
        animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    .live-dot {
        display: inline-block;
        width: 10px; height: 10px;
        background: #2ecc71;
        border-radius: 50%;
        margin-right: 6px;
        animation: blink 1s ease-in-out infinite;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; box-shadow: 0 0 8px #2ecc71; }
        50% { opacity: 0.4; box-shadow: none; }
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8f9fa, #ffffff);
        border-radius: 10px;
        padding: 0.7rem;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .discovery-badge {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        display: inline-block;
    }
    .disclaimer {
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 0.7rem;
        font-size: 0.8rem;
        margin-top: 0.8rem;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.4rem 1rem;
    }
</style>
""", unsafe_allow_html=True)


# --- Session State ---
if "prediction_history" not in st.session_state:
    st.session_state.prediction_history = []
if "last_prediction" not in st.session_state:
    st.session_state.last_prediction = None
if "discovered_sources" not in st.session_state:
    st.session_state.discovered_sources = []
if "discovered_feeds" not in st.session_state:
    st.session_state.discovered_feeds = {}
if "fetch_count" not in st.session_state:
    st.session_state.fetch_count = 0


# --- Sidebar ---
with st.sidebar:
    st.title("\u2699\ufe0f Controlli")

    st.markdown("### Aggiornamento")
    data_refresh = st.slider("Refresh dati (sec)", 60, 600, 300, step=30,
                             help="I dati RSS vengono cachati per questo intervallo")

    st.markdown("### Visualizzazione")
    show_articles = st.checkbox("Articoli recenti", True)
    show_signals = st.checkbox("Dettaglio segnali", True)
    show_discovery = st.checkbox("Source Discovery", True)
    show_feed_status = st.checkbox("Stato feed", False)

    st.markdown("---")
    st.markdown(f"**{config.REFERENDUM_TITLE}**")
    st.caption(config.REFERENDUM_DESCRIPTION)
    st.markdown("---")
    st.caption(
        "**Metodologia**: aggregazione ponderata di sondaggi, "
        "forza partitica, sentiment media e momentum. "
        "Refresh UI ogni secondo, dati ogni 5 min."
    )
    st.markdown("---")
    st.caption("**Come usare su smartphone:**")
    st.caption("Apri il link nel browser, aggiungi a Home Screen per esperienza app-like.")


# --- Live Header with JS-animated countdown (updates every second client-side) ---
st.markdown("""
<div class="main-header">
    <h1>\U0001f1ee\U0001f1f9 Referendum Knowledge Graph - Live</h1>
    <p>Riforma della Giustizia (Nordio) | 22-23 Marzo 2026</p>
    <p><span id="live-countdown" class="countdown-live">Caricamento...</span>
       &nbsp;|&nbsp; \U0001f551 <span id="live-clock">--:--:--</span></p>
</div>
""", unsafe_allow_html=True)

# Inject JS for live countdown + periodic data reload
refresh_ms = data_refresh * 1000
components.html(_JS_AUTOREFRESH % refresh_ms, height=0)


# --- Data Fetching (cached with TTL) ---
@st.cache_data(ttl=config.CACHE_TTL_SECONDS, show_spinner="Recupero dati live...")
def load_data(extra_feeds: dict | None = None):
    articles, statuses = fetch_all_feeds(extra_feeds)
    polls = get_all_polls(articles)
    return articles, statuses, polls


@st.cache_data(ttl=900, show_spinner="Scoperta nuove fonti...")
def run_discovery():
    return discover_sources(max_new=15)


# Run source discovery
if show_discovery:
    try:
        discovered = run_discovery()
        st.session_state.discovered_sources = discovered
        # Build extra feeds dict from active discovered sources
        extra = {}
        for src in discovered:
            if src.status == "active" and src.relevant_count > 0:
                extra[src.name] = {
                    "url": src.url,
                    "language": src.language,
                    "reliability": src.reliability,
                }
        st.session_state.discovered_feeds = extra
    except Exception:
        discovered = []
        extra = {}
else:
    extra = st.session_state.discovered_feeds
    discovered = st.session_state.discovered_sources

# Load data with discovered feeds
try:
    frozen_extra = {k: tuple(sorted(v.items())) for k, v in extra.items()} if extra else None
    articles, feed_statuses, polls = load_data(extra if extra else None)
    st.session_state.fetch_count += 1
    data_loaded = True
except Exception as e:
    st.error(f"Errore nel caricamento dati: {str(e)}")
    articles, feed_statuses, polls = [], [], config.KNOWN_POLLS
    data_loaded = False


# --- Build KG and Predict ---
graph = build_graph(articles, polls)
prediction = predict(articles, polls)

# Store prediction history (max 1 per 10 seconds to avoid bloat)
should_store = (
    st.session_state.last_prediction is None
    or abs(prediction.si_probability - st.session_state.last_prediction) > 0.001
    or (st.session_state.prediction_history
        and (datetime.now() - st.session_state.prediction_history[-1]["timestamp"]).total_seconds() > 10)
)
if should_store:
    st.session_state.prediction_history.append({
        "timestamp": datetime.now(),
        "si_prob": prediction.si_probability,
        "no_prob": prediction.no_probability,
        "confidence": prediction.confidence,
        "data_points": prediction.data_points,
    })
    st.session_state.last_prediction = prediction.si_probability

if len(st.session_state.prediction_history) > 1000:
    st.session_state.prediction_history = st.session_state.prediction_history[-1000:]


# --- Row 1: Key Metrics (responsive) ---
m1, m2, m3, m4 = st.columns(4)

with m1:
    delta_si = None
    if len(st.session_state.prediction_history) > 1:
        prev = st.session_state.prediction_history[-2]["si_prob"]
        d = (prediction.si_probability - prev) * 100
        if abs(d) > 0.01:
            delta_si = f"{d:+.1f}pp"
    st.metric("\u2705 Probabilita SI", f"{prediction.si_probability:.1%}", delta=delta_si)

with m2:
    delta_no = None
    if len(st.session_state.prediction_history) > 1:
        prev = st.session_state.prediction_history[-2]["no_prob"]
        d = (prediction.no_probability - prev) * 100
        if abs(d) > 0.01:
            delta_no = f"{d:+.1f}pp"
    st.metric("\u274c Probabilita NO", f"{prediction.no_probability:.1%}",
              delta=delta_no, delta_color="inverse")

with m3:
    st.metric("\U0001f3af Confidenza", f"{prediction.confidence:.0%}")

with m4:
    active_feeds = sum(1 for s in feed_statuses if s.success)
    discovered_active = len([s for s in discovered if s.status == "active"]) if discovered else 0
    st.metric("\U0001f4e1 Fonti Live",
              f"{active_feeds}+{discovered_active}",
              delta=f"{prediction.data_points} data points")

st.caption(
    f"Intervallo confidenza SI: **{prediction.ci_low:.0%} - {prediction.ci_high:.0%}** | "
    f"Ultimo refresh dati: {datetime.now().strftime('%H:%M:%S')}"
)


# --- Main Tabs ---
tab_kg, tab_pred, tab_party, tab_articles, tab_discovery = st.tabs([
    "\U0001f578\ufe0f Knowledge Graph",
    "\U0001f4ca Predizione",
    "\U0001f3db\ufe0f Partiti",
    "\U0001f4f0 Articoli",
    "\U0001f50d Discovery",
])


# --- Tab 1: Knowledge Graph ---
with tab_kg:
    fig_kg = graph_to_plotly(graph)
    st.plotly_chart(fig_kg, use_container_width=True, key="kg_main")

    stats = get_graph_stats(graph)
    scol1, scol2, scol3, scol4 = st.columns(4)
    scol1.metric("Nodi totali", stats["total_nodes"])
    scol2.metric("Archi totali", stats["total_edges"])
    scol3.metric("Articoli nel KG", stats["by_type"].get("article", 0))
    scol4.metric("Sondaggi nel KG", stats["by_type"].get("poll", 0))


# --- Tab 2: Prediction ---
with tab_pred:
    pcol1, pcol2 = st.columns([1, 1])

    with pcol1:
        # Gauge charts
        fig_gauge = go.Figure()

        fig_gauge.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=prediction.si_probability * 100,
            title={"text": "SI (Approvare)", "font": {"size": 18, "color": config.COLOR_SI}},
            number={"suffix": "%", "font": {"size": 32, "color": config.COLOR_SI}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "dtick": 10},
                "bar": {"color": config.COLOR_SI, "thickness": 0.75},
                "bgcolor": "#f0f0f0",
                "steps": [
                    {"range": [0, 40], "color": "#fadbd8"},
                    {"range": [40, 50], "color": "#fdebd0"},
                    {"range": [50, 60], "color": "#d5f5e3"},
                    {"range": [60, 100], "color": "#abebc6"},
                ],
                "threshold": {
                    "line": {"color": "#2c3e50", "width": 3},
                    "thickness": 0.85, "value": 50,
                },
            },
            domain={"x": [0, 1], "y": [0.55, 1]},
        ))

        fig_gauge.add_trace(go.Indicator(
            mode="gauge+number",
            value=prediction.no_probability * 100,
            title={"text": "NO (Respingere)", "font": {"size": 18, "color": config.COLOR_NO}},
            number={"suffix": "%", "font": {"size": 32, "color": config.COLOR_NO}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "dtick": 10},
                "bar": {"color": config.COLOR_NO, "thickness": 0.75},
                "bgcolor": "#f0f0f0",
                "steps": [
                    {"range": [0, 40], "color": "#d5f5e3"},
                    {"range": [40, 50], "color": "#fdebd0"},
                    {"range": [50, 60], "color": "#fadbd8"},
                    {"range": [60, 100], "color": "#f5b7b1"},
                ],
                "threshold": {
                    "line": {"color": "#2c3e50", "width": 3},
                    "thickness": 0.85, "value": 50,
                },
            },
            domain={"x": [0, 1], "y": [0, 0.45]},
        ))

        fig_gauge.update_layout(
            height=420, margin=dict(t=30, b=10, l=30, r=30),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_gauge, use_container_width=True, key="gauge")

    with pcol2:
        # Sondaggi table
        if polls:
            st.markdown("#### Ultimi Sondaggi")
            poll_df = pd.DataFrame(polls[:8])
            poll_df = poll_df.rename(columns={
                "source": "Istituto", "date": "Data",
                "si_pct": "SI %", "no_pct": "NO %", "note": "Note",
            })
            display_cols = [c for c in ["Istituto", "Data", "SI %", "NO %", "Note"]
                           if c in poll_df.columns]
            st.dataframe(poll_df[display_cols], use_container_width=True, hide_index=True)

        # Signals breakdown
        if show_signals and prediction.signals:
            st.markdown("#### Segnali del Modello")
            for signal in prediction.signals:
                leader = "SI" if signal.si_probability > 0.5 else "NO"
                leader_pct = max(signal.si_probability, signal.no_probability)
                color = config.COLOR_SI if leader == "SI" else config.COLOR_NO

                st.markdown(f"**{signal.name}** - {leader} {leader_pct:.1%}")
                st.progress(signal.confidence, text=f"Confidenza {signal.confidence:.0%} | Peso {signal.weight:.0%}")
                st.caption(signal.description)

    # Timeline
    if len(st.session_state.prediction_history) > 1:
        st.markdown("#### Andamento nel Tempo")
        hist_df = pd.DataFrame(st.session_state.prediction_history)

        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Scatter(
            x=hist_df["timestamp"], y=hist_df["si_prob"] * 100,
            mode="lines", name="SI %", fill="tozeroy",
            line=dict(color=config.COLOR_SI, width=2),
            fillcolor="rgba(46,204,113,0.15)",
        ))
        fig_timeline.add_trace(go.Scatter(
            x=hist_df["timestamp"], y=hist_df["no_prob"] * 100,
            mode="lines", name="NO %", fill="tozeroy",
            line=dict(color=config.COLOR_NO, width=2),
            fillcolor="rgba(231,76,60,0.15)",
        ))
        fig_timeline.add_hline(y=50, line_dash="dash", line_color="#95a5a6",
                               annotation_text="50%", annotation_position="bottom right")
        fig_timeline.update_layout(
            height=280,
            yaxis=dict(title="Probabilita %", range=[30, 70]),
            margin=dict(t=15, b=30, l=50, r=20),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_timeline, use_container_width=True, key="timeline")


# --- Tab 3: Partiti ---
with tab_party:
    pc1, pc2 = st.columns(2)

    si_parties = {k: v for k, v in config.PARTY_POSITIONS.items() if v["position"] == "SI"}
    no_parties = {k: v for k, v in config.PARTY_POSITIONS.items() if v["position"] == "NO"}

    with pc1:
        total_si = sum(p["estimated_support_pct"] for p in si_parties.values())
        st.markdown(f"### \u2705 Schieramento SI")
        st.metric("Consenso aggregato", f"{total_si:.1f}%")
        for pid, pdata in sorted(si_parties.items(), key=lambda x: -x[1]["estimated_support_pct"]):
            st.markdown(
                f"**{pdata['name']}** ({pdata['estimated_support_pct']}%) - {pdata['leader']}"
            )

    with pc2:
        total_no = sum(p["estimated_support_pct"] for p in no_parties.values())
        st.markdown(f"### \u274c Schieramento NO")
        st.metric("Consenso aggregato", f"{total_no:.1f}%")
        for pid, pdata in sorted(no_parties.items(), key=lambda x: -x[1]["estimated_support_pct"]):
            st.markdown(
                f"**{pdata['name']}** ({pdata['estimated_support_pct']}%) - {pdata['leader']}"
            )

    # Party chart
    fig_parties = go.Figure()
    sorted_parties = sorted(config.PARTY_POSITIONS.items(), key=lambda x: -x[1]["estimated_support_pct"])
    fig_parties.add_trace(go.Bar(
        x=[p[1]["name"] for p in sorted_parties],
        y=[p[1]["estimated_support_pct"] for p in sorted_parties],
        marker_color=[config.COLOR_SI if p[1]["position"] == "SI" else config.COLOR_NO
                      for p in sorted_parties],
        text=[f"{p[1]['estimated_support_pct']}%" for p in sorted_parties],
        textposition="outside",
    ))
    fig_parties.update_layout(
        height=350, yaxis_title="Consenso %",
        margin=dict(t=20, b=80, l=50, r=20),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis_tickangle=-30, showlegend=False,
    )
    st.plotly_chart(fig_parties, use_container_width=True, key="parties_chart")


# --- Tab 4: Articles ---
with tab_articles:
    if articles:
        st.markdown(f"**{len(articles)} articoli rilevanti trovati**")
        for article in articles[:20]:
            icon = {
                "SI": "\U0001f7e2", "NO": "\U0001f534", "NEUTRAL": "\u26aa"
            }.get(article.sentiment_direction, "\u26aa")

            with st.expander(
                f"{icon} [{article.source}] {article.title[:70]}",
                expanded=False,
            ):
                c1, c2, c3 = st.columns(3)
                c1.caption(f"**Fonte:** {article.source}")
                c2.caption(f"**Sentiment:** {article.sentiment_direction} ({article.sentiment_score:+.2f})")
                c3.caption(f"**Rilevanza:** {article.relevance:.0%}")

                if article.mentioned_entities:
                    st.caption(f"Politici: {', '.join(article.mentioned_entities)}")
                if article.mentioned_parties:
                    st.caption(f"Partiti: {', '.join(article.mentioned_parties)}")

                st.markdown(article.summary[:400])
                if article.url:
                    st.markdown(f"[\U0001f517 Leggi l'articolo]({article.url})")
    else:
        st.info("Nessun articolo rilevante trovato. I feed RSS verranno consultati al prossimo refresh.")


# --- Tab 5: Source Discovery ---
with tab_discovery:
    st.markdown("### \U0001f50d Motore di Scoperta Fonti")
    st.caption(
        "Ricerca automatica di nuovi feed RSS, Google News, Reddit e media internazionali "
        "rilevanti per il referendum. Le fonti attive vengono integrate nel Knowledge Graph."
    )

    if discovered:
        disc_stats = get_discovery_stats(discovered)
        dc1, dc2, dc3, dc4 = st.columns(4)
        dc1.metric("Fonti scoperte", disc_stats["total_discovered"])
        dc2.metric("Attive", disc_stats["active"])
        dc3.metric("Articoli trovati", disc_stats["total_articles"])
        dc4.metric("Rilevanti", disc_stats["total_relevant"])

        st.markdown("#### Fonti Attive (integrate nel KG)")
        for src in discovered:
            if src.status == "active":
                st.markdown(
                    f"\U0001f7e2 **{src.name}** | "
                    f"{src.language.upper()} | "
                    f"Articoli: {src.article_count} | "
                    f"Rilevanti: {src.relevant_count} | "
                    f"Affidabilita: {src.reliability:.0%}"
                )

        with st.expander("Tutte le fonti scoperte", expanded=False):
            for src in discovered:
                icon = {
                    "active": "\U0001f7e2",
                    "validated": "\U0001f7e1",
                    "failed": "\U0001f534",
                }.get(src.status, "\u26aa")
                st.markdown(
                    f"{icon} **{src.name}** [{src.status}] | "
                    f"{src.article_count} articoli | "
                    f"{src.relevant_count} rilevanti"
                )

        if st.button("Riesegui Discovery", key="rediscover"):
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("Attiva 'Source Discovery' nella sidebar per scoprire nuove fonti.")


# --- Feed Status (collapsible) ---
if show_feed_status:
    with st.expander("\U0001f4e1 Stato Feed RSS", expanded=False):
        for status in feed_statuses:
            icon = "\U0001f7e2" if status.success else "\U0001f534"
            detail = f"Articoli: {status.article_count} | Rilevanti: {status.relevant_count}"
            if status.error:
                detail = f"Errore: {status.error}"
            st.markdown(f"{icon} **{status.name}** - {detail}")


# --- Footer ---
st.markdown("---")
fc1, fc2, fc3, fc4 = st.columns(4)
fc1.caption(f"\U0001f551 {datetime.now().strftime('%H:%M:%S')}")
fc2.caption(f"\U0001f4e1 {sum(1 for s in feed_statuses if s.success)}/{len(feed_statuses)} feed")
fc3.caption(f"\U0001f4f0 {len(articles)} articoli")
fc4.caption(f"\U0001f504 Tick #{tick}")

st.markdown("""
<div class="disclaimer">
    <strong>\u26a0\ufe0f Disclaimer:</strong> Strumento sperimentale. Le predizioni sono basate su
    feed RSS pubblici, sondaggi pre-esistenti e analisi del sentiment con euristiche semplici.
    Non sostituisce analisi elettorali professionali.
    Nessun quorum richiesto per questo referendum confermativo.
</div>
""", unsafe_allow_html=True)

st.caption("Built with Streamlit, NetworkX, Plotly | [GitHub](https://github.com/mfantin/referendum-kgraph) | Open Source")
