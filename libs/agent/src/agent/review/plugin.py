from pathlib import Path

from harnessed import Inject, Plugin, SystemPrompt, ToolContext, needs, tool
from harnessed.models import Model

from agent.deck import DeckStore
from agent.prompts import read_prompt
from agent.review.critic import DeckCritic
from agent.review.transcript import conversation_transcript

_REVIEW_TIMEOUT_SECONDS = 180.0


class ReviewPlugin(Plugin):
    """Let the agent check its deck for artist and era balance."""

    model = needs(Model)

    def __init__(self, store: DeckStore) -> None:
        super().__init__()
        self._store = store

    def instructions(self) -> SystemPrompt:
        return SystemPrompt(read_prompt(Path(__file__).with_name("prompt.md")))

    @tool(
        description=(
            "Check the Hitster deck for artist and era balance near the end of a "
            "build. Returns concrete issues to fix with the deck tools."
        ),
        readonly=True,
        timeout_seconds=_REVIEW_TIMEOUT_SECONDS,
    )
    async def review_deck(self, *, ctx: Inject[ToolContext]) -> str:
        critic = DeckCritic(self.model, target_size=self._store.max_tracks)
        review = await critic.review(
            self._store.deck, brief=conversation_transcript(ctx.log.messages)
        )
        return review.content
