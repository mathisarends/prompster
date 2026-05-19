from dataclasses import dataclass, field

import time
import uuid
from typing import Any


@dataclass(kw_only=True)
class Event:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)


@dataclass(kw_only=True)
class RunStartedEvent(Event):
    message: str


@dataclass(kw_only=True)
class StepStartedEvent(Event):
    step: int


@dataclass(kw_only=True)
class ToolStatusEvent(Event):
    message: str


@dataclass(kw_only=True)
class RunCompletedEvent(Event):
    result: Any
