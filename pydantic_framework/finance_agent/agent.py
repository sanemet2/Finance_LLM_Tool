"""Agent construction and high-level helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai.settings import ModelSettings

from .config import Settings, load_settings
from .dependencies import FinanceDependencies, build_dependencies
from .prompts import SYSTEM_PROMPT
from .tools import attach_finance_tools


class FinanceAnswer(BaseModel):
    """Structured output returned by the finance agent."""

    text: str = Field(..., description="Human-readable answer for the caller.")


@dataclass(slots=True)
class FinanceAgentRunner:
    """Convenience wrapper bundling the agent instance with its dependencies."""

    agent: Agent[FinanceDependencies, Any]
    deps: FinanceDependencies

    async def run(self, prompt: str) -> Any:
        """Execute the agent with the configured dependencies."""

        return await self.agent.run(prompt, deps=self.deps)


def build_agent(
    settings: Optional[Settings] = None,
    deps: Optional[FinanceDependencies] = None,
) -> FinanceAgentRunner:
    """Construct the finance agent and register all tools."""

    resolved_settings = settings or load_settings()
    provider = OpenRouterProvider(api_key=resolved_settings.openrouter_api_key)
    model_settings: ModelSettings | None = None
    settings_payload: dict[str, object] = {}
    if resolved_settings.max_output_tokens is not None:
        settings_payload["max_tokens"] = resolved_settings.max_output_tokens
    if resolved_settings.temperature is not None:
        settings_payload["temperature"] = resolved_settings.temperature
    if settings_payload:
        model_settings = ModelSettings(**settings_payload)

    model = OpenAIChatModel(
        resolved_settings.model_name,
        provider=provider,
        settings=model_settings,
    )

    agent = Agent(
        model,
        deps_type=FinanceDependencies,
        system_prompt=SYSTEM_PROMPT,
    )
    attach_finance_tools(agent)

    resolved_deps = deps or build_dependencies()
    return FinanceAgentRunner(agent=agent, deps=resolved_deps)


async def run_finance_agent(prompt: str, settings: Optional[Settings] = None) -> FinanceAnswer:
    """One-shot helper mirroring the legacy generateFinanceAnswer function."""

    runner = build_agent(settings=settings)
    result = await runner.run(prompt)
    return result.output
