Pydantic Core Concept

# 1. Agents
  *I. Definition and Purpose*
    A. Agents are the primary abstraction for running language models with structure, context, and capabilities.
    B. They bundle configuration, tools, dependencies, system prompts, history, and output schemas into a single orchestrated object.
    C. They serve as the top-level interface between a model provider and your application.
    D. Agents unify behavior definition (system prompts), execution control (tools and retries), and validation (structured outputs).
  *II. Generic Parameters and Typing*
    A. Agents are generic over two types: dependency type (`DepsType`) and output type (`OutputType`).
    B. `DepsType` defines the shape of `ctx.deps`, the dependency object available to tools and prompts.
    C. `OutputType` defines the structure of the model's validated return value.
    D. These generics exist at development time; they improve linting and type-checking but do not affect runtime behavior.
  *III. Core Configuration Knobs*
    A. `model` represents the LLM backend identifier or `Model` instance.
      **i. Example identifiers include `openai:gpt-5`, `anthropic:claude-3.5`, or other registered providers.**
    B. `system_prompt` or instructions supply the root behavioral definition for the model.
      **i. They can be static text or a callable referencing `RunContext` for dynamic content.**
    C. `output_type` specifies the expected output schema, enabling structured validation.
      **i. This ensures consistent, typed responses for downstream use.**
    D. `model_settings` capture low-level model parameters such as temperature, `max_tokens`, or seed.
      **i. These defaults merge with per-run overrides for flexibility.**
    E. Provider-specific `model_settings` entries tune behaviors like JSON routing or tool choice hints.
      **i. `docs/agents.md:664` outlines Azure/OpenAI/Anthropic-specific knobs and safe ranges.**
    F. `deps_type` declares the dependency types the agent uses across tools and prompts.
      **i. This enables `ctx.deps` autocompletion and validation.**
    G. `tools`, `toolsets`, and `builtin_tools` define callable operations the model can invoke.
      **i. Tools are user-defined, while built-in sets provide reusable default capabilities.**
    H. `history_processors` transform or filter conversation history before model input.
      **i. They support privacy filtering, truncation, or message reformatting.**
    I. `usage_limits` govern aggregate token budgets, streaming durations, and request ceilings.
      **i. Configure `max_tokens`, `max_output_tokens`, or wall-clock allotments per `docs/agents.md:563`.**
    J. `retries`, `output_retries`, and `ModelRetry` hooks control automatic remediation loops.
      **i. `docs/agents.md:637` details capping tool calls, retry backoffs, and failure escalation.**
    K. `tool_call_limits` prevent runaway recursive chains by bounding distinct or total tool invocations.
      **i. Raise informative errors or switch end strategies when the cap is exceeded.**
    L. `end_strategy`, `instrument`, and `name` define run completion policy, telemetry hooks, and readable identifiers.
  *IV. Execution Methods*
    A. `agent.run` and `agent.run_sync` provide async versus synchronous full-run interfaces returning `RunResult`.
      **i. Use `run` for concurrent environments and `run_sync` for scripts or blocking calls.**
    B. `agent.run_stream` and `agent.run_stream_sync` stream incremental text or structured responses.
      **i. Streaming suits UI rendering or progressive output display.**
    C. `agent.run_stream_events` yields detailed event objects for each internal action.
      **i. Events include model deltas, tool calls, and completion notifications.**
    D. `agent.iter` walks the agent's computation graph for step-level debugging or orchestration.
      **i. Each node corresponds to a model invocation or tool execution.**
  *V. Run Inputs*
    A. User input consists of text or structured message sequences that initiate the run.
    B. `deps` is a concrete instance matching `deps_type`, provided to each run.
    C. `message_history` supplies prior messages for continuity across turns.
    D. Per-run overrides allow ad hoc adjustments to model choice, usage policies, or retry settings.
    E. Multi-modal parts (image, audio, binary, or document URLs) extend the prompt, and some providers emit `ThinkingPart` traces when reasoning features are enabled (`docs/input.md`, `docs/thinking.md`).
  *VI. RunContext*
    A. `RunContext` is a typed runtime object automatically injected into tools and prompts.
    B. It provides access to dependencies, message history, and helper methods for tool invocation and logging.
    C. The context mirrors the agent's declared `DepsType`, ensuring type consistency.
    D. It contextualizes execution without relying on global state.
  *VII. Streaming and Iteration APIs*
    A. `run_stream` exposes `.stream_text()` and `.stream_structured()` helpers for incremental UI updates.
      **i. `docs/agents.md:117` shows combining streamed output with event handlers for responsive UX.**
    B. `run_stream_events` feeds fine-grained events like `FunctionToolCallEvent` for telemetry or audits.
      **i. Inspect deltas (`TextPartDelta`, `ThinkingPartDelta`, `ToolCallPartDelta`) to visualize reasoning traces.**
    C. `agent.iter` plus `async for` lets you advance through each node of the execution DAG.
      **i. Use this to plug into custom schedulers or pause/resume complex orchestrations.**
    D. Manual `.next()` control provides per-step inspection when debugging stubborn tool sequences.
      **i. `docs/agents.md:343` demonstrates calling `await iterator.next(...)` to influence flow.**
    E. Event stream handlers wire low-level streaming events (e.g. `event_stream_handler`, `run_stream_events`) into custom UIs or telemetry sinks.
      **i. Hybrid approaches surface both structured outputs and raw deltas for observability (`docs/agents.md:225`).**
    F. `capture_run_messages` wraps any execution path so you can persist the exact provider transcript for debugging.
      **i. Use captured transcripts before filing model bugs or writing golden tests (`docs/agents.md:1009`).**
  *VIII. Prompt Assets*
    A. System prompts define non-negotiable behavior and can be plain strings or callables returning text.
      **i. Callable prompts receive `RunContext`, enabling dependency-backed instructions (`docs/agents.md:836`).**
    B. Instructions (developer plus user) let you layer role-specific guidance or reflection scaffolds.
      **i. `docs/agents.md:891` clarifies how to combine instructions with history for multi-turn handoffs.**
    C. Prompt factories encapsulate instruction assembly logic so reuse is centralized.
      **i. They often live on dependency objects to simplify overriding in tests.**
  *IX. Operational Controls*
    A. Runtime `UsageLimits` stop runaway costs by capping tokens, duration, or tool calls even if defaults allow more.
      **i. Pair with monitoring to alert when runs approach configured ceilings.**
    B. Telemetry instrumentation (Logfire or OpenTelemetry) streams spans, tool calls, and HTTP traces for observability (`docs/logfire.md`).
      **i. Tag spans with agent names and run IDs to align with broader APM traces.**
    C. Provider transports can be wrapped with custom `httpx.AsyncClient` instances or `AsyncTenacityTransport` to add retries/backoff (`docs/retries.md`).
      **i. Centralize retry logic so each agent does not hand-roll error handling.**
  *X. Advanced Orchestration*
    A. Agent delegation lets one agent invoke another via tools, sharing dependencies and budgets for collaborative behaviors (`docs/multi-agent-applications.md`).
      **i. Pass run metadata between agents to maintain audit trails.**
    B. Programmatic hand-offs chain multiple agents with human or application logic deciding the next step between runs.
      **i. Model guardrails or product logic can insert approvals between hand-offs.**
    C. Graph-based control flow and durable execution (pydantic-graph, Temporal/Prefect/DBOS) enable pause/resume semantics for complex workflows (`docs/graph.md`, `docs/durable_execution/overview.md`).
      **i. Persist graph state to survive worker restarts or long-running tool calls.**
  *XI. Interoperability and Evaluation*
    A. Agents can be exposed over open protocols like A2A or AG-UI and embedded into ASGI apps for cross-agent or frontend interoperability (`docs/a2a.md`, `docs/ag-ui.md`).
      **i. Surface streaming events over WebSockets so clients mirror Logfire dashboards.**
    B. Pydantic Evals provides a code-first harness for regression testing agents, logging results locally or to Logfire dashboards (`docs/evals.md`).
      **i. Reuse datasets across model versions to quantify quality or cost regressions.**
  *XII. Lifecycle and Quality Control*
    A. Runs versus conversations: control whether each call is stateless or part of a persisted history chain (`docs/agents.md:746`).
      **i. Map run IDs to chat sessions for CRM-style workflows.**
    B. Type safety: the `Agent[DepsType, OutputType]` signature enables IDE hints and static analysis (`docs/agents.md:775`).
      **i. Apply mypy/pyright to validate complex tool graphs ahead of time.**
    C. Reflection and self-correction pipelines prompt the model to critique outputs before returning them (`docs/agents.md:951`).
      **i. Combine thinking parts with evaluation prompts for more reliable results.**
    D. Model error handling defines how to surface provider errors, rate limits, or invalid tool payloads (`docs/agents.md:1005`).
      **i. Map exceptions to user-visible retry instructions or telemetry alerts.**

