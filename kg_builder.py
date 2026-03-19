"""
Knowledge Graph builder: constructs and visualizes the referendum KG.
"""

import networkx as nx
import plotly.graph_objects as go
import numpy as np

import config
from data_fetcher import Article


def build_graph(articles: list[Article], polls: list[dict]) -> nx.DiGraph:
    """Build the complete knowledge graph from articles and polls."""
    G = nx.DiGraph()

    _add_central_node(G)
    _add_outcome_nodes(G)
    _add_topic_nodes(G)
    _add_party_nodes(G)
    _add_politician_nodes(G)
    _add_poll_nodes(G, polls)
    _add_article_nodes(G, articles)
    _add_sentiment_aggregate(G, articles)

    return G


def _add_central_node(G: nx.DiGraph):
    G.add_node("Referendum", type="referendum", color=config.NODE_COLORS["referendum"],
               label="Referendum\n22-23 Mar 2026", size=50)


def _add_outcome_nodes(G: nx.DiGraph):
    G.add_node("SI", type="outcome", color=config.NODE_COLORS["outcome_si"],
               label="SI (Approvare)", size=40)
    G.add_node("NO", type="outcome", color=config.NODE_COLORS["outcome_no"],
               label="NO (Respingere)", size=40)
    G.add_edge("Referendum", "SI", relationship="POSSIBLE_OUTCOME", weight=0.5)
    G.add_edge("Referendum", "NO", relationship="POSSIBLE_OUTCOME", weight=0.5)


def _add_topic_nodes(G: nx.DiGraph):
    topics = [
        ("Separazione Carriere", "Separazione tra giudici e PM"),
        ("Sdoppiamento CSM", "Due CSM distinti per giudicanti e requirenti"),
        ("Sorteggio Membri", "Selezione per sorteggio dei membri laici"),
        ("Alta Corte Disciplinare", "Nuova corte per procedimenti disciplinari"),
    ]
    for topic_name, description in topics:
        G.add_node(topic_name, type="topic", color=config.NODE_COLORS["topic"],
                   label=topic_name, description=description, size=25)
        G.add_edge("Referendum", topic_name, relationship="CONTAINS_TOPIC", weight=0.8)


def _add_party_nodes(G: nx.DiGraph):
    for party_id, party_data in config.PARTY_POSITIONS.items():
        position = party_data["position"]
        color_key = "party_si" if position == "SI" else "party_no"
        G.add_node(
            party_id,
            type="party",
            color=config.NODE_COLORS[color_key],
            label=f"{party_data['name']}\n({position})",
            full_name=party_data["name"],
            position=position,
            support_pct=party_data["estimated_support_pct"],
            size=max(15, party_data["estimated_support_pct"]),
        )
        target = "SI" if position == "SI" else "NO"
        G.add_edge(party_id, target,
                   relationship="SUPPORTS",
                   weight=party_data["estimated_support_pct"] / 100)


def _add_politician_nodes(G: nx.DiGraph):
    for party_id, party_data in config.PARTY_POSITIONS.items():
        for figure in party_data["key_figures"]:
            G.add_node(
                figure,
                type="politician",
                color=config.NODE_COLORS["politician"],
                label=figure,
                party=party_id,
                position=party_data["position"],
                size=20,
            )
            G.add_edge(figure, party_id, relationship="MEMBER_OF", weight=0.9)


def _add_poll_nodes(G: nx.DiGraph, polls: list[dict]):
    for i, poll in enumerate(polls[:10]):  # Limit to latest 10
        node_id = f"Poll_{poll['source']}_{poll['date']}"
        si = poll["si_pct"]
        no = poll["no_pct"]
        G.add_node(
            node_id,
            type="poll",
            color=config.NODE_COLORS["poll"],
            label=f"{poll['source']}\n{poll['date']}\nSI:{si}% NO:{no}%",
            si_pct=si,
            no_pct=no,
            date=poll["date"],
            source=poll["source"],
            size=20,
        )
        # Edge weight proportional to SI percentage
        G.add_edge(node_id, "SI", relationship="INDICATES", weight=si / 100)
        G.add_edge(node_id, "NO", relationship="INDICATES", weight=no / 100)
        G.add_edge(node_id, "Referendum", relationship="MEASURES", weight=0.7)


