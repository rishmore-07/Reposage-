"""
app/ai/agents/base_agent.py

Abstract interface for all LangGraph agents.

Why this exists before any AI implementation:
- Forces all future agents to conform to the same interface
- Makes agents testable (mock the abstract class in tests)
- Enables the factory pattern: config flag selects the implementation
- Prevents AI code from bleeding into services/repositories

Implement concrete agents in sibling files (e.g., pr_review_agent.py)
extending this class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Abstract base class for all RepoSage LangGraph agents.

    An agent is a stateful, multi-step reasoning process that:
    1. Receives a task (AgentInput)
    2. Plans and executes steps using tools
    3. Returns a result (AgentOutput)
    """

    @abstractmethod
    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the agent's reasoning loop.

        Args:
            input_data: Typed dict containing all inputs the agent needs.
                        Structure is defined by each concrete implementation.

        Returns:
            Typed dict containing the agent's output.
            Structure is defined by each concrete implementation.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify that all external dependencies (LLM APIs, tools) are reachable.

        Returns:
            True if all dependencies are healthy.
        """
