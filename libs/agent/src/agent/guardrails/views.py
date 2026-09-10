import inspect
from collections.abc import Callable
from typing import Any

from agent.deck import DeckStore


class Guardrail:
    """A single deterministic check applied to the final deck state.

    Mirrors :class:`agent.tools.views.Tool`: a named, self-describing unit
    that the :class:`PostRunGuardrails` registry knows how to run. The
    callable receives the :class:`DeckStore` and mutates it in place; any
    resulting changes are surfaced via the store's pending updates, so a
    guardrail never returns events itself. Sync and async callables are
    both supported.
    """

    def __init__(
        self,
        name: str,
        fn: Callable[[DeckStore], Any],
        description: str | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self._fn = fn

    async def apply(self, store: DeckStore) -> None:
        result = self._fn(store)
        if inspect.isawaitable(result):
            await result

    def __eq__(self, other: object) -> bool:
        return (
            self.name == other.name if isinstance(other, Guardrail) else NotImplemented
        )

    def __hash__(self) -> int:
        return hash(self.name)
