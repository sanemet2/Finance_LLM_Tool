/**
 * TypeScript facade for the Python yfinance service. Validates tool inputs with
 * Zod, invokes the bridge, and re-parses the `{ok|error}` envelope so callers
 * receive structured results.
 */
import { z } from "zod";
import { runPythonModule } from "./pythonBridge.js";
import { pythonToolPath, pythonToolRoot } from "../config/paths.js";
const PERIOD_CHOICES = [
    "1d",
    "5d",
    "1mo",
    "3mo",
    "6mo",
    "1y",
    "2y",
    "5y",
    "10y",
    "ytd",
    "max",
];
const INTERVAL_CHOICES = [
    "1m",
    "2m",
    "5m",
    "15m",
    "30m",
    "60m",
    "90m",
    "1h",
    "1d",
    "5d",
    "7d",
    "1wk",
    "1mo",
    "3mo",
];
export const downloadPriceHistoryInputSchema = z.object({
    tickers: z.string(),
    period: z.enum(PERIOD_CHOICES).optional(),
    interval: z.enum(INTERVAL_CHOICES).optional(),
    start: z.string().optional().nullable(),
    end: z.string().optional().nullable(),
    actions: z.boolean().optional(),
    auto_adjust: z.boolean().optional().nullable(),
    prepost: z.boolean().optional(),
});
export const tickerOnlyInputSchema = z.object({
    ticker: z.string(),
});
export const getTickerNewsInputSchema = z.object({
    ticker: z.string(),
    count: z.number().int().positive().max(50).optional(),
});
const ALL_OPERATION_SCHEMAS = {
    download_price_history: downloadPriceHistoryInputSchema,
    get_ticker_fast_info: tickerOnlyInputSchema,
    get_ticker_summary: tickerOnlyInputSchema,
    get_ticker_news: getTickerNewsInputSchema,
    get_ticker_fundamentals: tickerOnlyInputSchema,
};
const responseSchema = z
    .object({
    ok: z.literal(true),
    operation: z.string(),
    data: z.unknown(),
})
    .transform((value) => ({
    ok: true,
    operation: value.operation,
    data: value.data,
}))
    .or(z.object({
    ok: z.literal(false),
    operation: z.string().nullable(),
    error: z.object({
        type: z.string(),
        message: z.string(),
    }),
}));
export async function invokeYFinanceOperation(operation, input) {
    const schema = ALL_OPERATION_SCHEMAS[operation];
    const params = schema.parse(input);
    const { stdout } = await runPythonModule(pythonToolPath, { operation, params }, {
        // Ensure relative imports/files inside the Python project resolve
        // exactly as they do when running from the command line.
        cwd: pythonToolRoot,
    });
    let parsed;
    try {
        parsed = JSON.parse(stdout);
    }
    catch (error) {
        throw new Error(`Failed to parse yfinance response: ${stdout}`, {
            cause: error,
        });
    }
    return responseSchema.parse(parsed);
}
export async function downloadPriceHistory(input) {
    return invokeYFinanceOperation("download_price_history", input);
}
export async function getTickerFastInfo(input) {
    return invokeYFinanceOperation("get_ticker_fast_info", input);
}
export async function getTickerSummary(input) {
    return invokeYFinanceOperation("get_ticker_summary", input);
}
export async function getTickerNews(input) {
    return invokeYFinanceOperation("get_ticker_news", input);
}
export async function getTickerFundamentals(input) {
    return invokeYFinanceOperation("get_ticker_fundamentals", input);
}
