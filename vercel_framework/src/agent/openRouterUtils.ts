/**
 * Utility helpers for working with OpenRouter responses and tool arguments.
 */
export function normaliseContent(content: unknown): string {
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

export function safeJsonParse(value: string | undefined): unknown {
  if (!value) {
    return {};
  }
  try {
    return JSON.parse(value);
  } catch (error) {
    throw new Error(`Failed to parse tool arguments: ${value}`, { cause: error });
  }
}
