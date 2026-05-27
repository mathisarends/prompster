from datetime import datetime


class UserMessageQuotaExceededError(Exception):
    def __init__(self, *, limit: int, reset_at: datetime) -> None:
        super().__init__(
            f"Daily agent message limit of {limit} reached. "
            f"Resets at {reset_at.isoformat()}."
        )
        self.limit = limit
        self.reset_at = reset_at
