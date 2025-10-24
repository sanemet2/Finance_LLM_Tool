
import "dotenv/config.js";

import { z } from "zod";

import {
  downloadPriceHistory,
  downloadPriceHistoryInputSchema,
  getTickerFastInfo,
  getTickerFundamentals,
  getTickerNews,
  getTickerNewsInputSchema,
  getTickerSummary,
  tickerOnlyInputSchema,
} from "../tools/yfinance.js";
import {
  MODEL_NAME,
  OPENROUTER_API_KEY_ENV,
  OPENROUTER_BASE_URL,
} from "../config/constants.js";

const apiKey = process.env[OPENROUTER_API_KEY_ENV];
if (!apiKey) {
  throw new Error(
    `Environment variable ${OPENROUTER_API_KEY_ENV} must be set to call the finance agent.`,
  );
}

type ToolCall = {
  id: string;
  type: "function";
  function: {
    name: string;
    arguments?: string;
  };
};

type ChatMessage =
  | { role: "system"; content: string }
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; tool_calls?: ToolCall[] }
  | {
      role: "tool";
      name: string;
      content: string;
      tool_call_id: string | null;
    };

const toolDefinitions = [
  {
    type: "function",
    function: {
      name: "download_price_history",
      description:
        "Fetch OHLCV price history for one ticker via yfinance.download.",
      parameters: zodToJson(downloadPriceHistoryInputSchema),
    },
  },
  {
    type: "function",
    function: {
      name: "get_ticker_fast_info",
      description: "Return Yahoo Finance fast_info snapshot for a ticker.",
      parameters: zodToJson(tickerOnlyInputSchema),
    },
  },
  {
    type: "function",
    function: {
      name: "get_ticker_summary",
      description: "Retrieve the Yahoo Finance summary profile for a ticker.",
      parameters: zodToJson(tickerOnlyInputSchema),
    },
  },
  {
    type: "function",
    function: {
      name: "get_ticker_news",
      description: "Fetch recent Yahoo Finance news items for a ticker.",
      parameters: zodToJson(getTickerNewsInputSchema),
    },
  },
  {
    type: "function",
    function: {
      name: "get_ticker_fundamentals",
      description:
        "Return fundamental financial statements (balance sheet, cash flow, etc.) for a ticker.",
      parameters: zodToJson(tickerOnlyInputSchema),
    },
  },
] as const;

const toolExecutors: Record<
  string,
  (input: unknown) => Promise<string>
> = {
  download_price_history: async (input) =>
    JSON.stringify(await downloadPriceHistory(input)),
  get_ticker_fast_info: async (input) =>
    JSON.stringify(await getTickerFastInfo(input)),
  get_ticker_summary: async (input) =>
    JSON.stringify(await getTickerSummary(input)),
  get_ticker_news: async (input) =>
    JSON.stringify(await getTickerNews(input)),
  get_ticker_fundamentals: async (input) =>
    JSON.stringify(await getTickerFundamentals(input)),
};

export async function generateFinanceAnswer(prompt: string) {
  const messages: ChatMessage[] = [
    { role: "system", content: systemPrompt },
    { role: "user", content: prompt },
  ];

  while (true) {
    const response = await requestCompletion(messages);
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
      throw new Error(`No executor registered for tool ${call.function?.name}`);
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

const systemPrompt =
  "You are a finance assistant. Provide concise market context and only call tools when the user explicitly asks for specific data points. Prefer summarising using high-level trends over fetching ticker-by-ticker statistics unless a detailed lookup is necessary.";

async function requestCompletion(messages: ChatMessage[]) {
  const response = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: MODEL_NAME,
      messages,
      tools: toolDefinitions,
      tool_choice: "auto",
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `OpenRouter request failed (${response.status} ${response.statusText}): ${text}`,
    );
  }

  return (await response.json()) as OpenRouterResponsePayload;
}

function normaliseContent(content: unknown): string {
  if (typeof content === "string") {
    return content;
  }
  if (!content) {
    return "";
  }
  if (Array.isArray(content)) {
    return content
      .map((chunk) => {
        if (typeof chunk === "string") {
          return chunk;
        }
        if (chunk && typeof chunk === "object" && "text" in chunk) {
          return String((chunk as { text?: unknown }).text ?? "");
        }
        return "";
      })
      .filter(Boolean)
      .join("");
  }
  if (typeof content === "object" && "text" in content) {
    return String((content as { text?: unknown }).text ?? "");
  }
  return String(content);
}

function safeJsonParse(value: string | undefined): unknown {
  if (!value) {
    return {};
  }
  try {
    return JSON.parse(value);
  } catch (error) {
    throw new Error(`Failed to parse tool arguments: ${value}`, { cause: error });
  }
}

function zodToJson(schema: z.ZodTypeAny) {
  const jsonSchema = schemaToOpenAPI(schema);
  return {
    type: "object",
    ...jsonSchema,
  };
}

function schemaToOpenAPI(schema: z.ZodTypeAny): Record<string, unknown> {
  if (schema instanceof z.ZodObject) {
    const shape = schema.shape;
    const properties: Record<string, unknown> = {};
    const required: string[] = [];
    for (const [key, value] of Object.entries(shape)) {
      properties[key] = schemaToOpenAPI(value);
      if (!(value.isOptional() || value.isNullable())) {
        required.push(key);
      }
    }
    return {
      type: "object",
      properties,
      ...(required.length ? { required } : {}),
    };
  }
  if (schema instanceof z.ZodString) {
    const checks = (schema as any)._def.checks ?? [];
    const enums = checks.find((check: any) => check.kind === "enum");
    return {
      type: "string",
      ...(enums ? { enum: enums.values } : {}),
    };
  }
  if (schema instanceof z.ZodBoolean) {
    return { type: "boolean" };
  }
  if (schema instanceof z.ZodNumber) {
    const def = (schema as any)._def;
    const result: Record<string, unknown> = { type: "number" };
    if (def.checks) {
      for (const check of def.checks) {
        if (check.kind === "min") {
          result.minimum = check.value;
        }
        if (check.kind === "max") {
          result.maximum = check.value;
        }
        if (check.kind === "int") {
          result.type = "integer";
        }
      }
    }
    return result;
  }
  if (schema instanceof z.ZodNullable) {
    return {
      anyOf: [schemaToOpenAPI(schema.unwrap()), { type: "null" }],
    };
  }
  if (schema instanceof z.ZodOptional) {
    return schemaToOpenAPI(schema.unwrap());
  }
  return {};
}

type OpenRouterResponsePayload = {
  id: string;
  model: string;
  choices: Array<{
    message?: {
      content?: unknown;
      tool_calls?: ToolCall[];
    };
  }>;
};
