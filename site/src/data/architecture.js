// Architecture, implementation, and the worked program example.

export const COMPONENTS = [
  {
    id: 'selector',
    name: 'Program picker',
    tagline: 'Is there a saved program for this?',
    body:
      'Given a new task, this decides whether the library already holds a program for it. By default a language model reads each saved program\'s description and picks one (or none), but a plain embedding search does just as well, so the choice is not important. When nothing fits, the agent simply solves the task itself.',
    file: 'preact/rag/selector.py',
    tone: 'replay',
  },
  {
    id: 'replayer',
    name: 'Program runner',
    tagline: 'Walk the program; check each step.',
    body:
      'It runs a saved program step by step: at each state it confirms the screen looks the way the program expects, and at each step it performs the action. No language model is involved, so a successful run is fast and cheap. The moment a check fails or an action errors, it hands the task to the full agent.',
    file: 'preact/executor/engine.py',
    tone: 'replay',
  },
  {
    id: 'cua',
    name: 'Full agent (fallback)',
    tagline: 'Hand control back to the agent.',
    body:
      'When no stored program fits, or a replay check fails, the full computer-using agent takes over from the live screen and finishes the task the slow way — reading the screen, reasoning, and acting step by step. We use AndroidWorld\'s T3A agent on mobile and Anthropic\'s Computer-Use API on desktop, each running its own standard prompt with nothing added.',
    file: 'preact/cua/loop.py',
    tone: 'neutral',
  },
  {
    id: 'compiler',
    name: 'Compiler',
    tagline: 'Turn the run into a program.',
    body:
      'Once the agent finishes, the recorded run is turned into a small program: states with a check on the screen, transitions with the action that moves between them. Values the agent typed (a name, a phone number) become parameters, so the same program works for any contact, not just this one.',
    file: 'preact/generator/compiler.py',
    tone: 'neutral',
  },
  {
    id: 'gate',
    name: 'Verification check',
    tagline: 'Did the program actually work?',
    body:
      'This is the part that matters most. Before a new program is kept, PreAct resets the environment, runs the program from scratch, and asks the benchmark\'s own evaluator whether the task was really solved. Only programs that pass are saved. This is what catches the dangerous case — a program that runs to its last step yet leaves the task undone — and it is what lets repeated runs improve instead of slowly decay.',
    file: 'benchmark/.../run_docker.py',
    tone: 'pass',
  },
  {
    id: 'corpus',
    name: 'Program library',
    tagline: 'The part that grows with use.',
    body:
      'A store of saved programs, one per kind of task. When the agent solves the same task again and produces a better program, it replaces the old one rather than piling up duplicates. The code that runs this loop never changes; what grows is the library of checked, runnable programs.',
    file: 'preact/rag/store.py',
    tone: 'pass',
  },
]

export const ALGORITHM = [
  { l: 'find a saved program for the task', c: 'there may be none', kind: 'select' },
  { l: 'if one was found:', c: '', kind: 'flow' },
  { l: '  run it, checking the screen at each step', c: 'no model calls', kind: 'replay' },
  { l: '  if it reached the goal:', c: '', kind: 'flow' },
  { l: '    done — fast and cheap', c: 'the common case once learned', kind: 'warm' },
  { l: 'otherwise, let the full agent solve the task', c: 'the slow way', kind: 'cua' },
  { l: 'if the agent could not solve it: stop', c: '', kind: 'flow' },
  { l: 'turn the run into a new program', c: 'states + actions', kind: 'compile' },
  { l: 'reset the environment to a clean state', c: 'for an honest re-check', kind: 'flow' },
  { l: 'run the new program from scratch', c: '', kind: 'replay' },
  { l: 'ask the evaluator whether the task was solved', c: '', kind: 'flow' },
  { l: 'if the program really worked:', c: 'the verification check', kind: 'gate' },
  { l: '  save it to the library', c: 'replacing any older version', kind: 'store' },
]

export const ACTION_SCHEMA = [
  ['action_click', 'Click a UI element. target: selector.'],
  ['action_long_press', 'Long-press a UI element. target: selector.'],
  ['input_text', 'Type into a focused element. text: literal or $param.'],
  ['action_keypress', 'Send a key event. key: Enter / Back / Tab …'],
  ['scroll', 'Scroll a region. direction: up / down / left / right.'],
  ['open_app', 'Launch an application by name.'],
  ['wait', "Sleep for the platform's default delay."],
  ['navigate_back', 'System Back gesture / browser back.'],
  ['navigate_home', 'Return to the home screen / desktop.'],
  ['inspect_text', 'Read a value at a selector. store_result_as: var.'],
  ['answer', 'Emit a final textual answer.'],
  ['status', 'Terminate. goal_status: complete / infeasible.'],
]

