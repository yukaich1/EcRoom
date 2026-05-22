from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from evolving_creative_room.models import AgentRole, CreativeState


@dataclass(slots=True)
class AgentResult:
    role: AgentRole
    summary: str
    state_delta: dict[str, object] = field(default_factory=dict)


class Agent(Protocol):
    role: AgentRole

    def run(self, state: CreativeState) -> AgentResult:
        """Run the agent against the current creative state."""
