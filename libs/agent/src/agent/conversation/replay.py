from dataclasses import replace

from harnessed import Plugin, hook, needs
from harnessed.hooks import Next, PrepareRequest
from harnessed.models import AssistantMessage, Message, Model, ModelInfo, ModelRequest


class ProviderReplayGuard(Plugin):
    """Let a conversation continue on another model.

    Providers sign their responses for replay to the same model. When the user
    switches models, earlier replies are sent as plain text instead.
    """

    model = needs(Model)

    @hook(PrepareRequest)
    async def drop_foreign_replay_state(
        self,
        _event: PrepareRequest,
        next_: Next[ModelRequest],
    ) -> ModelRequest:
        request = await next_()
        info = self.model.info
        messages = tuple(_portable(message, info) for message in request.messages)
        return replace(request, messages=messages)


def _portable(message: Message, info: ModelInfo) -> Message:
    if not isinstance(message, AssistantMessage) or message.provider_state is None:
        return message
    state = message.provider_state
    if state.provider == info.provider and state.model == info.name:
        return message
    return replace(message, provider_state=None)
