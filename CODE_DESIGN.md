# PreAct Code Design

## Architecture Overview

PreAct is structured as a Python package with clear module boundaries matching the
system architecture described in DESIGN.md. The system uses Playwright for browser
automation, Gemini 3 Flash for LLM inference, and ChromaDB for RAG-indexed program
retrieval.

```
preact/
├── __init__.py              # Package root, version
├── config.py                # Global configuration, LLM settings, timeouts
├── schemas.py               # Pydantic models for all JSON structures
│
├── environment/             # Computer Environment Interface
│   ├── __init__.py
│   ├── base.py              # Abstract ComputerEnvironment protocol
│   ├── browser.py           # Playwright-based browser environment
│   └── docker_env.py        # Docker container environment (for OSWorld)
│
├── executor/                # RPA Executor
│   ├── __init__.py
│   ├── engine.py            # State machine traversal engine
│   ├── actions.py           # Action executors (click, type, scroll, etc.)
│   └── context.py           # Execution data context (variables, params)
│
├── recorder/                # Interaction Recorder
│   ├── __init__.py
│   ├── trace.py             # Trace data structures
│   └── recorder.py          # Passive interaction monitor
│
├── generator/               # Model Generator
│   ├── __init__.py
│   ├── compiler.py          # Trace → State Machine compilation
│   └── prompts.py           # LLM prompts for compilation
│
├── rag/                     # RAG Database
│   ├── __init__.py
│   ├── store.py             # ChromaDB-backed program store
│   └── embeddings.py        # Embedding generation for program indexing
│
├── cua/                     # Standard CUA Loop
│   ├── __init__.py
│   ├── loop.py              # Observe-Reason-Act loop
│   ├── action_parser.py     # Parse LLM actions into executable format
│   └── prompts.py           # CUA system/user prompts
│
├── core/                    # Agent Core (Orchestrator)
│   ├── __init__.py
│   ├── agent.py             # Main orchestrator
│   └── refinement.py        # Monotonic graph extension logic
│
├── baselines/               # Baseline implementations
│   ├── __init__.py
│   ├── action_engine/       # ActionEngine (from paper)
│   │   ├── __init__.py
│   │   ├── crawler.py       # Untargeted app crawling
│   │   ├── codegen.py       # State machine → Python script
│   │   └── executor.py      # Python script executor
│   ├── muscle_mem/          # Muscle-Mem wrapper
│   │   ├── __init__.py
│   │   └── adapter.py       # Adapter for our environment interface
│   ├── agent_rr/            # AgentRR (from paper)
│   │   ├── __init__.py
│   │   ├── experience.py    # Multi-level experience store
│   │   └── replayer.py      # Experience-guided replay
│   └── workflow_use/        # Workflow-Use wrapper
│       ├── __init__.py
│       └── adapter.py       # Adapter for our environment interface
│
├── evaluation/              # Evaluation Framework
│   ├── __init__.py
│   ├── harness.py           # Benchmark execution harness
│   ├── metrics.py           # Metrics collection and computation
│   ├── experiments.py       # Experiment protocols (1-5)
│   ├── mutations.py         # UI mutation injection (Experiment 3)
│   └── report.py            # Results aggregation and reporting
│
└── llm/                     # LLM abstraction layer
    ├── __init__.py
    └── client.py            # Gemini 3 Flash client wrapper
```

## Module Contracts

### 1. `preact.schemas` — Data Models

All data flows through Pydantic v2 models for validation and serialization.

```python
# Core state machine types
class StateVerification: type, xpath, timeout_ms, data_key
class State: id, verification, description
class ActionSpec: type, target, text, parameter_name, prompt, store_result_as, ...
class Transition: from_state, to_state, action, condition
class HumanIntervention: before_state, prompt, intervention_type, timeout_sec, ...
class RPAProgram: metadata, states, transitions, human_interventions

# Trace types
class TraceStep: timestamp, screenshot_path, action, xpath, element_info, llm_reasoning
class InteractionTrace: task_description, steps, app_context, start_time, end_time

# Execution types
class ExecutionResult: success, states_visited, fallback_states, total_time_ms, ...
class FallbackEvent: failed_state, screenshot, llm_resolution, new_states, new_transitions
```

### 2. `preact.environment.base` — Computer Environment Protocol

```python
class ComputerEnvironment(Protocol):
    async def start() -> None
    async def stop() -> None
    async def screenshot() -> bytes                    # Full page screenshot
    async def element_screenshot(xpath) -> bytes       # Element-specific screenshot
    async def element_exists(xpath, timeout_ms) -> bool
    async def element_text(xpath) -> str
    async def click(xpath) -> None
    async def double_click(xpath) -> None
    async def type_text(xpath, text) -> None
    async def press_key(key) -> None
    async def scroll(direction, amount) -> None
    async def move_to(xpath) -> None
    async def drag(from_xpath, to_xpath) -> None
    async def get_page_url() -> str
    async def get_dom_snapshot() -> str                # For recorder
    async def evaluate_js(script) -> Any               # For advanced queries
```

