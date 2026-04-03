"""
Belief system integration helpers for simulation scripts.

Provides functions that the simulation scripts (run_reddit, run_parallel)
call to initialize, update, and inject belief state. Keeps the belief
logic in one place instead of duplicating across scripts.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from wonderwall.social_agent.belief_state import (
    BeliefState,
    extract_topics_from_requirement,
    inject_belief_context,
)
from wonderwall.social_agent.round_analyzer import (
    RoundAnalyzer,
    SimulationTrajectory,
    update_trust_from_actions,
)


class BeliefTracker:
    """Manages belief tracking for a single platform's simulation.

    Thread-safe (No-GIL): protège belief_states et trajectory via RLock.
    RLock car after_round() appelle des sous-méthodes qui lisent belief_states.
    """

    def __init__(self, config: Dict[str, Any], simulation_dir: str, platform: str):
        self._lock = threading.RLock()  # No-GIL thread safety
        simulation_req = config.get("simulation_requirement", "")
        self.topics = extract_topics_from_requirement(simulation_req)
        self.platform = platform
        self.simulation_dir = simulation_dir

        self.belief_states: Dict[int, BeliefState] = {}
        self.round_analyzer = RoundAnalyzer(self.topics)
        self.trajectory = SimulationTrajectory()
        self.trajectory.topics = self.topics

        # Initialize per-agent beliefs from config
        agent_configs = config.get("agent_configs", [])
        for cfg in agent_configs:
            agent_id = cfg.get("agent_id", 0)
            self.belief_states[agent_id] = BeliefState.from_profile(cfg, self.topics)

    def after_round(
        self,
        db_path: str,
        env,
        active_agents: List[Tuple[int, Any]],
        round_num: int,
        actual_actions: Optional[List[Dict[str, Any]]] = None,
    ):
        """Call after env.step() each round to update beliefs and inject context.

        Thread-safe: acquiert self._lock pour protéger belief_states et trajectory.

        Args:
            db_path: Path to the platform's SQLite database.
            env: The OasisEnv instance.
            active_agents: List of (agent_id, agent) tuples.
            round_num: Current round number.
            actual_actions: If available, the list of action dicts from this round
                (used for trust updates).
        """
        with self._lock:
            active_ids = [aid for aid, _ in active_agents]

            # Update trust from explicit actions (like/dislike/follow)
            if actual_actions:
                update_trust_from_actions(self.belief_states, actual_actions)

            # Analyze round and update beliefs
            snapshot = self.round_analyzer.analyze_round(
                db_path=db_path,
                belief_states=self.belief_states,
                active_agent_ids=active_ids,
                round_num=round_num,
                actual_actions=actual_actions,
            )
            self.trajectory.add_snapshot(snapshot)

            # Inject updated beliefs into each active agent's system message
            for agent_id, agent in active_agents:
                bs = self.belief_states.get(agent_id)
                if not bs:
                    continue
                belief_text = bs.to_prompt_text()
                feedback = self.round_analyzer.generate_agent_feedback(
                    snapshot, agent_id, bs
                )
                combined = belief_text
                if feedback:
                    combined += "\n\n" + feedback
                if combined.strip():
                    inject_belief_context(agent, combined)

    def save_trajectory(self):
        """Save trajectory.json for the report agent. Thread-safe."""
        with self._lock:
            path = os.path.join(self.simulation_dir, "trajectory.json")
            self.trajectory.save(path)
            return path

    def get_summary(self) -> str:
        """Return a short summary of belief dynamics. Thread-safe."""
        with self._lock:
            convergence = self.trajectory._compute_convergence()
            turning = self.trajectory._find_turning_points()
            lines = [f"Belief tracking: {len(self.topics)} topics, {len(self.belief_states)} agents"]
            for topic, conv in convergence.items():
                if conv > 0.1:
                    lines.append(f"  {topic}: opinions CONVERGED by {conv:.2f}")
                elif conv < -0.1:
                    lines.append(f"  {topic}: opinions POLARIZED by {abs(conv):.2f}")
                else:
                    lines.append(f"  {topic}: opinions stayed roughly stable")
            if turning:
                lines.append(f"  {len(turning)} significant belief shifts detected")
            return "\n".join(lines)
