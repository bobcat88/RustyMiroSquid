"""
Market Connector — Données de marché en temps réel.

Connecte RustyMiroSquid aux marchés financiers réels :
- Binance WebSocket (crypto : BTC, ETH, SOL, etc.)
- yfinance snapshots (equities, ETFs, leveraged ETPs, commodities)

Les données enrichissent le MarketMediaBridge existant pour donner
aux agents-simulés un contexte de marché réel en complément des
prix simulés Polymarket.

Usage:
    connector = MarketConnector()

    # Démarrer le flux WebSocket Binance (utilise la watchlist crypto)
    await connector.start_binance()

    # Snapshot yfinance (toute la watchlist non-crypto)
    data = connector.fetch_equities()

    # Ajouter un ticker custom
    connector.add_to_watchlist("TSLA", "us_equities")

    # Prompt formaté pour injection dans les agents
    prompt = connector.to_agent_prompt()

    # Arrêt propre
    await connector.stop()
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import orjson

logger = logging.getLogger(__name__)


# ── Watchlist par catégorie ───────────────────────────────────────
# Les tickers sont au format yfinance.
# Suffixes : .NE (Cboe Canada), .L (LSE), .DE (Xetra), sans suffixe (US)

DEFAULT_WATCHLIST: Dict[str, List[str]] = {
    # Crypto — symboles Binance (lowercase, paires USDT)
    "crypto": [
        "btcusdt", "ethusdt", "solusdt",
    ],

    # US Equities
    "us_equities": [
        "SPY",    # S&P 500 ETF
        "AAPL",   # Apple
        "MSFT",   # Microsoft
        "NVDA",   # NVIDIA
        "INTC",   # Intel
        "IREN",   # IREN Ltd (ex-Iris Energy) — Bitcoin mining
        "NBIS",   # Nebius Group — AI infrastructure (ex-Yandex)
        "ADUR",   # Aduro Clean Technologies
    ],

    # Canadian Equities
    "ca_equities": [
        "DEFI.NE",  # DeFi Technologies Inc. (Cboe Canada)
    ],

    # Leveraged ETPs (WisdomTree, LSE)
    "leveraged_etps": [
        "3SIL.L",   # WisdomTree Silver 3x Daily Leveraged (WKN: A1VBKL)
        "3HCL.L",   # WisdomTree Copper 3x Daily Leveraged (WKN: A1VBKQ)
    ],

    # ETFs / Commodities
    "etfs_commodities": [
        "UBUD.DE",  # UBS Solactive Global Pure Gold Miners UCITS ETF (WKN: A1JVYP)
    ],
}


@dataclass
class TickerPrice:
    """Prix d'un ticker à un instant donné."""
    symbol: str
    price: float
    timestamp: float
    volume_24h: float = 0.0
    change_pct_24h: float = 0.0
    source: str = "unknown"  # "binance" | "yfinance"


