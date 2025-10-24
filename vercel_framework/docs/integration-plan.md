# Vercel AI SDK Integration Plan

## 1. Objectives
- Port the existing finance chat experience into the Vercel AI SDK agent framework.
- Preserve the yfinance-backed tooling while making it available through the SDK's ToolSet API.
- Deliver a server-ready entrypoint (API route/CLI) that can drive web UI clients via streaming responses.

## 2. High-Level Architecture
- **Agent:** Vercel ToolLoopAgent wrapping finance-specific system prompt and model choice.
- **Tools:** Node adapters invoking existing Python yfinance_service operations (probably via spawned process or local service).
- **Runtime Surface:** Next.js route handler or standalone serverless handler returning createAgentUIStreamResponse.
- **UI Hooks (optional):** Connect to @ai-sdk/react hooks later; not in first milestone.

## 3. Decisions Needed (Knobs)
1. **Model Provider & Identifier**
   - Options: Vercel Gateway alias (model: 'openai/gpt-5') vs direct provider SDK (e.g., openai('gpt-4o')).
   - Also pick temperature, top_p, max tokens, stop conditions.
2. **Tool Execution Strategy**
   - Spawn Python per call vs persistent worker vs HTTP bridge.
   - Where the Python env lives; how to handle stderr/timeouts.
3. **Tool Input/Output Schema**
   - How strictly we mirror the Python schemas (Zod vs manual typing).
   - Whether to normalize the {ok:bool, result/error} envelope or reinterpret.
4. **Telemetry & Logging**
   - Enable experimental telemetry hooks? custom logging? (affects settings).
5. **Streaming Behaviour**
   - Fully stream tokens, or buffer per step? configure onStepFinish, partial outputs.
6. **Deployment Target**
   - Next.js App Router route? Standalone Node script? influences packaging.
7. **Configuration Surface**
   - Where API keys and runtime flags live (env vars, config module, .env).
8. **Error Handling UX**
   - Map Python tool errors to agent errors vs convert into textual replies.

## 4. Proposed Work Sequence
1. Finalize decisions for sections 3.1–3.4 (core runtime knobs).
2. Scaffold TypeScript workspace inside `vercel framework/` (package.json, tsconfig, src/...).
3. Implement tool adapter prototype for one operation and integration test.
4. Define full tool set + agent wiring (custom OpenRouter `/chat/completions` loop).
5. Add API/CLI entrypoint.
6. Add tests + docs.

## 5. Decision Log
- 2025-10-20: Model provider set to `openai('gpt-4o')` via `@ai-sdk/openai`.
- 2025-10-20: Tool execution uses spawn-per-call bridge into `yfinance_service.py`.
- 2025-10-20: Tool schemas mirrored with Zod; `{ok,result|error}` envelope preserved.
- 2025-10-20: Telemetry left disabled initially; rely on console logging.

