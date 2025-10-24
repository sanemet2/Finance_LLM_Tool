/**
 * Makes a single OpenRouter `/chat/completions` call and returns the parsed
 * JSON response. The caller supplies the API key and current chat transcript.
 */
import { MODEL_NAME, OPENROUTER_BASE_URL } from "../config/constants.js";
import { toolDefinitions } from "./tooling.js";
export async function requestCompletion(apiKey, messages) {
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
        throw new Error(`OpenRouter request failed (${response.status} ${response.statusText}): ${text}`);
    }
    return (await response.json());
}
