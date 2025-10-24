/**
 * Core agent loop that talks to OpenRouter, executes yfinance-backed tools,
 * and returns the final assistant reply to any caller.
 *
 * Flow overview:
 *   prompt -> build ChatMessage array -> requestCompletion -> (optional) tool loop -> final answer
 */
import "dotenv/config.js";

import { OPENROUTER_API_KEY_ENV } from "../config/constants.js";
import type { ChatMessage, ToolCall } from "./chatTypes.js";
import { normaliseContent, safeJsonParse } from "./openRouterUtils.js";
import { requestCompletion } from "./requestCompletion.js";
import { systemPrompt } from "./systemPrompt.js";
import { toolExecutors } from "./tooling.js";

const apiKey = process.env[OPENROUTER_API_KEY_ENV];
if (!apiKey) {
  throw new Error(
    `Environment variable ${OPENROUTER_API_KEY_ENV} must be set to call the finance agent.`,
  );
}
const resolvedApiKey = apiKey;

// Main entrypoint: runs the chat loop, wiring model responses to tool executions until completion.
export async function generateFinanceAnswer(prompt: string) {
  const messages: ChatMessage[] = [
    { role: "system", content: systemPrompt },
    { role: "user", content: prompt },
  ];

  while (true) {
    // Send the accumulated transcript to OpenRouter and inspect the top choice.
    const response = await requestCompletion(resolvedApiKey, messages);
    const choice = response.choices?.[0];
    if (!choice) {
      throw new Error("No choices returned from OpenRouter.");
    }

    const assistantMessage = choice.message ?? {};
    const content = normaliseContent(assistantMessage.content);
    const toolCalls = (assistantMessage.tool_calls as ToolCall[]) ?? [];

    messages.push({
      role: "assistant",
      content,
      tool_calls: toolCalls.length ? toolCalls : undefined,
    });

    if (!toolCalls.length) {
      return {
        text: content,
        raw: response,
      };
    }

    for (const call of toolCalls) {
      console.log(
        `[tool] ${call.function?.name ?? "unknown"} args: ${
          call.function?.arguments ?? "{}"
        }`,
      );
      const executor = toolExecutors[call.function?.name ?? ""];
      if (!executor) {
        throw new Error(
          `No executor registered for tool ${call.function?.name}`,
        );
      }
      const args = safeJsonParse(call.function?.arguments);
      const result = await executor(args);
      messages.push({
        role: "tool",
        name: call.function.name,
        content: result,
        tool_call_id: call.id ?? null,
      });
    }
  }
}
