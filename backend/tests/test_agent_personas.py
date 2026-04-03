import pytest
from app.models.agent_personas import BeliefState, AgentPersona, EntityType

def test_belief_state_clamping():
    state = BeliefState(positions={"btc": 1.5, "eth": -1.2})
    assert state.positions["btc"] == 1.0 # Clamped to 1.0
    assert state.positions["eth"] == -1.0 # Clamped to -1.0

def test_agent_persona():
    agent = AgentPersona(
        agent_id=1,
        entity_name="Alice",
        entity_type=EntityType.INDIVIDUAL,
        profile_summary="Test profile",
        personality_traits=["bold"],
        risk_tolerance=0.8
    )
    assert agent.agent_id == 1
    assert agent.entity_name == "Alice"
    assert agent.risk_tolerance == 0.8
