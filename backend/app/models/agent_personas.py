"""
Pydantic v2 models (Rust-core validation) for agent personas.

Remplace la gestion dict-based des personas par des schémas validés.
Pydantic v2 utilise un validateur Rust-core pour des performances
10-50x supérieures à la validation Python pure.

Ces modèles sont utilisés par :
- oasis_profile_generator.py (génération de personas)
- simulation_config_generator.py (configuration de simulation)
- polars_analytics.py (analyse des résultats)
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class InvestmentSector(str, Enum):
    """Secteurs d'investissement supportés par la simulation."""
    CRYPTO = "crypto"
    EQUITY = "equity"
    MACRO = "macro"
    MIXED = "mixed"


class EntityType(str, Enum):
    """Type d'entité (détection automatique via keyword matching)."""
    INDIVIDUAL = "individual"
    INSTITUTIONAL = "institutional"


class BeliefState(BaseModel):
    """
    État de croyance d'un agent à un instant T.

    Chaque agent maintient un BeliefState qui évolue round par round :
    - positions: stance sur chaque topic (-1 bearish → +1 bullish)
    - confidence: certitude sur chaque position (0 uncertain → 1 certain)
    - trust: niveau de confiance envers les autres agents (0 → 1)
    """
    positions: dict[str, float] = Field(
        default_factory=dict,
        description="topic → stance (-1 bearish to +1 bullish)"
    )
    confidence: dict[str, float] = Field(
        default_factory=dict,
        description="topic → certainty (0 to 1)"
    )
    trust: dict[str, float] = Field(
        default_factory=dict,
        description="agent_id (str) → trust level (0 to 1)"
    )

    @field_validator("positions", "confidence", mode="before")
    @classmethod
    def clamp_values(cls, v: dict) -> dict:
        """Valide que les valeurs sont dans les bornes attendues."""
        if isinstance(v, dict):
            return {k: max(-1.0, min(1.0, float(val))) for k, val in v.items()}
        return v


class AgentPersona(BaseModel):
    """
    Modèle validé de persona d'agent de simulation.

    Chaque agent dans RustyMiroSquid est défini par un persona
    qui capture son identité, son style d'investissement,
    et son état de croyance courant.
    """
    agent_id: int = Field(ge=0, description="Identifiant unique de l'agent")
    entity_name: str = Field(min_length=1, description="Nom de l'entité (personne ou organisation)")
    entity_type: EntityType = Field(default=EntityType.INDIVIDUAL)
    sector: InvestmentSector = Field(default=InvestmentSector.MIXED)

    # Profil
    profile_summary: str = Field(default="", description="Résumé du profil (généré par LLM)")
    personality_traits: list[str] = Field(default_factory=list, description="Traits de personnalité")
    background: str = Field(default="", description="Background contextuel")

    # Paramètres d'investissement
    investment_style: Optional[str] = Field(
        default=None,
        description="Style d'investissement (value, growth, momentum, contrarian)"
    )
    risk_tolerance: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Tolérance au risque (0 conservative → 1 aggressive)"
    )
    initial_balance: float = Field(
        ge=0.0, default=1000.0,
        description="Solde initial pour le trading Polymarket"
    )

    # État de croyance
    belief_state: BeliefState = Field(default_factory=BeliefState)


class SimulationConfig(BaseModel):
    """
    Configuration validée d'une simulation multi-agents.

    Regroupe tous les paramètres nécessaires pour lancer
    une simulation sur les trois plateformes.
    """
    simulation_id: str = Field(description="Identifiant unique de la simulation")
    document_title: str = Field(default="", description="Titre du document source")
    max_rounds: int = Field(ge=1, le=100, default=10)
    platforms: list[str] = Field(
        default=["twitter", "reddit", "polymarket"],
        description="Plateformes actives"
    )
    agent_configs: list[AgentPersona] = Field(
        default_factory=list,
        description="Liste des personas d'agents"
    )
    cross_platform: bool = Field(
        default=True,
        description="Les agents voient leur activité sur les autres plateformes"
    )

    @property
    def agent_count(self) -> int:
        """Nombre total d'agents dans la simulation."""
        return len(self.agent_configs)

    def get_sector_agents(self, sector: InvestmentSector) -> list[AgentPersona]:
        """Retourne les agents d'un secteur donné."""
        return [a for a in self.agent_configs if a.sector == sector]
