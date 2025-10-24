/**
 * CLI helper that takes a user prompt (argv or interactive prompt) and prints
 * the finance agent's response. Useful for quick manual queries.
 */
import readline from "node:readline";
import { generateFinanceAnswer } from "../agent/financeAgent.js";
async function readPrompt() {
    const [, , ...rest] = process.argv;
    if (rest.length > 0) {
        return rest.join(" ");
    }
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });
    const question = await new Promise((resolve) => {
        rl.question("Enter your finance question: ", (answer) => {
            rl.close();
            resolve(answer.trim());
        });
    });
    if (!question) {
        throw new Error("A prompt is required to query the finance agent.");
    }
    return question;
}
async function run() {
    const prompt = await readPrompt();
    const result = await generateFinanceAnswer(prompt);
    // Show only the natural-language answer; callers can inspect `result.raw` if needed.
    console.log(result.text);
}
run().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
