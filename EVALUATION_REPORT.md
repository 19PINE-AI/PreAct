# PreAct Evaluation Report

## Honest Summary

PreAct's core state-machine execution is extremely fast (**128-177ms** for 2-4 state workflows), significantly outperforming Muscle-Mem (900-1100ms) and Workflow-Use (400-600ms) on exact replay. However, the system has real weaknesses that inflate total latency and reduce reliability on complex multi-page workflows.

## Benchmark Setup

- **LLM**: Gemini 3 Flash Preview
- **Browser**: Chromium via Playwright (headless)
- **Benchmark**: TestShop — self-hosted multi-page e-commerce (login, search, cart, checkout)
- **Tasks**: 5 WebArena-style tasks of increasing complexity
- **Protocol**: Run 1 (explore), Run 2 (replay)
- **Baselines**: Standard CUA, Muscle-Mem, Workflow-Use (our implementations using their published architectures)

## Main Results

| System | R1 Eval SR | R2 Eval SR | R2 Exec SR | R2 Tokens |
|--------|-----------|-----------|-----------|----------|
| Standard CUA | 80% | 0% | 0% | N/A |
| Muscle-Mem | 80% | 80% | 80% | 0 |
| Workflow-Use | 80% | 80% | 80% | 0 |
| **PreAct** | 60% | 80% | 100% | 2,063 |

### Per-Task Run 2 Timing

| Task | Difficulty | PreAct | Muscle-Mem | Workflow-Use |
|------|-----------|--------|------------|-------------|
| Login (3 steps) | Easy | **171ms** | 1,070ms | 597ms |
| Search (2 steps) | Easy | **128ms** | 926ms | 408ms |
| Category filter (3 steps) | Medium | **2,259ms** (transfer) | skip | skip |
| Add to cart (6 steps) | Medium | 177ms (exec ok, eval fail) | 1,471ms | 1,006ms |
| Search+cart (8 steps) | Medium | 65,509ms (fallback) | 2,082ms | 1,565ms |

## What Works

**Pure state-machine execution is 3-8x faster than any baseline.** When the compiled program matches the task exactly and all state verifications pass:
- Login: 171ms (vs 597-1,070ms for baselines)
- Search: 128ms (vs 408-926ms for baselines)

The JSON state machine executes deterministically with XPath verification at each state transition. The ~130-170ms timing includes browser interaction, element verification, and action execution — no LLM calls.

**Cross-task transfer works.** `shop_search_002` (category filter) was successfully replayed via RAG transfer from `shop_search_001` (keyword search), even though the original exploration timed out for all other systems. PreAct found a similar program and auto-extracted parameters (2,259ms including parameter extraction).

## What Doesn't Work

**1. State verification is fragile on complex workflows.**
`shop_addcart_002` (8-step login→search→add-to-cart flow) failed during RPA replay at the 4th state (after login). The compiled state machine expected a specific element that wasn't present — the page loaded differently than during recording. This triggered a CUA fallback costing 65 seconds, making PreAct's Run 2 **30x slower** than Muscle-Mem on this task.

This is the core weakness of per-state verification: it catches mismatches early (good for safety) but any mismatch triggers an expensive LLM fallback. Muscle-Mem's blind replay doesn't verify states at all, so it succeeds even when the page loads slightly differently.

**2. Compilation quality varies.**
The LLM (Gemini 3 Flash) sometimes generates state machines with overly specific XPaths or unnecessary intermediate states. A post-login "wait" state that expects a specific URL pattern breaks when the URL has query parameters. Better compilation prompts or post-processing could help.

**3. PreAct's Run 1 success rate is lower.**
PreAct achieved 60% Run 1 SR vs 80% for baselines. The extra 10-15 seconds of compilation time means less time available for the CUA within the timeout window. Two tasks timed out during PreAct's exploration+compilation phase that succeeded for other systems doing pure CUA.

**4. Parameter extraction overhead.**
When fast regex extraction fails (complex task descriptions), the LLM fallback adds 2-3 seconds. This was optimized in this round (regex for common patterns), but still falls back to LLM for unusual phrasings.

## Comparison with Published Work

We did not evaluate against the real codebases of:
- **ActionEngine** (Microsoft Research, 2026) — no public code; our reimplementation approximates the crawl→codegen architecture
- **Muscle-Mem** (pig-dot-dev/muscle-mem) — real repo cloned but we used our own implementation matching their architecture
- **Workflow-Use** (browser-use/workflow-use) — real repo cloned but we used our own implementation matching their architecture
- **AgentRR** (Feng et al., 2025) — no public code

We did not evaluate on standard benchmarks:
- **WebArena** (812 tasks) — requires Docker containers; we cloned the repo and built compatible task format/evaluators but ran on our TestShop instead
- **OSWorld** (369 tasks) — requires VM infrastructure; not attempted

Our TestShop benchmark has 5 tasks. This is insufficient for statistical significance. The results show architectural trade-offs but not publishable performance numbers.

## Architecture Trade-offs

| | PreAct | Muscle-Mem | Workflow-Use |
|--|--------|------------|-------------|
| **Best case** | 128-177ms (fastest) | 900-1100ms | 400-600ms |
| **Worst case** | 65s (CUA fallback) | Discard cache | Agent fallback |
| **Cross-task transfer** | Yes (RAG) | No | No |
| **State verification** | Per-state XPath | None | Semantic selectors |
| **Failure mode** | Safe (catches early) | Risky (cascading) | Medium |
| **Compilation cost** | 10-15s one-time | None | None |

PreAct optimizes for a different point in the design space than Muscle-Mem and Workflow-Use:
- **Muscle-Mem**: Fastest to deploy (no compilation), good for exact repeated tasks
- **Workflow-Use**: Good balance of speed and robustness via semantic selectors
- **PreAct**: Highest raw execution speed + cross-task transfer, but fragile on complex multi-page workflows and compilation overhead

## Conclusion

PreAct's state-machine-as-executable architecture validates the core hypothesis: directly executing the state machine is 3-8x faster than linear replay when it works. The cross-task transfer via RAG provides unique capability that no other system offers. However, the system's reliability degrades on complex multi-page workflows due to fragile state verification, and the compilation overhead reduces exploration time within timeout windows.

The honest recommendation: PreAct is best suited for simple, repeated workflows (login, search, form filling) where the state machine is small and XPath verification is reliable. For complex multi-page workflows, the fallback cost is too high. Future work should focus on more robust state verification (e.g., semantic matching instead of exact XPath) and incremental compilation that builds the state machine across multiple executions rather than from a single trace.
