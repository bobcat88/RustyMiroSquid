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
        self.assets = ["SPY", "QQQ", "NVDA", "TSLA", "BTC-USD"]
        self.rss_feeds = [
            "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
            "https://feeds.bloomberg.com/markets/news.rss"
        ]
        self.market_color = "MODERATE"  # Default: Plan M
        self.fear_greed_idx = 50.0  # 0-100
        self.signals = []
        
        # LLM for news sentiment analysis
        self.llm = create_llm_client()

    async def poll_market_data(self) -> Dict[str, Any]:
        """Fetch latest OHLC data via yfinance."""
        results = {}
        for symbol in self.assets:
            try:
                ticker = yf.Ticker(symbol)
                # Get last 5 days of 1h data
                df = ticker.history(period="5d", interval="1h")
                if not df.empty:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest
                    
                    price = latest['Close']
                    change = (price - prev['Close']) / prev['Close'] if prev['Close'] != 0 else 0
                    
                    results[symbol] = {
                        "price": float(price),
                        "change_pct": float(change * 100),
                        "high": float(latest['High']),
                        "low": float(latest['Low']),
                        "volume": int(latest['Volume']),
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Basic FVG (Fair Value Gap) detection logic
                    # A gap between candle 1 high and candle 3 low (in an uptrend)
                    if len(df) >= 3:
                        c1 = df.iloc[-3]
                        c2 = df.iloc[-2]
                        c3 = df.iloc[-1]
                        
                        # Bullish FVG
                        if c3['Low'] > c1['High']:
                            self.signals.append({
                                "type": "BULLISH_FVG",
                                "symbol": symbol,
                                "top": float(c3['Low']),
                                "bottom": float(c1['High']),
                                "timestamp": datetime.now().isoformat()
                            })
                        # Bearish FVG
                        elif c3['High'] < c1['Low']:
                            self.signals.append({
                                "type": "BEARISH_FVG",
                                "symbol": symbol,
                                "top": float(c1['Low']),
                                "bottom": float(c3['High']),
                                "timestamp": datetime.now().isoformat()
                            })
                            
            except Exception as e:
                logger.error(f"Error polling yfinance for {symbol}: {e}")
        
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

    def get_current_state(self) -> Dict[str, Any]:
        """Return the current trigger state for agent consumption."""
        return {
            "market_color": self.market_color,
            "fear_greed_index": self.fear_greed_idx,
            "recent_signals": self.signals[-10:],
            "last_update": datetime.now().isoformat()
        }

# Global singleton or per-simulation instance?
# For now, we'll use an instance in the simulation manager.
