"""
Market-Media Bridge — connects Polymarket prices and social media sentiment.

Shared state object that all three platform coroutines read/write to:
- Polymarket loop writes current market prices after each round
- Twitter/Reddit loops read prices and inject them into agent prompts
- Twitter/Reddit loops write aggregate sentiment after each round
- Polymarket loop reads sentiment and injects it into trader prompts

Since the three platform loops run concurrently via asyncio.gather()
(single-threaded), no locking is needed. Data is eventually consistent —
which models real-world information lag between markets and social media.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger('rustymirosquid.bridge')


@dataclass
class MarketSnapshot:
    """Current state of all prediction markets."""
    round_num: int = 0
    markets: List[Dict[str, Any]] = field(default_factory=list)
    # Each market: {market_id, question, price_yes, price_no, num_trades, price_delta}

    def to_social_media_prompt(self) -> str:
        """Format market data for injection into Twitter/Reddit agent prompts."""
        if not self.markets:
            return ""

        lines = ["# PREDICTION MARKET PRICES (Polymarket)"]
        lines.append(
            "These are live prices from the prediction market. "
            "You may discuss, agree, or disagree with these prices in your posts."
        )
        lines.append("")

        for m in self.markets:
            price_yes = m.get("price_yes", 0.5)
            question = m.get("question", "")
            num_trades = m.get("num_trades", 0)
            delta = m.get("price_delta", 0)

            pct = f"{price_yes * 100:.0f}%"
            lines.append(f"  \"{question}\" → {pct} YES")

            details = []
            if num_trades > 0:
                details.append(f"{num_trades} trades")
            if abs(delta) > 0.01:
                direction = "↑" if delta > 0 else "↓"
                details.append(f"{direction}{abs(delta)*100:.1f}% this round")
            if details:
                lines.append(f"    ({', '.join(details)})")

        lines.append("")
        lines.append(
            "Consider: Do you think the market is overpricing or underpricing this? "
            "What information might the market be missing?"
        )
        return "\n".join(lines)


@dataclass
class SentimentSnapshot:
    """Aggregate social media sentiment about market topics."""
    round_num: int = 0
    platform: str = ""
    topic_sentiments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # topic -> {positive_pct, negative_pct, neutral_pct, top_argument, post_count}
    viral_posts: List[Dict[str, Any]] = field(default_factory=list)

    def to_trading_prompt(self) -> str:
        """Format sentiment data for injection into Polymarket agent prompts."""
        if not self.topic_sentiments and not self.viral_posts:
            return ""

        lines = ["# SOCIAL MEDIA SENTIMENT"]
        lines.append(
            "This is what people on Twitter and Reddit are saying about the markets. "
            "Social media sentiment can signal information the market hasn't priced in yet, "
            "but it can also be noise. Use your judgment."
        )
        lines.append("")

        for topic, data in self.topic_sentiments.items():
            pos = data.get("positive_pct", 0)
            neg = data.get("negative_pct", 0)
            count = data.get("post_count", 0)
            top_arg = data.get("top_argument", "")

            if count == 0:
                continue

            # Determine dominant sentiment
            if pos > neg + 15:
                mood = "strongly bullish"
            elif pos > neg:
                mood = "leaning bullish"
            elif neg > pos + 15:
                mood = "strongly bearish"
            elif neg > pos:
                mood = "leaning bearish"
            else:
                mood = "divided"

            lines.append(f"  On \"{topic}\": {mood} ({count} posts)")
            lines.append(f"    Positive: {pos:.0f}% | Negative: {neg:.0f}% | Neutral: {100-pos-neg:.0f}%")
            if top_arg:
                lines.append(f"    Key argument: \"{top_arg[:150]}\"")
            lines.append("")

        posts = self.viral_posts
        if posts:
            lines.append("  Most discussed posts:")
            # Use a loop instead of slice to satisfy strict type checkers
            count = 0
            for vp in posts:
                if count >= 3:
                    break
                content = vp.get("content", "")[:120]
                likes = vp.get("num_likes", 0)
                lines.append(f"    - \"{content}\" ({likes} likes)")
                count += 1
            lines.append("")

        return "\n".join(lines)


@dataclass
class TriggerSnapshot:
    """News triggers, market color, and SMC signals from TriggerService."""
    round_num: int = 0
    market_color: str = "Neutral"
    sentiment_score: float = 0.0
    rss_headlines: List[str] = field(default_factory=list)
    smc_signals: Dict[str, List[str]] = field(default_factory=dict)
    price_data: Dict[str, float] = field(default_factory=dict)

    def to_agent_prompt(self) -> str:
        """Format trigger data for injection into agent prompts with MTF clarity."""
        lines = ["# INSTITUTIONAL MARKET CONTEXT & TRIGGERS"]
        lines.append(f"Global Sentiment Index: **{self.sentiment_score:+.2f}**")
        lines.append(f"OVTLYR Market Color: **{self.market_color}**")
        lines.append("---")

        if self.smc_signals:
            lines.append("## SMC MULTI-TIMEFRAME (MTF) SIGNALS")
            for symbol, signals in self.smc_signals.items():
                if signals:
                    htf = [s for s in signals if "HTF_BIAS" in s]
                    ltf = [s for s in signals if "LTF_" in s]
                    
                    sig_str = ""
                    if htf: sig_str += f"[TREND: {', '.join(htf)}] "
                    if ltf: sig_str += f"[ENTRIES: {', '.join(ltf)}]"
                    
                    lines.append(f" - **{symbol}**: {sig_str}")
            lines.append("")

        if self.rss_headlines:
            lines.append("## MACRO NEWS HEADLINES")
            for h in self.rss_headlines[:5]:
                lines.append(f" - {h}")
            lines.append("")

        if self.price_data:
            lines.append("## CURRENT MARKET PRICES")
            for symbol, price in self.price_data.items():
                lines.append(f" - {symbol}: ${price:.2f}")

        lines.append("\n**STRATEGY NOTE**: For a high-probability institutional setup, ensure confluences:")
        lines.append("1. **Trend Bias** (HTF_BIAS matches trade direction)")
        lines.append("2. **Liquidity Sweep** (LTF_SWEEP at opposing level)")
        lines.append("3. **Structure Shift** (LTF_MSS in trade direction)")
        
        return "\n".join(lines)


class MarketMediaBridge:
    """Shared state enabling feedback between prediction markets and social media.

    Usage:
        bridge = MarketMediaBridge()

        # In Polymarket loop, after each round:
        bridge.update_prices(polymarket_db_path, round_num)

        # In Twitter/Reddit loop, before agent actions:
        prompt = bridge.get_market_prompt()
        inject_market_context(agent, prompt)

        # In Twitter/Reddit loop, after each round:
        bridge.update_sentiment(belief_states, actual_actions, round_num, "twitter")

        # In Polymarket loop, before agent actions:
        prompt = bridge.get_sentiment_prompt()
        inject_sentiment_context(agent, prompt)
    """

    def __init__(self):
        self.latest_prices: Optional[MarketSnapshot] = None
        self.latest_sentiment: Optional[SentimentSnapshot] = None
        self.latest_triggers: Optional[TriggerSnapshot] = None
        self._price_history: List[MarketSnapshot] = []

    # ── Polymarket → Social Media ──────────────────────────────

    def update_prices(self, polymarket_db_path: str, round_num: int):
        """Called by the Polymarket loop after each round to publish current prices."""
        try:
            conn = sqlite3.connect(polymarket_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT market_id, question, reserve_a, reserve_b, resolved "
                "FROM market WHERE resolved = 0"
            )
            markets = []
            for row in cursor.fetchall():
                ra = row["reserve_a"]
                rb = row["reserve_b"]
                total = ra + rb
                price_yes = rb / total if total > 0 else 0.5

                # Count trades
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM trade WHERE market_id = ?",
                    (row["market_id"],),
                )
                num_trades = cursor.fetchone()["cnt"]

                # Compute price delta from last snapshot
                prev_price = 0.5
                prices = self.latest_prices
                if prices is not None:
                    for pm in prices.markets:
                        if pm.get("market_id") == row["market_id"]:
                            prev_price = pm.get("price_yes", 0.5)
                            break

                markets.append({
                    "market_id": row["market_id"],
                    "question": row["question"],
                    "price_yes": price_yes,
                    "price_no": 1 - price_yes,
                    "num_trades": num_trades,
                    "price_delta": price_yes - prev_price,
                })

            conn.close()

            snapshot = MarketSnapshot(round_num=round_num, markets=markets)
            self._price_history.append(snapshot)
            self.latest_prices = snapshot

        except Exception as e:
            pass  # Non-critical — simulation continues without price broadcast

    def get_market_prompt(self) -> str:
        """Called by Twitter/Reddit loops to get current market prices for agent injection."""
        prices = self.latest_prices
        if prices is None or not hasattr(prices, 'to_social_media_prompt'):
            return ""
        return prices.to_social_media_prompt()

    # ── Social Media → Polymarket ──────────────────────────────

    def update_sentiment(
        self,
        belief_states: Dict[int, Any],
        actual_actions: List[Dict[str, Any]],
        round_num: int,
        platform: str,
    ):
        """Called by Twitter/Reddit loops after each round to publish sentiment."""
        topic_sentiments = {}

        # Aggregate belief positions across all agents
        if belief_states:
            topic_counts: Dict[str, List[float]] = {}
            for bs in belief_states.values():
                if hasattr(bs, 'positions'):
                    for topic, pos in bs.positions.items():
                        topic_counts.setdefault(topic, []).append(pos)

            for topic, positions in topic_counts.items():
                if not positions:
                    continue
                positive = sum(1 for p in positions if p > 0.2)
                negative = sum(1 for p in positions if p < -0.2)
                neutral = len(positions) - positive - negative
                total = len(positions)

                topic_sentiments[topic] = {
                    "positive_pct": (positive / total) * 100,
                    "negative_pct": (negative / total) * 100,
                    "neutral_pct": (neutral / total) * 100,
                    "post_count": total,
                    "top_argument": "",
                }

        # Extract top argument from actual actions (most-liked post content)
        if actual_actions:
            posts = [
                a for a in actual_actions
                if a.get("action_type") in ("CREATE_POST", "CREATE_COMMENT")
                and a.get("action_args", {}).get("content")
            ]
            if posts:
                # Use the first post as representative (actions are already recent)
                top_content = posts[0]["action_args"]["content"]
                # Assign to first matching topic
                for topic in topic_sentiments:
                    if not topic_sentiments[topic]["top_argument"]:
                        topic_sentiments[topic]["top_argument"] = top_content
                        break

        # Find viral posts from actions
        viral_posts_list = []
        for a in (actual_actions or []):
            if a.get("action_type") == "CREATE_POST":
                viral_posts_list.append({
                    "content": a.get("action_args", {}).get("content", ""),
                    "num_likes": 0,  # We don't have likes yet for this round's posts
                    "agent_name": a.get("agent_name", ""),
                })

        # Cap viral posts (explicitly loop to satisfy strict type checkers)
        limited_viral = []
        for vp in viral_posts_list:
            if len(limited_viral) >= 5:
                break
            limited_viral.append(vp)

        self.latest_sentiment = SentimentSnapshot(
            round_num=round_num,
            platform=platform,
            topic_sentiments=topic_sentiments,
            viral_posts=limited_viral,
        )

    def get_sentiment_prompt(self) -> str:
        """Called by Polymarket loop to get social media sentiment for trader injection."""
        sentiment = self.latest_sentiment
        if sentiment is None:
            return ""
        return sentiment.to_trading_prompt()

    def update_triggers(self, trigger_data: Dict[str, Any], round_num: int):
        """Update the bridge with real-world market color and news triggers."""
        self.latest_triggers = TriggerSnapshot(
            round_num=round_num,
            market_color=trigger_data.get("market_color", "Neutral"),
            sentiment_score=trigger_data.get("sentiment_score", 0.0),
            rss_headlines=trigger_data.get("headlines", []),
            smc_signals=trigger_data.get("smc_signals", {}),
            price_data=trigger_data.get("prices", {})
        )

    def get_trigger_prompt(self) -> str:
        """Get the formatted market color and triggers prompt."""
        triggers = self.latest_triggers
        if triggers is None:
            return ""
        return triggers.to_agent_prompt()


# ── Injection helpers (same pattern as cross_platform_digest) ──

_MARKET_MARKER = "\n\n# PREDICTION MARKET PRICES"
_SENTIMENT_MARKER = "\n\n# SOCIAL MEDIA SENTIMENT"


def inject_market_context(agent, market_text: str):
    """Inject market prices into a social media agent's system message."""
    if not market_text:
        return
    content = agent.system_message.content
    marker_pos = content.find(_MARKET_MARKER)
    if marker_pos != -1:
        next_marker = content.find("\n\n# ", marker_pos + len(_MARKET_MARKER))
        if next_marker != -1:
            content = content[:marker_pos] + content[next_marker:]
        else:
            content = content[:marker_pos]
    agent.system_message.content = content + "\n\n" + market_text


