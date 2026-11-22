import logging
from collections.abc import Callable
from typing import Any

from agent.deck import DeckDraftUpdate, DeckStore
from agent.guardrails.views import Guardrail

logger = logging.getLogger(__name__)


class PostRunGuardrails:
    """Deterministic checks applied to the final deck state.

    Runs once the LLM has ended its tool loop, before the assistant
    completion is published, to keep the published deck consistent
    regardless of what the model did.

    The shape mirrors :class:`agent.tools.tools.Tools`: guardrails are
    registered with the :meth:`guardrail` decorator and applied in
    registration order. Adding a new rule is a single decorated function
    in :meth:`_register_default_guardrails` (or via :meth:`register` from
    outside).
    """

    def __init__(self, deck_store: DeckStore) -> None:
        self._deck_store = deck_store
        self._guardrails: list[Guardrail] = []

        self._register_default_guardrails()

    def guardrail(
        self,
        fn: Callable[[DeckStore], Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Callable:
        def decorator(fn: Callable[[DeckStore], Any]) -> Callable[[DeckStore], Any]:
            self.register(
                Guardrail(
                    name=name or fn.__name__,
                    fn=fn,
                    description=description,
                )
            )
            return fn

        return decorator(fn) if fn is not None else decorator

    def register(self, guardrail: Guardrail) -> None:
        self._guardrails.append(guardrail)

    async def run(self) -> list[DeckDraftUpdate]:
        for guardrail in self._guardrails:
            await self._apply(guardrail)
        return self._deck_store.drain_deck_draft_updates()

    async def _apply(self, guardrail: Guardrail) -> None:
        try:
            await guardrail.apply(self._deck_store)
        except Exception:
            # One guardrail failing must not block the others or the completion.
            logger.exception("Post-run guardrail '%s' failed", guardrail.name)

    def _register_default_guardrails(self) -> None:
        @self.guardrail(
            description=(
                "Drop tracks that share a Spotify URI so the published deck "
                "never contains duplicates, even if the model added the same "
                "track twice across tool calls."
            ),
        )
        def remove_duplicate_tracks(store: DeckStore) -> None:
            store.remove_duplicate_tracks()
