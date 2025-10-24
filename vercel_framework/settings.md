# Current Integration Settings

- **Model Provider**: OpenRouter `openai/gpt-4.1-mini` accessed via direct REST calls to `/chat/completions`.
- **Tool Execution Strategy**: spawn a Python process per tool call invoking yfinance_service.py with JSON arguments.
- **Tool Schemas**: strict Zod definitions mirroring the existing Python input contracts; preserve the {ok,result|error} response envelope.
- **Telemetry**: Vercel SDK telemetry disabled; rely on console logging around tool execution.
