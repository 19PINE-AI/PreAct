// Benchmark test-case data for the PreAct interactive paper site.
// All task definitions and per-seed / per-rep results are transcribed from the
// paper (preact.tex), findings_summary.md, and the raw results JSON in
// benchmark/{androidworld,osworld,webarena}/results/.

export const BENCHMARKS = {
  androidworld: {
    id: 'androidworld',
    name: 'AndroidWorld',
    subset: 'official-15',
    blurb:
      '15 curated tasks across 8 Android app domains — the same subset used by the upstream T3A baseline.',
    container: 'huggingface/android_world:latest (+ /state endpoint patch)',
    cuaModel: 'Gemini 3 Flash (multi-provider port)',
    evalNote:
      'Success is the AndroidWorld environment evaluator: task.is_successful(env) == 1.0 over the final device state.',
    seeds: ['42', '100', '1337'],
    seedLabel: 'Warm-run pass across the three Gemini 3 Flash monotonicity seeds',
  },
  osworld: {
    id: 'osworld',
    name: 'OSWorld',
    subset: 'test_tiny',
    blurb:
      '6 desktop tasks across Chrome, LibreOffice Calc, and LibreOffice Writer, run via the DesktopEnv provider.',
    container: 'happysixd/osworld-docker (DesktopEnv)',
    cuaModel: 'Claude Sonnet 4.6 (Computer-Use API)',
    evalNote:
      'Each task runs a postconfig save step, then a custom evaluator compares the resulting state against ground-truth reference data.',
    reps: ['gate ON', 'gate OFF'],
  },
  webarena: {
    id: 'webarena',
    name: 'WebArena',
    subset: 'shopping_admin · 12-task',
    blurb:
      'A 12-task answer-extraction subset on a Magento e-commerce admin panel — string-match against reference answers.',
    container: 'shopping_admin_final_0719 Magento Docker stack',
    cuaModel: 'Claude Sonnet 4.6 (Computer-Use API)',
    evalNote:
      'WebArena string_match (exact / must_include / fuzzy_match) against reference_answers on the live admin panel.',
  },
}

// ── AndroidWorld official-15 ──────────────────────────────────────────────
// warm[seed42, seed100, seed1337] from Appendix C (Table tab:gemini-3seed).
// "dagger" = live evaluator passed but the verify-gate rejected the recompiled
// program on that seed (verify_score=0); the warm run still passed.
export const ANDROID_TASKS = [
  { id: 'AudioRecorderRecordAudio', app: 'Audio Recorder', desc: 'Record an audio clip.', warm: ['PASS', 'PASS', 'PASS'] },
  { id: 'AudioRecorderRecordAudioWithFileName', app: 'Audio Recorder', desc: 'Record an audio clip and save it under a specified file name (requires clearing a pre-filled filename field).', warm: ['PASS†', 'PASS', 'PASS†'] },
  { id: 'BrowserDraw', app: 'Browser', desc: 'Reproduce a drawing on an HTML canvas.', warm: ['FAIL', 'FAIL', 'FAIL'], stable: true, why: 'Harness-deterministic: the image canvas is not represented in the accessibility tree.' },
  { id: 'BrowserMaze', app: 'Browser', desc: 'Navigate a ball to the goal through an on-screen maze.', warm: ['PASS', 'PASS', 'FAIL'], variance: true },
  { id: 'CameraTakePhoto', app: 'Camera', desc: 'Take one photo.', warm: ['PASS', 'PASS', 'PASS'] },
  { id: 'CameraTakeVideo', app: 'Camera', desc: 'Record one video.', warm: ['FAIL', 'FAIL', 'PASS'], variance: true },
  { id: 'ClockStopWatchPausedVerify', app: 'Clock', desc: 'Verify the stopwatch is in a paused state.', warm: ['PASS', 'PASS', 'PASS'] },
  { id: 'ClockStopWatchRunning', app: 'Clock', desc: 'Start the stopwatch so it is running.', warm: ['PASS', 'PASS', 'PASS'] },
  { id: 'ContactsAddContact', app: 'Contacts', desc: 'Add a new contact with the given details.', warm: ['PASS†', 'PASS†', 'FAIL'], variance: true, smokingGun: '80bff413' },
  { id: 'ContactsNewContactDraft', app: 'Contacts', desc: 'Open the new-contact screen and enter the given first name, last name, phone number and phone label.', warm: ['PASS', 'PASS', 'PASS'] },
  { id: 'FilesDeleteFile', app: 'Files', desc: 'Delete a specified file from the file manager.', warm: ['PASS', 'PASS', 'PASS'] },
  { id: 'MarkorCreateFolder', app: 'Markor', desc: 'Create a new folder in the Markor notes app.', warm: ['PASS†', 'PASS†', 'PASS†'], smokingGun: '(auto)' },
  { id: 'MarkorCreateNote', app: 'Markor', desc: 'Create a new note in Markor.', warm: ['PASS', 'PASS', 'PASS'] },
  { id: 'SystemBrightnessMax', app: 'System', desc: 'Set the screen brightness to maximum.', warm: ['FAIL', 'FAIL', 'FAIL'], stable: true, why: 'Harness-deterministic: scroll-on-seekbar incompatibility — the agent runs its full budget then fails.' },
  { id: 'SystemWifiTurnOn', app: 'System', desc: 'Turn on Wi-Fi.', warm: ['FAIL', 'FAIL', 'FAIL'], stable: true, why: 'Harness-deterministic: the agent trusts a stale status-bar Wi-Fi icon.' },
]

