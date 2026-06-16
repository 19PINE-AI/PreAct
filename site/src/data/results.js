// Headline results, ablation tables, and figure data for the PreAct site.
// Transcribed verbatim from preact.tex and findings_summary.md.

export const HEADLINES = [
  { value: '8.5–13×', unit: 'cheaper', label: 'replaying a saved program vs. solving the task again', tone: 'pass' },
  { value: '3', unit: 'platforms', label: 'a phone (AndroidWorld), a desktop (OSWorld), a website (WebArena)', tone: 'replay' },
  { value: '55', unit: 'programs', label: 'real saved programs you can browse below', tone: 'replay' },
  { value: '~$30–35', unit: '', label: 'total model cost · ~50h of autonomous runs', tone: 'neutral' },
]

// Figure 1 — cross-platform verify-gate diff-of-deltas (the central figure).
export const GATE_ABLATION = [
  { platform: 'Android', sub: 'n=5 seeds · Gemini 3 Flash', on: 1.2, onErr: 0.45, off: -1.4, offErr: 0.89, diff: 2.6, ppt: '17.3 pp', tasks: 15 },
  { platform: 'OSWorld', sub: 'n=5 reps · Claude Sonnet 4.6', on: 0.2, onErr: 0.45, off: -2.4, offErr: 0.55, diff: 2.6, ppt: '43 pp', tasks: 6 },
  { platform: 'WebArena', sub: 'n=4+4 · Claude Sonnet 4.6', on: -4.0, onErr: 2.94, off: -5.75, offErr: 1.71, diff: 1.75, ppt: '15 pp', tasks: 12 },
]

// Android verify-gate ablation, per-seed (Table 4 in paper).
export const GATE_ANDROID = {
  cols: ['Seed', 'Cold ON', 'Warm ON', 'Δ ON', 'Cold OFF', 'Warm OFF', 'Δ OFF'],
  rows: [
    ['42', 10, 11, '+1', 11, 10, '−1'],
    ['100', 9, 11, '+2', 11, 10, '−1'],
    ['1337', 9, 10, '+1', 10, 9, '−1'],
    ['2024', 11, 12, '+1', 11, 10, '−1'],
    ['7777', 10, 11, '+1', 12, 9, '−3'],
  ],
  mean: ['Mean', '9.8', '11.0', '+1.2 ± .45', '11.0', '9.6', '−1.4 ± .89'],
  note: 'Diff-of-deltas 2.6 tasks. Zero inversions across 10 paired observations; paired sign-test p ≈ 0.031.',
}

export const GATE_OSWORLD = {
  cols: ['Rep', 'Cold ON', 'Warm ON', 'Δ ON', 'Cold OFF', 'Warm OFF', 'Δ OFF'],
  rows: [
    ['1', '5/6', '5/6', '0', '5/6', '2/6', '−3'],
    ['2', '5/6', '5/6', '0', '6/6', '3/6', '−3'],
    ['3', '5/6', '5/6', '0', '5/6', '3/6', '−2'],
    ['4', '5/6', '5/6', '0', '5/6', '3/6', '−2'],
    ['5', '5/6', '6/6', '+1', '5/6', '3/6', '−2'],
  ],
  mean: ['Mean', '5.0', '5.2', '+0.2 ± .45', '5.2', '2.8', '−2.4 ± .55'],
  note: 'Diff-of-deltas 2.6 tasks (43 pp). All five OFF reps regress; all five ON reps non-decreasing.',
}

// Cold→warm monotonicity (Table 1 in paper, n=3 Gemini seeds).
export const MONOTONIC = [
  { seed: '42', cold: 10, warm: 11, delta: '+1', shift: '8 of 13 solved by replay' },
  { seed: '100', cold: 9, warm: 11, delta: '+2', shift: '8 of 11 solved by replay' },
  { seed: '1337', cold: 9, warm: 10, delta: '+1', shift: '5 of 10 solved by replay' },
]

// Head-to-head baselines on WebArena (Table tab:baselines).
export const BASELINES = [
  { sys: 'Muscle-Mem', subtitle: 'blind linear cache', cold: '7.0 ± 1.41', warm: '6.25 ± 0.96', delta: -0.75, note: 'Cache miss → CUA fallback per task', kind: 'baseline' },
  { sys: 'Workflow-Use', subtitle: 'per-task scripts', cold: '7.0 ± 0.82', warm: '0 ± 0', delta: -7.0, note: 'Script replay fails; no verification', kind: 'baseline' },
  { sys: 'PreAct gate-OFF', subtitle: 'verify gate disabled', cold: '5.75 ± 1.71', warm: '0 ± 0', delta: -5.75, note: 'Stores every compile; warm SR collapses', kind: 'preact-off' },
  { sys: 'PreAct gate-ON', subtitle: 'verify gate enabled', cold: '6.0 ± 0.82', warm: '2.0 ± 2.31', delta: -4.0, note: 'Gate rejects ≈83% of compiles; bimodal warm SR', kind: 'preact' },
  { sys: 'PreAct gate-ON + fallback', subtitle: 'cache-miss → CUA', cold: '7.25 ± 1.50', warm: '6.25 ± 0.96', delta: -1.0, note: 'Matches Muscle-Mem (Welch p ≈ 0.84)', kind: 'preact-best' },
]

