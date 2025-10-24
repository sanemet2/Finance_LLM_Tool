/**
 * Centralised path helpers so every module resolves the project root and
 * bundled Python bridge from a single source of truth.
 */
import path from "node:path";
import { fileURLToPath } from "node:url";
const moduleDir = path.dirname(fileURLToPath(import.meta.url));
export const projectRoot = path.resolve(moduleDir, "..", "..");
export const pythonToolRoot = path.resolve(projectRoot, "python");
export const pythonToolPath = path.resolve(pythonToolRoot, "yfinance_service.py");
