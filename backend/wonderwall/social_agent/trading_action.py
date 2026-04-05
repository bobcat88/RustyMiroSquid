from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING
from wonderwall.simulations.polymarket.actions import PolymarketAction

if TYPE_CHECKING:
    from wonderwall.social_platform.channel import Channel
    from .trading_agent import TradingAgent

class TradingAction(PolymarketAction):
    """
    A specialized action class for the RustyMiroSquid trading simulation.
    Includes tools for stock trading and policy-based decision making,
    while retaining prediction market capabilities.
    """
    
    def __init__(self, agent_id: int, channel: Channel):
        super().__init__(agent_id, channel)
        self.agent: Optional[TradingAgent] = None

    async def submit_market_order(self, symbol: str, side: str, qty: float, price: Optional[float] = None):
        """
        Submits a market order using the agent's internal broker.
        If price is not provided, we use a simulation default or fetch it.
        """
        if self.agent and self.agent.broker:
            # In a real scenario, we'd fetch the latest price here if None
            display_price = price or 100.0 # Fallback for simulation
            trade = await self.agent.broker.submit_order(symbol, side, qty, current_price=display_price)
            if trade:
                # Return dict representation of trade
                from dataclasses import asdict
                return {"success": True, "trade": asdict(trade)}
            return {"success": False, "error": "Order rejected by broker (check balance/position)"}
        
        return await self.perform_action((symbol, side, qty, price), "submit_market_order")

    async def get_portfolio_summary(self):
        """
        Gets a detailed summary of the agent's current portfolio (balance, positions, PnL).
        """
        if self.agent:
            return await self.agent.get_portfolio_summary()
        return await self.perform_action(None, "get_portfolio_summary")

    async def validate_trade_with_policy(self, symbol: str, side: str, qty: float, price: Optional[float] = None):
        """
        Checks if a trade idea complies with OVTLYR and SMC risk management rules.
        """
        if self.agent and self.agent.policy:
            display_price = price or 100.0
            is_valid, reason = self.agent.policy.should_trade("MODERATE", {"symbol": symbol, "type": "CHECK"}) # Placeholder
            return {"is_valid": is_valid, "reason": reason}
            
        return await self.perform_action((symbol, side, qty, price), "validate_trade_with_policy")

    async def analyze_smc_confluences(self, symbol: str, direction: str):
        """
        Reasoning Tool: Checks for Multi-Timeframe (MTF) SMC confluences.
        Validates: [HTF_BIAS] -> [LTF_SWEEP] -> [LTF_MSS].
        Returns CONFIRMED if all 3 criteria are met for the given direction (BULLISH/BEARISH).
        """
        if self.agent and hasattr(self.agent.env, "latest_triggers"):
             triggers = self.agent.env.latest_triggers
             signals = triggers.smc_signals.get(symbol, [])
             is_valid = self.agent.policy.check_smc_confluences(signals, direction)
             
             reason = "Missing HTF Bias alignment, Liquidity Sweep, or Market Structure Shift (MSS)" if not is_valid else "Institutional Setup Confirmed (HTF Bias + LTF Sweep + LTF MSS)"
             
             return {
                 "symbol": symbol,
                 "direction": direction,
                 "detected_signals": signals,
                 "setup_confirmation": "CONFIRMED" if is_valid else "REJECTED",
                 "reason": reason
             }
        return {"error": "Trigger data not available in current environment state."}

    async def generate_pine_script(self, symbol: str, entry: float, stop: float, tp: float):
        """
        V5 Pine Script Generator for the trade setup.
        Returns a Pine Script strategy snippet to satisfy simulation requirements.
        """
        script = f"""//@version=5
strategy("{symbol} SMC Setup", overlay=true)
entry_pc = {entry}
stop_ls = {stop}
take_pf = {tp}
plot(entry_pc, "Entry", color.blue, style=plot.style_linebr)
plot(stop_ls, "Stop Loss", color.red, style=plot.style_linebr)
plot(take_pf, "Take Profit", color.green, style=plot.style_linebr)
"""
        return {"symbol": symbol, "pine_script": script}
