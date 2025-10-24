# Usage Notes

1. Install dependencies (once):
   ```bash
   cd "vercel framework"
   npm install
   ```
2. Create `.env` with your OpenRouter key (example already checked in):
   ```bash
   echo "OPENROUTER_API_KEY=sk-or-..." > .env
   ```
   Replace `sk-or-...` with your actual key. The `dev` script auto-loads this file.
3. Run the Python bridge smoke test (no LLM call):
   ```bash
   npm run smoke:python
   ```
   This executes `src/scripts/smokeDownloadPriceHistory.ts` and prints the `{ok,result|error}` payload returned from the bundled yfinance tool.
4. Ask an ad-hoc question through the agent:
   ```bash
   npm run ask -- "How did MSFT trade last week?"
   ```
   If you omit the trailing prompt the script will interactively ask for it.
5. Run the sample agent execution:
   ```bash
   npm run dev
   ```
   This executes `src/index.ts`, which calls `financeAgent.generate` with a sample prompt.
6. To invoke other yfinance helpers directly, import from `src/tools/yfinance.ts` and run them via `tsx` or reuse them inside other tools.

## Environment Expectations
- Python must be available on `PATH`; the adapter shells out to `yfinance_service.py`.
- The Python bridge is bundled in `./python/yfinance_service.py`, so no external checkout is required.
- Set `OPENROUTER_API_KEY` (either via `.env` or environment) so the agent can call the OpenRouter Responses API.

## Next Steps
- Add automated tests with `vitest`, mocking the Python bridge or using canned fixtures.
- Implement an HTTP handler (e.g., Next.js App Router route) using `createAgentUIStreamResponse`.
- Extend logging/telemetry once the integration stabilises.
