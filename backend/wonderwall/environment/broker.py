from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
try:
    from app.services.fiscal_service import FiscalService
except ImportError:
    # Fallback for standalone tests or path issues
    FiscalService = None

@dataclass
class Trade:
    symbol: str
    side: str  # "buy" or "sell"
    qty: float
    price: float
    timestamp: str
    order_id: str
    status: str = "filled"  # filled, open, canceled

@dataclass
class Position:
    symbol: str
    qty: float
    avg_price: float
    unrealized_pnl: float = 0.0

class Broker(ABC):
    @abstractmethod
    async def get_balance(self) -> float:
        """Returns the current cash balance."""
        return 0.0

    @abstractmethod
    async def get_equity(self) -> float:
        """Returns the total equity (cash + position value)."""
        return 0.0

    @abstractmethod
    async def get_net_equity(self, domicile: str = "international") -> float:
        """Returns the net equity after estimated taxes."""
        return 0.0

    @abstractmethod
    async def submit_order(self, symbol: str, side: str, qty: float, current_price: float, order_type: str = "market") -> Optional[Trade]:
        return None

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        return []

class LocalBroker(Broker):
    """
    A local trading platform simulator for backtesting.
    Does not use real capital.
    """
    def __init__(self, initial_balance: float = 100000.0):
        self.balance = initial_balance
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity = initial_balance

    async def get_balance(self) -> float:
        return self.balance

    async def get_equity(self) -> float:
        """Returns balance + current market value of all positions."""
        # Note: In a real simulation, we'd need current prices from a market service.
        # Here we assume self.equity is updated via update_pnl.
        return self.equity

    async def get_net_equity(self, domicile: str = "international") -> float:
        """Calculates equity net of estimated taxes on unrealized profits."""
        total_unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        
        if FiscalService and total_unrealized_pnl > 0:
            # Estimate tax on unrealized profit as if we sold everything now
            net_profit = FiscalService.calculate_net_profit(total_unrealized_pnl, domicile)
            tax_liability = total_unrealized_pnl - net_profit
            return self.equity - tax_liability
            
        return self.equity

    async def submit_order(self, symbol: str, side: str, qty: float, current_price: float, order_type: str = "market") -> Optional[Trade]:
        """Submit an order with the provided price (simulated fill)."""
        cost = qty * current_price
        
        if side == "buy":
            if cost > self.balance:
                return None  # Insufficient funds
            
            self.balance -= cost
            if symbol in self.positions:
                pos = self.positions[symbol]
                total_cost = (pos.avg_price * pos.qty) + cost
                pos.qty += qty
                pos.avg_price = total_cost / pos.qty
            else:
                self.positions[symbol] = Position(symbol, qty, current_price)
                
        elif side == "sell":
            if symbol not in self.positions or self.positions[symbol].qty < qty:
                return None  # No position or insufficient qty
            
            pos = self.positions[symbol]
            self.balance += cost
            pos.qty -= qty
            if pos.qty == 0:
                self.positions.pop(symbol, None)

        
        trade = Trade(
            symbol=symbol,
            side=side,
            qty=qty,
            price=current_price,
            timestamp=datetime.now().isoformat(),
            order_id=f"order_{len(self.trades) + 1}"
        )
        self.trades.append(trade)
        self.update_pnl(symbol, current_price)
        return trade

    async def get_positions(self) -> List[Position]:
        return list(self.positions.values())

    def update_pnl(self, symbol: str, current_price: float):
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.unrealized_pnl = (current_price - pos.avg_price) * pos.qty
            self.equity = self.balance + sum(p.unrealized_pnl for p in self.positions.values())