def _add_article_nodes(G: nx.DiGraph, articles: list[Article]):
    # Add only top articles to keep graph readable
    top_articles = sorted(articles, key=lambda a: a.relevance, reverse=True)[:15]

    for i, article in enumerate(top_articles):
        node_id = f"Art_{i}_{article.source[:10]}"
        G.add_node(
            node_id,
            type="article",
            color=config.NODE_COLORS["article"],
            label=article.title[:40] + "...",
            full_title=article.title,
            source=article.source,
            url=article.url,
            sentiment=article.sentiment_direction,
            sentiment_score=article.sentiment_score,
            relevance=article.relevance,
            size=12,
        )

        # Link to outcome based on sentiment
        if article.sentiment_direction == "SI":
            G.add_edge(node_id, "SI", relationship="FAVORS", weight=abs(article.sentiment_score) * 0.5)
        elif article.sentiment_direction == "NO":
            G.add_edge(node_id, "NO", relationship="FAVORS", weight=abs(article.sentiment_score) * 0.5)

        # Link to mentioned parties
        for party in article.mentioned_parties:
            if party in G:
                G.add_edge(node_id, party, relationship="MENTIONS", weight=0.3)

        # Link to mentioned politicians
        for politician in article.mentioned_entities:
            if politician in G:
                G.add_edge(node_id, politician, relationship="MENTIONS", weight=0.3)


def _add_sentiment_aggregate(G: nx.DiGraph, articles: list[Article]):
    """Add aggregate sentiment signal nodes."""
    if not articles:
        return

    si_articles = [a for a in articles if a.sentiment_direction == "SI"]
    no_articles = [a for a in articles if a.sentiment_direction == "NO"]
    neutral_articles = [a for a in articles if a.sentiment_direction == "NEUTRAL"]

    total = len(articles)
    si_pct = len(si_articles) / total * 100 if total > 0 else 0
    no_pct = len(no_articles) / total * 100 if total > 0 else 0

    G.add_node(
        "Sentiment_Media",
        type="sentiment",
        color=config.COLOR_SI if si_pct > no_pct else config.COLOR_NO,
        label=f"Sentiment Media\nSI:{si_pct:.0f}% NO:{no_pct:.0f}%",
        si_pct=si_pct,
        no_pct=no_pct,
        neutral_pct=100 - si_pct - no_pct,
        total_articles=total,
        size=30,
    )
    G.add_edge("Sentiment_Media", "SI", relationship="INDICATES", weight=si_pct / 100)
    G.add_edge("Sentiment_Media", "NO", relationship="INDICATES", weight=no_pct / 100)
    G.add_edge("Sentiment_Media", "Referendum", relationship="MEASURES", weight=0.6)


def get_graph_stats(G: nx.DiGraph) -> dict:
    """Get graph statistics by node type."""
    stats = {"total_nodes": G.number_of_nodes(), "total_edges": G.number_of_edges()}
    type_counts = {}
    for _, data in G.nodes(data=True):
        t = data.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    stats["by_type"] = type_counts
    return stats


def _get_edge_color(G, edge):
    """Determine edge color based on relationship type."""
    rel = edge[2].get("relationship", "")
    if rel in ("SUPPORTS", "FAVORS"):
        if G.nodes.get(edge[1], {}).get("color") == config.NODE_COLORS["outcome_si"]:
            return "rgba(46, 204, 113, 0.4)"
        return "rgba(231, 76, 60, 0.4)"
    if rel == "INDICATES":
        return "rgba(243, 156, 18, 0.4)"
    if rel == "MENTIONS":
        return "rgba(52, 152, 219, 0.2)"
    return "rgba(149, 165, 166, 0.3)"


