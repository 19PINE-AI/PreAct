# PreAct Cross-Platform Evaluation Results

**Date**: 2026-04-16  
**LLM Backend**: Claude Sonnet 4.6 (Anthropic API)  
**Architecture**: CUA-compile-store-replay pipeline

## Executive Summary

PreAct was evaluated across three benchmarks spanning web, mobile, and desktop environments. Performance varies dramatically by platform complexity:

| Benchmark | Tasks | Success Rate | Best Metric | RPA Replay Rate |
|-----------|-------|-------------|-------------|-----------------|
| **WebArena** | 31 | 41.9% CUA / 29.0% replay | 58.1% exec, 5.3x token savings | ~45% of tasks |
| **AndroidWorld** | 30 | 33.3% (43.3% ground-truth) | 100% on simple tasks | 0% (RAG issues) |
| **OSWorld** | 36 | **0%** | N/A | 0% (all CUA failed) |

**Key Finding**: PreAct's compile-and-replay pipeline works when the base CUA agent can complete tasks. On WebArena (web), CUA succeeds 42% of the time, and compiled programs achieve 58% execution accuracy with 5.3x token savings. On AndroidWorld (mobile), CUA succeeds on simple linear tasks. On OSWorld (desktop), CUA cannot complete any task — so there are no successful trajectories to compile.

---

## 1. WebArena (Web Navigation)

**Environment**: Magento admin panel (shopping_admin), 31 easy/medium tasks  
**Max Steps**: 15 per task

### Results

| System | Eval SR | Exec SR | Avg Time | Avg Tokens |
|--------|---------|---------|----------|------------|
| Standard CUA | 41.9% | 61.3% | 54.7s | 55,010 |
| PreAct R1 (compile) | 41.9% | 61.3% | 64.7s | 57,813 |
| PreAct R2 (replay) | 29.0% | 58.1% | 42.3s | 10,958 |

### Analysis
- **Token efficiency**: 5.3x reduction in R2, pure RPA replays use ~116 tokens (50-100x speedup)
- **Eval gap (R1 41.9% → R2 29.0%)**: Compiled programs navigate correctly but `inspect_text` extracts wrong answers from wrong table views
- **Exec gap (R1 61.3% ��� R2 58.1%)**: Small — navigation compilation is reliable
- **Bottleneck**: Answer extraction, not navigation. Search/lookup tasks execute correctly but return wrong data

### What Works
- Web page navigation and form interaction compile reliably into RPA programs
- State verification via XPath selectors works for web DOM elements
- Structured web pages provide clear, deterministic targets for automation

### What Doesn't
- Data extraction from dynamic table views (different sort orders, pagination states)
- Tasks requiring semantic understanding of page content (not just navigation)

---

## 2. AndroidWorld (Mobile)

**Environment**: Android emulator in Docker, 15 task types x 2 instances = 30 tasks  
**Max Steps**: 15 per task

### Results

| Metric | Value |
|--------|-------|
| Self-reported success | 10/30 = 33.3% |
| Ground-truth score=1.0 | 13/30 = 43.3% |
| Avg tokens | 33,056 |
| Avg time | 42.8s |
| RPA replay attempts | 0% (all tasks ran in CUA mode) |

### Per-Task Success (Ground-Truth)

| Task Category | Success | Rate | Notes |
|--------------|---------|------|-------|
| ContactsAddContact | 2/2 | 100% | Simple linear workflow |
| ContactsNewContactDraft | 2/2 | 100% | Simple linear workflow |
| ClockStopWatchRunning | 2/2 | 100% | Single toggle action |
| BluetoothOn/Off | 4/4 | 100% | Simple settings toggle |
| MarkorCreateFolder | 2/2 | 100% | Simple create action |
| MarkorCreateNote | 1/2 | 50% | Multi-step, sometimes times out |
| ClockTimerEntry | 0/2 | 0% | Complex digit-by-digit input |
| MarkorDeleteNote | 0/2 | 0% | Long-press + context menu |
| MarkorEditNote | 0/2 | 0% | Multi-step edit workflow |
| CalendarAddEvent | 0/2 | 0% | Complex form with date/time pickers |
| SmsSend/Reply | 0/4 | 0% | Emulator lacks telephony |
| NotesIsTodo | 0/2 | 0% | "answer" action not recognized as terminal |
| FilesDeleteFile | 0/2 | 0% | File manager navigation failure |

### Analysis
- **Simple tasks succeed reliably**: Add contact, toggle setting, create folder — all 100%
- **Complex interactions fail**: Timer digit entry, note editing, calendar events — all 0%
- **RAG never helped**: All tasks ran CUA (no successful RPA replays) — RAG matching produced false positives (ContactsAddContact program matched Calendar/Markor tasks)
- **Patched server is critical**: Without the custom `/state` endpoint (base64 PNG + UI elements), CUA gets 0% success

### What Works
- Simple linear mobile workflows with clear UI targets
- CUA performs well when the task is a straight sequence of taps

### What Doesn't
- Complex UI interactions (long-press, swipe, digit pickers)
- Multi-app workflows
- Tasks requiring emulator features (telephony)
- RAG program matching (0% RPA utilization despite stored programs)

---

## 3. OSWorld (Desktop)

**Environment**: Ubuntu 22.04 VM in Docker, 36 scored tasks across 10 application domains (3 skipped due to eval errors)  
**Max Steps**: 15 per task

### Results

