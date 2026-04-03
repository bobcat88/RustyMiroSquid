import orjson
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.market_connector import MarketConnector
from app.services.sentiment_velocity import SentimentVelocityTracker

router = APIRouter()

# WebSocket Hub for real-time market data
class MarketHub:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        # Sérialisation via orjson pour la performance
        raw_msg = orjson.dumps(message).decode()
        for connection in self.active_connections:
            try:
                await connection.send_text(raw_msg)
            except Exception:
                continue

market_hub = MarketHub()

# Global instances (init in main or dependencies)
market_connector = MarketConnector()
velocity_tracker = SentimentVelocityTracker()

@router.get("/snapshot")
async def get_market_snapshot():
    """Retourne un snapshot complet des prix et de la watchlist."""
    return {
        "prices": market_connector.prices,
        "watchlist": market_connector.get_watchlist(),
        "last_update": market_connector.last_update.isoformat() if market_connector.last_update else None
    }

@router.get("/velocity")
async def get_sentiment_velocity(top_n: int = Query(10, ge=1)):
    """Retourne les signaux de vélocité de sentiment."""
    signals = velocity_tracker.compute_velocities()
    alerts = velocity_tracker.get_trading_alerts()
    return {
        "signals": signals[:top_n],
        "alerts": alerts
    }

@router.get("/watchlist")
async def get_watchlist():
    """Retourne la watchlist actuelle."""
    return {"watchlist": market_connector.get_watchlist()}

@router.post("/watchlist/add")
async def add_to_watchlist(symbol: str, category: str = "us_equities"):
    """Ajoute un ticker à la watchlist."""
    market_connector.add_to_watchlist(symbol, category)
    return {"status": "success", "symbol": symbol}

@router.post("/watchlist/remove")
async def remove_from_watchlist(symbol: str):
    """Supprime un ticker de la watchlist."""
    market_connector.remove_from_watchlist(symbol)
    return {"status": "success", "symbol": symbol}

@router.websocket("/ws/market")
async def market_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time market updates.
    Upon connection, sends a full snapshot.
    Then broadcasts periodic updates from the market connector and velocity tracker.
    """
    await market_hub.connect(websocket)
    
    # Send initial snapshot
    await websocket.send_text(orjson.dumps({
        "type": "snapshot",
        "prices": market_connector.prices,
        "velocity": velocity_tracker.compute_velocities()[:10],
        "alerts": velocity_tracker.get_trading_alerts()
    }).decode())

    try:
        while True:
            # On attend un message du client (heartbeat) ou on boucle
            # En production, on utiliserait un event loop séparé pour le broadcast
            data = await websocket.receive_text()
            # On peut répondre à des commandes directes ici si besoin
    except WebSocketDisconnect:
        market_hub.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        market_hub.disconnect(websocket)
