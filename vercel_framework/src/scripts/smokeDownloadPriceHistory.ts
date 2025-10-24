import { downloadPriceHistory } from "../tools/yfinance.js";

async function run() {
  const response = await downloadPriceHistory({
    tickers: "AAPL",
    period: "1mo",
    interval: "1d",
  });

  console.dir(response, { depth: null });
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
