import path from "node:path";
import { fileURLToPath } from "node:url";

const moduleDir = path.dirname(fileURLToPath(import.meta.url));

export const projectRoot = path.resolve(moduleDir, "..", "..");
export const pythonToolRoot = path.resolve(projectRoot, "python");
export const pythonToolPath = path.resolve(pythonToolRoot, "yfinance_service.py");
