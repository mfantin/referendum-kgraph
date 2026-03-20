"""
Italian Referendum Knowledge Graph - Live Prediction Dashboard
Referendum Costituzionale: Riforma della Giustizia (Nordio) - 22-23 Marzo 2026

Smooth live updates via st.fragment | JS animated countdown | Mobile-friendly
"""

import os

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone
import streamlit.components.v1 as components

import config
from data_fetcher import fetch_all_feeds, get_all_polls
from kg_builder import build_graph, graph_to_plotly, get_graph_stats
from predictor import predict
from source_discovery import discover_sources, get_discovery_stats
from exit_poll import collect_exit_polls, is_exit_poll_time, aggregate_exit_polls

# --- Page Config ---
st.set_page_config(
    page_title="Referendum KG - Predizione Live",
    page_icon="\U0001f1ee\U0001f1f9",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Viewport meta tag: prevent unwanted zoom on mobile ---
# --- Google Analytics (invisible to visitors, data in GA dashboard) ---
_GA_ID = os.environ.get("GA_MEASUREMENT_ID", "")
_ga_snippet = ""
if _GA_ID:
    _ga_snippet = f"""
    if (!window.parent.document.querySelector('script[src*="gtag"]')) {{
        var s = document.createElement('script');
        s.async = true;
        s.src = 'https://www.googletagmanager.com/gtag/js?id={_GA_ID}';
        window.parent.document.head.appendChild(s);
        var s2 = document.createElement('script');
        s2.textContent = "window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{_GA_ID}');";
        window.parent.document.head.appendChild(s2);
    }}
    """

components.html(f"""
<script>
(function() {{
    if (!document.querySelector('meta[name="viewport"]')) {{
        var meta = document.createElement('meta');
        meta.name = 'viewport';
        meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
        window.parent.document.head.appendChild(meta);
    }}
    {_ga_snippet}
}})();
</script>
""", height=0)

# --- CSS (rendered once, never refreshed) ---
st.markdown("""
<style>
    /* Hide Streamlit Deploy button */
    .stDeployButton,
    .stAppDeployButton,
    [data-testid="stAppDeployButton"],
    button[title="Deploy"],
    header[data-testid="stHeader"] a,
    .stMainMenu {
        display: none !important;
        visibility: hidden !important;
    }

    /* === DESKTOP (default) === */
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
    .disclaimer {
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 0.7rem;
        font-size: 0.8rem;
        margin-top: 0.8rem;
    }
    /* Tab styling desktop */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.4rem !important;
        border-radius: 8px 8px 0 0 !important;
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
    }
    div[data-baseweb="tab-list"] button p {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
    }

    /* === MOBILE (< 768px) === */
    @media (max-width: 768px) {
        /* Prevent overflow and horizontal scroll */
        .main .block-container {
            padding: 0.4rem 0.6rem !important;
            max-width: 100% !important;
            overflow-x: hidden !important;
        }
        .stApp {
            overflow-x: hidden !important;
        }

        /* Header compact */
        .main-header {
            padding: 0.8rem 1rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }
        .main-header h1 { font-size: 1rem !important; }
        .main-header p { font-size: 0.7rem !important; }
        .countdown-live { padding: 0.2rem 0.5rem; font-size: 0.75rem; }

        /* Metrics: 2x2 grid instead of 4 columns */
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            flex: 0 0 48% !important;
            max-width: 48% !important;
            margin-bottom: 0.3rem;
        }
        div[data-testid="stMetric"] {
            padding: 0.4rem !important;
        }
        div[data-testid="stMetric"] label {
            font-size: 0.65rem !important;
        }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            font-size: 1.1rem !important;
        }

        /* Tabs: scrollable, compact */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            -webkit-overflow-scrolling: touch;
        }
        .stTabs [data-baseweb="tab-list"] button {
            font-size: 0.75rem !important;
            padding: 0.4rem 0.6rem !important;
            white-space: nowrap !important;
            min-width: auto !important;
        }
        div[data-baseweb="tab-list"] button p {
            font-size: 0.75rem !important;
        }

        /* Plotly charts: full width, prevent overflow */
        .js-plotly-plot, .plotly {
            width: 100% !important;
            max-width: 100% !important;
        }
        .js-plotly-plot .plot-container {
            max-width: 100% !important;
        }

        /* Gauge labels */
        .gauge-label {
            font-size: 0.9rem !important;
        }

        /* Columns inside tabs: stack vertically */
        div[data-testid="stHorizontalBlock"]:not(:first-child) {
            flex-direction: column !important;
        }
        div[data-testid="stHorizontalBlock"]:not(:first-child) > div[data-testid="stColumn"] {
            flex: 0 0 100% !important;
            max-width: 100% !important;
        }

        /* Expanders compact */
        details summary {
            font-size: 0.8rem !important;
        }

        /* Disclaimer compact */
        .disclaimer {
            font-size: 0.7rem;
            padding: 0.5rem;
        }

        /* Dataframe scroll */
        div[data-testid="stDataFrame"] {
            overflow-x: auto !important;
            max-width: 100% !important;
        }

        /* Footer compact */
        .footer-mobile { font-size: 0.7rem; }
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

# --- Sidebar (static, outside fragment) ---
with st.sidebar:
    st.title("\u2699\ufe0f Controlli")

    st.markdown("### Aggiornamento")
    data_refresh = st.slider("Refresh dati (sec)", 1, 600, 5, step=1,
                             help="Intervallo di aggiornamento dati (il countdown e sempre live)")

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
        "Countdown live via JS, dati aggiornati via fragment."
    )
    st.markdown("---")
    st.caption("**Come usare su smartphone:**")
    st.caption("Apri il link nel browser, aggiungi a Home Screen per esperienza app-like.")

# --- Header with JS countdown (always animated, independent from data refresh) ---
st.markdown("""
<div class="main-header">
    <h1>\U0001f1ee\U0001f1f9 Referendum Knowledge Graph - Live</h1>
    <p>Riforma della Giustizia (Nordio) | 22-23 Marzo 2026</p>
    <p><span id="live-countdown" class="countdown-live">Caricamento...</span>
       &nbsp;|&nbsp; \U0001f551 <span id="live-clock">--:--:--</span></p>
</div>
""", unsafe_allow_html=True)

# JS countdown only - no page reload, runs purely client-side
components.html("""
<script>
(function() {
    function updateCountdown() {
        var el = window.parent.document.getElementById('live-countdown');
        var clk = window.parent.document.getElementById('live-clock');
        if (!el) return;
        var target = new Date('2026-03-22T07:00:00Z').getTime();
        var end = new Date('2026-03-23T15:00:00Z').getTime();
        var now = Date.now();
        if (now > end) {
            el.innerHTML = '\\u{1F534} VOTO CONCLUSO';
        } else if (now > target) {
            var rem = Math.floor((end - now) / 1000);
            var h = Math.floor(rem / 3600);
            var m = Math.floor((rem % 3600) / 60);
            var s = rem % 60;
            el.innerHTML = '<span class="live-dot"></span> VOTAZIONE IN CORSO - ' +
                String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
        } else {
            var rem = Math.floor((target - now) / 1000);
            var d = Math.floor(rem / 86400);
            var h = Math.floor((rem % 86400) / 3600);
            var m = Math.floor((rem % 3600) / 60);
            var s = rem % 60;
            el.innerHTML = '\\u{1F7E1} ' + d + 'g ' +
                String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0') + ' al voto';
        }
        if (clk) clk.textContent = new Date().toLocaleTimeString('it-IT');
    }
    setInterval(updateCountdown, 1000);
    updateCountdown();
})();
</script>
""", height=0)


# --- Cached data loading functions ---
@st.cache_data(ttl=config.CACHE_TTL_SECONDS, show_spinner="Recupero dati live...")
def load_data(extra_feeds_keys=None, extra_feeds=None):
    articles, statuses = fetch_all_feeds(extra_feeds)
    polls = get_all_polls(articles)
    return articles, statuses, polls


@st.cache_data(ttl=900, show_spinner="Scoperta nuove fonti...")
def run_discovery():
    return discover_sources(max_new=50)


# ============================================================
# FRAGMENT: all dynamic content lives here.
# Only this section re-renders at each interval - no full page flash.
# ============================================================
@st.fragment(run_every=timedelta(seconds=data_refresh))
def live_dashboard():
    # --- Source Discovery ---
    if show_discovery:
        try:
            discovered = run_discovery()
            st.session_state.discovered_sources = discovered
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

    # --- Load data ---
    try:
        extra_keys = tuple(sorted(extra.keys())) if extra else None
        articles, feed_statuses, polls = load_data(extra_keys, extra if extra else None)
        st.session_state.fetch_count += 1
    except Exception as e:
        st.error(f"Errore nel caricamento dati: {str(e)}")
        articles, feed_statuses, polls = [], [], config.KNOWN_POLLS

    # --- Collect Exit Polls ---
    exit_polls = collect_exit_polls(articles) if is_exit_poll_time() else []

    # --- Build KG and Predict ---
    graph = build_graph(articles, polls)
    prediction = predict(articles, polls, exit_polls)

    # Store prediction history
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

    # --- Row 1: Key Metrics ---
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
        f"Ultimo refresh: {datetime.now().strftime('%H:%M:%S')} | "
        f"Prossimo tra {data_refresh}s"
    )

    # --- Tabs ---
    tab_kg, tab_pred, tab_exitpoll, tab_party, tab_articles, tab_discovery, tab_method = st.tabs([
        "\U0001f578\ufe0f Knowledge Graph",
        "\U0001f4ca Predizione",
        "\U0001f3af Exit Poll",
        "\U0001f3db\ufe0f Partiti",
        "\U0001f4f0 Articoli",
        "\U0001f50d Discovery",
        "\U0001f4d6 Metodologia",
    ])

    # --- Tab 1: Knowledge Graph ---
    with tab_kg:
        st.caption("Tocca e trascina per esplorare il grafo. Pizzica per zoom.")
        fig_kg = graph_to_plotly(graph)
        fig_kg.update_layout(height=500)
        st.plotly_chart(fig_kg, use_container_width=True,
                        config={"scrollZoom": True, "displayModeBar": False})

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
            # --- Gauge SI ---
            st.markdown(
                f"<h4 style='color:{config.COLOR_SI}; text-align:center; margin-bottom:0;'>"
                f"\u2705 SI (Approvare la riforma)</h4>",
                unsafe_allow_html=True,
            )
            fig_si = go.Figure(go.Indicator(
                mode="gauge+number",
                value=prediction.si_probability * 100,
                number={"suffix": "%", "font": {"size": 36, "color": config.COLOR_SI}},
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
            ))
            fig_si.update_layout(
                height=220, margin=dict(t=10, b=10, l=30, r=30),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_si, use_container_width=True)

            # --- Gauge NO ---
            st.markdown(
                f"<h4 style='color:{config.COLOR_NO}; text-align:center; margin-bottom:0;'>"
                f"\u274c NO (Respingere la riforma)</h4>",
                unsafe_allow_html=True,
            )
            fig_no = go.Figure(go.Indicator(
                mode="gauge+number",
                value=prediction.no_probability * 100,
                number={"suffix": "%", "font": {"size": 36, "color": config.COLOR_NO}},
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
            ))
            fig_no.update_layout(
                height=220, margin=dict(t=10, b=10, l=30, r=30),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_no, use_container_width=True)

        with pcol2:
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

            if show_signals and prediction.signals:
                st.markdown("#### Segnali del Modello")
                for signal in prediction.signals:
                    leader = "SI" if signal.si_probability > 0.5 else "NO"
                    leader_pct = max(signal.si_probability, signal.no_probability)

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
            st.plotly_chart(fig_timeline, use_container_width=True)

    # --- Tab 3: Exit Poll ---
    with tab_exitpoll:
        ep_active = is_exit_poll_time()

        if ep_active and exit_polls:
            ep_agg = aggregate_exit_polls(exit_polls)
            si_val = ep_agg["si_pct"]
            no_val = ep_agg["no_pct"]
            ep_confidence = ep_agg["confidence"]

            st.markdown(
                "<div style='text-align:center; padding:0.5rem;'>"
                "<span class='live-dot'></span> "
                "<strong style='font-size:1.1rem;'>EXIT POLL LIVE</strong> "
                f"- {ep_agg['count']} fonti rilevate"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            si_val = 50.0
            no_val = 50.0
            ep_confidence = 0.0

        epc1, epc2 = st.columns(2)

        with epc1:
            st.markdown(
                f"<h4 style='color:{config.COLOR_SI}; text-align:center; margin-bottom:0;'>"
                f"SI</h4>",
                unsafe_allow_html=True,
            )
            fig_ep_si = go.Figure(go.Indicator(
                mode="gauge+number+delta" if ep_active and exit_polls else "gauge+number",
                value=si_val,
                number={"suffix": "%", "font": {"size": 48, "color": config.COLOR_SI}},
                delta={"reference": 50, "increasing": {"color": config.COLOR_SI},
                       "decreasing": {"color": config.COLOR_NO}} if ep_active and exit_polls else None,
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 2, "dtick": 10,
                             "tickcolor": "#333", "tickfont": {"size": 12}},
                    "bar": {"color": config.COLOR_SI if ep_active and exit_polls else "#bdc3c7",
                            "thickness": 0.8},
                    "bgcolor": "#f0f0f0",
                    "borderwidth": 2,
                    "bordercolor": "#ddd",
                    "steps": [
                        {"range": [0, 30], "color": "#fadbd8"},
                        {"range": [30, 45], "color": "#fdebd0"},
                        {"range": [45, 55], "color": "#fef9e7"},
                        {"range": [55, 70], "color": "#d5f5e3"},
                        {"range": [70, 100], "color": "#abebc6"},
                    ],
                    "threshold": {
                        "line": {"color": "#2c3e50", "width": 4},
                        "thickness": 0.9, "value": 50,
                    },
                },
            ))
            fig_ep_si.update_layout(
                height=280, margin=dict(t=30, b=10, l=30, r=30),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_ep_si, use_container_width=True)

        with epc2:
            st.markdown(
                f"<h4 style='color:{config.COLOR_NO}; text-align:center; margin-bottom:0;'>"
                f"NO</h4>",
                unsafe_allow_html=True,
            )
            fig_ep_no = go.Figure(go.Indicator(
                mode="gauge+number+delta" if ep_active and exit_polls else "gauge+number",
                value=no_val,
                number={"suffix": "%", "font": {"size": 48, "color": config.COLOR_NO}},
                delta={"reference": 50, "increasing": {"color": config.COLOR_NO},
                       "decreasing": {"color": config.COLOR_SI}} if ep_active and exit_polls else None,
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 2, "dtick": 10,
                             "tickcolor": "#333", "tickfont": {"size": 12}},
                    "bar": {"color": config.COLOR_NO if ep_active and exit_polls else "#bdc3c7",
                            "thickness": 0.8},
                    "bgcolor": "#f0f0f0",
                    "borderwidth": 2,
                    "bordercolor": "#ddd",
                    "steps": [
                        {"range": [0, 30], "color": "#d5f5e3"},
                        {"range": [30, 45], "color": "#fdebd0"},
                        {"range": [45, 55], "color": "#fef9e7"},
                        {"range": [55, 70], "color": "#fadbd8"},
                        {"range": [70, 100], "color": "#f5b7b1"},
                    ],
                    "threshold": {
                        "line": {"color": "#2c3e50", "width": 4},
                        "thickness": 0.9, "value": 50,
                    },
                },
            ))
            fig_ep_no.update_layout(
                height=280, margin=dict(t=30, b=10, l=30, r=30),
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_ep_no, use_container_width=True)

        if not ep_active:
            # Show waiting state
            import math
            now = datetime.now(timezone.utc)
            threshold = config.EXIT_POLL_AVAILABLE_AFTER.replace(tzinfo=timezone.utc)
            remaining = threshold - now
            hours_left = remaining.total_seconds() / 3600

            st.markdown(
                "<div style='text-align:center; padding:1.5rem; background:linear-gradient(135deg,#f8f9fa,#e9ecef); "
                "border-radius:12px; margin:1rem 0;'>"
                "<h3 style='color:#6c757d; margin:0;'>In attesa degli exit poll...</h3>"
                f"<p style='color:#adb5bd; margin:0.5rem 0 0 0;'>Disponibili dopo le 15:00 del 23 marzo 2026"
                f" ({hours_left:.0f} ore rimanenti)</p>"
                "<p style='color:#ced4da; font-size:0.85rem; margin-top:0.5rem;'>"
                "Le lancette si attiveranno automaticamente quando i primi exit poll saranno pubblicati."
                "</p></div>",
                unsafe_allow_html=True,
            )

            st.markdown("#### Fonti exit poll monitorate")
            for source_name in config.EXIT_POLL_SOURCES:
                st.markdown(f"- {source_name}")

        elif exit_polls:
            # Show exit poll details
            st.markdown("#### Dettaglio Exit Poll Rilevati")
            for ep in exit_polls:
                icon = "📊" if ep.is_projection else "🗳️"
                st.markdown(
                    f"{icon} **{ep.source}** | "
                    f"SI {ep.si_pct}% - NO {ep.no_pct}% | "
                    f"Affidabilita: {ep.reliability:.0%} | "
                    f"{ep.note}"
                )

            st.markdown(
                f"<div style='text-align:center; padding:0.8rem; background:#d4edda; "
                f"border-radius:8px; margin-top:1rem;'>"
                f"<strong>Media ponderata:</strong> SI {si_val:.1f}% - NO {no_val:.1f}% "
                f"| Confidenza: {ep_confidence:.0%}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "Votazione conclusa ma nessun exit poll ancora rilevato nei feed RSS. "
                "Gli agenti continuano a cercare - i dati appariranno automaticamente."
            )

    # --- Tab 4: Partiti ---
    with tab_party:
        pc1, pc2 = st.columns(2)
        si_parties = {k: v for k, v in config.PARTY_POSITIONS.items() if v["position"] == "SI"}
        no_parties = {k: v for k, v in config.PARTY_POSITIONS.items() if v["position"] == "NO"}

        with pc1:
            total_si = sum(p["estimated_support_pct"] for p in si_parties.values())
            st.markdown("### \u2705 Schieramento SI")
            st.metric("Consenso aggregato", f"{total_si:.1f}%")
            for pid, pdata in sorted(si_parties.items(), key=lambda x: -x[1]["estimated_support_pct"]):
                st.markdown(f"**{pdata['name']}** ({pdata['estimated_support_pct']}%) - {pdata['leader']}")

        with pc2:
            total_no = sum(p["estimated_support_pct"] for p in no_parties.values())
            st.markdown("### \u274c Schieramento NO")
            st.metric("Consenso aggregato", f"{total_no:.1f}%")
            for pid, pdata in sorted(no_parties.items(), key=lambda x: -x[1]["estimated_support_pct"]):
                st.markdown(f"**{pdata['name']}** ({pdata['estimated_support_pct']}%) - {pdata['leader']}")

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
        st.plotly_chart(fig_parties, use_container_width=True)

    # --- Tab 4: Articles ---
    with tab_articles:
        if articles:
            st.markdown(f"**{len(articles)} articoli rilevanti trovati**")
            for article in articles[:20]:
                icon = {
                    "SI": "\U0001f7e2", "NO": "\U0001f534", "NEUTRAL": "\u26aa"
                }.get(article.sentiment_direction, "\u26aa")

                with st.expander(f"{icon} [{article.source}] {article.title[:70]}", expanded=False):
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
        st.markdown("### \U0001f50d Discovery Multi-Agente")
        st.caption(
            "17 agenti RSS + 4 fetcher diretti (Reddit JSON, Telegram, Bluesky, Mastodon) "
            "scandagliano la rete in parallelo senza API key."
        )

        # Show agent breakdown (three rows for readability)
        from source_discovery import DISCOVERY_AGENTS
        agent_items = list(DISCOVERY_AGENTS.items())
        row1 = agent_items[:6]
        row2 = agent_items[6:12]
        row3 = agent_items[12:]
        cols1 = st.columns(len(row1))
        for i, (agent_name, count) in enumerate(row1):
            cols1[i].metric(agent_name, f"{count} fonti")
        cols2 = st.columns(len(row2))
        for i, (agent_name, count) in enumerate(row2):
            cols2[i].metric(agent_name, f"{count} fonti")
        cols3 = st.columns(len(row3))
        for i, (agent_name, count) in enumerate(row3):
            cols3[i].metric(agent_name, f"{count} fonti")

        # Social platform direct fetcher stats
        st.markdown("#### Fetcher Diretti (accesso senza API key)")
        try:
            from social_fetchers import get_social_stats
            social_stats = get_social_stats(articles)
            if social_stats:
                platform_labels = {
                    "reddit": "Reddit JSON API",
                    "telegram": "Telegram Scraper",
                    "bluesky": "Bluesky API",
                    "mastodon": "Mastodon API",
                    "youtube": "YouTube RSS",
                }
                scols = st.columns(min(len(social_stats), 5))
                for i, (platform, stats) in enumerate(social_stats.items()):
                    label = platform_labels.get(platform, platform.title())
                    with scols[i % len(scols)]:
                        st.metric(label, f"{stats['count']} post")
                        si_pct = round(stats['si'] / stats['count'] * 100) if stats['count'] > 0 else 0
                        no_pct = round(stats['no'] / stats['count'] * 100) if stats['count'] > 0 else 0
                        st.caption(f"SI {si_pct}% | NO {no_pct}% | Eng: {stats['avg_engagement']:.2f}")
            else:
                st.info("Nessun dato dai fetcher social diretti in questo ciclo.")
        except Exception:
            st.info("Fetcher social diretti non ancora attivi.")

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

            if st.button("Riesegui Discovery"):
                st.cache_data.clear()
                st.rerun()
        else:
            st.info("Attiva 'Source Discovery' nella sidebar per scoprire nuove fonti.")

    # --- Tab 7: Metodologia ---
    with tab_method:
        st.markdown("### Come funziona questo strumento")
        st.caption(
            "Questo strumento non e un sondaggio. E un aggregatore sperimentale che combina "
            "segnali pubblicamente disponibili per produrre una stima indicativa dell'orientamento elettorale."
        )

        st.markdown("---")

        st.markdown("#### Modello a 5 segnali ([ensemble](https://it.wikipedia.org/wiki/Ensemble_learning))")
        st.markdown(
            "La predizione nasce dalla combinazione ponderata di segnali indipendenti, "
            "ispirati ai [modelli ensemble](https://en.wikipedia.org/wiki/Ensemble_learning) "
            "e agli aggregatori come [FiveThirtyEight](https://it.wikipedia.org/wiki/FiveThirtyEight)."
        )

        # Signal weights table
        from source_discovery import DISCOVERY_AGENTS as _DISC_AGENTS
        ep_active_now = is_exit_poll_time() and len(exit_polls) > 0

        sig_data = {
            "Segnale": ["Sondaggi", "Forza partitica", "Sentiment media", "Momentum", "Exit Poll"],
            "Peso normale": ["45%", "25%", "20%", "10%", "-"],
            "Peso con exit poll": ["15%", "10%", "15%", "10%", "50%"],
            "Stato attuale": [
                "Attivo", "Attivo", "Attivo", "Attivo",
                "ATTIVO" if ep_active_now else "In attesa (dopo le 15:00 del 23/03)"
            ],
        }
        st.dataframe(pd.DataFrame(sig_data), use_container_width=True, hide_index=True)

        with st.expander("Sondaggi (peso 45%)", expanded=False):
            st.markdown(
                "[Media ponderata](https://it.wikipedia.org/wiki/Media_ponderata) dei sondaggi disponibili. "
                "Ogni sondaggio e pesato per "
                "**recenza** ([decay esponenziale](https://it.wikipedia.org/wiki/Decadimento_esponenziale): "
                "1.0, 0.8, 0.64...) e **dimensione del campione** "
                "(campioni > 1000 pesano di piu). Confidenza massima: 70%.\n\n"
                "Fonti: Ipsos, SWG, EMG, Tecne, Euromedia + sondaggi estratti automaticamente "
                "dal testo degli articoli tramite "
                "[espressioni regolari](https://it.wikipedia.org/wiki/Espressione_regolare).\n\n"
                "**Limite noto:** errore storico dei sondaggi referendari italiani ~13pp "
                "([referendum 2016](https://it.wikipedia.org/wiki/Referendum_costituzionale_in_Italia_del_2016))."
            )

        with st.expander("Forza partitica (peso 25%)", expanded=False):
            st.markdown(
                "Stima il bacino SI/NO sulla base del consenso elettorale dei partiti schierati.\n\n"
                "- **SI** (centrodestra + centristi): ~52%\n"
                "- **NO** (opposizione): ~40.5%\n\n"
                "Confidenza fissata al 40%: il voto partitico non si traduce linearmente "
                "nel voto referendario. Nel 2016 circa il 20% degli elettori PD voto in dissenso."
            )

        with st.expander("Sentiment media (peso 20%)", expanded=False):
            st.markdown(
                "Analizza il tono degli articoli da 80+ fonti con "
                "[keyword matching](https://en.wikipedia.org/wiki/Keyword_spotting) su 200+ termini "
                "([analisi del sentiment](https://it.wikipedia.org/wiki/Analisi_del_sentimento)).\n\n"
                "**Rilevamento negazioni:** il sistema verifica se nelle 4 parole precedenti a un keyword "
                "compare una negazione (non, mai, senza, mica...). Esempi:\n"
                '- "e una buona riforma" -> SI\n'
                '- "non e una buona riforma" -> NO\n'
                '- "non e pericolosa" -> SI\n\n'
                "**Limite noto:** non cattura [ironia](https://it.wikipedia.org/wiki/Ironia), "
                "sarcasmo o doppie negazioni complesse."
            )

        with st.expander("Momentum (peso 10%)", expanded=False):
            st.markdown(
                "Misura lo spostamento del sentiment nel tempo con "
                "[**decay esponenziale**](https://it.wikipedia.org/wiki/Decadimento_esponenziale) "
                "([emivita](https://it.wikipedia.org/wiki/Emivita_(fisica)) 24h). "
                "Gli articoli delle ultime 48h vengono confrontati con quelli precedenti.\n\n"
                "Formula: `SI% = 0.5 + shift * 0.3` (coefficiente di smorzamento).\n\n"
                "La confidenza scala dinamicamente con il numero di articoli direzionali (max 40%)."
            )

        with st.expander("Exit Poll (peso 50%, solo post-voto)", expanded=False):
            st.markdown(
                "Si attiva automaticamente dopo le 15:00 del 23 marzo. "
                "Estrae dati dagli articoli con 3 pattern "
                "[regex](https://it.wikipedia.org/wiki/Espressione_regolare):\n\n"
                '1. Percentuali dirette: "si 47,3%" / "no 52,7%"\n'
                '2. Percentuali invertite: "47,3% per il si"\n'
                '3. Range: "si tra 45 e 49" (usa il punto medio)\n\n'
                "Fonti monitorate: Consorzio Opinio (Rai), "
                "[Quorum/YouTrend](https://it.wikipedia.org/wiki/YouTrend) (Sky TG24), "
                "Tecne (Mediaset), SWG (La7), Piepoli, EMG Different.\n\n"
                "Quando attivo, ridistribuisce i pesi e restringe "
                "l'[intervallo di confidenza](https://it.wikipedia.org/wiki/Intervallo_di_confidenza)."
            )

        st.markdown("---")
        st.markdown("#### Discovery Multi-Agente")
        st.markdown("6 agenti specializzati scandagliano la rete in parallelo:")

        agent_info = {
            "Agente": list(_DISC_AGENTS.keys()),
            "Fonti": list(_DISC_AGENTS.values()),
        }
        st.dataframe(pd.DataFrame(agent_info), use_container_width=True, hide_index=True)

        st.markdown(
            f"**Totale fonti candidate:** {sum(_DISC_AGENTS.values())} (discovery) + "
            f"{len(config.RSS_FEEDS)} (configurate) = {sum(_DISC_AGENTS.values()) + len(config.RSS_FEEDS)}"
        )

        st.markdown("---")
        st.markdown("#### Auto-calibrazione")
        st.markdown(
            "Ogni segnale ha un livello di "
            "[**confidenza**](https://it.wikipedia.org/wiki/Intervallo_di_confidenza) "
            "che moltiplica il suo peso base. "
            "Se un segnale ha pochi dati, la sua confidenza scende e pesa meno nella predizione finale. "
            "Questo rende il modello robusto anche con dati incompleti "
            "([calibrazione](https://en.wikipedia.org/wiki/Calibration_(statistics)))."
        )

        st.markdown("---")
        st.markdown(
            "#### [Intervallo di confidenza](https://it.wikipedia.org/wiki/Intervallo_di_confidenza)"
        )
        st.markdown(
            "Calibrato sull'errore storico del "
            "[referendum 2016](https://it.wikipedia.org/wiki/Referendum_costituzionale_in_Italia_del_2016) "
            "(~13pp).\n\n"
            "- **Pre-voto:** margine ~9.5pp con confidenza al 53%\n"
            "- **Con [exit poll](https://it.wikipedia.org/wiki/Exit_poll):** margine ridotto a 2-3pp\n\n"
            "Formula: `margine = errore_base * (1 - confidenza * 0.5)`"
        )

        st.markdown("---")
        st.markdown("#### Changelog versioni")

        versions = [
            {
                "Versione": "3.0",
                "Data": "19 marzo 2026",
                "Novita": (
                    "Tab Exit Poll con gauge a lancetta (attivo post-voto). "
                    "Agente 6 (Exit Poll & Risultati, 10 fonti). "
                    "Rilevamento negazioni nel sentiment. "
                    "Momentum con decay esponenziale (emivita 24h). "
                    "Keyword affluenza/partecipazione (200+ termini). "
                    "Tab Metodologia integrato nell'app."
                ),
            },
            {
                "Versione": "2.0",
                "Data": "15 marzo 2026",
                "Novita": (
                    "Discovery multi-agente (5 agenti, 54 fonti). "
                    "Lessico sentiment espanso a 187 termini. "
                    "Redesign mobile-responsive completo. "
                    "Countdown JS indipendente dal refresh dati."
                ),
            },
            {
                "Versione": "1.0",
                "Data": "10 marzo 2026",
                "Novita": (
                    "Rilascio iniziale. Knowledge Graph con NetworkX. "
                    "4 segnali di predizione (sondaggi, partiti, sentiment, momentum). "
                    "8 feed RSS configurati. Dashboard Streamlit."
                ),
            },
        ]
        st.dataframe(pd.DataFrame(versions), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown(
            "**Metodologia completa:** "
            "[METODOLOGIA.md su GitHub](https://github.com/mfantin/referendum-kgraph/blob/main/METODOLOGIA.md)"
        )
        st.markdown(
            "**Riferimenti:** "
            "[Dietterich (2000)](https://en.wikipedia.org/wiki/Ensemble_learning) - Ensemble Methods | "
            "[Liu (2012)](https://en.wikipedia.org/wiki/Sentiment_analysis) - Sentiment Analysis | "
            "[Silver (2012)](https://it.wikipedia.org/wiki/Nate_Silver) - The Signal and the Noise | "
            "[McCombs & Shaw (1972)](https://it.wikipedia.org/wiki/Agenda_setting) - Agenda Setting | "
            "[Mitofsky (1991)](https://en.wikipedia.org/wiki/Warren_Mitofsky) - Exit Polls"
        )

    # --- Feed Status ---
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
    fc1, fc2, fc3 = st.columns(3)
    fc1.caption(f"\U0001f4e1 {sum(1 for s in feed_statuses if s.success)}/{len(feed_statuses)} feed attivi")
    fc2.caption(f"\U0001f4f0 {len(articles)} articoli analizzati")
    fc3.caption(f"\U0001f504 Aggiornamento #{st.session_state.fetch_count}")


# --- Run the fragment ---
live_dashboard()

# --- Static footer (outside fragment, rendered once) ---
st.markdown("""
<div class="disclaimer">
    <strong>\u26a0\ufe0f Disclaimer:</strong> Strumento sperimentale. Le predizioni sono basate su
    feed RSS pubblici, sondaggi pre-esistenti e analisi del sentiment con euristiche semplici.
    Non sostituisce analisi elettorali professionali.
    Nessun quorum richiesto per questo referendum confermativo.
    <br><br>
    <strong>\u00a9 2026 Mauro Fantin.</strong> Tutti i diritti riservati.
    Built with Streamlit, NetworkX, Plotly |
    <a href="https://github.com/mfantin/referendum-kgraph" target="_blank">GitHub</a> | Open Source
</div>
""", unsafe_allow_html=True)
