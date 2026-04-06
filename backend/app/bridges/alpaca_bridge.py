import os
import logging
from typing import List, Optional, Dict
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

from wonderwall.environment.broker import BaseBroker, Trade, Position
from app.services.fiscal_service import FiscalService

logger = logging.getLogger(__name__)

class AlpacaBroker(BaseBroker):
    """
    Broker implementation for Alpaca API.
    Supports both Paper Trading and Live Trading via environment variables.
    """
    def __init__(self, api_key: str = None, secret_key: str = None, paper: bool = True, fiscal_service: Optional[FiscalService] = None):
        super().__init__(fiscal_service)
        
        # Load from env if not provided
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        self.paper = paper
        
        if not self.api_key or not self.secret_key:
            logger.warning("Alpaca API credentials missing. Bridge will fail on live calls.")
            
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=self.paper)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)

    async def get_balance(self) -> float:
        """Returns the current buying power (cash)."""
        try:
            account = self.trading_client.get_account()
            return float(account.buying_power)
        except Exception as e:
            logger.error(f"Alpaca get_balance failed: {e}")
            return 0.0

    async def get_equity(self) -> float:
        """Returns the total portfolio value (equity)."""
        try:
            account = self.trading_client.get_account()
            return float(account.equity)
        except Exception as e:
            logger.error(f"Alpaca get_equity failed: {e}")
            return 0.0

    async def get_net_equity(self, domicile: str = "France") -> float:
        """Calculates equity net of estimated taxes on profits."""
        account = self.trading_client.get_account()
        equity = float(account.equity)
        # Note: To be perfectly accurate, we'd need to calculate realized AND unrealized PnL 
        # for the current tax year. For now, we estimate based on unrealized PnL of current positions.
        
        positions = self.trading_client.get_all_positions()
        total_unrealized_pnl = sum(float(p.unrealized_pl) for p in positions)
        
        if self.fiscal_service and total_unrealized_pnl > 0:
            net_profit = self.fiscal_service.calculate_net_profit(total_unrealized_pnl, domicile)
            tax_liability = total_unrealized_pnl - net_profit
            return equity - tax_liability
            
        return equity

    async def submit_order(self, symbol: str, side: str, qty: float, current_price: float = 0, order_type: str = "market") -> Optional[Trade]:
        """Submit an order to Alpaca."""
        alpaca_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        
        order_data = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=alpaca_side,
            time_in_force=TimeInForce.GTC
        )
        
        try:
            order = self.trading_client.submit_order(order_data=order_data)
            # Re-map to our Trade dataclass
            return Trade(
                symbol=order.symbol,
                side=side,
                qty=float(order.qty),
                price=float(order.filled_avg_price) if order.filled_avg_price else 0.0,
                timestamp=order.created_at.isoformat(),
                order_id=str(order.id),
                status=order.status.value
            )
        except Exception as e:
            logger.error(f"Alpaca order submission failed: {e}")
            return None

    async def get_positions(self) -> List[Position]:
        """List all current positions in Alpaca."""
        alpaca_positions = self.trading_client.get_all_positions()
        return [
            Position(
                symbol=p.symbol,
                qty=float(p.qty),
                avg_price=float(p.avg_entry_price),
                unrealized_pnl=float(p.unrealized_pl)
            ) for p in alpaca_positions
        ]

    async def get_latest_price(self, symbol: str) -> float:
        """Get the latest quote for a symbol."""
        request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        latest_quote = self.data_client.get_stock_latest_quote(request_params)
        return latest_quote[symbol].ask_price
