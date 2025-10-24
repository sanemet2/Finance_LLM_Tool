import { spawn } from "node:child_process";
import { Buffer } from "node:buffer";

import { TOOL_CALL_TIMEOUT_MS } from "../config/constants.js";

export interface PythonInvocationOptions {
  readonly args?: ReadonlyArray<string>;
  readonly cwd?: string;
  readonly timeoutMs?: number;
  readonly pythonPath?: string;
}

export interface PythonInvocationResult {
  readonly stdout: string;
  readonly stderr: string;
}

export async function runPythonModule(
  modulePath: string,
  payload: unknown,
  options: PythonInvocationOptions = {},
): Promise<PythonInvocationResult> {
  const {
    args = [],
    cwd,
    timeoutMs = TOOL_CALL_TIMEOUT_MS,
    pythonPath = "python",
  } = options;

  return new Promise<PythonInvocationResult>((resolve, reject) => {
    const child = spawn(pythonPath, [modulePath, ...args], {
      cwd,
      stdio: ["pipe", "pipe", "pipe"],
    });

    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];

    child.stdout?.on("data", (chunk: Buffer) => {
      stdoutChunks.push(chunk);
    });

    child.stderr?.on("data", (chunk: Buffer) => {
      stderrChunks.push(chunk);
    });

    child.once("error", (error) => {
      clearTimeout(timeout);
      reject(error);
    });

    const timeout = setTimeout(() => {
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