// Smoking-gun cov=100% / score=0 lossy-replay events (Table 2).
export const SMOKING_GUN = [
  { platform: 'Android', task: 'ContactsAddContact', pid: '80bff413', mech: 'Replay completes; evaluator misses the contact' },
  { platform: 'Android', task: 'MarkorCreateFolder', pid: '(auto)', mech: 'Replay completes; folder not at expected path' },
  { platform: 'OSWorld', task: 'Chrome history clean', pid: '8f0fdfa4', mech: 'Replay completes; browser state mismatches' },
  { platform: 'OSWorld', task: 'LibreOffice Calc formula', pid: '43188217', mech: 'Replay completes; cell formula mismatches' },
  { platform: 'OSWorld', task: 'LibreOffice Calc chart', pid: 'c1f04f87', mech: 'Replay completes; chart properties mismatch' },
]

// Selector backend ablation (Table tab:selector-ablation).
export const SELECTOR_ABLATION = [
  { sel: 'Embedding · MiniLM-L6-v2', tau: '0.40', functional: 100, nopick: '0%', falsepick: 6.7 },
  { sel: 'Embedding · MiniLM-L6-v2', tau: '0.50–0.65', functional: 100, nopick: '0%', falsepick: 0, best: true },
  { sel: 'Embedding · MiniLM-L6-v2', tau: '0.70', functional: 86.7, nopick: '13.3%', falsepick: 0 },
  { sel: 'Embedding · MiniLM-L6-v2', tau: '0.85', functional: 64.4, nopick: '35.6%', falsepick: 0 },
  { sel: 'Embedding · bge-large-en-v1.5', tau: '0.50', functional: 100, nopick: '0%', falsepick: 93.3 },
  { sel: 'Embedding · bge-large-en-v1.5', tau: '0.60', functional: 100, nopick: '0%', falsepick: 20.0 },
  { sel: 'Embedding · bge-large-en-v1.5', tau: '0.65–0.85', functional: 100, nopick: '0%', falsepick: 0, best: true },
  { sel: 'Agentic LLM (default)', tau: '—', functional: 75.6, nopick: '24%', falsepick: 0, agentic: true },
]

// What did NOT change the numbers.
export const NEGATIVE_FINDINGS = [
  {
    title: 'The wording of the prompts',
    verdict: 'No effect',
    detail:
      'In production the agent runs its standard prompt with nothing special added. The 73.3% score on the phone benchmark comes with zero prompt tweaks of our own.',
  },
  {
    title: 'Hand-written runtime guardrails',
    verdict: 'No measurable effect',
    detail:
      'Turning the extra guardrails on or off gives identical results before reuse (10.2 vs 10.2) and a difference of just +0.4 after — well within normal run-to-run noise.',
  },
  {
    title: 'How long the agent is allowed to try',
    verdict: 'Only changes speed',
    detail:
      'A tighter step limit versus a generous one barely changes how many tasks are solved, but it does cut wall-clock time by about 30% on the tasks that fail.',
  },
  {
    title: 'Whether the program is a graph or a flat script',
    verdict: 'Small, consistent edge',
    detail:
      'Running programs as checked graphs beats flat scripts by a small, consistent margin (+0.67 tasks across matched runs) — suggestive, but a far smaller effect than the check itself.',
  },
]

// Validity-threat closure (Table tab:gap-closure).
export const THREATS = [
  { n: 1, threat: 'Single-run variance', status: 'Closed', ev: 'n=3 cold→warm + n=5 cold-runs' },
  { n: 2, threat: 'Verify-gate ablation', status: 'Closed ×3 platforms', ev: 'Android p<0.001; OSWorld 43pp; WebArena 15pp; meta p≈10⁻⁴', hero: true },
  { n: 3, threat: 'Android cold→warm monotonicity', status: 'Closed', ev: 'n=3 with rag_db reset, all monotonic' },
  { n: 4, threat: 'Prompt-guidance inertness', status: 'Closed', ev: 'agent.py:464 omits additional_guidelines' },
  { n: 5, threat: 'Code-level guardrails', status: 'Closed (n=5)', ev: 'Aggregate-neutral (cold 10.2 = 10.2)' },
  { n: 6, threat: 'Compile-fidelity taxonomy', status: 'Closed', ev: '5/5 manual agreement per bucket' },
  { n: 7, threat: 'Step-budget AB', status: 'Closed (n=5)', ev: 'Within ±2 prediction; wall ratio 0.69' },
  { n: 8, threat: 'Platform-coverage', status: 'Out of scope', ev: 'Requires net-new benchmarks', oos: true },
  { n: 9, threat: 'Baseline-parity replication', status: 'Closed', ev: 'Cross-model and cross-seed' },
  { n: 10, threat: 'Cache-miss-to-CUA fallback', status: 'Closed (n=4)', ev: 'WebArena Δ −4.0 → −1.0, matches Muscle-Mem', hero: true },
  { n: 11, threat: 'Compile-LLM robustness', status: 'Closed (n=3)', ev: 'Gemini vs Claude: rejection 83 ≈ 89%' },
  { n: 12, threat: 'Embedding-selector robustness', status: 'Closed', ev: 'Both 100% functional; bge wider safe window' },
]

export const CROSS_MODEL = {
  claude: { label: 'Claude Sonnet 4.6', sr: '11/15', pct: 73.3 },
  gemini: { label: 'Gemini 3 Flash (3-seed mean)', sr: '11.0/15', pct: 73.3 },
  fails: ['BrowserDraw', 'SystemBrightnessMax', 'SystemWifiTurnOn'],
}
