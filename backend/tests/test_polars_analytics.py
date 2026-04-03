import pytest
import polars as pl
from app.services.polars_analytics import SimulationAnalytics

def test_compute_aggregate_sentiment():
    analytics = SimulationAnalytics()
    # Mock data [round, agent_id, topic, stance, confidence]
    df = pl.LazyFrame({
        "round": [1, 1, 2, 2],
        "agent_id": [101, 102, 101, 102],
        "topic": ["crypto", "crypto", "crypto", "crypto"],
        "stance": [0.5, 0.5, 0.8, -0.2],
        "confidence": [0.8, 0.6, 0.9, 0.5]
    })
    
    res = analytics.compute_aggregate_sentiment(df, group_by="round")
    assert len(res) == 2
    
    r1 = res.filter(pl.col("round") == 1).to_dicts()[0]
    assert r1["mean_sentiment"] == 0.5
    assert r1["mean_confidence"] == 0.7
    
    r2 = res.filter(pl.col("round") == 2).to_dicts()[0]
    assert pytest.approx(r2["mean_sentiment"]) == 0.3
