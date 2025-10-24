/**
 * Shared TypeScript types that describe the chat transcript exchanged with
 * OpenRouter as well as the tool call payloads the model can emit.
 */
export type ToolCall = {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments?: string;
  };
};

export type ChatMessage =
  | { role: "system"; content: string }
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; tool_calls?: ToolCall[] }
  | {
      role: "tool";
      name: string;
      content: string;
      tool_call_id: string | null;
    };

export type OpenRouterResponsePayload = {
  id: string;
  model: string;
  choices: Array<{
    message?: {
      content?: unknown;
      tool_calls?: ToolCall[];
    };
  }>;
};
