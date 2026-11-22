from harnessed import Inject, Plugin, SystemPrompt, ToolContext, tool

from agent.messages import conversation_transcript, load_prompt
from agent.plugins.run_context import AgentRunContext

_REVIEW_TIMEOUT_SECONDS = 180.0


class ReviewPlugin(Plugin):
    """Let the agent check its deck for artist and era balance."""

    def __init__(self, run: AgentRunContext) -> None:
        super().__init__()
        self._run = run

    def instructions(self) -> SystemPrompt:
        return SystemPrompt(load_prompt("review"))

    @tool(
        description=(
            "Check the Hitster deck for artist and era balance near the end of a "
            "build. Returns concrete issues to fix with the deck tools."
        ),
        readonly=True,
        timeout_seconds=_REVIEW_TIMEOUT_SECONDS,
    )
    async def review_deck(self, *, ctx: Inject[ToolContext]) -> str:
        brief = conversation_transcript(ctx.log.messages)
        result = await self._run.critic.review(brief=brief)
        return result.content