def inject_sentiment_context(agent, sentiment_text: str):
    """Inject social media sentiment into a Polymarket agent's system message."""
    if not sentiment_text:
        return
    content = agent.system_message.content
    marker_pos = content.find(_SENTIMENT_MARKER)
    if marker_pos != -1:
        next_marker = content.find("\n\n# ", marker_pos + len(_SENTIMENT_MARKER))
        if next_marker != -1:
            content = content[:marker_pos] + content[next_marker:]
        else:
            content = content[:marker_pos]
    agent.system_message.content = content + "\n\n" + sentiment_text


_TRIGGER_MARKER = "\n\n# GLOBAL MARKET COLOR & TRIGGERS"


def inject_trigger_context(agent, trigger_text: str):
    """Inject real-world market color and triggers into an agent's system message."""
    if not trigger_text:
        return
    content = agent.system_message.content
    marker_pos = content.find(_TRIGGER_MARKER)
    if marker_pos != -1:
        next_marker = content.find("\n\n# ", marker_pos + len(_TRIGGER_MARKER))
        if next_marker != -1:
            content = content[:marker_pos] + content[next_marker:]
        else:
            content = content[:marker_pos]
    agent.system_message.content = content + "\n\n" + trigger_text


_PORTFOLIO_MARKER = "\n\n# PERSONAL PORTFOLIO STATUS"


def inject_portfolio_context(agent, portfolio_text: str):
    """Inject personal portfolio state into a TradingAgent's system message."""
    if not portfolio_text:
        return
    content = agent.system_message.content
    marker_pos = content.find(_PORTFOLIO_MARKER)
    if marker_pos != -1:
        next_marker = content.find("\n\n# ", marker_pos + len(_PORTFOLIO_MARKER))
        if next_marker != -1:
            content = content[:marker_pos] + content[next_marker:]
        else:
            content = content[:marker_pos]
    agent.system_message.content = content + "\n\n" + portfolio_text
