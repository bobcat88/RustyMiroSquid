import random
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .oasis_profile_generator import OasisAgentProfile

logger = logging.getLogger('miroshark.trading_persona')

@dataclass
class TradingArchetype:
    name: str
    description: str
    risk_tolerance: str
    preference_plan: str
    base_bio: str
    base_persona: str
    base_balance: float

ARCHETYPES = {
    "Institutional Whale": TradingArchetype(
        name="Institutional Whale",
        description="Market-moving entity, conservative and focused on macro trends.",
        risk_tolerance="low",
        preference_plan="Plan ETF",
        base_bio="Hedge fund manager with 20+ years of institutional experience. Focused on capital preservation and long-term yield.",
        base_persona="You are a seasoned institutional trader. You ignore retail noise and focus on volume profiles and macro-economic shifts. You prefer ETF-based tactical allocations (OVTLYR Plan ETF) and Sit In Cash (SICADFU) when volatility is too high.",
        base_balance=10000000.0  # $10M
    ),
    "Aggressive Alpha": TradingArchetype(
        name="Aggressive Alpha",
        description="High-frequency scalper looking for breakout momentum.",
        risk_tolerance="high",
        preference_plan="Plan A",
        base_bio="Proprietary trader specializing in momentum breakouts and alpha generation. Known for aggressive sizing on high-probability setups.",
        base_persona="You are an aggressive momentum trader. You seek high-volatility breakouts (OVTLYR Plan A). You use SMC signals to scalp entries and exits with high precision. You are comfortable with high risk for high alpha.",
        base_balance=250000.0  # $250k
    ),
    "SMC Sniper": TradingArchetype(
        name="SMC Sniper",
        description="Patient technical analyst focused on Smart Money Concepts.",
        risk_tolerance="moderate",
        preference_plan="Plan M",
        base_bio="Technical analyst mastering Smart Money Concepts (SMC). Waits for Fair Value Gaps (FVG) and Order Blocks (OB) to align with OVTLYR plans.",
        base_persona="You are a patient SMC trader. You only enter when price returns to a valid Order Block or fills a Fair Value Gap. You use OVTLYR Plan M (Moderate) to filter your signals. You prioritize high Risk/Reward ratios over trade frequency.",
        base_balance=100000.0  # $100k
    ),
    "Retail Reactor": TradingArchetype(
        name="Retail Reactor",
        description="Sentiment-driven trader influenced by social media and news.",
        risk_tolerance="moderate",
        preference_plan="Plan A",
        base_bio="Individual trader active on social media. Closely follows market news and 'Market Color' sentiment indicators.",
        base_persona="You are a retail trader heavily influenced by the 'Market Color' (Fear/Greed). You react quickly to news triggers and RSS feeds. You are prone to FOMO in Greed and FUD in Fear. You look for validation from other traders before acting.",
        base_balance=10000.0  # $10k
    )
}

class TradingPersonaFactory:
    """
    Factory to generate specialized trading personas for the simulation.
    """
    
    @staticmethod
    def generate_persona(archetype_name: str, user_id: int) -> OasisAgentProfile:
        if archetype_name not in ARCHETYPES:
            # Fallback to random archetype if not found
            archetype_name = random.choice(list(ARCHETYPES.keys()))
            
        arch = ARCHETYPES[archetype_name]
        
        # Add some randomness to metrics
        follower_count = random.randint(1000, 50000) if "Whale" in archetype_name else random.randint(100, 5000)
        
        return OasisAgentProfile(
            user_id=user_id,
            user_name=f"{archetype_name.replace(' ', '_')}_{user_id}",
            name=f"{archetype_name} #{user_id}",
            bio=arch.base_bio,
            persona=arch.base_persona,
            risk_tolerance=arch.risk_tolerance,
            profession="Financial Trader",
            interested_topics=["Trading", "Crypto", "Macro", "OVTLYR", "SMC"],
            follower_count=follower_count,
            friend_count=random.randint(50, 500),
            statuses_count=random.randint(200, 10000)
        )

    @staticmethod
    def get_diverse_trading_team(count: int, start_id: int = 1000) -> List[OasisAgentProfile]:
        """Generates a balanced team of trading personas."""
        team = []
        archetype_list = list(ARCHETYPES.keys())
        for i in range(count):
            arch = archetype_list[i % len(archetype_list)]
            team.append(TradingPersonaFactory.generate_persona(arch, start_id + i))
        return team
