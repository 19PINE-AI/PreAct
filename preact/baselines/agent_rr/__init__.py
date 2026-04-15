"""AgentRR baseline — multi-level experience replay.

AgentRR (Feng et al., 2025) introduces a Record-Summary-Replay framework
with multi-level experiences and check functions as trust anchors.

Key differences from PreAct:
1. Produces natural-language experiences, not formal state machines
2. Low-level experiences are descriptions, not XPath-verified executables
3. No quantitative benchmarks provided in the original paper
"""

from preact.baselines.agent_rr.system import AgentRRBaseline

__all__ = ["AgentRRBaseline"]
