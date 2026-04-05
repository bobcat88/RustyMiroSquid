import asyncio
import yfinance as yf
import feedparser
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from ..utils.logger import get_logger
from ..utils.llm_client import create_llm_client
from ..config import Config

logger = get_logger('rusty.trigger_service')

class TriggerService:
    """
    TriggerService polls external data sources (yfinance, RSS) 
    to extract market signals and compute 'Market Color'.
    """
    
    def __init__(self):
        self.assets: List[str] = ["SPY", "QQQ", "TQQQ", "NVDA", "AAPL", "MSFT", "TSLA", "BTC-USD"]
        self.rss_feeds: List[str] = [
            "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
            "https://feeds.bloomberg.com/markets/news.rss"
        ]
        self.market_color: str = "MODERATE"  # Default: Plan M
        self.fear_greed_idx: float = 50.0  # 0-100
        self.signals: List[Dict[str, Any]] = []
        
        # State persistence
        self.latest_prices: Dict[str, Any] = {}
        self.headlines: List[Dict[str, str]] = []

        # LLM for news sentiment analysis
        self.llm = create_llm_client()

    async def poll_market_data(self) -> Dict[str, Any]:
        """Fetch latest OHLC data via yfinance for HTF trend and LTF entries."""
        results = {}
        for symbol in self.assets:
            try:
                ticker = yf.Ticker(symbol)
                
                # HTF: 1h for Trend Bias (last 10 days)
                df_htf = ticker.history(period="10d", interval="1h")
                # LTF: 15m for Execution (last 2 days)
                df_ltf = ticker.history(period="2d", interval="15m")
                
                if df_htf.empty or df_ltf.empty:
                    continue

                # --- HTF Trend Bias (EMA 50 check) ---
                close_htf = df_htf['Close']
                ema50_htf = close_htf.ewm(span=50, adjust=False).mean()
                latest_close_htf = close_htf.iloc[-1]
                latest_ema50_htf = ema50_htf.iloc[-1]
                
                bias = "BULLISH" if latest_close_htf > latest_ema50_htf else "BEARISH"
                self.signals.append({
                    "type": f"HTF_BIAS_{bias}", "symbol": symbol,
                    "htf_price": float(latest_close_htf), "htf_ema50": float(latest_ema50_htf),
                    "timestamp": datetime.now().isoformat()
                })

                # Latest Price for results
                current_price = float(df_ltf['Close'].iloc[-1])
                results[symbol] = {
                    "price": current_price,
                    "change_pct": float((current_price - df_htf['Close'].iloc[-1]) / df_htf['Close'].iloc[-1] * 100),
                    "bias": bias,
                    "timestamp": datetime.now().isoformat()
                }

                # --- SMC (Smart Money Concepts) Detection on LTF (15m) ---
                # 1. FVG Detection (LTF)
                if len(df_ltf) >= 3:
                    c1, c2, c3 = df_ltf.iloc[-3], df_ltf.iloc[-2], df_ltf.iloc[-1]
                    if c3['Low'] > c1['High']: # Bullish FVG
                        self.signals.append({
                            "type": "LTF_FVG_BULLISH", "symbol": symbol,
                            "top": float(c3['Low']), "bottom": float(c1['High']),
                            "timestamp": datetime.now().isoformat()
                        })
                    elif c3['High'] < c1['Low']: # Bearish FVG
                        self.signals.append({
                            "type": "LTF_FVG_BEARISH", "symbol": symbol,
                            "top": float(c1['Low']), "bottom": float(c3['High']),
                            "timestamp": datetime.now().isoformat()
                        })

                # 2. LTF Liquidity Sweep
                high_24h = df_ltf.iloc[:-1]['High'].max()
                low_24h = df_ltf.iloc[:-1]['Low'].min()
                l_high, l_low, l_close = df_ltf.iloc[-1]['High'], df_ltf.iloc[-1]['Low'], df_ltf.iloc[-1]['Close']

                if l_high > high_24h and l_close < high_24h:
                    self.signals.append({"type": "LTF_SWEEP_TOP", "symbol": symbol, "level": float(high_24h)})
                elif l_low < low_24h and l_close > low_24h:
                    self.signals.append({"type": "LTF_SWEEP_BOTTOM", "symbol": symbol, "level": float(low_24h)})
                
                # 3. Market Structure Shift (MSS) on LTF
                # Simple version: cross of recent fractal high/low
                prev_high = df_ltf.iloc[-5:-1]['High'].max()
                prev_low = df_ltf.iloc[-5:-1]['Low'].min()
                if l_close > prev_high and bias == "BULLISH":
                    self.signals.append({"type": "LTF_MSS_BULLISH", "symbol": symbol, "timestamp": datetime.now().isoformat()})
                elif l_close < prev_low and bias == "BEARISH":
                    self.signals.append({"type": "LTF_MSS_BEARISH", "symbol": symbol, "timestamp": datetime.now().isoformat()})
                            
            except Exception as e:
                logger.error(f"Error polling yfinance for {symbol}: {e}")
        
        self.latest_prices = results
        return results

    async def poll_news(self) -> List[Dict[str, str]]:
        """Fetch and analyze news sentiment."""
        headlines = []
        for url in self.rss_feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    headlines.append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.get('summary', '')
                    })
            except Exception as e:
                logger.error(f"Error polling RSS {url}: {e}")
        
        self.headlines = headlines
        if headlines:
            # Aggregate sentiment using LLM
            await self._analyze_sentiment(headlines)
            
        return headlines

    async def _analyze_sentiment(self, news: List[Dict[str, str]]):
        """Analyze news list for aggregate Fear/Greed impact."""
        try:
            titles = "\n".join([f"- {n['title']}" for n in news])
            prompt = f"""Analyze the following financial headlines and determine the aggregate 'Fear vs Greed' sentiment on a scale of 0 (Extreme Fear) to 100 (Extreme Greed). 
            Return ONLY a JSON object: {{"score": float, "reason": "string", "market_color": "AGGRESSIVE|MODERATE|DEFENSIVE|CASH"}}
            
            Headlines:
            {titles}
            """
            
            response = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response)
            self.fear_greed_idx = float(result.get("score", 50.0))
            self.market_color = result.get("market_color", "MODERATE")
            logger.info(f"Updated Market Color: {self.market_color} (Score: {self.fear_greed_idx})")
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")

    async def update(self) -> Dict[str, Any]:
        """Poll all data sources and return the latest state."""
        logger.info("Updating market triggers...")
        await self.poll_market_data()
        await self.poll_news()
        return self.get_current_state()

    def get_current_state(self) -> Dict[str, Any]:
        """Return the current trigger state for agent consumption."""
        # Group signals by symbol for the bridge
        smc_by_symbol: Dict[str, List[str]] = {}
        
        # Explicit type check for the linter
        all_signals: List[Dict[str, Any]] = self.signals
        
        for s in all_signals[-20:]:  # Slice from the end
            symbol = str(s.get("symbol", "GLOBAL"))
            sig_type = str(s.get("type", "UNKNOWN"))
            
            if symbol not in smc_by_symbol:
                smc_by_symbol[symbol] = []
            smc_by_symbol[symbol].append(sig_type)

        return {
            "market_color": self.market_color,
            "sentiment_score": (self.fear_greed_idx - 50.0) / 10.0,
            "headlines": [str(h.get('title', '')) for h in self.headlines],
            "smc_signals": smc_by_symbol,
            "prices": {str(s): data.get('price', 0.0) for s, data in self.latest_prices.items()},
            "last_update": datetime.now().isoformat()
        }

# Global singleton or per-simulation instance?
# For now, we'll use an instance in the simulation manager.