### 3. `preact.executor.engine` — State Machine Engine

```python
class RPAExecutor:
    def __init__(env: ComputerEnvironment, llm: LLMClient)
    
    async def execute(program: RPAProgram, params: dict) -> ExecutionResult:
        """Traverse the state graph. For each state:
        1. Verify current state via XPath polling
        2. On success: execute action, transition to next state
        3. On failure: return FallbackEvent with current context
        4. On terminal state: return success
        """
    
    async def verify_state(state: State) -> bool
    async def execute_action(action: ActionSpec, context: ExecutionContext) -> None
    async def evaluate_condition(expr: str, context: ExecutionContext) -> bool
```

### 4. `preact.recorder.recorder` — Interaction Recorder

```python
class InteractionRecorder:
    def __init__(env: ComputerEnvironment)
    
    def start_recording(task_description: str) -> None
    async def record_step(action: ActionSpec, screenshot: bytes, 
                          llm_reasoning: str = None) -> None
    def stop_recording() -> InteractionTrace
```

### 5. `preact.generator.compiler` — Model Generator

```python
class ModelGenerator:
    def __init__(llm: LLMClient)
    
    async def compile(trace: InteractionTrace) -> RPAProgram:
        """Single LLM call that analyzes the full trace and produces
        a JSON state machine. Uses structured output."""
    
    async def extend_graph(program: RPAProgram, 
                           fallback: FallbackEvent) -> RPAProgram:
        """Monotonic graph extension: add new states/transitions
        from a fallback resolution without modifying existing graph."""
```

### 6. `preact.rag.store` — Program Store

```python
class ProgramStore:
    def __init__(persist_dir: str)
    
    async def store(program: RPAProgram) -> str         # Returns program_id
    async def query(task: str, context: str, k: int) -> list[RPAProgram]
    async def update(program_id: str, program: RPAProgram) -> None
    async def delete(program_id: str) -> None
```

### 7. `preact.cua.loop` — Standard CUA Loop

```python
class CUALoop:
    def __init__(env: ComputerEnvironment, llm: LLMClient, 
                 recorder: InteractionRecorder)
    
    async def run(task: str, max_steps: int = 30) -> CUAResult:
        """Full observe-reason-act loop. Each step:
        1. Screenshot → LLM
        2. LLM reasons and outputs action
        3. Parse action, execute via environment
        4. Record step in interaction recorder
        """
    
    async def run_from_context(task: str, current_screenshot: bytes,
                                context: str, max_steps: int) -> CUAResult:
        """Resume CUA from a specific context (for fallback)."""
```

### 8. `preact.core.agent` — Agent Core

```python
class PreActAgent:
    def __init__(env: ComputerEnvironment, llm: LLMClient,
                 store: ProgramStore)
    
    async def execute_task(task: str, params: dict = None) -> TaskResult:
        """Main entry point:
        1. Query RAG for matching program
        2. If found: execute via RPA Executor
           - On state failure: fallback to CUA, then extend graph
        3. If not found: run full CUA loop, compile trace to program
        4. Store/update program in RAG
        """
```

### 9. `preact.llm.client` — LLM Client

```python
class LLMClient:
    def __init__(model: str, api_key: str)
    
    async def complete(messages: list[dict], 
                       response_format: type = None) -> str
    async def complete_with_vision(messages: list[dict],
                                    images: list[bytes]) -> str
    
    # Token/cost tracking
    total_input_tokens: int
    total_output_tokens: int
```

## Data Flow

```
User Task
    │
    ▼
Agent Core ──query──▶ RAG DB
    │                    │
    │◀──program found────┘
    │
    ▼ (if found)
RPA Executor ──verify state──▶ Environment
    │                              │
    │◀──element exists/not─────────┘
    │
    ├──(success)──▶ execute action ──▶ Environment
    │
    └──(failure)──▶ Agent Core ──▶ CUA Loop ──▶ Environment
                        │              │
                        │              ▼
                        │         Recorder ──trace──▶ Model Generator
                        │                                  │
                        │◀──extended program────────────────┘
                        │
                        ▼
                    RAG DB (store/update)
```

## Key Design Decisions

1. **Async throughout**: All environment interactions are async (Playwright is async).
   The entire execution pipeline uses asyncio.

2. **Pydantic schemas**: JSON state machines are validated through Pydantic models,
   ensuring type safety and easy serialization/deserialization.

3. **Gemini 3 Flash**: Used as the primary LLM for all components (CUA loop, model
   generation, inspection actions). Structured output (JSON mode) for compilation.

4. **ChromaDB for RAG**: Lightweight, embeddable vector DB. Programs are indexed by
   task description embeddings + metadata filtering on app context.

5. **Playwright for browser**: Industry-standard browser automation with built-in
   XPath support, screenshot capabilities, and DOM inspection.

6. **Stateless executor**: The RPA Executor has no persistent state — all context
   is passed through ExecutionContext, making it easy to test and reason about.

7. **Monotonic extension**: Graph refinement only adds states/transitions, never
   removes or modifies existing ones, ensuring convergence.
