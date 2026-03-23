"""
Knowledge Graph builder: constructs and visualizes the referendum KG.
"""

import networkx as nx
import plotly.graph_objects as go
import numpy as np

import config
from data_fetcher import Article


def build_graph(articles: list[Article], polls: list[dict],
                exit_polls=None) -> nx.DiGraph:
    """Build the complete knowledge graph from articles, polls, and exit polls."""
    G = nx.DiGraph()

    _add_central_node(G)
    _add_outcome_nodes(G)
    _add_topic_nodes(G)
    _add_party_nodes(G)
    _add_politician_nodes(G)
    _add_poll_nodes(G, polls)
    _add_article_nodes(G, articles)
    _add_social_platform_nodes(G, articles)
    _add_sentiment_aggregate(G, articles)
    if exit_polls:
        _add_exit_poll_nodes(G, exit_polls)

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
    for i, poll in enumerate(polls[:25]):  # Latest 25 polls
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
    # Split: RSS/news articles vs social posts
    news_articles = [a for a in articles if a.platform == "rss"]
    social_articles = [a for a in articles if a.platform != "rss"]

    # Scale graph nodes with data: up to 50 news + 50 social
    max_news = min(50, len(news_articles))
    max_social = min(50, len(social_articles))
    top_news = sorted(news_articles, key=lambda a: a.relevance, reverse=True)[:max_news]
    top_social = sorted(
        social_articles,
        key=lambda a: a.relevance * (1.0 + (a.engagement_score or 0.0)),
        reverse=True,
    )[:max_social]

    for i, article in enumerate(top_news + top_social):
        is_social = article.platform != "rss"
        prefix = "Social" if is_social else "Art"
        node_id = f"{prefix}_{i}_{article.source[:10]}"

        node_type = "social" if is_social else "article"
        color = config.NODE_COLORS.get(node_type, config.NODE_COLORS["article"])

        # Social posts with high engagement get bigger nodes
        base_size = 12
        if is_social and article.engagement_score:
            base_size = max(12, min(22, 12 + article.engagement_score * 10))

        G.add_node(
            node_id,
            type=node_type,
            color=color,
            label=article.title[:40] + "..." if len(article.title) > 40 else article.title,
            full_title=article.title,
            source=article.source,
            url=article.url,
            sentiment=article.sentiment_direction,
            sentiment_score=article.sentiment_score,
            relevance=article.relevance,
            platform=article.platform,
            engagement=article.engagement_score,
            size=base_size,
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

        # Link social posts to their platform hub node (added later)
        if is_social:
            platform_node = f"Platform_{article.platform}"
            if platform_node in G:
                G.add_edge(node_id, platform_node, relationship="POSTED_ON", weight=0.4)


def _add_social_platform_nodes(G: nx.DiGraph, articles: list[Article]):
    """Add hub nodes for each social platform with aggregated sentiment."""
    social_articles = [a for a in articles if a.platform != "rss"]
    if not social_articles:
        return

    # Group by platform
    platforms: dict[str, list[Article]] = {}
    for a in social_articles:
        platforms.setdefault(a.platform, []).append(a)

    platform_meta = {
        "reddit": {"label": "Reddit", "color": "#FF4500"},
        "telegram": {"label": "Telegram", "color": "#0088CC"},
        "bluesky": {"label": "Bluesky", "color": "#0085FF"},
        "mastodon": {"label": "Mastodon", "color": "#6364FF"},
        "youtube": {"label": "YouTube", "color": "#FF0000"},
    }

    for platform, arts in platforms.items():
        node_id = f"Platform_{platform}"
        meta = platform_meta.get(platform, {"label": platform.title(), "color": "#95a5a6"})

        si_count = sum(1 for a in arts if a.sentiment_direction == "SI")
        no_count = sum(1 for a in arts if a.sentiment_direction == "NO")
        total = len(arts)
        si_pct = si_count / total * 100 if total > 0 else 0
        no_pct = no_count / total * 100 if total > 0 else 0

        G.add_node(
            node_id,
            type="platform",
            color=meta["color"],
            label=f"{meta['label']}\n{total} post\nSI:{si_pct:.0f}% NO:{no_pct:.0f}%",
            platform=platform,
            post_count=total,
            si_pct=si_pct,
            no_pct=no_pct,
            size=max(20, min(35, 20 + total * 0.5)),
        )

        # Connect platform to Referendum
        G.add_edge(node_id, "Referendum", relationship="MONITORS", weight=0.5)

        # Connect platform to outcome based on dominant sentiment
        if si_pct > no_pct + 5:
            G.add_edge(node_id, "SI", relationship="LEANS_TOWARD", weight=si_pct / 100 * 0.4)
        elif no_pct > si_pct + 5:
            G.add_edge(node_id, "NO", relationship="LEANS_TOWARD", weight=no_pct / 100 * 0.4)

        # Link individual social posts to their platform
        for a_node, a_data in list(G.nodes(data=True)):
            if a_data.get("type") == "social" and a_data.get("platform") == platform:
                if not G.has_edge(a_node, node_id):
                    G.add_edge(a_node, node_id, relationship="POSTED_ON", weight=0.4)


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


def _add_exit_poll_nodes(G: nx.DiGraph, exit_polls):
    """Add exit poll / projection nodes to the graph."""
    for i, ep in enumerate(exit_polls):
        node_id = f"ExitPoll_{i}_{ep.source[:15]}"
        label_type = "Proiezione" if ep.is_projection else "Exit Poll"
        G.add_node(
            node_id,
            type="exit_poll",
            color="#e74c3c" if ep.no_pct > ep.si_pct else "#2ecc71",
            label=f"{label_type}\n{ep.source[:20]}\nSI:{ep.si_pct:.1f}% NO:{ep.no_pct:.1f}%",
            si_pct=ep.si_pct,
            no_pct=ep.no_pct,
            source=ep.source,
            reliability=ep.reliability,
            size=max(25, 20 + ep.reliability * 15),
        )
        G.add_edge(node_id, "SI", relationship="INDICATES", weight=ep.si_pct / 100)
        G.add_edge(node_id, "NO", relationship="INDICATES", weight=ep.no_pct / 100)
        G.add_edge(node_id, "Referendum", relationship="MEASURES", weight=0.9)


def get_graph_stats(G: nx.DiGraph) -> dict:
    """Get graph statistics by node type."""
    stats = {"total_nodes": G.number_of_nodes(), "total_edges": G.number_of_edges()}
    type_counts = {}
    for _, data in G.nodes(data=True):
        t = data.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    stats["by_type"] = type_counts
    return stats


def graph_to_plotly(G: nx.DiGraph) -> go.Figure:
    """Convert the knowledge graph to an interactive Plotly figure."""
    if G.number_of_nodes() == 0:
        fig = go.Figure()
        fig.add_annotation(text="Nessun dato disponibile", x=0.5, y=0.5,
                          showarrow=False, font=dict(size=20))
        return fig

    # Use spring layout with fixed seed for reproducibility
    pos = nx.spring_layout(G, seed=config.GRAPH_LAYOUT_SEED, k=2.5, iterations=50)

    # --- Edge traces ---
    edge_traces = []
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        rel = edge[2].get("relationship", "")
        weight = edge[2].get("weight", 0.3)

        # Color edges by type
        if rel in ("SUPPORTS", "FAVORS"):
            target_type = G.nodes.get(edge[1], {}).get("type", "")
            if G.nodes.get(edge[1], {}).get("color") == config.NODE_COLORS["outcome_si"]:
                edge_color = "rgba(46, 204, 113, 0.4)"
            else:
                edge_color = "rgba(231, 76, 60, 0.4)"
        elif rel == "INDICATES":
            edge_color = "rgba(243, 156, 18, 0.4)"
        elif rel == "MENTIONS":
            edge_color = "rgba(52, 152, 219, 0.2)"
        else:
            edge_color = "rgba(149, 165, 166, 0.3)"

        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            line=dict(width=max(1, weight * 4), color=edge_color),
            hoverinfo="none",
            mode="lines",
            showlegend=False,
        ))

    # --- Node traces (grouped by type for legend) ---
    type_groups = {}
    for node, data in G.nodes(data=True):
        t = data.get("type", "unknown")
        if t not in type_groups:
            type_groups[t] = {"x": [], "y": [], "text": [], "hover": [],
                              "color": [], "size": []}
        x, y = pos[node]
        type_groups[t]["x"].append(x)
        type_groups[t]["y"].append(y)
        type_groups[t]["text"].append(data.get("label", node)[:30])
        type_groups[t]["color"].append(data.get("color", "#95a5a6"))
        type_groups[t]["size"].append(data.get("size", 15))

        # Build hover text
        hover_parts = [f"<b>{data.get('label', node)}</b>", f"Tipo: {t}"]
        if t == "poll":
            hover_parts.append(f"SI: {data.get('si_pct', '?')}% | NO: {data.get('no_pct', '?')}%")
        elif t == "article":
            hover_parts.append(f"Fonte: {data.get('source', '?')}")
            hover_parts.append(f"Sentiment: {data.get('sentiment', '?')}")
        elif t == "social":
            hover_parts.append(f"Fonte: {data.get('source', '?')}")
            hover_parts.append(f"Piattaforma: {data.get('platform', '?')}")
            hover_parts.append(f"Sentiment: {data.get('sentiment', '?')}")
            eng = data.get('engagement')
            if eng:
                hover_parts.append(f"Engagement: {eng:.2f}")
        elif t == "platform":
            hover_parts.append(f"Post: {data.get('post_count', 0)}")
            hover_parts.append(f"SI: {data.get('si_pct', 0):.0f}% | NO: {data.get('no_pct', 0):.0f}%")
        elif t == "party":
            hover_parts.append(f"Posizione: {data.get('position', '?')}")
            hover_parts.append(f"Consenso stimato: {data.get('support_pct', '?')}%")
        type_groups[t]["hover"].append("<br>".join(hover_parts))

    TYPE_LABELS = {
        "referendum": "Referendum",
        "outcome": "Esiti",
        "topic": "Temi",
        "party": "Partiti",
        "politician": "Politici",
        "poll": "Sondaggi",
        "article": "Articoli",
        "social": "Post Social",
        "platform": "Piattaforme",
        "sentiment": "Sentiment",
    }

    node_traces = []
    for t, group in type_groups.items():
        node_traces.append(go.Scatter(
            x=group["x"], y=group["y"],
            mode="markers+text",
            name=TYPE_LABELS.get(t, t.capitalize()),
            text=group["text"],
            textposition="top center",
            textfont=dict(size=9, color="#2c3e50"),
            hovertext=group["hover"],
            hoverinfo="text",
            marker=dict(
                color=group["color"],
                size=group["size"],
                line=dict(width=1.5, color="#2c3e50"),
                opacity=0.9,
            ),
        ))

    fig = go.Figure(data=edge_traces + node_traces)
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
    )

    return fig
