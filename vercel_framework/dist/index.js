/**
 * CLI/demo entrypoint that exercises the finance agent once with a canned prompt.
 * Keeps the example synchronous via async/await so errors bubble up cleanly.
 */
import { generateFinanceAnswer } from "./agent/financeAgent.js";
async function main() {
    // Sample question that drives the entire agent/toolchain pipeline.
    const result = await generateFinanceAnswer("Provide a quick market update for AAPL over the last month.");
    console.log(result.text);
}
main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