# 2. Dependencies
  *I. Role and Purpose*
    A. Dependencies encapsulate external services, configurations, and contextual data required by the agent.
    B. They allow agents to remain stateless and portable across environments.
  *II. Declaration*
    A. Define `deps_type` using any Python type or dataclass that aggregates necessary resources.
    B. This enables predictable access via `ctx.deps` for all dependent components.
    C. The dependency schema documents what runtime data tools and prompts can expect.
  *III. Runtime Provision*
    A. Provide an instance of dependencies per run through the `deps` parameter.
    B. The framework injects that instance into `RunContext` for every tool and prompt call.
    C. Dependencies can be overridden per run for testing or multi-tenant setups.
  *IV. Usage in Components*
    A. Tools access `ctx.deps` to query data or invoke services.
    B. Dynamic system prompts may interpolate fields from `ctx.deps`.
    C. Output validators may use dependencies for post-processing or cross-checks.
  *V. Async and Sync Compatibility*
    A. Dependencies can expose synchronous or asynchronous methods.
    B. Tools and validators respect async context and await automatically when required.
  *VI. Overriding and Testing*
    A. Substitute mock or stub dependencies in tests to simulate external systems.
    B. Environment-specific dependency instances differentiate production from staging or development contexts.
  *VII. Access Patterns*
    A. System prompts accept `RunContext[Deps]` to fetch secrets or cached resources before composing instructions (`docs/dependencies.md:52`).
      **i. Pass `ctx` as the sole parameter when building prompt factories.**
    B. Function tools and `@agent.tool_plain` branch on dependency state without extra wiring.
      **i. Inject HTTP clients or database handles so tools remain stateless and testable.**
    C. Output validators inspect `ctx.deps` to cross-check responses against policies or ground truth data.
      **i. Combine with `ModelRetry` to automatically request fixes when validations fail.**
    D. Async versus sync helpers can coexist—blocking dependencies will run in a thread pool transparently.
      **i. Prefer async IO when possible to reduce thread churn (`docs/dependencies.md:101`).**
  *VIII. Override Strategies*
    A. Use `agent.override(deps=...)` as a context manager to replace dependencies during tests or one-off runs (`docs/dependencies.md:226`).
      **i. Overridden values apply to nested agent calls without touching global state.**
    B. Multi-tenant apps can swap dependency bundles per request to isolate customer data.
      **i. Pair with request-scoped caches to avoid leaking credentials across tenants.**
    C. Always restore defaults after overrides to keep long-lived agent instances predictable.
      **i. Context managers guarantee cleanup even when exceptions bubble up.**
  *IX. Integrated Example*
    A. `docs/dependencies.md:158` shows a single agent using dependencies inside prompts, tools, and validators.
    B. The pattern demonstrates sharing HTTP clients, API keys, and factories without global variables.
    C. Replicate that structure when bootstrapping your finance agent so every LLM hook observes the same config.

