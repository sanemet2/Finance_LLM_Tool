"""Minimal OpenRouter-backed orchestrator agent."""

from __future__ import annotations

import os
from time import perf_counter
from typing import Final

from dotenv import load_dotenv
from pydantic_ai import Agent, AgentRunResult, ModelMessage

from analytics import ToolMetrics, log_turn_metrics
from toolbox import build_toolbox

ENV_PATH: Final[str] = os.fspath(os.path.join(os.path.dirname(__file__), '.env'))

# Core Concepts 6.A
load_dotenv(ENV_PATH)

# See pydantic-ai/docs/models/openai.md:390 for the provider:model format.
OPENROUTER_MODEL: Final[str] = os.environ.get(
    'OPENROUTER_MODEL',
    'openrouter:openai/gpt-4o-mini',
)

SYSTEM_PROMPT: Final[str] = (
    'Answer in a concise and accurate manner based on the user prompt'
    ' and call out when more data is required. When the user asks about current events, breaking news, '
    'or anything you cannot answer from memory, call the `duckduckgo_search` tool to gather fresh facts.' 
    ' Use the `python_exec` tool to perform calculations or run code snippets as needed. If asked for any kind of calculation use this. '
)
class OrchestratorRunner:
    """Coordinate agent execution, memory, and analytics logging."""

    # Parameters in the parantheses are constructors, they are parameters we can supply when creating an instance. 
    def __init__(
        self,
        *,
        model: str = OPENROUTER_MODEL,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        # Core Concepts 1.III.A-D, 4.A
        self._tool_metrics = ToolMetrics()

        def record_tool_duration(tool_name: str, duration_ms: float) -> None:
            self._tool_metrics.record(tool_name, duration_ms)

        self._agent: Agent[None, str] = Agent(
            model,
            system_prompt=system_prompt,
            output_type=str,
            tools=build_toolbox(record_tool_duration),  # <-- added
        )
        # This creates a single conversation history per runner instance.
        self._conversation_history: list[ModelMessage] = []

    def run(self, user_input: str) -> str:
        """Execute the orchestrator turn and return the model output."""
        total_start = perf_counter()
        self._require_api_key()
        self._tool_metrics.reset()

        prep_end = perf_counter()
        result = self._agent.run_sync(
            user_input,
            message_history=self._conversation_history,
        )
        model_end = perf_counter()

        # Core Concepts 5.II.A keeps multi-turn continuity.
        self._conversation_history.extend(result.new_messages())
        total_end = perf_counter()

        self._log_metrics(
            prompt=user_input,
            total_start=total_start,
            prep_end=prep_end,
            model_end=model_end,
            total_end=total_end,
            result=result,
        )
        return result.output

    def _require_api_key(self) -> None:
        # Core Concepts 1.IV.A, 1.V.A-C
        if 'OPENROUTER_API_KEY' not in os.environ:
            msg = 'OPENROUTER_API_KEY must be exported before calling the orchestrator agent.'
            raise RuntimeError(msg)

    def _log_metrics(
        self,
        *,
        prompt: str,
        total_start: float,
        prep_end: float,
            model_end: float,
            total_end: float,
            result: AgentRunResult[str],
        ) -> None:
        usage = result.usage()
        log_turn_metrics(
            prompt=prompt,
            total_start=total_start,
            prep_end=prep_end,
            model_end=model_end,
            total_end=total_end,
            usage=usage,
            tool_ms=self._tool_metrics.total_ms,
            tool_calls=self._tool_metrics.total_calls,
            tool_details={
                'sequence': self._tool_metrics.call_sequence.copy(),
                'per_tool_ms': self._tool_metrics.per_tool_ms.copy(),
                'per_tool_calls': self._tool_metrics.per_tool_calls.copy(),
            },
        )


runner = OrchestratorRunner()


if __name__ == '__main__':
    print('Type your finance prompt or /quit to exit.')
    while True:
        # Core Concepts 1.V.A keeps user text as the primary run input.
        prompt = input('Enter orchestrator prompt: ').strip()
        if not prompt:
            print('Please enter a non-empty prompt.')
            continue

        lowered = prompt.lower()
        if lowered in {'/quit', '/exit'}:
            break

        try:
            output = runner.run(prompt)
        except RuntimeError as exc:
            print(f'Error: {exc}')
            break

        print(f'Agent: {output}\n')
