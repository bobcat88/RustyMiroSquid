import pytest
import nest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch

nest_asyncio.apply()

from app.bridges.alpaca_bridge import AlpacaBroker
from app.services.fiscal_service import FiscalService

@pytest.fixture
def mock_fiscal_service():
    service = MagicMock(spec=FiscalService)
    service.calculate_net_profit.side_effect = lambda profit, domicile: profit * 0.7 if profit > 0 else profit
    return service

@pytest.mark.asyncio
async def test_alpaca_get_balance(mock_fiscal_service):
    # Fix patch path to match the actual import in alpaca_bridge.py
    with patch("app.bridges.alpaca_bridge.TradingClient") as MockTradingClient:
        mock_client = MockTradingClient.return_value
        mock_client.get_account.return_value = MagicMock(buying_power="100000.0", equity="150000.0")
        
        broker = AlpacaBroker(api_key="test", secret_key="test", fiscal_service=mock_fiscal_service)
        balance = await broker.get_balance()
        
        assert balance == 100000.0
        assert mock_client.get_account.called

@pytest.mark.asyncio
async def test_alpaca_get_net_equity(mock_fiscal_service):
    with patch("app.bridges.alpaca_bridge.TradingClient") as MockTradingClient:
        mock_client = MockTradingClient.return_value
        mock_client.get_account.return_value = MagicMock(equity="150000.0")
        # Position with 10k profit
        mock_client.get_all_positions.return_value = [
            MagicMock(unrealized_pl="10000.0")
        ]
        
        broker = AlpacaBroker(api_key="test", secret_key="test", fiscal_service=mock_fiscal_service)
        net_equity = await broker.get_net_equity(domicile="France")
        
        # Profit 10k -> Net 7k (tax 3k)
        # Equity 150k - Tax 3k = 147k
        assert net_equity == 147000.0

@pytest.mark.asyncio
async def test_ibkr_get_equity(mock_fiscal_service):
    # Delayed import to ensure nest_asyncio is applied
    from app.bridges.ibkr_bridge import IBKRBroker
    with patch("app.bridges.ibkr_bridge.IB") as MockIB:
        mock_ib = MockIB.return_value
        mock_ib.isConnected.return_value = True
        mock_ib.accountSummary.return_value = [
            MagicMock(tag="NetLiquidation", currency="USD", value="200000.0")
        ]
        
        broker = IBKRBroker(fiscal_service=mock_fiscal_service)
        broker.ib = mock_ib
        
        equity = await broker.get_equity()
        assert equity == 200000.0

@pytest.mark.asyncio
async def test_alpaca_get_balance_error(mock_fiscal_service):
    """Vérifie que AlpacaBroker.get_balance gère les erreurs API."""
    with patch("app.bridges.alpaca_bridge.TradingClient") as MockTradingClient:
        mock_client = MockTradingClient.return_value
        mock_client.get_account.side_effect = Exception("API Error")
        
        broker = AlpacaBroker(api_key="test", secret_key="test", fiscal_service=mock_fiscal_service)
        balance = await broker.get_balance()
        
        assert balance == 0.0

@pytest.mark.asyncio
async def test_alpaca_submit_order_error(mock_fiscal_service):
    """Vérifie que AlpacaBroker.submit_order gère les erreurs API."""
    with patch("app.bridges.alpaca_bridge.TradingClient") as MockTradingClient:
        mock_client = MockTradingClient.return_value
        mock_client.submit_order.side_effect = Exception("Order Failed")
        
        broker = AlpacaBroker(api_key="test", secret_key="test", fiscal_service=mock_fiscal_service)
        trade = await broker.submit_order("AAPL", "buy", 10)
        
        assert trade is None

@pytest.mark.asyncio
async def test_ibkr_get_equity_error(mock_fiscal_service):
    """Vérifie que IBKRBroker.get_equity gère les erreurs API."""
    from app.bridges.ibkr_bridge import IBKRBroker
    with patch("app.bridges.ibkr_bridge.IB") as MockIB:
        mock_ib = MockIB.return_value
        mock_ib.isConnected.return_value = False
        mock_ib.connectAsync.side_effect = Exception("Connection Failed")
        
        broker = IBKRBroker(fiscal_service=mock_fiscal_service)
        equity = await broker.get_equity()
        
        assert equity == 0.0

@pytest.mark.asyncio
async def test_ibkr_get_positions_error(mock_fiscal_service):
    """Vérifie que IBKRBroker.get_positions gère les erreurs API."""
    from app.bridges.ibkr_bridge import IBKRBroker
    with patch("app.bridges.ibkr_bridge.IB") as MockIB:
        mock_ib = MockIB.return_value
        mock_ib.isConnected.return_value = True
        mock_ib.positions.side_effect = Exception("Fetch Failed")
        
        broker = IBKRBroker(fiscal_service=mock_fiscal_service)
        positions = await broker.get_positions()
        
        assert positions == []