# 3. Function Tools
  *I. Purpose*
    A. Function tools expose controlled actions that the model can call via structured API-like invocations.
    B. They extend the model's reasoning with deterministic external operations.
  *II. Registration*
    A. `@agent.tool` is the default decorator when a tool needs `RunContext` access (`docs/tools.md:25`).
      **i. The context provides dependencies, history, and helper methods.**
    B. `@agent.tool_plain` registers stateless helpers without passing `RunContext`.
      **i. Ideal for pure functions like random dice rolls or formatting utilities.**
    C. Constructor arguments (`tools`, `toolsets`) accept callables or `Tool` objects discovered at import time.
      **i. Combine with MCP or third-party toolsets to onboard large collections at once.**
  *III. Function Signature*
    A. The first parameter must be `ctx: RunContext[DepsType]` for context-enabled tools.
      **i. This provides the runtime context and dependency access.**
    B. Subsequent parameters define the callable inputs required from the model.
      **i. Argument names and type hints drive automatic schema generation.**
      **ii. Default values provide optional arguments.**
    C. Return types determine output schemas, ensuring the model receives structured results.
  *IV. Schema Construction*
    A. Pydantic uses type hints to create a JSON schema representation for arguments and results.
    B. Documentation strings become tool descriptions for the LLM.
    C. Accurate typing enhances model performance when selecting and invoking tools.
    D. Enrich schemas with `Annotated[...]`, `Field(...)`, enums, or literal types for extra clarity (`docs/tools.md:238`).
      **i. Return annotations map directly to tool output payloads.**
  *V. Execution Flow*
    A. The model outputs a function call with tool name and JSON arguments.
    B. The runtime deserializes arguments, constructs `RunContext`, and executes the tool.
    C. The returned value is fed back into the conversation as a model-observable result.
    D. The agent manages ordering, error handling, and retries around tool calls.
  *VI. Toolsets and Extensions*
    A. Toolsets group multiple tools into modular collections reusable across agents.
    B. Built-in toolsets include utilities for math, web search, and system introspection.
    C. External MCP integrations expand capability to connected APIs and systems.
    D. Advanced use cases include dynamically registering tools or conditionally enabling them at runtime.
  *VII. Advanced Tool Behaviors*
    A. Deferred tools let you schedule long-running work and resume when results arrive (`docs/deferred-tools.md:180`).
      **i. Raise `CallDeferred` with the pending task ID so the platform can correlate completions.**
    B. Approval-required tools can pause execution until a human or policy engine okays the call.
      **i. Throw `ApprovalRequired` when arguments or dependencies indicate elevated risk (`docs/deferred-tools.md:22`).**
    C. Mixed-origin toolsets (local plus MCP) allow you to compose bespoke capability bundles per agent (`docs/toolsets.md`).
      **i. Combine toolsets before registering with the agent to maintain deterministic ordering.**

