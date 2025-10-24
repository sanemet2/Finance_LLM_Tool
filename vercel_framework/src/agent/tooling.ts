/**
 * Shared tool metadata and executors that bridge OpenRouter tool calls to the
 * underlying yfinance helpers.
 */
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
import { zodToJson } from "./schemaUtils.js";

export const toolDefinitions = [
  {
    type: "function" as const,
    function: {
      name: "download_price_history",
      description:
        "Fetch OHLCV price history for one ticker via yfinance.download. Provide explicit ISO start/end dates when possible.",
      parameters: zodToJson(downloadPriceHistoryInputSchema),
    },
  },
  {
    type: "function" as const,
    function: {
      name: "get_ticker_fast_info",
      description: "Return Yahoo Finance fast_info snapshot for a ticker.",
      parameters: zodToJson(tickerOnlyInputSchema),
    },
  },
  {
    type: "function" as const,
    function: {
      name: "get_ticker_summary",
      description: "Retrieve the Yahoo Finance summary profile for a ticker.",
      parameters: zodToJson(tickerOnlyInputSchema),
    },
  },
  {
    type: "function" as const,
    function: {
      name: "get_ticker_news",
      description: "Fetch recent Yahoo Finance news items for a ticker.",
      parameters: zodToJson(getTickerNewsInputSchema),
    },
  },
  {
    type: "function" as const,
    function: {
      name: "get_ticker_fundamentals",
      description:
        "Return fundamental financial statements (balance sheet, cash flow, etc.) for a ticker.",
      parameters: zodToJson(tickerOnlyInputSchema),
    },
  },
] as const;

export const toolExecutors: Record<string, (input: unknown) => Promise<string>> =
  {
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
