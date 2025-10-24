import { generateFinanceAnswer } from "./agent/financeAgent.js";

async function main() {
  const result = await generateFinanceAnswer(
    "Provide a quick market update for AAPL over the last month.",
  );
  console.log(result.text);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