// ── OSWorld test_tiny ─────────────────────────────────────────────────────
// gateON / gateOFF columns are the mean cold→warm behaviour from the n=5
// verify-gate ablation; mode is from the representative warm result JSON.
export const OSWORLD_TASKS = [
  {
    id: 'bb5e4c0d',
    fullId: 'bb5e4c0d-f964-439c-97b6-bdb9747de3f4',
    app: 'Chrome',
    desc: 'Make Bing the default search engine in Chrome.',
    evalCriterion: 'match_in_list — default_search_engine must be "Microsoft Bing" / "Bing".',
    mode: 'hybrid',
  },
  {
    id: '7b6c7e24',
    fullId: '7b6c7e24-c58a-49fc-a5bb-d57b80e5b4c3',
    app: 'Chrome',
    desc: 'Clear all Amazon tracking cookies so browsing is private.',
    evalCriterion: 'is_cookie_deleted — Cookies for .amazon.com domains removed.',
    mode: 'hybrid',
  },
  {
    id: '357ef137',
    fullId: '357ef137-7eeb-4c80-a3bb-0951f26a8aff',
    app: 'LibreOffice Calc',
    desc: 'Multiply a duration ("total hours", a time value) by an hourly rate (a number) to get total earnings, filling the correct cell.',
    evalCriterion: 'compare_table — cell E3 ≈ 191.6667 (tol 0.001).',
    mode: 'cua',
  },
  {
    id: '42e0a640',
    fullId: '42e0a640-4f19-4b28-973d-729602b5a4a7',
    app: 'LibreOffice Calc',
    desc: 'Sum "Revenue" and "Total Expenses" into two named columns on a new Sheet2.',
    evalCriterion: 'compare_table — Sheet2 matches expected sheet_data.',
    mode: 'hybrid',
  },
  {
    id: '0810415c',
    fullId: '0810415c-bde4-4443-9047-d5f70165a697',
    app: 'LibreOffice Writer',
    desc: 'Make the first two paragraphs double line-spaced.',
    evalCriterion: 'compare_line_spacing on the first two paragraphs vs gold file.',
    mode: 'rpa',
  },
  {
    id: '0a0faba3',
    fullId: '0a0faba3-5580-44df-965d-f562a99b291c',
    app: 'LibreOffice Writer',
    desc: 'Left-align the first three words of each sentence and right-align the rest using tab stops.',
    evalCriterion: 'check_tabstops — first sentence split at word 3.',
    mode: 'cua',
  },
]

// OSWorld smoking-gun (gate-OFF cov=100% / score=0) programs.
export const OSWORLD_SMOKING = {
  '8f0fdfa4': { task: 'Chrome history clean', reps: '2/5', note: 'browser state mismatches evaluator on warm replay' },
  '43188217': { task: 'LibreOffice Calc formula', reps: '5/5 (fully deterministic)', note: 'cell formula not as expected after mechanical replay' },
  'c1f04f87': { task: 'LibreOffice Calc chart', reps: '4/5', note: 'chart properties mismatch evaluator' },
}

// ── WebArena shopping_admin 12-task subset ────────────────────────────────
// run1 score / answer transcribed from benchmark/webarena/results/latest.json
export const WEBARENA_TASKS = [
  { id: 0, intent: 'What is the top-1 best-selling product in 2022', answer: 'Quest Lumaflex™ Band', eval: 'exact_match', cold: 'PASS', family: 'bestseller' },
  { id: 1, intent: 'What is the top-1 best-selling brand in Quarter 1 2022', answer: 'Sprite', eval: 'exact_match', cold: 'FAIL', family: 'bestseller' },
  { id: 2, intent: 'What is the top-1 best-selling product type in Quarter 1 2022', answer: 'Yoga ball', eval: 'exact_match', cold: 'FAIL', family: 'bestseller' },
  { id: 3, intent: 'What are the top-2 best-selling products in 2022', answer: 'Quest Lumaflex™ Band, Sprite Stasis Ball 65 cm', eval: 'must_include', cold: 'PASS', family: 'bestseller' },
  { id: 4, intent: 'What are the top-3 best-selling products in Jan 2023', answer: 'Impulse Duffle, Overnight Duffle, Hawkeye Yoga Short-32-Blue', eval: 'must_include', cold: 'FAIL', family: 'bestseller' },
  { id: 5, intent: 'What is the top-1 best-selling product type in Jan 2023', answer: 'Duffle', eval: 'exact_match', cold: 'FAIL', family: 'bestseller' },
  { id: 6, intent: 'What are the top-5 best-selling products in 2023', answer: 'Sprite Yoga Strap 6 foot, Overnight Duffle, Ida Workout Parachute Pant-29-Purple, Hawkeye Yoga Short-32-Blue, Sprite Stasis Ball 65 cm', eval: 'must_include', cold: 'FAIL', family: 'bestseller' },
  { id: 11, intent: 'Number of reviews that mention the term "disappointed"', answer: '6', eval: 'must_include', cold: 'PASS', family: 'review-count' },
  { id: 12, intent: 'Number of reviews that mention the term "satisfied"', answer: '2', eval: 'must_include', cold: 'PASS', family: 'review-count' },
  { id: 13, intent: 'Number of reviews that mention the term "decent"', answer: '2', eval: 'must_include', cold: 'PASS', family: 'review-count' },
  { id: 14, intent: 'Number of reviews that mention the term "not useful"', answer: '0', eval: 'must_include', cold: 'PASS', family: 'review-count' },
  { id: 15, intent: 'Number of reviews that mention the term "best"', answer: '2', eval: 'must_include', cold: 'PASS', family: 'review-count' },
]
