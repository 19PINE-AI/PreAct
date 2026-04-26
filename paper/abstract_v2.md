# Updated Abstract Draft (post-validation, 2026-04-26)

The current §1 abstract in `DESIGN.md` predates the empirical-validation push. This draft incorporates the §2.3.2.1 closures (8 of 9 paper-grade gaps) and removes the validation hedge from the original framing. Drop-in replacement for §1.

---

## §1 Abstract (revised)

Current Computer Using Agents (CUAs), often based on the Observation-Reasoning-Action paradigm (e.g., ReAct), exhibit significant latency (4-5 seconds per operation) due to visual token processing and LLM inference. Recent work has explored two directions to address this: (1) saving agent behaviors as *skills* that still require LLM invocation at execution time (CUA-Skill, Memento-Skills, SAGE), and (2) *compiling* agent workflows into deterministic code to eliminate repeated LLM calls (Compiled AI, Agentic Compilation). However, skill-based approaches retain per-execution LLM costs, while compilation approaches either target narrow business-logic functions rather than multi-page GUI workflows (Compiled AI), or lack concrete implementation details for complex interactive tasks (Agentic Compilation). Concurrent systems that record and replay agent trajectories — such as Muscle-Mem, AgentRR, and Workflow-Use — produce linear action sequences or unstructured experiences, lacking formal state verification, conditional branching, and incremental model refinement.

PreAct introduces a fundamentally different approach: it records task-directed CUA trajectories and compiles them into **formal state transition graphs** that serve as both the representation and the directly executable runtime artifact. Unlike ActionEngine (Microsoft Research, 2026), which builds state machines through untargeted app exploration and then generates flat Python scripts from them, PreAct constructs its graphs from goal-directed task execution and executes the state machine directly — enabling lightweight XPath-based state verification, conditional branching within the compiled artifact, and monotonic graph extension on each fallback cycle.

The key contributions are: (1) a **state-machine-as-executable** architecture where the formal state transition graph is simultaneously the compiled artifact and the runtime program — unlike ActionEngine, which generates flat Python scripts from its state machine, PreAct executes the graph directly, enabling lightweight per-state verification and in-place patching; (2) **task-directed trajectory recording** that constructs minimal, goal-focused state graphs from a single successful task execution, rather than requiring untargeted app exploration; (3) **monotonic graph refinement** where each LLM fallback extends the existing state graph with new states and transitions rather than discarding and regenerating the compiled artifact; and (4) a **verify-before-store gate** (`replay.success ∧ score ≥ 1.0`) that filters lossy compiles before they enter the program library — empirically necessary for monotonicity, as a 2×2 ablation demonstrates that gate-OFF produces a one-task warm regression driven by stored programs that replay at 100% coverage but fail the live evaluator.

We validate these claims through controlled AB experiments on AndroidWorld (15-task official subset, n=3 multi-seed cold→warm pairs with rag_db reset per seed), with cross-model replication confirming SOTA-parity is not LLM-specific (73.3% mean for both Gemini 3 Flash and Claude Sonnet 4.6 on the same subset, with an identical stable failure set across both backends and three seeds). Ablation experiments isolate the source of Pre-Act's success-rate value: the harness (RAG retrieval + verify-gate + agentic selector + hybrid replay) is empirically load-bearing, while runtime add-ons (prompt-level Pre-Act guidance, code-level guardrails, dynamic step-budget cap) are aggregate-neutral. Across the full evaluation, eight of nine §2.3.2 validity threats are explicitly closed; the ninth (platform-coverage generalizability) is acknowledged as out-of-scope for this work.

---

## Notes for paper integration

1. **Dropped from original abstract**: "achieves up to 10x acceleration over standard CUA loops" — kept implicitly via the WebArena 6.9× / OSWorld results. Not a load-bearing claim; the verify-gate validation is more central.

2. **Added**: explicit verify-gate claim with the AB result + smoking-gun mechanism. This is the strongest empirical contribution post-validation.

3. **Added**: cross-model replication with Gemini and Claude. This was a §2.3.2 gap that's now closed and worth highlighting.

4. **Tone**: removed the original "validate these claims through comprehensive evaluation" promise (forward-looking) in favor of a past-tense statement of completed work.

5. **Length**: 4 paragraphs vs. the original 3. The validation-result paragraph is the new addition.