# 4. Output
  *I. Definition*
    A. The `output_type` defines the structure and validation of the final model response.
    B. It can be a basic type, Pydantic model, or complex nested schema.
    C. It ensures predictable and typed downstream consumption.
  *II. Modes*
    A. Native output returns raw text with minimal parsing.
      **i. Pick this when free-form prose is acceptable or when another parser handles the text.**
    B. Prompted output uses textual hints to approximate structured formats.
      **i. Useful for quick prototypes where strict schemas feel heavy.**
    C. Structured output enforces strict schema validation and error recovery.
      **i. Choose this when downstream automation needs validated data classes.**
    D. Output functions allow the model to end a run by calling a finalizer instead of returning text (`docs/output.md:118`).
      **i. Use them to trigger side effects or post-processing without another model call.**
  *III. Validation and Retries*
    A. All model outputs are parsed and validated against `output_type`.
    B. Validation errors trigger re-prompting with correction context.
      **i. The system automatically reissues the model call with error feedback.**
    C. Retry policies are capped via `output_retries` to prevent infinite loops.
    D. Custom JSON schemas (including `TypedDict` or `BaseModel`) tighten guarantees for dict outputs (`docs/output.md:388`).
      **i. Validate nested structures before shipping them to downstream systems.**
    E. Image outputs carry metadata and binary payload references that must pass validation (`docs/output.md:473`).
      **i. Store signed URLs or base64 strings alongside textual answers.**
    F. `ModelRetry` exceptions raised inside validators inject human-readable remediation tips.
      **i. Combine with dependency-aware validators to request precise corrections.**
  *IV. Result Object*
    A. The `RunResult` contains output, usage, and message metadata.
    B. `output` represents the validated final answer.
    C. `usage` tracks token counts and cost estimates.
    D. `all_messages` and `new_messages` expose conversation-level traceability.
  *V. Streaming*
    A. Stream modes emit incremental text or partial structured outputs.
    B. Streaming supports responsive UI integration and interactive feedback.
    C. `run_stream_events` surfaces granular lifecycle events including thinking, tool calls, and completion.
    D. Streamed text, structured payloads, and model responses have dedicated iterators (`docs/output.md:511`).
      **i. Use `.stream_text()` for chat bubbles, `.stream_structured()` for progressive JSON, and `.stream_model_responses()` for raw provider output.**
  *VI. Validators*
    A. Custom validators can post-process or inspect results before returning them.
    B. They may use `ctx.deps` for contextual verification or augmentation.
    C. The validation chain ensures semantic correctness in addition to syntactic compliance.