# Order in which node types appear during the wave animation
_ANIMATION_LAYERS = [
    "referendum", "outcome", "topic", "sentiment",
    "party", "politician", "poll", "article",
]

TYPE_LABELS = {
    "referendum": "Referendum",
    "outcome": "Esiti",
    "topic": "Temi",
    "party": "Partiti",
    "politician": "Politici",
    "poll": "Sondaggi",
    "article": "Articoli",
    "sentiment": "Sentiment",
}


def _build_node_groups(G, pos):
    """Group nodes by type with positions, labels, hover text and sizes."""
    type_groups = {}
    for node, data in G.nodes(data=True):
        t = data.get("type", "unknown")
        if t not in type_groups:
            type_groups[t] = {"x": [], "y": [], "text": [], "hover": [],
                              "color": [], "size": [], "nodes": []}
        x, y = pos[node]
        type_groups[t]["x"].append(x)
        type_groups[t]["y"].append(y)
        type_groups[t]["text"].append(data.get("label", node)[:30])
        type_groups[t]["color"].append(data.get("color", "#95a5a6"))
        type_groups[t]["size"].append(data.get("size", 15))
        type_groups[t]["nodes"].append(node)

        hover_parts = [f"<b>{data.get('label', node)}</b>", f"Tipo: {t}"]
        if t == "poll":
            hover_parts.append(f"SI: {data.get('si_pct', '?')}% | NO: {data.get('no_pct', '?')}%")
        elif t == "article":
            hover_parts.append(f"Fonte: {data.get('source', '?')}")
            hover_parts.append(f"Sentiment: {data.get('sentiment', '?')}")
        elif t == "party":
            hover_parts.append(f"Posizione: {data.get('position', '?')}")
            hover_parts.append(f"Consenso stimato: {data.get('support_pct', '?')}%")
        type_groups[t]["hover"].append("<br>".join(hover_parts))

    return type_groups


def _build_edge_traces(G, pos, visible_nodes=None):
    """Build edge traces, optionally filtering to only edges between visible nodes."""
    edge_traces = []
    for edge in G.edges(data=True):
        if visible_nodes is not None:
            if edge[0] not in visible_nodes or edge[1] not in visible_nodes:
                continue
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        weight = edge[2].get("weight", 0.3)
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            line=dict(width=max(1, weight * 4), color=_get_edge_color(G, edge)),
            hoverinfo="none",
            mode="lines",
            showlegend=False,
        ))
    return edge_traces


def _build_node_traces(type_groups, visible_types=None, pulse_type=None):
    """Build node traces, optionally showing only certain types."""
    node_traces = []
    for t in _ANIMATION_LAYERS:
        if t not in type_groups:
            continue
        group = type_groups[t]
        is_visible = visible_types is None or t in visible_types
        sizes = list(group["size"])

        # Pulse effect: enlarge the pulsing type slightly
        if pulse_type and t == pulse_type:
            sizes = [s * 1.25 for s in sizes]

        node_traces.append(go.Scatter(
            x=group["x"] if is_visible else [],
            y=group["y"] if is_visible else [],
            mode="markers+text",
            name=TYPE_LABELS.get(t, t.capitalize()),
            text=group["text"] if is_visible else [],
            textposition="top center",
            textfont=dict(size=9, color="#2c3e50"),
            hovertext=group["hover"] if is_visible else [],
            hoverinfo="text",
            marker=dict(
                color=group["color"] if is_visible else [],
                size=sizes if is_visible else [],
                line=dict(width=1.5, color="#2c3e50"),
                opacity=0.9,
            ),
        ))

    # Add any types not in _ANIMATION_LAYERS
    for t, group in type_groups.items():
        if t in _ANIMATION_LAYERS:
            continue
        is_visible = visible_types is None or t in visible_types
        node_traces.append(go.Scatter(
            x=group["x"] if is_visible else [],
            y=group["y"] if is_visible else [],
            mode="markers+text",
            name=TYPE_LABELS.get(t, t.capitalize()),
            text=group["text"] if is_visible else [],
            textposition="top center",
            textfont=dict(size=9, color="#2c3e50"),
            hovertext=group["hover"] if is_visible else [],
            hoverinfo="text",
            marker=dict(
                color=group["color"] if is_visible else [],
                size=group["size"] if is_visible else [],
                line=dict(width=1.5, color="#2c3e50"),
                opacity=0.9,
            ),
        ))
    return node_traces


