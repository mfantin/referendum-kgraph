"""
Prediction engine: aggregates signals into a referendum outcome prediction.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import config
from data_fetcher import Article


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
    """Detect trend/momentum in recent vs older articles."""
    if len(articles) < 4:
        return Signal("Momentum", 0.5, 0.5, 0.05, config.SIGNAL_WEIGHTS["momentum"],
                      "Dati insufficienti per analisi trend")

    # Split into recent half and older half
    mid = len(articles) // 2
    recent = articles[:mid]
    older = articles[mid:]

    def avg_sentiment(arts):
        scores = [a.sentiment_score for a in arts if a.sentiment_direction != "NEUTRAL"]
        return sum(scores) / len(scores) if scores else 0.0

    recent_avg = avg_sentiment(recent)
    older_avg = avg_sentiment(older)
    shift = recent_avg - older_avg

    # Positive shift = moving toward SI, negative = toward NO
    si_prob = 0.5 + shift * 0.3  # Dampened effect
    si_prob = max(0.2, min(0.8, si_prob))
    no_prob = 1.0 - si_prob

    direction = "SI" if shift > 0 else "NO" if shift < 0 else "stabile"

    return Signal(
        "Momentum",
        round(si_prob, 4),
        round(no_prob, 4),
        0.25,
        config.SIGNAL_WEIGHTS["momentum"],
        f"Trend: verso {direction} (shift: {shift:+.3f})",
    )


def predict(articles: list[Article], polls: list[dict]) -> Prediction:
    """
    Generate a prediction by combining all signals.
    """
    signals = [
        _poll_signal(polls),
        _party_strength_signal(),
        _sentiment_signal(articles),
        _momentum_signal(articles),
    ]

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
    confidence = min(0.85, confidence)

    # Confidence interval based on historical error
    error_margin = config.HISTORICAL_POLL_ERROR * (1.0 - confidence * 0.5)
    ci_low = max(0.0, si_prob - error_margin)
    ci_high = min(1.0, si_prob + error_margin)

    data_points = len(articles) + len(polls)

    return Prediction(
        si_probability=round(si_prob, 4),
        no_probability=round(no_prob, 4),
        confidence=round(confidence, 4),
        ci_low=round(ci_low, 4),
        ci_high=round(ci_high, 4),
        signals=signals,
        data_points=data_points,
    )
