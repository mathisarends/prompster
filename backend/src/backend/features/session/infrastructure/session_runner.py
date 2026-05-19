import json
from collections.abc import AsyncIterator

from agent.agent import (
    Agent,
    AssistantMessageEvent,
    FollowUpRequestedEvent,
    ToolCallEvent,
    ToolResultEvent,
    WorkspaceUpdatedEvent,
)
from agent import MessageManager, Spotify, PlaylistDraft
from agent.tools.views import AskFollowUpQuestion

from llmify import ChatModel
from llmify.messages import ToolCall as LLMToolCall
from spotifyify import Spotifyify

from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerAssistantMessage,
    SessionRunnerEvent,
    SessionRunnerFollowUpRequested,
    SessionRunnerPlaylistUpdated,
    SessionRunnerToolCallCompleted,
    SessionRunnerToolCallStarted,
)
from backend.features.session.domain import (
    AssistantMessage,
    CompletedCall,
    FailedCall,
    FollowUpOption,
    FollowUpQuestion,
    PendingCall,
    Playlist,
    PlaylistTrack,
    Session,
    ToolCall,
    ToolCallGroup,
    ToolFunction,
    UserMessage,
)


class AgentSessionRunner(SessionRunner):
    def __init__(
        self,
        llm: ChatModel,
        spotify: Spotifyify,
        system_prompt: str | None = None,
    ) -> None:
        self._llm = llm
        self._spotify = spotify
        self._system_prompt = system_prompt

    async def run(self, *, session: Session) -> AsyncIterator[SessionRunnerEvent]:
        agent = Agent(
            llm=self._llm,
            messages=_to_message_manager(
                session=session,
                system_prompt=self._system_prompt,
            ),
            spotify=Spotify(client=self._spotify),
        )

        try:
            async for event in agent.continue_stream():
                if isinstance(event, AssistantMessageEvent):
                    yield SessionRunnerAssistantMessage(content=event.content)
                elif isinstance(event, ToolCallEvent):
                    yield SessionRunnerToolCallStarted(
                        call=PendingCall(
                            id=event.tool_call_id,
                            function=ToolFunction(
                                name=event.name,
                                arguments=dict(event.args),
                            ),
                        )
                    )
                elif isinstance(event, ToolResultEvent):
                    yield SessionRunnerToolCallCompleted(
                        tool_call_id=event.tool_call_id,
                        result=event.result,
                    )
                elif isinstance(event, FollowUpRequestedEvent):
                    yield SessionRunnerFollowUpRequested(
                        questions=[
                            _to_follow_up_question(question)
                            for question in event.questions
                        ]
                    )
                elif isinstance(event, WorkspaceUpdatedEvent):
                    yield SessionRunnerPlaylistUpdated(
                        playlist=_to_playlist(event.playlist_draft)
                    )
        finally:
            await agent.close()


def _to_message_manager(
    *,
    session: Session,
    system_prompt: str | None,
) -> MessageManager:
    manager = MessageManager(system_prompt=system_prompt)
    for entry in session.entries:
        if isinstance(entry, UserMessage):
            manager.add_user(entry.content)
        elif isinstance(entry, AssistantMessage):
            manager.add_assistant(entry.content)
        elif isinstance(entry, ToolCallGroup):
            manager.add_assistant(
                "",
                tool_calls=[_to_llm_tool_call(call) for call in entry.calls],
            )
            for call in entry.calls:
                if isinstance(call, CompletedCall):
                    manager.add_tool_result(
                        tool_call_id=call.id,
                        content=call.result,
                    )
                elif isinstance(call, FailedCall):
                    manager.add_tool_result(
                        tool_call_id=call.id,
                        content=call.error,
                    )
    return manager


def _to_llm_tool_call(call: ToolCall) -> LLMToolCall:
    return LLMToolCall(
        id=call.id,
        function={
            "name": call.function.name,
            "arguments": json.dumps(
                call.function.arguments,
                ensure_ascii=False,
            ),
        },
    )


def _to_follow_up_question(question: AskFollowUpQuestion) -> FollowUpQuestion:
    return FollowUpQuestion(
        question=question.question,
        options=[
            FollowUpOption(id=str(index + 1), label=option.label)
            for index, option in enumerate(question.options)
        ],
    )


def _to_playlist(playlist_draft: PlaylistDraft) -> Playlist:
    return Playlist(
        name=playlist_draft.name,
        tracks=[
            PlaylistTrack(
                title=track.title,
                artist=track.artist,
                year=track.year,
                cover_url=track.cover_url,
            )
            for track in playlist_draft.tracks
        ],
    )
