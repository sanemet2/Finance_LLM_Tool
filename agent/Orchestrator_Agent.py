"""Minimal OpenRouter-backed orchestrator agent."""

from __future__ import annotations

import os
from time import perf_counter
from typing import Final, List

from dotenv import load_dotenv
from pydantic_ai import Agent, ModelMessage

from analytics import TimingSample, record, utc_timestamp

ENV_PATH: Final[str] = os.fspath(os.path.join(os.path.dirname(__file__), '.env'))

# Core Concepts 6.A
load_dotenv(ENV_PATH)

# See pydantic-ai/docs/models/openai.md:390 for the provider:model format.
OPENROUTER_MODEL: Final[str] = os.environ.get(
    'OPENROUTER_MODEL',
    'openrouter:openai/gpt-5-mini',
)

SYSTEM_PROMPT: Final[str] = (
    'You are a concise finance orchestrator. Provide clear, two-sentence answers '
    'and call out when more data is required.'
)

# Core Concepts 1.III.A-D, 4.A
orchestrator_agent: Agent[None, str] = Agent(
    OPENROUTER_MODEL,
    system_prompt=SYSTEM_PROMPT,
    output_type=str,
)

# This will create one version of memory, if two LLMS access it simultaneously they will overwrite each other.
conversation_history: List[ModelMessage] = []

def run_orchestrator_turn(user_input: str) -> str:
    """Execute the minimal agent synchronously and return the model output."""
    total_start = perf_counter()

    # Core Concepts 1.IV.A, 1.V.A-C
    if 'OPENROUTER_API_KEY' not in os.environ:
        msg = 'OPENROUTER_API_KEY must be exported before calling the orchestrator agent.'
        raise RuntimeError(msg)

    prep_end = perf_counter()
    result = orchestrator_agent.run_sync(
        user_input,
        message_history=conversation_history,
    )
    model_end = perf_counter()

    # Extend the conversation with new messages for continuity.
    conversation_history.extend(result.new_messages())
    total_end = perf_counter()

    record(
        TimingSample(
            ts=utc_timestamp(),
            prompt=user_input,
            prep_ms=(prep_end - total_start) * 1_000,
            model_ms=(model_end - prep_end) * 1_000,
            post_ms=(total_end - model_end) * 1_000,
            total_ms=(total_end - total_start) * 1_000,
            tokens_in=result.usage().input_tokens,
            tokens_out=result.usage().output_tokens,
        )
    )

    return result.output


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

        # Core Concepts 5.II.A passes message history to maintain continuity.
        try:
            output = run_orchestrator_turn(prompt)
        except RuntimeError as exc:
            print(f'Error: {exc}')
            break

        print(f'Agent: {output}\n')
