"""ActionEngine baseline — reimplemented from arxiv 2602.20502.

ActionEngine (Zhong et al., 2026, Microsoft Research) builds state machines
through untargeted app crawling and generates Python scripts from them.

Key differences from PreAct:
1. Untargeted exploration to build graph (wasteful for goal-directed workflows)
2. Generates flat Python scripts from state machine (lossy transformation)
3. Fallback is selector-level re-grounding, not full CUA reasoning
"""

from preact.baselines.action_engine.system import ActionEngineBaseline

__all__ = ["ActionEngineBaseline"]
