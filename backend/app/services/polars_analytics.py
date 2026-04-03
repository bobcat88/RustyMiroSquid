"""
Polars-based analytics engine for simulation results.

Remplace les analyses pandas par des expressions Polars Rust-native.
Utilisé pour le traitement post-simulation : sentiment agrégé,
ROI simulé, vélocité de sentiment, convergence des croyances.

NOTE : Wonderwall/CAMEL-AI garde pandas en interne → ne pas toucher.
       Ce module ne traite que les logs d'output (JSONL).
"""

import polars as pl
from pathlib import Path


class SimulationAnalytics:
    """Analyse les logs de simulation avec Polars (Rust-native)."""

    def load_actions_log(self, jsonl_path: Path) -> pl.LazyFrame:
        """
        Charge un fichier actions.jsonl en LazyFrame.

        Le format attendu est celui produit par action_logger.py :
        {"round": int, "platform": str, "agent_id": int, "agent_name": str,
         "action_type": str, "action_args": {...}}

        Returns:
            LazyFrame pour évaluation fainéante (deferred computing)
        """
        return pl.scan_ndjson(str(jsonl_path))

    def compute_aggregate_sentiment(
        self,
        belief_data: pl.LazyFrame,
        group_by: str = "round"
    ) -> pl.DataFrame:
        """
        Calcule le sentiment agrégé par round et par plateforme.

        Args:
            belief_data: LazyFrame avec colonnes [round, agent_id, topic, stance, confidence]
            group_by: Colonne de regroupement ("round" ou "platform")

        Returns:
            DataFrame avec sentiment moyen, médian, et écart-type par groupe
        """
        return (
            belief_data
            .group_by(group_by)
            .agg([
                pl.col("stance").mean().alias("mean_sentiment"),
                pl.col("stance").median().alias("median_sentiment"),
                pl.col("stance").std().alias("std_sentiment"),
                pl.col("confidence").mean().alias("mean_confidence"),
                pl.len().alias("agent_count"),
            ])
            .sort(group_by)
            .collect()
        )

    def compute_simulated_roi(
        self,
        trades: pl.LazyFrame,
        initial_balance: float = 1000.0
    ) -> pl.DataFrame:
        """
        Calcule le ROI simulé basé sur les trades Polymarket.

        Args:
            trades: LazyFrame avec colonnes [round, agent_id, action, shares, price]
            initial_balance: Solde initial par agent

        Returns:
            DataFrame avec ROI par agent
        """
        return (
            trades
            .filter(pl.col("action").is_in(["buy_shares", "sell_shares"]))
            .with_columns(
                pl.when(pl.col("action") == "buy_shares")
                .then(-pl.col("shares") * pl.col("price"))
                .otherwise(pl.col("shares") * pl.col("price"))
                .alias("cash_flow")
            )
            .group_by("agent_id")
            .agg([
                pl.col("cash_flow").sum().alias("net_pnl"),
                pl.col("cash_flow").count().alias("trade_count"),
            ])
            .with_columns(
                (pl.col("net_pnl") / initial_balance * 100).alias("roi_pct")
            )
            .sort("roi_pct", descending=True)
            .collect()
        )

    def compute_sentiment_velocity(
        self,
        belief_history: pl.LazyFrame
    ) -> pl.DataFrame:
        """
        Calcule la vitesse de changement d'opinion (first derivative dS/dt).

        Une vélocité élevée indique un changement rapide d'opinion —
        potentiel signal de marché.

        Args:
            belief_history: LazyFrame [round, agent_id, topic, stance]

        Returns:
            DataFrame avec dS/dt par agent par topic par round
        """
        return (
            belief_history
            .sort("round")
            .with_columns(
                pl.col("stance")
                .diff()
                .over("agent_id", "topic")
                .alias("sentiment_velocity")
            )
            .filter(pl.col("sentiment_velocity").is_not_null())
            .collect()
        )

    def compute_belief_convergence(
        self,
        belief_history: pl.LazyFrame
    ) -> pl.DataFrame:
        """
        Mesure la convergence/divergence des croyances entre agents.

        Si l'écart-type de stance diminue → consensus.
        Si l'écart-type augmente → polarisation.

        Args:
            belief_history: LazyFrame [round, agent_id, topic, stance]

        Returns:
            DataFrame avec métriques de convergence par round par topic
        """
        return (
            belief_history
            .group_by("round", "topic")
            .agg([
                pl.col("stance").std().alias("stance_dispersion"),
                pl.col("stance").mean().alias("mean_stance"),
                pl.col("stance").min().alias("min_stance"),
                pl.col("stance").max().alias("max_stance"),
                (pl.col("stance").max() - pl.col("stance").min()).alias("stance_range"),
                pl.len().alias("agent_count"),
            ])
            .sort("round", "topic")
            .collect()
        )

    def get_top_movers(
        self,
        belief_history: pl.LazyFrame,
        top_n: int = 10
    ) -> pl.DataFrame:
        """
        Identifie les agents ayant le plus changé d'opinion (top movers).

        Args:
            belief_history: LazyFrame [round, agent_id, agent_name, topic, stance]
            top_n: Nombre de top movers à retourner

        Returns:
            DataFrame des top_n agents avec le plus grand delta de stance
        """
        return (
            belief_history
            .group_by("agent_id", "agent_name", "topic")
            .agg([
                pl.col("stance").first().alias("initial_stance"),
                pl.col("stance").last().alias("final_stance"),
                (pl.col("stance").last() - pl.col("stance").first()).abs().alias("total_shift"),
            ])
            .sort("total_shift", descending=True)
            .head(top_n)
            .collect()
        )
