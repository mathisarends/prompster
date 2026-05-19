from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class AgentResult:
    output: str
    finish_reason: Literal["done", "max_iterations_reached"]
    total_tokens: int = 0


@dataclass(frozen=True, slots=True)
class StepResult:
    done: bool
    output: str = ""
