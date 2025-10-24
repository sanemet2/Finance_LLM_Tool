/**
 * Thin wrapper around spawning the Python yfinance service. Responsible for
 * serialising payloads, buffering stdout/stderr, and enforcing runtime limits.
 */
import { spawn } from "node:child_process";
import { Buffer } from "node:buffer";
import { TOOL_CALL_TIMEOUT_MS } from "../config/constants.js";
export async function runPythonModule(modulePath, payload, options = {}) {
    const { args = [], cwd, timeoutMs = TOOL_CALL_TIMEOUT_MS, pythonPath = "python", } = options;
    return new Promise((resolve, reject) => {
        const child = spawn(pythonPath, [modulePath, ...args], {
            cwd,
            stdio: ["pipe", "pipe", "pipe"],
        });
        const stdoutChunks = [];
        const stderrChunks = [];
        // Accumulate stdout/stderr so we can surface detailed errors/captured data.
        child.stdout?.on("data", (chunk) => {
            stdoutChunks.push(chunk);
        });
        child.stderr?.on("data", (chunk) => {
            stderrChunks.push(chunk);
        });
        child.once("error", (error) => {
            clearTimeout(timeout);
            reject(error);
        });
        const timeout = setTimeout(() => {
            // Kill runaway processes so the agent loop cannot hang indefinitely.
            child.kill("SIGTERM");
            reject(new Error(`Python process timed out after ${timeoutMs}ms`));
        }, timeoutMs);
        if (!child.stdin) {
            clearTimeout(timeout);
            child.kill("SIGTERM");
            reject(new Error("Failed to open stdin for python process"));
            return;
        }
        child.stdin.write(JSON.stringify(payload));
        child.stdin.end();
        child.once("close", (code, signal) => {
            clearTimeout(timeout);
            const stdout = Buffer.concat(stdoutChunks).toString("utf-8");
            const stderr = Buffer.concat(stderrChunks).toString("utf-8");
            if (code !== 0) {
                const errorMessage = [
                    `Python exited with code ${code ?? "null"}`,
                    signal ? `(signal ${signal})` : "",
                    stdout ? `stdout: ${stdout.trim()}` : "",
                    stderr ? `stderr: ${stderr.trim()}` : "",
                ]
                    .filter(Boolean)
                    .join(" ");
                reject(new Error(errorMessage));
                return;
            }
            resolve({
                stdout,
                stderr,
            });
        });
    });
}
