from llm import Usage

from agent.tokens.views import TokenUsageEntry, UsageSummary


class TokenTracker:
    def __init__(self) -> None:
        self._entries: list[TokenUsageEntry] = []

    def add(self, usage: Usage | None, model: str) -> None:
        if usage is None:
            return

        self._entries.append(
            TokenUsageEntry(
                model=model,
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                prompt_cached_tokens=usage.cache_read_tokens,
            )
        )

    def reset(self) -> None:
        self._entries = []

    @property
    def total_tokens(self) -> int:
        return sum(e.total_tokens for e in self._entries)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> list[TokenUsageEntry]:
        return list(self._entries)

    def summary(self) -> UsageSummary:
        return UsageSummary(
            total_tokens=sum(e.total_tokens for e in self._entries),
            total_prompt_tokens=sum(e.prompt_tokens for e in self._entries),
            total_completion_tokens=sum(e.completion_tokens for e in self._entries),
            total_prompt_cached_tokens=sum(
                e.prompt_cached_tokens or 0 for e in self._entries
            ),
        )
