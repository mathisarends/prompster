from enum import StrEnum


class Phase(StrEnum):
    ONBOARDING = "onboarding"
    BUILD = "build"


class RunStatus(StrEnum):
    """What a running agent turn is doing, as far as the user can tell."""

    RUNNING = "running"
    PAUSED = "paused"
    COMPACTING = "compacting"
