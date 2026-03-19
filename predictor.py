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
    confidence = min(0.7, len(polls) * 0.12)  # More polls = more confidence, capped

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

    # Lower confidence: party support doesn't translate 1:1 to referendum vote
    return Signal(
        "Forza Partiti",
        round(si_prob, 4),
        round(no_prob, 4),
        0.4,
        config.SIGNAL_WEIGHTS["party_strength"],
        f"Centrodestra (SI): {si_support:.0f}% | Opposizione (NO): {no_support:.0f}%",
    )


def _sentiment_signal(articles: list[Article]) -> Signal:
    """Aggregate media sentiment across all articles."""
    if not articles:
        return Signal("Sentiment Media", 0.5, 0.5, 0.1, config.SIGNAL_WEIGHTS["media_sentiment"],
                      "Nessun articolo analizzato")

    si_count = sum(1 for a in articles if a.sentiment_direction == "SI")
    no_count = sum(1 for a in articles if a.sentiment_direction == "NO")
    total_directional = si_count + no_count

    if total_directional == 0:
        return Signal("Sentiment Media", 0.5, 0.5, 0.15, config.SIGNAL_WEIGHTS["media_sentiment"],
                      f"{len(articles)} articoli, tutti neutrali")

    # Also weight by sentiment strength and relevance
    weighted_si = sum(
        a.sentiment_score * a.relevance
        for a in articles if a.sentiment_direction == "SI"
    )
    weighted_no = sum(
        abs(a.sentiment_score) * a.relevance
        for a in articles if a.sentiment_direction == "NO"
    )

    total_weighted = weighted_si + weighted_no
    if total_weighted == 0:
        si_prob = 0.5
    else:
        si_prob = 0.5 + (weighted_si - weighted_no) / (2 * total_weighted)

    si_prob = max(0.1, min(0.9, si_prob))
    no_prob = 1.0 - si_prob

    # Higher confidence scaling: more directional articles = more confidence
    coverage = total_directional / max(len(articles), 1)
    confidence = min(0.7, total_directional * 0.04 + coverage * 0.2)

    return Signal(
        "Sentiment Media",
        round(si_prob, 4),
        round(no_prob, 4),
        confidence,
        config.SIGNAL_WEIGHTS["media_sentiment"],
        f"SI: {si_count} articoli | NO: {no_count} | Neutri: {len(articles) - total_directional} | Copertura: {coverage:.0%}",
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
        relevance_weight = time_weight * a.relevance

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

    # Confidence scales with amount of data
    n_directional = sum(1 for a in articles if a.sentiment_direction != "NEUTRAL")
    confidence = min(0.4, 0.05 + n_directional * 0.02)

    direction = "SI" if shift > 0.01 else "NO" if shift < -0.01 else "stabile"

    return Signal(
        "Momentum",
        round(si_prob, 4),
        round(no_prob, 4),
        confidence,
        config.SIGNAL_WEIGHTS["momentum"],
        f"Trend: verso {direction} (shift: {shift:+.3f}, {n_directional} articoli direzionali)",
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

    # Override weights on existing signals when exit polls are active
    poll_sig = _poll_signal(polls)
    poll_sig.weight = weights["polls"]
    signals.append(poll_sig)

    party_sig = _party_strength_signal()
    party_sig.weight = weights["party_strength"]
    signals.append(party_sig)

    sent_sig = _sentiment_signal(articles)
    sent_sig.weight = weights["media_sentiment"]
    signals.append(sent_sig)

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
    confidence = min(0.95 if use_exit_poll_weights else 0.85, confidence)

    # Confidence interval: narrower when exit polls are available
    base_error = config.HISTORICAL_POLL_ERROR * (0.3 if use_exit_poll_weights else 1.0)
    error_margin = base_error * (1.0 - confidence * 0.5)
    ci_low = max(0.0, si_prob - error_margin)
    ci_high = min(1.0, si_prob + error_margin)

    data_points = len(articles) + len(polls) + (len(exit_polls) if exit_polls else 0)

    return Prediction(
        si_probability=round(si_prob, 4),
        no_probability=round(no_prob, 4),
        confidence=round(confidence, 4),
        ci_low=round(ci_low, 4),
        ci_high=round(ci_high, 4),
        signals=signals,
        data_points=data_points,
    )