| Metric | Value |
|--------|-------|
| Success rate | **0/36 = 0%** |
| CUA tasks | 30/36 (83%) |
| RPA false positives | 6/36 (17%) |
| Stuck-clicking rate | ~22/30 CUA tasks (73%) |
| Avg tokens | 35,916 |
| Avg time | 46.0s per task |

### Per-Domain Breakdown (All 0% Success)

| Domain | Tasks | Mode | Stuck |
|--------|-------|------|-------|
| chrome | 4 | all CUA | 4/4 |
| gimp | 2 | all CUA | 2/2 |
| libreoffice_calc | 3 | all CUA | 1/3 |
| libreoffice_impress | 2 | 1 CUA + 1 FP | 1/1 |
| libreoffice_writer | 2 | all CUA | 2/2 |
| multi_apps | 14 | 9 CUA + 5 FP | ~7/9 |
| os | 2 | all CUA | 2/2 |
| thunderbird | 2 | all CUA | 2/2 |
| vlc | 2 | all CUA | 2/2 |
| vs_code | 3 | all CUA | 2/3 |

### Failure Analysis

**Dominant failure: CUA stuck-clicking (67% of CUA tasks)**
The LLM repeatedly sends identical `pyautogui.click(x, y)` coordinates. The auto-recovery mechanism (scroll, escape, Alt+Left after 4 identical actions) triggers but doesn't change screen state enough to break the loop.

**RAG false positives (15% of all tasks)**
6 tasks matched program `862006d6` ("Enter a list of names/items into a text editor and save the file") via word-overlap text matching. The program executes its 2-3 states, reaches terminal state, reports `cov=100%` but scores 0.0 because the program is completely irrelevant to the actual task.

**SOTA comparison:**
- UI-TARS-2: 47.5% on OSWorld-Verified
- OpenCUA-72B: 45.0% on OSWorld-Verified
- PreAct (Claude Sonnet CUA): 0%

### Root Causes
1. Desktop GUI screenshots are harder to parse than web/mobile — more visual complexity, smaller targets, deeper menus
2. Accessibility tree truncation (3000 chars) misses critical elements
3. No structured DOM equivalent — CUA relies entirely on visual + limited a11y
4. Specialized vision models (UI-TARS, OpenCUA) trained specifically for desktop UI interaction outperform generic LLM CUA by a wide margin

---

## Cross-Platform Analysis

### Platform Difficulty Gradient
```
Web (WebArena) > Mobile (AndroidWorld) > Desktop (OSWorld)
   42% CUA           33-43% CUA             0% CUA
```

### Why the Gradient?
1. **Web**: Structured DOM, clean layouts, standardized UI patterns, XPath verification works
2. **Mobile**: Simpler visual layouts than desktop, but touch interactions (swipe, long-press) are harder than clicks; UI element data helps significantly
3. **Desktop**: Most complex visual layouts, smallest click targets, deepest menu hierarchies, no structured DOM, complex multi-window interactions

### PreAct Pipeline Assessment

| Component | WebArena | AndroidWorld | OSWorld |
|-----------|----------|-------------|---------|
| CUA agent | Works (42%) | Works for simple (43%) | Broken (0%) |
| Trajectory recording | Works | Works | Records failures |
| LLM compilation | Works | Works | Compiles failures |
| RAG storage | Works | Works | Works (but accumulates bad programs) |
| RAG retrieval | Works | False positives | False positives |
| RPA execution | Works (58% exec) | Not tested | N/A |
| Answer extraction | Bottleneck | N/A | N/A |

### Key Insights

1. **PreAct amplifies CUA quality**: When CUA works, PreAct provides reliable 5x token savings. When CUA fails, PreAct has nothing to work with.

2. **RAG text matching needs improvement**: The word-overlap algorithm with 0.4 threshold produces false positives on all platforms. Stop-word filtering and higher thresholds are needed.

3. **Platform-specific CUA models matter**: Generic Claude Sonnet CUA works for web (42%) and simple mobile (43%) but fails completely on desktop (0%). SOTA desktop agents use specialized vision models.

4. **Compilation is not the bottleneck**: The LLM compiler reliably converts successful trajectories into executable state machines. The problem is generating successful trajectories in the first place.

5. **Answer extraction is the web bottleneck**: On WebArena, programs navigate correctly (58% exec) but extract wrong answers (29% eval). This is a compiler prompt issue, not a fundamental limitation.

---

## Recommendations

### Short-term (improve existing benchmarks)
1. Fix RAG text matching: add stop-word filtering, raise threshold to 0.6+
2. Fix answer extraction prompts for WebArena compiled programs
3. Increase max steps for complex tasks (15 is too low for multi-app desktop tasks)
4. Add "answer" action type recognition to AndroidWorld agent
5. Fix separate RAG DB issue (relative persist_dir path)

### Medium-term (architecture improvements)
1. Add semantic validation to RPA terminal state (don't just return success=True)
2. Implement domain-specific RAG matching (check application context before accepting matches)
3. Use embedding-only RAG matching (remove text-overlap fast path)
4. Expand a11y tree size limit for desktop environments

### Long-term (fundamental improvements for OSWorld)
1. Integrate specialized vision models (UI-TARS, OpenCUA) as CUA backend instead of generic LLM
2. Build desktop-specific action primitives (menu navigation, dialog handling, multi-window management)
3. Add screen region analysis to break stuck-clicking loops
4. Consider hybrid approach: specialized vision for desktop screenshot parsing + LLM for task planning
