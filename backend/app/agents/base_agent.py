from abc import ABC, abstractmethod
from typing import Any

from app.models.schemas import AgentStep


class BaseAgent(ABC):
    agent_name: str
    role: str

    @abstractmethod
    def run(self, context: dict[str, Any]) -> AgentStep:
        raise NotImplementedError

    def step(
        self,
        input_summary: str,
        output_summary: str,
        confidence: float,
        evidence_ids: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> AgentStep:
        return AgentStep(
            agent_name=self.agent_name,
            role=self.role,
            input_summary=input_summary,
            output_summary=output_summary,
            status="completed",
            confidence=confidence,
            evidence_ids=evidence_ids or [],
            details=details or {},
        )