# 5. Messages and Chat History
  *I. Message Model*
    A. Messages represent atomic communication units: system, user, model, or tool responses.
    B. They are structured objects rather than plain strings, enabling reproducibility and persistence.
  *II. Message History*
    A. `message_history` carries prior messages to maintain continuity across runs.
    B. It is essential for conversational agents requiring memory.
    C. The agent automatically appends new messages after each run.
  *III. History Processors*
    A. `history_processors` modify or filter messages before the model sees them.
    B. Common uses include redacting sensitive data, summarizing context, or truncating long histories.
    C. Multiple processors can be chained for layered transformations.
    D. `docs/message-history.md:330` discusses best practices for pruning, summarizing, and enforcing policy.
      **i. Write processors as pure functions for easy unit testing (`docs/message-history.md:460`).**
      **ii. Compose processors carefully to avoid repeatedly truncating vital context (`docs/message-history.md:513`).**
  *IV. Accessing History*
    A. Run results provide `all_messages` for full trace retrieval.
    B. `new_messages` isolates outputs generated during the latest run.
    C. Developers can manually append these to maintain persistent session state.
  *V. Session Management*
    A. Stateful sessions store `message_history` across runs to simulate memory.
    B. External persistence enables database-backed conversational continuity.
    C. Manual management allows explicit control over pruning and context reuse.
    D. Feed stored histories back into `agent.run(..., message_history=...)` for follow-up conversations (`docs/message-history.md:139`).
  *VI. Storage and Replay*
    A. Serialize messages to JSON for later auditing or offline evaluation (`docs/message-history.md:211`).
    B. Reload stored transcripts to recreate identical agent inputs when debugging tricky runs.
    C. Use message snapshots as fixtures in integration tests to verify regression scenarios.

# 6. Direct Model Requests
  *I. Definition*
    A. Direct model requests invoke models without using the Agent abstraction.
    B. They are thin wrappers for one-shot inference or low-level control.
  *II. Core Functions*
    A. `model_request` and `model_request_sync` send a single prompt and return a `ModelResponse` (`docs/direct.md:14`).
      **i. Supply explicit `messages` and model IDs just like raw provider APIs.**
    B. `model_request_stream` and `model_request_stream_sync` provide token-level streaming interfaces.
      **i. Pair with async iterators to display output as it arrives.**
    C. These calls expose the raw interaction layer between model and caller.
    D. Tool-calling requests require you to register schemas manually and handle follow-up invocations (`docs/direct.md:36`).
      **i. Build the event loop yourself for function-call responses.**
  *III. Use Cases*
    A. Direct requests are appropriate when structured orchestration or dependency injection is unnecessary.
    B. They are ideal for lightweight tasks like embeddings, completions, or diagnostics.
    C. Use the Agent abstraction when tools, validation, or complex workflow management are needed.
  *IV. Schema and Tools*
    A. Direct mode still supports manually defined schemas and tools but requires explicit management.
    B. It maps closely to provider-level APIs with minimal automation.
    C. Agent builds atop this layer to provide orchestration, validation, and dependency wiring.
  *V. Instrumentation*
    A. Direct calls can emit OpenTelemetry or Logfire spans for observability (`docs/direct.md:105`).
    B. Attach span IDs yourself since there is no agent-run container to do it automatically.
    C. Use consistent trace metadata so mixed agent/direct workflows can be correlated.
  *VI. Decision Checklist*
    A. Prefer agents when you need dependencies, structured outputs, or automatic retries.
    B. Prefer direct calls for one-off diagnostics, provider benchmarking, or ultra-low-latency use cases.
    C. Keep both paths wired so you can fall back to direct mode if agent constraints block experimentation.