export const ENV_KNOBS = [
  { k: 'PREACT_VERIFY_GATE', v: 'on / off', d: 'The main experiment — turn the verification check on or off.' },
  { k: 'PREACT_CACHE_MISS_FALLBACK', v: 'cua / skip', d: 'When the check rejects everything, let the full agent solve the repeat run.' },
  { k: 'PREACT_SELECTOR_MODE', v: 'agentic / embedding', d: 'Pick saved programs with an LLM or with a plain embedding search.' },
  { k: 'PREACT_COMPILE_PROVIDER', v: 'claude / gemini', d: 'Swap the compile-step LLM (cross-model robustness).' },
  { k: 'PREACT_RUNTIME_MODE', v: 'state_machine / flat_script', d: 'Run programs as checked graphs or as flat scripts.' },
  { k: 'PREACT_GUARDRAILS', v: 'on / off', d: 'Extra hand-written runtime safeguards.' },
  { k: 'PREACT_LLM_PROVIDER', v: 'claude / gemini', d: 'Which model the full agent uses.' },
]

export const MODULES = [
  { name: 'rag/', lines: 791, role: 'Program library + the program picker (LLM and embedding)', comp: 'Picker · Library' },
  { name: 'executor/', lines: 839, role: 'Program runner — walks the program, checks each step', comp: 'Runner' },
  { name: 'generator/', lines: 639, role: 'Turns a finished run into a saved program', comp: 'Compiler' },
  { name: 'cua/', lines: 826, role: 'The full agent: read–reason–act loop and fallback entry', comp: 'Full agent' },
  { name: 'core/', lines: 717, role: 'Orchestration — pick / run / fall back / save', comp: 'Main loop' },
  { name: 'schemas.py', lines: 278, role: 'Program, State, Transition, Action, run traces', comp: 'Program model' },
  { name: 'platforms/', lines: 5888, role: 'Android / OSWorld / Web adapters and agent backends', comp: 'Backends' },
  { name: 'evaluation/', lines: 1309, role: 'Benchmark harness + the verification-check driver', comp: 'Check · Eval' },
]

// A real saved program, taken verbatim from the corpus (program ab4390a9):
// the one compiled the first time the agent ran AndroidWorld's "add a contact" task.
export const EXAMPLE_PROGRAM = {
  metadata: {
    task_description: 'Create a new contact for Emilia Gonzalez. Their number is +14240925675.',
    application_context: 'com.google.android.contacts',
    parameters: ['first_name', 'last_name', 'phone_number'],
  },
  states: [
    { id: 'contacts_app_open', verify: "'+' create button is visible", desc: 'Contacts list is open' },
    { id: 'create_contact_form', verify: 'First name field is shown', desc: 'New-contact form is open' },
    { id: 'first_name_entered', verify: 'Last name field is shown', desc: 'First name entered' },
    { id: 'last_name_entered', verify: 'Phone field is shown', desc: 'Last name entered' },
    { id: 'phone_entered', verify: "'Mobile' label is shown", desc: 'Phone number entered' },
    { id: 'phone_type_selected', verify: "'Save' button is shown", desc: 'Phone type selected' },
    { id: 'contact_saved', verify: 'task complete', desc: 'Contact saved', terminal: true },
  ],
  transitions: [
    { from: 'contacts_app_open', to: 'create_contact_form', action: 'tap', detail: "tap the + (create contact) button" },
    { from: 'create_contact_form', to: 'first_name_entered', action: 'type', detail: 'type $first_name' },
    { from: 'first_name_entered', to: 'last_name_entered', action: 'type', detail: 'type $last_name' },
    { from: 'last_name_entered', to: 'phone_entered', action: 'type', detail: 'type $phone_number' },
    { from: 'phone_entered', to: 'phone_type_selected', action: 'tap', detail: "tap 'Mobile'" },
    { from: 'phone_type_selected', to: 'contact_saved', action: 'tap', detail: "tap 'Save'" },
  ],
}
