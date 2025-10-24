/**
 * Shared runtime constants so the agent, tools, and scripts agree on model
 * selection, API location, and default timeout behaviour.
 */
export const MODEL_NAME = "openai/gpt-4.1-mini";
export const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";
export const OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY";
export const TOOL_CALL_TIMEOUT_MS = 15_000;
