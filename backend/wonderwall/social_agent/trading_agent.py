from typing import List, Optional, Dict, Any, Union
import logging
from camel.models import BaseModelBackend, ModelManager
from wonderwall.social_platform.config import UserInfo
from wonderwall.social_platform.typing import ActionType
from wonderwall.social_agent.agent import SocialAgent
from wonderwall.environment.broker import LocalBroker
from .trading_policy import TradingPolicy

logger = logging.getLogger("social.trading_agent")

class TradingAgent(SocialAgent):
    """
    A specialized SocialAgent with a built-in Broker and TradingPolicy.
    Used for the RustyMiroSquid trading simulation.
    """
    def __init__(
        self,
        agent_id: int,
        user_info: UserInfo,
        model: Optional[Union[BaseModelBackend, List[BaseModelBackend], ModelManager]] = None,
        agent_graph: "AgentGraph" = None,
        available_actions: List[ActionType] = None,
        simulation=None,
        initial_balance: float = 100000.0,
        risk_per_trade: float = 0.01,
        archetype: str = "Retail Reactor"
    ):
        # Load Persona if available
        try:
            import json, os
            persona_path = os.path.join(os.path.dirname(__file__), "..", "..", "app", "storage", "personas_v1.json")
            if os.path.exists(persona_path):
                with open(persona_path, "r") as f:
                    personas = json.load(f)
                    # Find matching persona by archetype key or Name
                    p_data = personas.get(archetype) or next((v for v in personas.values() if v["archetype"] == archetype), None)
                    if p_data:
                        user_info.name = p_data["name"]
                        user_info.description = p_data["description"]
                        if hasattr(user_info, "profile") and "other_info" in user_info.profile:
                            user_info.profile["other_info"]["user_profile"] = p_data["persona"]
                        logger.info(f"Loaded persona {user_info.name} for agent {agent_id}")
        except Exception as e:
            logger.error(f"Failed to load persona for archetype {archetype}: {e}")

        # Override simulation to use TradingAction for TradingAgents
        if simulation is not None:
             from dataclasses import replace
             from .trading_action import TradingAction
             simulation = replace(simulation, action_cls=TradingAction)
             if available_actions is None:
                 # Ensure trading tools are available
                 available_actions = (simulation.default_actions or []) + [
                     "submit_market_order", "get_portfolio_summary", 
                     "validate_trade_with_policy", "buy_shares", "sell_shares",
                     "analyze_smc_confluences", "generate_pine_script"
                 ]

        super().__init__(
            agent_id=agent_id,
            user_info=user_info,
            model=model,
            agent_graph=agent_graph,
            available_actions=available_actions,
            simulation=simulation
        )
        self.domicile = "France" # Default for now
        self.broker = LocalBroker(initial_balance=initial_balance)
        self.policy = TradingPolicy(risk_per_trade=risk_per_trade, domicile=self.domicile)
        self.archetype = archetype
        
        # Link agent to action for direct tool execution
        from .trading_action import TradingAction
        if hasattr(self.env, "action") and isinstance(self.env.action, TradingAction):
            self.env.action.agent = self
        
    async def get_portfolio_summary(self) -> str:
        """Returns a string representation of the current portfolio for prompting."""
        balance = await self.broker.get_balance()
        equity = await self.broker.get_equity()
        net_equity = await self.broker.get_net_equity(self.domicile)
        positions = await self.broker.get_positions()
        
        summary = f"\n[PORTFOLIO STATE - {self.domicile}]\n"
        summary += f"- Real Balance: ${balance:,.2f}\n"
        summary += f"- Total Equity (Gross): ${equity:,.2f}\n"
        summary += f"- Total Equity (Net Est.): ${net_equity:,.2f}\n"
        
        if not positions:
            summary += "- Positions: None\n"
        else:
            summary += "- Positions:\n"
            for pos in positions:
                summary += f"  * {pos.symbol}: {pos.qty} units @ avg ${pos.avg_price:,.2f} (Unrealized PnL: ${pos.unrealized_pnl:,.2f})\n"
        
        return summary
