from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class UserMessageRateLimitPolicy:
    daily_message_limit: int
    window: timedelta = timedelta(hours=24)

    def __post_init__(self) -> None:
        if self.daily_message_limit <= 0:
            raise ValueError("daily_message_limit must be positive")
