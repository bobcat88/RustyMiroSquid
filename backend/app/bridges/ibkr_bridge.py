import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict
from ib_insync import IB, Stock, MarketOrder, Trade as IBTrade, Position as IBPosition, util

from wonderwall.environment.broker import BaseBroker, Trade, Position
from app.services.fiscal_service import FiscalService

logger = logging.getLogger(__name__)

class IBKRBroker(BaseBroker):
    """
    Broker implementation for Interactive Brokers (IBKR).
    Connects to TWS or IB Gateway (default ports: 7497/4002).
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1, fiscal_service: Optional[FiscalService] = None):
        super().__init__(fiscal_service)
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()

    async def connect(self):
        """Connect to TWS/Gateway."""
        if not self.ib.isConnected():
            try:
                await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
                logger.info(f"Connected to IBKR at {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"IBKR connection failed: {e}")
                raise

    async def disconnect(self):
        """Disconnect from TWS/Gateway."""
        if self.ib.isConnected():
            self.ib.disconnect()

    async def get_balance(self) -> float:
        """Returns the current cash balance."""
        await self.connect()
        # Summary returns a list of AccountValue objects
        summary = self.ib.accountSummary()
        for item in summary:
            if item.tag == "CashBalance" and item.currency == "USD":
                return float(item.value)
        return 0.0

    async def get_equity(self) -> float:
        """Returns the total Net Liquidation value."""
        await self.connect()
        summary = self.ib.accountSummary()
        for item in summary:
            if item.tag == "NetLiquidation" and item.currency == "USD":
                return float(item.value)
        return 0.0

    async def get_net_equity(self, domicile: str = "France") -> float:
        """Calculates equity net of estimated taxes on unrealized profits."""
        await self.connect()
        equity = await self.get_equity()
        
        # Calculate unrealized PnL from positions
        positions = self.ib.positions()
        # Note: ib_insync positions don't have direct PnL, we'd need to subscribe to PnL or calculate it.
        # For simplicity in this bridge, we assume we need to calculate it from avgCost/marketPrice.
        # But IBKR provides a pnl() method if we subscribe.
        
        # Placeholder for complex calculation
        unrealized_pnl = 0.0
        for pos in positions:
            # We'd need to fetch the ticker to get market price
            ticker = self.ib.reqTickers(pos.contract)[0]
            if ticker.marketPrice() > 0:
                unrealized_pnl += (ticker.marketPrice() - pos.avgCost) * pos.quantity
        
        if self.fiscal_service and unrealized_pnl > 0:
            net_profit = self.fiscal_service.calculate_net_profit(unrealized_pnl, domicile)
            tax_liability = unrealized_pnl - net_profit
            return equity - tax_liability
            
        return equity

    async def submit_order(self, symbol: str, side: str, qty: float, current_price: float = 0, order_type: str = "market") -> Optional[Trade]:
        """Submit a Market order to IBKR."""
        await self.connect()
        contract = Stock(symbol, 'SMART', 'USD')
        ib_side = 'BUY' if side == 'buy' else 'SELL'
        order = MarketOrder(ib_side, qty)
        
        try:
            trade = self.ib.placeOrder(contract, order)
            # Wait for fill (timeout 30s)
            while not trade.isDone():
                await asyncio.sleep(1)
            
            fill = trade.fills[0] if trade.fills else None
            
            return Trade(
                symbol=symbol,
                side=side,
                qty=qty,
                price=fill.execution.avgPrice if fill else current_price,
                timestamp=datetime.now().isoformat(),
                order_id=str(order.orderId),
                status=trade.status
            )
        except Exception as e:
            logger.error(f"IBKR order submission failed: {e}")
            return None

    async def get_positions(self) -> List[Position]:
        """List all current positions in IBKR."""
        await self.connect()
        ib_positions = self.ib.positions()
        positions = []
        for p in ib_positions:
            # Fetch market price for PnL
            ticker = self.ib.reqTickers(p.contract)[0]
            mkt_price = ticker.marketPrice() if ticker.marketPrice() > 0 else p.avgCost
            positions.append(Position(
                symbol=p.contract.symbol,
                qty=p.quantity,
                avg_price=p.avgCost,
                unrealized_pnl=(mkt_price - p.avgCost) * p.quantity
            ))
        return positions
