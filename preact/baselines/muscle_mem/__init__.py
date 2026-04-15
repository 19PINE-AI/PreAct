"""Muscle-Mem baseline — linear tool-call replay with agent fallback.

Muscle-Mem (Dunteman, 2025) caches linear tool-call sequences and replays
them deterministically, falling back to full agent mode on any failure.

Key differences from PreAct:
1. Records linear sequences, not state transition graphs
2. Replays blindly without per-step state verification
3. No incremental refinement — discards cache entirely on failure
"""

from preact.baselines.muscle_mem.system import MuscleMemBaseline

__all__ = ["MuscleMemBaseline"]
