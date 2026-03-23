"""
Prediction engine: aggregates signals into a referendum outcome prediction.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import config
from data_fetcher import Article
from exit_poll import ExitPollResult


@dataclass
class Signal:
    name: str
    si_probability: float
    no_probability: float
    confidence: float
    weight: float
    description: str = ""


@dataclass
class Prediction:
    si_probability: float
    no_probability: float
    confidence: float
    ci_low: float  # Confidence interval low for SI
    ci_high: float  # Confidence interval high for SI
    signals: list[Signal] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_points: int = 0


def _poll_signal(polls: list[dict]) -> Signal:
    """Aggregate polling data with recency weighting."""
    if not polls:
        return Signal("Sondaggi", 0.5, 0.5, 0.1, config.SIGNAL_WEIGHTS["polls"],
                      "Nessun dato disponibile")

    total_weight = 0.0
    weighted_si = 0.0

    for i, poll in enumerate(polls):
        # More recent polls get higher weight (exponential decay)
        recency_weight = 0.8 ** i
        sample_weight = 1.0
        if poll.get("sample_size"):
            sample_weight = min(2.0, poll["sample_size"] / 1000)

        w = recency_weight * sample_weight
        weighted_si += poll["si_pct"] / 100 * w
        total_weight += w

    if total_weight == 0:
        return Signal("Sondaggi", 0.5, 0.5, 0.1, config.SIGNAL_WEIGHTS["polls"])

    si_prob = weighted_si / total_weight
    no_prob = 1.0 - si_prob
    # More polls = more confidence; cap raised to 0.85
    confidence = min(0.85, len(polls) * 0.12)

    return Signal(
        "Sondaggi",
        round(si_prob, 4),
        round(no_prob, 4),
        confidence,
        config.SIGNAL_WEIGHTS["polls"],
        f"Media ponderata di {len(polls)} sondaggi",
    )


def _party_strength_signal() -> Signal:
    """Estimate based on party electoral strength and their positions."""
    si_support = 0.0
    no_support = 0.0

    for party_id, party_data in config.PARTY_POSITIONS.items():
        support = party_data["estimated_support_pct"]
        if party_data["position"] == "SI":
            si_support += support
        else:
            no_support += support

    total = si_support + no_support
    if total == 0:
        return Signal("Forza Partiti", 0.5, 0.5, 0.3, config.SIGNAL_WEIGHTS["party_strength"])

    si_prob = si_support / total
    no_prob = no_support / total

    # Party strength confidence raised: party positions are well-known facts
    n_parties = len(config.PARTY_POSITIONS)
    confidence = min(0.55, 0.3 + n_parties * 0.025)

    return Signal(
        "Forza Partiti",
        round(si_prob, 4),
        round(no_prob, 4),
        confidence,
        config.SIGNAL_WEIGHTS["party_strength"],
        f"Centrodestra (SI): {si_support:.0f}% | Opposizione (NO): {no_support:.0f}%",
    )


def _sentiment_signal(articles: list[Article]) -> Signal:
    """Aggregate media sentiment across all articles (RSS/news only)."""
    media_articles = [a for a in articles if a.platform == "rss"]
    if not media_articles:
        return Signal("Sentiment Media", 0.5, 0.5, 0.1, config.SIGNAL_WEIGHTS["media_sentiment"],
                      "Nessun articolo analizzato")

    si_count = sum(1 for a in media_articles if a.sentiment_direction == "SI")
    no_count = sum(1 for a in media_articles if a.sentiment_direction == "NO")
    total_directional = si_count + no_count

    if total_directional == 0:
        return Signal("Sentiment Media", 0.5, 0.5, 0.15, config.SIGNAL_WEIGHTS["media_sentiment"],
                      f"{len(media_articles)} articoli, tutti neutrali")

    # Weight by sentiment strength and relevance
    weighted_si = sum(
        a.sentiment_score * a.relevance
        for a in media_articles if a.sentiment_direction == "SI"
    )
    weighted_no = sum(
        abs(a.sentiment_score) * a.relevance
        for a in media_articles if a.sentiment_direction == "NO"
    )

    total_weighted = weighted_si + weighted_no
    if total_weighted == 0:
        si_prob = 0.5
    else:
        si_prob = 0.5 + (weighted_si - weighted_no) / (2 * total_weighted)

    si_prob = max(0.1, min(0.9, si_prob))
    no_prob = 1.0 - si_prob

    # Higher confidence scaling; cap raised to 0.80
    coverage = total_directional / max(len(media_articles), 1)
    confidence = min(0.80, total_directional * 0.04 + coverage * 0.2)

    return Signal(
        "Sentiment Media",
        round(si_prob, 4),
        round(no_prob, 4),
        confidence,
        config.SIGNAL_WEIGHTS["media_sentiment"],
        f"SI: {si_count} articoli | NO: {no_count} | Neutri: {len(media_articles) - total_directional} | Copertura: {coverage:.0%}",
    )


def _social_sentiment_signal(articles: list[Article]) -> Signal:
    """Separate social media sentiment signal with engagement weighting."""
    social_articles = [a for a in articles if a.platform != "rss"]
    if not social_articles:
        return Signal("Social Sentiment", 0.5, 0.5, 0.05,
                      config.SIGNAL_WEIGHTS.get("social_sentiment", 0.10),
                      "Nessun contenuto social")

    si_count = sum(1 for a in social_articles if a.sentiment_direction == "SI")
    no_count = sum(1 for a in social_articles if a.sentiment_direction == "NO")
    total_directional = si_count + no_count

    if total_directional == 0:
        return Signal("Social Sentiment", 0.5, 0.5, 0.10,
                      config.SIGNAL_WEIGHTS.get("social_sentiment", 0.10),
                      f"{len(social_articles)} post social, tutti neutrali")

    # Engagement-weighted sentiment: high-engagement posts count more
    weighted_si = 0.0
    weighted_no = 0.0
    for a in social_articles:
        if a.sentiment_direction == "NEUTRAL":
            continue
        eng_boost = 1.0 + (a.engagement_score or 0.0) * 2.0
        w = abs(a.sentiment_score) * a.relevance * eng_boost
        if a.sentiment_direction == "SI":
            weighted_si += w
        else:
            weighted_no += w

    total_weighted = weighted_si + weighted_no
    if total_weighted == 0:
        si_prob = 0.5
    else:
        si_prob = 0.5 + (weighted_si - weighted_no) / (2 * total_weighted)

    si_prob = max(0.1, min(0.9, si_prob))
    no_prob = 1.0 - si_prob

    # Confidence: more directional social posts + diversity of platforms
    platforms_seen = len(set(a.platform for a in social_articles if a.sentiment_direction != "NEUTRAL"))
    platform_bonus = platforms_seen * 0.05
    coverage = total_directional / max(len(social_articles), 1)
    confidence = min(0.75, total_directional * 0.03 + coverage * 0.15 + platform_bonus)

    # Avg engagement boost
    avg_eng = sum(a.engagement_score or 0.0 for a in social_articles) / len(social_articles)
    confidence = min(0.75, confidence + avg_eng * 0.1)

    return Signal(
        "Social Sentiment",
        round(si_prob, 4),
        round(no_prob, 4),
        round(confidence, 4),
        config.SIGNAL_WEIGHTS.get("social_sentiment", 0.10),
        f"SI: {si_count} | NO: {no_count} | Neutri: {len(social_articles) - total_directional} | "
        f"Piattaforme: {platforms_seen} | Engagement medio: {avg_eng:.2f}",
    )


def _cross_platform_consensus_signal(articles: list[Article]) -> Signal:
    """
    Measure agreement across different platforms.
    If social AND media agree on direction, confidence gets a boost.
    """
    platform_groups: dict[str, dict] = {}
    for a in articles:
        if a.sentiment_direction == "NEUTRAL":
            continue
        group = "media" if a.platform == "rss" else a.platform
        if group not in platform_groups:
            platform_groups[group] = {"si": 0, "no": 0}
        if a.sentiment_direction == "SI":
            platform_groups[group]["si"] += 1
        else:
            platform_groups[group]["no"] += 1

    if len(platform_groups) < 2:
        return Signal("Consenso Cross-Platform", 0.5, 0.5, 0.05,
                      config.SIGNAL_WEIGHTS.get("cross_platform", 0.08),
                      "Piattaforme insufficienti per confronto")

    # Check if platforms agree on the leading direction
    platform_directions = []
    for group, counts in platform_groups.items():
        total = counts["si"] + counts["no"]
        if total >= 2:  # need at least 2 directional posts
            si_pct = counts["si"] / total
            platform_directions.append(("SI" if si_pct > 0.5 else "NO", si_pct, total))

    if len(platform_directions) < 2:
        return Signal("Consenso Cross-Platform", 0.5, 0.5, 0.08,
                      config.SIGNAL_WEIGHTS.get("cross_platform", 0.08),
                      f"{len(platform_groups)} piattaforme, dati insufficienti")

    # Count how many platforms agree
    si_platforms = sum(1 for d, _, _ in platform_directions if d == "SI")
    no_platforms = sum(1 for d, _, _ in platform_directions if d == "NO")
    total_platforms = len(platform_directions)

    # Consensus strength
    majority = max(si_platforms, no_platforms)
    consensus_ratio = majority / total_platforms
    leading = "SI" if si_platforms > no_platforms else "NO"

    # Average SI probability across platforms
    avg_si = sum(pct for _, pct, _ in platform_directions) / total_platforms
    si_prob = avg_si if leading == "SI" else 1.0 - avg_si
    si_prob = max(0.2, min(0.8, si_prob))
    no_prob = 1.0 - si_prob

    # Confidence: high consensus + many platforms = high confidence
    confidence = min(0.70, consensus_ratio * 0.4 + total_platforms * 0.06)

    return Signal(
        "Consenso Cross-Platform",
        round(si_prob, 4),
        round(no_prob, 4),
        round(confidence, 4),
        config.SIGNAL_WEIGHTS.get("cross_platform", 0.08),
        f"{majority}/{total_platforms} piattaforme verso {leading} (consenso: {consensus_ratio:.0%})",
    )


def _momentum_signal(articles: list[Article]) -> Signal:
    """Detect trend/momentum using time-weighted sentiment decay."""
    if len(articles) < 4:
        return Signal("Momentum", 0.5, 0.5, 0.05, config.SIGNAL_WEIGHTS["momentum"],
                      "Dati insufficienti per analisi trend")

    import math

    now = datetime.now(timezone.utc)
    HALF_LIFE_HOURS = 24  # sentiment halves in relevance every 24h
    decay_lambda = math.log(2) / (HALF_LIFE_HOURS * 3600)

    recent_weighted = 0.0
    recent_total_w = 0.0
    older_weighted = 0.0
    older_total_w = 0.0

    for a in articles:
        if a.sentiment_direction == "NEUTRAL":
            continue
        age_seconds = max(0, (now - a.published).total_seconds())
        time_weight = math.exp(-decay_lambda * age_seconds)
        # Engagement boosts social content weight
        eng_boost = 1.0 + (a.engagement_score or 0.0)
        relevance_weight = time_weight * a.relevance * eng_boost

        if age_seconds < 48 * 3600:  # last 48h = "recent"
            recent_weighted += a.sentiment_score * relevance_weight
            recent_total_w += relevance_weight
        else:
            older_weighted += a.sentiment_score * relevance_weight
            older_total_w += relevance_weight

    recent_avg = recent_weighted / recent_total_w if recent_total_w > 0 else 0.0
    older_avg = older_weighted / older_total_w if older_total_w > 0 else 0.0
    shift = recent_avg - older_avg

    # Positive shift = moving toward SI, negative = toward NO
    si_prob = 0.5 + shift * 0.3  # Dampened effect
    si_prob = max(0.2, min(0.8, si_prob))
    no_prob = 1.0 - si_prob

    # Confidence scales with data; cap raised to 0.65
    n_directional = sum(1 for a in articles if a.sentiment_direction != "NEUTRAL")
    n_platforms = len(set(a.platform for a in articles if a.sentiment_direction != "NEUTRAL"))
    confidence = min(0.65, 0.05 + n_directional * 0.02 + n_platforms * 0.03)

    direction = "SI" if shift > 0.01 else "NO" if shift < -0.01 else "stabile"

    return Signal(
        "Momentum",
        round(si_prob, 4),
        round(no_prob, 4),
        round(confidence, 4),
        config.SIGNAL_WEIGHTS["momentum"],
        f"Trend: verso {direction} (shift: {shift:+.3f}, {n_directional} articoli, {n_platforms} piattaforme)",
    )


def _exit_poll_signal(exit_polls: list[ExitPollResult]) -> Signal | None:
    """Aggregate exit poll data into a signal. Returns None if no exit polls available."""
    if not exit_polls:
        return None

    from exit_poll import aggregate_exit_polls
    agg = aggregate_exit_polls(exit_polls)

    if agg["count"] == 0:
        return None

    si_prob = agg["si_pct"] / 100.0
    no_prob = agg["no_pct"] / 100.0
    confidence = agg["confidence"]

    # Projections get even higher confidence
    has_projections = any(ep.is_projection for ep in exit_polls)
    label = "Exit Poll + Proiezioni" if has_projections else "Exit Poll"

    return Signal(
        label,
        round(si_prob, 4),
        round(no_prob, 4),
        confidence,
        config.SIGNAL_WEIGHTS_WITH_EXIT_POLL["exit_poll"],
        f"{agg['count']} fonti | SI {agg['si_pct']:.1f}% - NO {agg['no_pct']:.1f}%",
    )


def _extract_social_polls(articles: list[Article]) -> list[dict]:
    """
    Extract synthetic poll-like data from social media.
    Treats highly-engaged directional social posts as low-confidence poll proxies.
    """
    synthetic_polls = []
    # Group social posts by platform+day and compute sentiment ratios
    from collections import defaultdict
    daily_platform: dict[str, dict] = defaultdict(lambda: {"si": 0, "no": 0, "total_eng": 0.0})

    for a in articles:
        if a.platform == "rss" or a.sentiment_direction == "NEUTRAL":
            continue
        day_key = f"{a.platform}_{a.published.strftime('%Y-%m-%d')}"
        if a.sentiment_direction == "SI":
            daily_platform[day_key]["si"] += 1
        else:
            daily_platform[day_key]["no"] += 1
        daily_platform[day_key]["total_eng"] += (a.engagement_score or 0.0)
        daily_platform[day_key]["date"] = a.published.strftime("%Y-%m-%d")
        daily_platform[day_key]["platform"] = a.platform

    for key, data in daily_platform.items():
        total = data["si"] + data["no"]
        if total < 3:  # need at least 3 directional posts to form a synthetic poll
            continue
        si_pct = round(data["si"] / total * 100, 1)
        no_pct = round(data["no"] / total * 100, 1)
        synthetic_polls.append({
            "source": f"Social ({data['platform']})",
            "date": data["date"],
            "si_pct": si_pct,
            "no_pct": no_pct,
            "sample_size": total * 10,  # low effective sample size
            "note": f"Sondaggio sintetico da {total} post social ({data['platform']})",
        })

    return synthetic_polls


def predict(articles: list[Article], polls: list[dict],
            exit_polls: list[ExitPollResult] | None = None) -> Prediction:
    """
    Generate a prediction by combining all signals.
    When exit polls are available, weights shift to prioritize them.
    """
    ep_signal = _exit_poll_signal(exit_polls or [])
    use_exit_poll_weights = ep_signal is not None

    # Choose weight set
    weights = config.SIGNAL_WEIGHTS_WITH_EXIT_POLL if use_exit_poll_weights else config.SIGNAL_WEIGHTS

    signals = []
    if ep_signal:
        signals.append(ep_signal)

    # Add synthetic polls from social media
    social_polls = _extract_social_polls(articles)
    all_polls = polls + social_polls

    # Override weights on existing signals when exit polls are active
    poll_sig = _poll_signal(all_polls)
    poll_sig.weight = weights["polls"]
    signals.append(poll_sig)

    party_sig = _party_strength_signal()
    party_sig.weight = weights["party_strength"]
    signals.append(party_sig)

    sent_sig = _sentiment_signal(articles)
    sent_sig.weight = weights["media_sentiment"]
    signals.append(sent_sig)

    # NEW: Social sentiment as separate signal
    social_sig = _social_sentiment_signal(articles)
    social_sig.weight = weights.get("social_sentiment", 0.10)
    signals.append(social_sig)

    # NEW: Cross-platform consensus signal
    cross_sig = _cross_platform_consensus_signal(articles)
    cross_sig.weight = weights.get("cross_platform", 0.08)
    signals.append(cross_sig)

    mom_sig = _momentum_signal(articles)
    mom_sig.weight = weights["momentum"]
    signals.append(mom_sig)

    # Weighted combination
    total_weight = 0.0
    weighted_si = 0.0
    weighted_confidence = 0.0

    for signal in signals:
        effective_weight = signal.weight * signal.confidence
        weighted_si += signal.si_probability * effective_weight
        weighted_confidence += signal.confidence * signal.weight
        total_weight += effective_weight

    if total_weight == 0:
        si_prob = 0.5
        confidence = 0.1
    else:
        si_prob = weighted_si / total_weight
        confidence = weighted_confidence / sum(s.weight for s in signals)

    no_prob = 1.0 - si_prob
    # Cap raised: 0.92 without exit polls, 0.97 with
    confidence = min(0.97 if use_exit_poll_weights else 0.92, confidence)

    # Confidence interval: narrower when exit polls are available
    base_error = config.HISTORICAL_POLL_ERROR * (0.3 if use_exit_poll_weights else 1.0)
    error_margin = base_error * (1.0 - confidence * 0.5)
    ci_low = max(0.0, si_prob - error_margin)
    ci_high = min(1.0, si_prob + error_margin)

    data_points = len(articles) + len(all_polls) + (len(exit_polls) if exit_polls else 0)

    return Prediction(
        si_probability=round(si_prob, 4),
        no_probability=round(no_prob, 4),
        confidence=round(confidence, 4),
        ci_low=round(ci_low, 4),
        ci_high=round(ci_high, 4),
        signals=signals,
        data_points=data_points,
    )
