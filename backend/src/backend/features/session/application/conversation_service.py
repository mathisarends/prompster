import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from backend.features.session.application.events import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionEvent,
    SessionFollowUpGroupAdded,
    SessionPlaylistSet,
    SessionToolCallGroupAdded,
    SessionToolCallGroupCompleted,
    SessionToolCallResolved,
)
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerFollowUpRequested,
    SessionRunnerPlaylistUpdated,
    SessionRunnerToolCallCompleted,
    SessionRunnerToolCallStarted,
)
from backend.features.session.domain import (
    AssistantMessage,
    FollowUpQuestionGroup,
    NoPendingToolCallGroupError,
    Session,
    SessionRepository,
    ToolCallGroup,
)


@dataclass(frozen=True)
class FollowUpAnswer:
    question_id: UUID
    option_id: str | None
    text: str | None


@dataclass(frozen=True)
class _ResolvedToolCall:
    group_id: UUID
    tool_call_id: str
    result: str
    group_completed: bool


class SessionConversationService:
    def __init__(
        self,
        session_repository: SessionRepository,
        runner: SessionRunner,
    ) -> None:
        self._session_repository = session_repository
        self._runner = runner

    async def send_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        content: str,
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        resolved_tool_call = self._prepare_follow_up_context_for_message(
            session=session
        )
        session.add_user_message(content=content)
        await self._session_repository.save(session=session)
        for event in self._to_tool_call_resolution_events(resolved_tool_call):
            yield event
        async for event in self._run_agent(session=session):
            yield event

    async def answer_follow_ups(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        answers: list[FollowUpAnswer],
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        pending_group = session.require_pending_follow_up_group()
        for answer in answers:
            if answer.option_id is not None:
                session.answer_follow_up_with_option(
                    question_id=answer.question_id,
                    option_id=answer.option_id,
                )
            else:
                session.answer_follow_up_with_text(
                    question_id=answer.question_id,
                    text=answer.text or "",
                )
        if not pending_group.is_complete:
            await self._session_repository.save(session=session)
            return

        resolved_tool_call = self._resolve_pending_tool_call(
            session=session,
            result=self._serialize_follow_up_answers(pending_group),
        )
        await self._session_repository.save(session=session)
        for event in self._to_tool_call_resolution_events(resolved_tool_call):
            yield event
        async for event in self._run_agent(session=session):
            yield event

    async def skip_remaining_follow_ups(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        pending_group = session.require_pending_follow_up_group()
        resolved_tool_call = self._skip_remaining_follow_ups(
            session=session,
            pending_group=pending_group,
        )
        await self._session_repository.save(session=session)
        for event in self._to_tool_call_resolution_events(resolved_tool_call):
            yield event
        async for event in self._run_agent(session=session):
            yield event

    async def _get_authorized(self, *, session_id: UUID, user_id: UUID) -> Session:
        session = await self._session_repository.get_by_id(session_id=session_id)
        session.has_access(user_id)
        return session

    def _prepare_follow_up_context_for_message(
        self, *, session: Session
    ) -> _ResolvedToolCall | None:
        pending_group = session.pending_follow_up_group()
        if pending_group is None:
            return None

        return self._skip_remaining_follow_ups(
            session=session,
            pending_group=pending_group,
        )

    def _skip_remaining_follow_ups(
        self,
        *,
        session: Session,
        pending_group: FollowUpQuestionGroup,
    ) -> _ResolvedToolCall | None:
        current_question = pending_group.current_question
        if current_question is None:
            return None

        session.skip_remaining_follow_ups(question_id=current_question.id)
        return self._resolve_pending_tool_call(
            session=session,
            result=self._serialize_follow_up_answers(pending_group),
        )

    def _resolve_pending_tool_call(
        self,
        *,
        session: Session,
        result: str,
    ) -> _ResolvedToolCall:
        group = self._require_pending_tool_call_group(session=session)
        call = group.pending_calls[0]
        session.resolve_tool_call(tool_call_id=call.id, result=result)
        return _ResolvedToolCall(
            group_id=group.id,
            tool_call_id=call.id,
            result=result,
            group_completed=group.is_complete,
        )

    def _require_pending_tool_call_group(self, *, session: Session) -> ToolCallGroup:
        group = session.pending_tool_call_group()
        if group is None or not group.pending_calls:
            raise NoPendingToolCallGroupError(
                f"Session {session.id} has no pending tool call group."
            )
        return group

    def _serialize_follow_up_answers(self, group: FollowUpQuestionGroup) -> str:
        return json.dumps(
            {
                "answers": [
                    {
                        "question": question.question,
                        "state": question.state.value,
                        "answer": question.answer_text,
                    }
                    for question in group.questions
                ]
            },
            ensure_ascii=False,
        )

    def _to_tool_call_resolution_events(
        self,
        resolved_tool_call: _ResolvedToolCall | None,
    ) -> tuple[SessionEvent, ...]:
        if resolved_tool_call is None:
            return ()
        events: list[SessionEvent] = [
            SessionToolCallResolved(
                group_id=resolved_tool_call.group_id,
                tool_call_id=resolved_tool_call.tool_call_id,
                result=resolved_tool_call.result,
            )
        ]
        if resolved_tool_call.group_completed:
            events.append(
                SessionToolCallGroupCompleted(group_id=resolved_tool_call.group_id)
            )
        return tuple(events)

    async def _run_agent(self, *, session: Session) -> AsyncIterator[SessionEvent]:
        current_assistant_message: AssistantMessage | None = None

        async for event in self._runner.run(session=session):
            if isinstance(event, SessionRunnerAssistantMessageChunk):
                if current_assistant_message is None:
                    current_assistant_message = session.add_assistant_message()
                    await self._session_repository.save(session=session)
                    yield SessionAssistantMessageStarted(
                        message=current_assistant_message
                    )

                session.append_to_current_assistant_message(event.chunk)
                yield SessionAssistantMessageChunk(
                    message_id=current_assistant_message.id,
                    chunk=event.chunk,
                )
            elif isinstance(event, SessionRunnerAssistantMessage):
                if current_assistant_message is None:
                    current_assistant_message = session.add_assistant_message()
                    await self._session_repository.save(session=session)
                    yield SessionAssistantMessageStarted(
                        message=current_assistant_message
                    )

                if event.content:
                    if current_assistant_message.content:
                        current_assistant_message.content = event.content
                    else:
                        session.append_to_current_assistant_message(event.content)
                        yield SessionAssistantMessageChunk(
                            message_id=current_assistant_message.id,
                            chunk=event.content,
                        )

                await self._session_repository.save(session=session)
                yield SessionAssistantMessageCompleted(
                    message=current_assistant_message
                )
                current_assistant_message = None
            elif isinstance(event, SessionRunnerToolCallStarted):
                if current_assistant_message is not None:
                    await self._session_repository.save(session=session)
                    yield SessionAssistantMessageCompleted(
                        message=current_assistant_message
                    )
                    current_assistant_message = None

                group = session.add_tool_call(event.call)
                await self._session_repository.save(session=session)
                yield SessionToolCallGroupAdded(group=group)
            elif isinstance(event, SessionRunnerToolCallCompleted):
                group = self._require_pending_tool_call_group(session=session)
                session.resolve_tool_call(
                    tool_call_id=event.tool_call_id,
                    result=event.result,
                )
                await self._session_repository.save(session=session)
                yield SessionToolCallResolved(
                    group_id=group.id,
                    tool_call_id=event.tool_call_id,
                    result=event.result,
                )
                if group.is_complete:
                    yield SessionToolCallGroupCompleted(group_id=group.id)
            elif isinstance(event, SessionRunnerFollowUpRequested):
                group = session.add_follow_up_questions(event.questions)
                await self._session_repository.save(session=session)
                yield SessionFollowUpGroupAdded(group=group)
                return
            elif isinstance(event, SessionRunnerPlaylistUpdated):
                playlist = session.set_playlist(
                    tracks=list(event.playlist.tracks),
                    name=event.playlist.name,
                )
                await self._session_repository.save(session=session)
                yield SessionPlaylistSet(playlist=playlist)