def graph_to_plotly(G: nx.DiGraph) -> go.Figure:
    """Convert the knowledge graph to an animated Plotly figure with wave entrance."""
    if G.number_of_nodes() == 0:
        fig = go.Figure()
        fig.add_annotation(text="Nessun dato disponibile", x=0.5, y=0.5,
                          showarrow=False, font=dict(size=20))
        return fig

    # Use spring layout with fixed seed for reproducibility
    pos = nx.spring_layout(G, seed=config.GRAPH_LAYOUT_SEED, k=2.5, iterations=50)

    type_groups = _build_node_groups(G, pos)

    # Determine which types are actually present, in animation order
    present_types = [t for t in _ANIMATION_LAYERS if t in type_groups]
    extra_types = [t for t in type_groups if t not in _ANIMATION_LAYERS]
    present_types.extend(extra_types)

    # --- Build animation frames ---
    # Each frame reveals one more layer of node types + their edges
    frames = []
    for step in range(len(present_types)):
        visible_types = set(present_types[:step + 1])
        visible_nodes = set()
        for t in visible_types:
            visible_nodes.update(type_groups[t]["nodes"])

        frame_edges = _build_edge_traces(G, pos, visible_nodes)
        # Pulse the newly added type
        pulse = present_types[step]
        frame_nodes = _build_node_traces(type_groups, visible_types, pulse_type=pulse)

        frames.append(go.Frame(
            data=frame_edges + frame_nodes,
            name=f"step_{step}",
        ))

    # Final "settled" frame: all nodes, no pulse
    all_nodes = set()
    for t in present_types:
        all_nodes.update(type_groups[t]["nodes"])
    final_edges = _build_edge_traces(G, pos, all_nodes)
    final_nodes = _build_node_traces(type_groups)
    frames.append(go.Frame(
        data=final_edges + final_nodes,
        name="final",
    ))

    # --- Initial state: only first layer ---
    init_visible = {present_types[0]} if present_types else set()
    init_nodes_set = set()
    for t in init_visible:
        init_nodes_set.update(type_groups[t]["nodes"])
    init_edges = _build_edge_traces(G, pos, init_nodes_set)
    init_nodes = _build_node_traces(type_groups, init_visible, pulse_type=present_types[0] if present_types else None)

    fig = go.Figure(
        data=init_edges + init_nodes,
        frames=frames,
    )

    # Calculate frame duration: spread over ~3 seconds total
    n_frames = len(frames)
    frame_duration = max(80, 3000 // max(n_frames, 1))

    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        hovermode="closest",
        margin=dict(b=10, l=10, r=10, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#fafafa",
        paper_bgcolor="#fafafa",
        height=600,
        updatemenus=[{
            "type": "buttons",
            "showactive": False,
            "x": 0.0,
            "y": -0.02,
            "xanchor": "left",
            "yanchor": "top",
            "buttons": [
                {
                    "label": "Anima",
                    "method": "animate",
                    "args": [
                        None,
                        {
                            "frame": {"duration": frame_duration, "redraw": True},
                            "fromcurrent": False,
                            "transition": {"duration": frame_duration * 0.6, "easing": "cubic-in-out"},
                            "mode": "immediate",
                        },
                    ],
                },
            ],
        }],
    )

    return fig
