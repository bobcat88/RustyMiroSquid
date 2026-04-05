import logging
from typing import Dict, Any, List, Optional, Tuple

# Simple logger until structure is clarified
logger = logging.getLogger('rusty.trading_policy')

class TradingPolicy:
    """
    Implements OVTLYR (Plan A, M, ETF, SICADFU) and SMC (FVG, OB) logic.
    Used by agents to validate and execute trade ideas.
    """
    
    def __init__(self, risk_per_trade: float = 0.01):
        self.risk_per_trade = risk_per_trade  # 1% risk of account
        self.min_rr = 3.0  # 1:3 Risk/Reward

    def should_trade(self, market_color: str, signal: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Main decision gate based on OVTLYR market color.
        """
        if market_color == "CASH":
            return False, "SICADFU: Market environment is too risky (No trade allowed)."
            
        if not signal:
            return False, "No valid SMC signal detected."

        if market_color == "DEFENSIVE" and signal.get("type", "").startswith("AGGRESSIVE"):
            return False, "Plan ETF: Defensive mode forbids aggressive individual stock signals."

        return True, "Signal validated against Market Color."

    def calculate_position_size(self, balance: float, entry: float, stop_loss: float) -> float:
        """
        Calculate units to buy based on fixed percentage risk.
        Position Size = (Balance * Risk%) / (Entry - StopLoss)
        """
        risk_amount = balance * self.risk_per_trade
        stop_dist = abs(entry - stop_loss)
        if stop_dist == 0:
            return 0.0
        return risk_amount / stop_dist

    def validate_rr(self, entry: float, stop_loss: float, take_profit: float) -> bool:
        """Verify 1:3 R:R minimum."""
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        if risk == 0:
            return False
        return (reward / risk) >= self.min_rr

    def get_plan_name(self, market_color: str) -> str:
        """Map Market Color to OVTLYR Plan Name."""
        mapping = {
            "AGGRESSIVE": "Plan A (Alpha)",
            "MODERATE": "Plan M (Momentum)",
            "DEFENSIVE": "Plan ETF (Tactical)",
            "CASH": "SICADFU (Sit In Cash)"
        }
        return mapping.get(market_color, "Unknown Plan")
