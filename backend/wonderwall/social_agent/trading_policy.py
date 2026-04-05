import logging
from typing import Dict, Any, List, Optional, Tuple

# Simple logger until structure is clarified
logger = logging.getLogger('rusty.trading_policy')

class TradingPolicy:
    """
    Implements OVTLYR (Plan A, M, ETF, SICADFU) and SMC (FVG, OB) logic.
    Used by agents to validate and execute trade ideas.
    """
    
    def __init__(self, risk_per_trade: float = 0.01, domicile: str = "France"):
        self.risk_per_trade = risk_per_trade  # 1% risk of account
        self.domicile = domicile
        self.min_rr = 3.0  # Default 1:3 Risk/Reward
        
        # Adjust minimum R:R for tax drag (France: 31.4%)
        # To get a NET 2.0 R:R, we need ~2.9 gross.
        # To get a NET 3.0 R:R, we need ~4.3 gross.
        if self.domicile == "France":
            self.min_rr = 4.0 # Conservative institutional floor for French residents

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

    def should_move_to_be(self, entry: float, current_price: float, stop_loss: float) -> bool:
        """Move SL to break even after 1:1 displacement."""
        risk = abs(entry - stop_loss)
        displacement = abs(current_price - entry)
        # Check if we've moved in the right direction
        if (entry > stop_loss and current_price > entry) or (entry < stop_loss and current_price < entry):
            return displacement >= risk
        return False

    def should_scale_out(self, entry: float, current_price: float, stop_loss: float) -> bool:
        """Take 50% partial at 2.0 R:R (Double the initial risk)."""
        risk = abs(entry - stop_loss)
        if risk == 0:
            return False
        displacement = abs(current_price - entry)
        return displacement >= (2.0 * risk)

    def check_smc_confluences(self, signals: List[str], bias: str) -> bool:
        """
        Claude-style 3-step check for institutional setups:
        1. HTF Trend/Bias (OVTLYR or EMA).
        2. LTF Liquidity Sweep.
        3. LTF Structure Shift (MSS).
        """
        # 1. Bias Check (HTF)
        # 2. Sweep Check (LTF)
        # 3. MSS Check (LTF)
        
        # Bullish setup: Bottom sweep + Bullish MSS + Bullish Bias
        if bias.upper() == "BULLISH":
            has_sweep = any("SWEEP_BOTTOM" in s for s in signals)
            has_mss = any("MSS_BULLISH" in s for s in signals)
            return has_sweep and has_mss
            
        # Bearish setup: Top sweep + Bearish MSS + Bearish Bias
        elif bias.upper() == "BEARISH":
            has_sweep = any("SWEEP_TOP" in s for s in signals)
            has_mss = any("MSS_BEARISH" in s for s in signals)
            return has_sweep and has_mss
            
        return False