class MarketConnector:
    """Connecteur de données de marché multi-source avec watchlist configurable.

    Thread-safe: protège _prices via Lock pour accès concurrent
    depuis le WebSocket thread et le thread de simulation.

    Args:
        watchlist: Watchlist custom par catégorie. None = DEFAULT_WATCHLIST.
        binance_ws_url: URL WebSocket Binance.
        yfinance_throttle_seconds: Intervalle minimum entre les appels yfinance.
    """

    def __init__(
        self,
        watchlist: Optional[Dict[str, List[str]]] = None,
        binance_ws_url: str = "wss://stream.binance.com:9443/ws",
        yfinance_throttle_seconds: float = 30.0,
    ):
        self.binance_ws_url = binance_ws_url
        self.yfinance_throttle = yfinance_throttle_seconds

        # Watchlist configurable (copie profonde pour éviter les mutations)
        self._watchlist: Dict[str, List[str]] = {
            k: list(v) for k, v in (watchlist or DEFAULT_WATCHLIST).items()
        }

        self._lock = threading.Lock()
        self._prices: Dict[str, TickerPrice] = {}
        self._price_history: Dict[str, List[TickerPrice]] = {}
        self._ws_task: Optional[asyncio.Task] = None
        self._running = False

        # Throttle yfinance
        self._last_yfinance_fetch: float = 0.0

    # ── Watchlist management ──────────────────────────────────────

    def add_to_watchlist(self, symbol: str, category: str) -> None:
        """Ajouter un symbole à une catégorie de la watchlist."""
        if category not in self._watchlist:
            self._watchlist[category] = []
        if symbol not in self._watchlist[category]:
            self._watchlist[category].append(symbol)
            logger.info(f"Watchlist: ajouté {symbol} dans {category}")

    def remove_from_watchlist(self, symbol: str, category: Optional[str] = None) -> bool:
        """Retirer un symbole de la watchlist. Si category=None, cherche partout."""
        categories = [category] if category else list(self._watchlist.keys())
        for cat in categories:
            if cat in self._watchlist and symbol in self._watchlist[cat]:
                self._watchlist[cat].remove(symbol)
                logger.info(f"Watchlist: retiré {symbol} de {cat}")
                return True
        return False

    def get_watchlist(self) -> Dict[str, List[str]]:
        """Obtenir la watchlist complète."""
        return {k: list(v) for k, v in self._watchlist.items()}

    @property
    def crypto_symbols(self) -> List[str]:
        """Symboles crypto (pour Binance WebSocket)."""
        return self._watchlist.get("crypto", [])

    @property
    def yfinance_symbols(self) -> List[str]:
        """Tous les symboles non-crypto (pour yfinance batch download)."""
        symbols = []
        for cat, tickers in self._watchlist.items():
            if cat != "crypto":
                symbols.extend(tickers)
        return symbols

    # ── Binance WebSocket (crypto) ────────────────────────────────

    async def start_binance(
        self,
        symbols: Optional[List[str]] = None,
    ):
        """Démarrer le flux WebSocket Binance pour les symboles donnés.

        Args:
            symbols: Liste de paires (lowercase). None = utilise la watchlist crypto.
        """
        if self._running:
            logger.warning("MarketConnector: WebSocket déjà actif")
            return

        if symbols is None:
            symbols = self.crypto_symbols

        if not symbols:
            logger.warning("MarketConnector: aucun symbole crypto dans la watchlist")
            return

        self._running = True
        self._ws_task = asyncio.create_task(
            self._binance_ws_loop(symbols)
        )
        logger.info(f"MarketConnector: WebSocket Binance démarré pour {symbols}")

    async def _binance_ws_loop(self, symbols: List[str]):
        """Boucle WebSocket — reçoit les mini-tickers Binance.

        Utilise le stream combiné pour recevoir les prix de
        plusieurs symboles sur une seule connexion.
        """
        try:
            import websockets
        except ImportError:
            logger.error(
                "websockets non installé. WebSocket Binance désactivé. "
                "Installer avec: uv add websockets"
            )
            self._running = False
            return

        # Stream combiné : wss://stream.binance.com:9443/stream?streams=...
        streams = "/".join(f"{s}@miniTicker" for s in symbols)
        url = f"{self.binance_ws_url}/{streams}"

        retry_delay = 1.0

        while self._running:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    logger.info(f"Binance WebSocket connecté: {url}")
                    retry_delay = 1.0  # Reset on success

                    async for message in ws:
                        if not self._running:
                            break

                        try:
                            data = orjson.loads(message)

                            # Stream combiné enveloppe les données
                            if "data" in data:
                                data = data["data"]

                            symbol = data.get("s", "").lower()
                            price = float(data.get("c", 0))  # Close price
                            volume = float(data.get("v", 0))  # Volume 24h
                            change_pct = float(data.get("P", 0))  # Price change %

                            if symbol and price > 0:
                                ticker = TickerPrice(
                                    symbol=symbol,
                                    price=price,
                                    timestamp=time.time(),
                                    volume_24h=volume,
                                    change_pct_24h=change_pct,
                                    source="binance",
                                )
                                self._update_price(ticker)

                        except (ValueError, KeyError) as e:
                            logger.debug(f"Binance parse error: {e}")

            except Exception as e:
                if self._running:
                    logger.warning(
                        f"Binance WebSocket déconnecté: {e}. "
                        f"Reconnexion dans {retry_delay:.0f}s..."
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 60.0)

    def _update_price(self, ticker: TickerPrice):
        """Mettre à jour le prix d'un symbole (thread-safe)."""
        with self._lock:
            self._prices[ticker.symbol] = ticker

            # Historique (garder les 100 derniers points)
            if ticker.symbol not in self._price_history:
                self._price_history[ticker.symbol] = []
            history = self._price_history[ticker.symbol]
            history.append(ticker)
            if len(history) > 100:
                del history[:len(history) - 100]

    # ── yfinance (equities) ──────────────────────────────────────

    def fetch_equities(
        self,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, TickerPrice]:
        """Récupérer les prix de la watchlist via yfinance.

        Récupère TOUS les symboles non-crypto de la watchlist en batch.
        Rate-limited: respecte yfinance_throttle_seconds entre les appels.

        Args:
            symbols: Liste de tickers override. None = toute la watchlist yfinance.

        Returns:
            Dict symbol -> TickerPrice.
        """
        if symbols is None:
            symbols = self.yfinance_symbols

        if not symbols:
            logger.debug("yfinance: aucun symbole dans la watchlist")
            return {}

        # Throttle
        now = time.time()
        elapsed = now - self._last_yfinance_fetch
        if elapsed < self.yfinance_throttle:
            logger.debug(
                f"yfinance throttled ({elapsed:.1f}s < {self.yfinance_throttle}s)"
            )
            with self._lock:
                return {s: self._prices[s.lower()] for s in symbols if s.lower() in self._prices}

        try:
            import yfinance as yf
        except ImportError:
            logger.error(
                "yfinance non installé. Equities désactivées. "
                "Installer avec: uv add yfinance"
            )
            return {}

        results = {}
        try:
            # Batch download (plus efficace que ticker par ticker)
            data = yf.download(
                " ".join(symbols),
                period="1d",
                interval="1m",
                progress=False,
                threads=True,
            )

            self._last_yfinance_fetch = time.time()

            if data.empty:
                logger.warning("yfinance: aucune donnée retournée")
                return results

            for symbol in symbols:
                try:
                    if len(symbols) > 1:
                        close = data["Close"][symbol].iloc[-1]
                    else:
                        close = data["Close"].iloc[-1]

                    # Identifier la catégorie source
                    source_cat = self._find_category(symbol)

                    ticker = TickerPrice(
                        symbol=symbol.lower(),
                        price=float(close),
                        timestamp=time.time(),
                        source=f"yfinance:{source_cat}",
                    )
                    self._update_price(ticker)
                    results[symbol] = ticker

                except (KeyError, IndexError) as e:
                    logger.debug(f"yfinance skip {symbol}: {e}")

        except Exception as e:
            logger.error(f"yfinance fetch error: {e}")

        return results

    def _find_category(self, symbol: str) -> str:
        """Trouver la catégorie d'un symbole dans la watchlist."""
        for cat, tickers in self._watchlist.items():
            if symbol in tickers:
                return cat
        return "unknown"

    # ── Lecture des prix ──────────────────────────────────────────

    def get_latest_price(self, symbol: str) -> Optional[TickerPrice]:
        """Obtenir le dernier prix d'un symbole. Thread-safe."""
        with self._lock:
            return self._prices.get(symbol.lower())

    def get_all_prices(self) -> Dict[str, TickerPrice]:
        """Obtenir tous les dernier prix. Thread-safe."""
        with self._lock:
            return dict(self._prices)

    def get_price_history(self, symbol: str) -> List[TickerPrice]:
        """Obtenir l'historique des prix d'un symbole. Thread-safe."""
        with self._lock:
            return list(self._price_history.get(symbol.lower(), []))

    # ── Prompt injection ─────────────────────────────────────────

    def to_agent_prompt(self) -> str:
        """Générer un prompt formaté avec les données de marché réelles.

        Injecté dans les agents pour leur donner une conscience
        du contexte financier réel en complément de Polymarket simulé.
        Organise les données par catégorie de la watchlist.
        """
        with self._lock:
            if not self._prices:
                return ""

            lines = ["# REAL MARKET DATA (Live)"]
            lines.append(
                "These are REAL market prices from financial exchanges. "
                "Use this context to ground your analysis in actual market conditions."
            )
            lines.append("")

            # Labels humains pour les catégories
            cat_labels = {
                "crypto": "Crypto",
                "us_equities": "US Equities",
                "ca_equities": "Canadian Equities",
                "leveraged_etps": "Leveraged ETPs (3x)",
                "etfs_commodities": "ETFs & Commodities",
            }

            # Grouper les prix par catégorie
            for cat, cat_symbols in self._watchlist.items():
                cat_prices = [
                    (s, self._prices.get(s.lower()))
                    for s in cat_symbols
                    if s.lower() in self._prices
                ]
                if not cat_prices:
                    continue

                label = cat_labels.get(cat, cat.replace("_", " ").title())
                lines.append(f"  {label}:")

                for symbol, ticker in cat_prices:
                    if ticker is None:
                        continue
                    age = time.time() - ticker.timestamp
                    age_str = f"{age:.0f}s ago" if age < 60 else f"{age/60:.0f}m ago"
                    change = ""
                    if ticker.change_pct_24h:
                        change = f" ({ticker.change_pct_24h:+.2f}%)"
                    lines.append(
                        f"    {symbol.upper()}: ${ticker.price:,.2f}{change} [{age_str}]"
                    )

            lines.append("")
            return "\n".join(lines)

    # ── Lifecycle ─────────────────────────────────────────────────

    async def stop(self):
        """Arrêter proprement le WebSocket et libérer les ressources."""
        self._running = False
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        logger.info("MarketConnector arrêté")

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques du connecteur."""
        with self._lock:
            return {
                "running": self._running,
                "symbols_tracked": len(self._prices),
                "crypto_count": sum(1 for p in self._prices.values() if p.source == "binance"),
                "equity_count": sum(1 for p in self._prices.values() if p.source == "yfinance"),
                "history_points": sum(len(h) for h in self._price_history.values()),
            }
