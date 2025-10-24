import readline from "node:readline";

import { generateFinanceAnswer } from "../agent/financeAgent.js";

async function readPrompt(): Promise<string> {
  const [, , ...rest] = process.argv;
  if (rest.length > 0) {
    return rest.join(" ");
  }

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const question = await new Promise<string>((resolve) => {
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

  console.log(result.text);
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
