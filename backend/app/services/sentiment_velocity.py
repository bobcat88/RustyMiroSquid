"""
Sentiment Velocity — Calcul de la dérivée de sentiment (dS/dt) par agent et par topic.

Mesure la VITESSE de changement d'opinion des agents dans la simulation.
Un dS/dt élevé indique un shift rapide de sentiment (bullish→bearish ou inversement),
ce qui peut être un signal prédictif fort pour les marchés.

Implémenté en Polars (Rust-native) pour performance maximale.

Usage:
    tracker = SentimentVelocityTracker()

    # Après chaque round, enregistrer les positions des agents
    tracker.record_round(round_num, belief_states)

    # Calculer la vélocité
    velocity_df = tracker.compute_velocity()

    # Détecter les shifts rapides
    alerts = tracker.detect_rapid_shifts(threshold=0.3)

    # Résumé pour injection dans les agents traders
    prompt = tracker.to_trading_signal()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import polars as pl
    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False
    logger.warning("Polars non installé. SentimentVelocityTracker dégradé.")


@dataclass
class VelocityAlert:
    """Alerte de shift rapide de sentiment."""
    topic: str
    agent_id: int
    velocity: float  # dS/dt (positif = bullish, négatif = bearish)
    current_position: float
    previous_position: float
    round_num: int
    magnitude: str  # "moderate" | "strong" | "extreme"


class SentimentVelocityTracker:
    """Tracker de vélocité de sentiment par agent et par topic.

    Enregistre les positions des agents à chaque round et calcule
    la dérivée première (dS/dt) pour détecter les shifts rapides.

    Thread-safe: protège _records via Lock.

    Args:
        window_size: Nombre de rounds utilisés pour le calcul de vélocité.
        alert_threshold: Seuil de |dS/dt| pour déclencher une alerte.
    """

    def __init__(
        self,
        window_size: int = 3,
        alert_threshold: float = 0.3,
    ):
        self._lock = threading.Lock()
        self.window_size = window_size
        self.alert_threshold = alert_threshold

        # Stockage brut: list de {round_num, agent_id, topic, position, timestamp}
        self._records: List[Dict[str, Any]] = []
        self._alerts: List[VelocityAlert] = []

    def record_round(
        self,
        round_num: int,
        belief_states: Dict[int, Any],
    ):
        """Enregistrer les positions de croyance de tous les agents pour ce round.

        Args:
            round_num: Numéro du round courant.
            belief_states: Dict agent_id -> BeliefState (avec attribut .positions).
        """
        timestamp = time.time()
        new_records = []

        for agent_id, bs in belief_states.items():
            positions = getattr(bs, "positions", None)
            if not positions:
                continue

            for topic, position in positions.items():
                new_records.append({
                    "round_num": round_num,
                    "agent_id": agent_id,
                    "topic": topic,
                    "position": float(position),
                    "timestamp": timestamp,
                })

        with self._lock:
            self._records.extend(new_records)

        logger.debug(f"Round {round_num}: {len(new_records)} positions enregistrées")

    def compute_velocity(self) -> Optional[Any]:
        """Calculer la vélocité de sentiment (dS/dt) pour chaque agent × topic.

        Utilise Polars LazyFrame pour le calcul vectorisé:
        - Trie par (agent_id, topic, round_num)
        - Calcule diff() sur la position
        - Retourne dS/dt moyen sur la fenêtre glissante

        Returns:
            Polars DataFrame avec colonnes:
            [agent_id, topic, velocity, current_pos, avg_pos, rounds_tracked]
            Ou None si Polars non disponible ou données insuffisantes.
        """
        if not HAS_POLARS:
            logger.warning("Polars requis pour compute_velocity()")
            return None

        with self._lock:
            if len(self._records) < 2:
                return None
            records_copy = list(self._records)

        df = pl.LazyFrame(records_copy)

        velocity = (
            df
            .sort(["agent_id", "topic", "round_num"])
            .with_columns(
                pl.col("position")
                .diff()
                .over(["agent_id", "topic"])
                .alias("delta_s")
            )
            .filter(pl.col("delta_s").is_not_null())
            # Fenêtre glissante : derniers N rounds par groupe
            .filter(
                pl.col("round_num") >= (
                    pl.col("round_num").max().over(["agent_id", "topic"])
                    - self.window_size
                )
            )
            .group_by(["agent_id", "topic"])
            .agg(
                pl.col("delta_s").mean().alias("velocity"),
                pl.col("position").last().alias("current_pos"),
                pl.col("position").mean().alias("avg_pos"),
                pl.col("round_num").count().alias("rounds_tracked"),
                pl.col("round_num").max().alias("last_round"),
            )
            .sort(pl.col("velocity").abs(), descending=True)
            .collect()
        )

        return velocity

    def detect_rapid_shifts(
        self,
        threshold: Optional[float] = None,
    ) -> List[VelocityAlert]:
        """Détecter les agents avec des shifts rapides de sentiment.

        Args:
            threshold: Seuil de |dS/dt| pour l'alerte. None = self.alert_threshold.

        Returns:
            Liste de VelocityAlert pour les agents dépassant le seuil.
        """
        if not HAS_POLARS:
            return []

        threshold = threshold or self.alert_threshold
        velocity_df = self.compute_velocity()

        if velocity_df is None or velocity_df.is_empty():
            return []

        alerts = []
        for row in velocity_df.iter_rows(named=True):
            v = abs(row["velocity"])
            if v < threshold:
                continue

            # Classifier la magnitude
            if v >= 0.6:
                magnitude = "extreme"
            elif v >= 0.4:
                magnitude = "strong"
            else:
                magnitude = "moderate"

            # Retrouver la position précédente
            prev_pos = row["current_pos"] - row["velocity"]

            alert = VelocityAlert(
                topic=row["topic"],
                agent_id=row["agent_id"],
                velocity=row["velocity"],
                current_position=row["current_pos"],
                previous_position=prev_pos,
                round_num=row["last_round"],
                magnitude=magnitude,
            )
            alerts.append(alert)

        with self._lock:
            self._alerts = alerts

        if alerts:
            logger.info(
                f"Sentiment velocity: {len(alerts)} alerte(s) détectée(s) "
                f"(seuil: {threshold})"
            )

        return alerts

    def compute_aggregate_velocity(self) -> Dict[str, float]:
        """Calculer la vélocité agrégée par topic (moyenne de tous les agents).

        Returns:
            Dict topic -> vélocité moyenne.
        """
        if not HAS_POLARS:
            return {}

        velocity_df = self.compute_velocity()
        if velocity_df is None or velocity_df.is_empty():
            return {}

        agg = (
            velocity_df
            .lazy()
            .group_by("topic")
            .agg(pl.col("velocity").mean().alias("avg_velocity"))
            .collect()
        )

        return {
            row["topic"]: row["avg_velocity"]
            for row in agg.iter_rows(named=True)
        }

    def to_trading_signal(self) -> str:
        """Générer un signal de trading basé sur la vélocité de sentiment.

        Formaté pour injection dans les agents Polymarket.
        Les shifts rapides sont des signaux potentiels de mouvement de marché.

        Returns:
            Prompt texte ou chaîne vide si pas de données.
        """
        alerts = self.detect_rapid_shifts()
        aggregate = self.compute_aggregate_velocity()

        if not alerts and not aggregate:
            return ""

        lines = ["# SENTIMENT VELOCITY SIGNALS"]
        lines.append(
            "These signals measure how FAST opinions are changing. "
            "Rapid sentiment shifts often precede market movements."
        )
        lines.append("")

        # Vélocité agrégée par topic
        if aggregate:
            lines.append("  Topic velocity (average dS/dt across all agents):")
            for topic, vel in sorted(aggregate.items(), key=lambda x: abs(x[1]), reverse=True):
                if abs(vel) < 0.05:
                    continue
                direction = "→ BULLISH shift" if vel > 0 else "→ BEARISH shift"
                lines.append(f"    \"{topic}\": {vel:+.3f} {direction}")
            lines.append("")

        # Alertes de shifts rapides
        if alerts:
            # Grouper par topic
            by_topic: Dict[str, List[VelocityAlert]] = {}
            for alert in alerts:
                by_topic.setdefault(alert.topic, []).append(alert)

            lines.append("  ⚡ Rapid sentiment shifts detected:")
            for topic, topic_alerts in by_topic.items():
                count = len(topic_alerts)
                extreme = sum(1 for a in topic_alerts if a.magnitude == "extreme")
                strong = sum(1 for a in topic_alerts if a.magnitude == "strong")
                avg_vel = sum(a.velocity for a in topic_alerts) / count

                direction = "turning bullish" if avg_vel > 0 else "turning bearish"
                severity = ""
                if extreme > 0:
                    severity = f" [EXTREME: {extreme} agents]"
                elif strong > 0:
                    severity = f" [STRONG: {strong} agents]"

                lines.append(
                    f"    \"{topic}\": {count} agents {direction} "
                    f"(avg velocity: {avg_vel:+.3f}){severity}"
                )
            lines.append("")

        lines.append(
            "High velocity → sentiment is moving fast → potential trading opportunity. "
            "Consider whether the market has already priced this shift in."
        )
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques du tracker."""
        with self._lock:
            unique_agents = len(set(r["agent_id"] for r in self._records))
            unique_topics = len(set(r["topic"] for r in self._records))
            unique_rounds = len(set(r["round_num"] for r in self._records))
            return {
                "total_records": len(self._records),
                "unique_agents": unique_agents,
                "unique_topics": unique_topics,
                "unique_rounds": unique_rounds,
                "active_alerts": len(self._alerts),
                "window_size": self.window_size,
                "alert_threshold": self.alert_threshold,
                "polars_available": HAS_POLARS,
            }

    def clear(self):
        """Réinitialiser le tracker."""
        with self._lock:
            self._records.clear()
            self._alerts.clear()
