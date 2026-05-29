import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from uuid import UUID

from backend.features.user.application import UserMessageRateLimitService
from backend.features.session.application.events import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCancelled,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionEvent,
    SessionFollowUpGroupAdded,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionPlaylistTrackReplaced,
    SessionToolCallSequenceAdded,
    SessionToolCallSequenceCompleted,
    SessionToolCallResolved,
)
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerCancelled,
    SessionRunnerEvent,
    SessionRunnerFollowUpRequested,
    SessionRunnerPlaylistTracksAdded,
    SessionRunnerPlaylistTracksRemoved,
    SessionRunnerPlaylistTracksReplaced,
    SessionRunnerPlaylistUpdated,
    SessionRunnerToolCallCompleted,
    SessionRunnerToolCallStarted,
)
from backend.features.session.domain import (
    AssistantMessage,
    FollowUpQuestionGroup,
    NoPendingToolCallSequenceError,
    Session,
    SessionRepository,
    ToolCallSequence,
    UserMessageAttachment,
    UserMessageAttachmentKind,
)


@dataclass(frozen=True)
class FollowUpAnswer:
    question_id: UUID
    option_id: str | None
    text: str | None


@dataclass(frozen=True)
class SessionMessageAttachment:
    kind: str
    external_id: str
    title: str
    subtitle: str | None = None
    image_url: str | None = None
    spotify_id: str | None = None


@dataclass(frozen=True)
class _ResolvedToolCall:
    sequence_id: UUID
    tool_call_id: str
    result: str
    sequence_completed: bool


@dataclass
class _AgentRunState:
    current_assistant_message: AssistantMessage | None = None
    cancelled: bool = False
    stopped: bool = False


class SessionConversationService:
    def __init__(
        self,
        session_repository: SessionRepository,
        runner: SessionRunner,
        user_message_rate_limit_service: UserMessageRateLimitService,
    ) -> None:
        self._session_repository = session_repository
        self._runner = runner
        self._user_message_rate_limit_service = user_message_rate_limit_service

    async def send_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        content: str,
        attachments: list[SessionMessageAttachment] | None = None,
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        await self._user_message_rate_limit_service.consume(user_id=user_id)
        resolved_tool_call = self._prepare_follow_up_context_for_message(
            session=session
        )
        session.add_user_message(
            content=content,
            attachments=[
                UserMessageAttachment(
                    kind=UserMessageAttachmentKind(attachment.kind),
                    external_id=attachment.external_id,
                    title=attachment.title,
                    subtitle=attachment.subtitle,
                    image_url=attachment.image_url,
                    spotify_id=attachment.spotify_id,
                )
                for attachment in (attachments or [])
            ],
        )
        async for event in self._persist_and_resume_agent(
            session=session,
            resolved_tool_call=resolved_tool_call,
        ):
            yield event

    async def _persist_and_resume_agent(
        self,
        *,
        session: Session,
        resolved_tool_call: _ResolvedToolCall | None = None,
    ) -> AsyncIterator[SessionEvent]:
        await self._persist_session(session=session)
        for event in self._to_tool_call_resolution_events(resolved_tool_call):
            yield event
        async for event in self._run_agent_and_consume_user_curation_events(
            session=session
        ):
            yield event

    async def stop_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
    ) -> bool:
        await self._get_authorized(session_id=session_id, user_id=user_id)
        return await self._runner.stop(session_id=session_id)

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

        await self._user_message_rate_limit_service.consume(user_id=user_id)
        resolved_tool_call = self._resolve_pending_tool_call(
            session=session,
            result=self._serialize_follow_up_answers(pending_group),
        )
        async for event in self._persist_and_resume_agent(
            session=session,
            resolved_tool_call=resolved_tool_call,
        ):
            yield event

    async def skip_remaining_follow_ups(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        pending_group = session.require_pending_follow_up_group()
        await self._user_message_rate_limit_service.consume(user_id=user_id)
        resolved_tool_call = self._skip_remaining_follow_ups(
            session=session,
            pending_group=pending_group,
        )
        async for event in self._persist_and_resume_agent(
            session=session,
            resolved_tool_call=resolved_tool_call,
        ):
            yield event

    async def _persist_session(self, *, session: Session) -> None:
        await self._session_repository.save(session=session)

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
        sequence = self._require_pending_tool_call_sequence(session=session)
        call = sequence.pending_calls[0]
        session.resolve_tool_call(tool_call_id=call.id, result=result)
        return _ResolvedToolCall(
            sequence_id=sequence.id,
            tool_call_id=call.id,
            result=result,
            sequence_completed=sequence.is_complete,
        )

    def _require_pending_tool_call_sequence(
        self, *, session: Session
    ) -> ToolCallSequence:
        sequence = session.pending_tool_call_sequence()
        if sequence is None or not sequence.pending_calls:
            raise NoPendingToolCallSequenceError(
                f"Session {session.id} has no pending tool call sequence."
            )
        return sequence

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
                sequence_id=resolved_tool_call.sequence_id,
                tool_call_id=resolved_tool_call.tool_call_id,
                result=resolved_tool_call.result,
            )
        ]
        if resolved_tool_call.sequence_completed:
            events.append(
                SessionToolCallSequenceCompleted(
                    sequence_id=resolved_tool_call.sequence_id
                )
            )
        return tuple(events)

    async def _run_agent(
        self,
        *,
        session: Session,
        on_cancelled: Callable[[], None] | None = None,
    ) -> AsyncIterator[SessionEvent]:
        state = _AgentRunState()

        async for event in self._runner.run(session=session):
            for session_event in await self._handle_runner_event(
                event=event,
                session=session,
                state=state,
            ):
                yield session_event

            if state.cancelled and on_cancelled is not None:
                on_cancelled()

            if state.stopped:
                return

    async def _handle_runner_event(
        self,
        *,
        event: SessionRunnerEvent,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        match event:
            case SessionRunnerAssistantMessageChunk():
                return await self._handle_assistant_message_chunk(
                    event=event,
                    session=session,
                    state=state,
                )
            case SessionRunnerAssistantMessage():
                return await self._handle_assistant_message(
                    event=event,
                    session=session,
                    state=state,
                )
            case SessionRunnerToolCallStarted():
                return await self._handle_tool_call_started(
                    event=event,
                    session=session,
                    state=state,
                )
            case SessionRunnerToolCallCompleted():
                return await self._handle_tool_call_completed(
                    event=event,
                    session=session,
                )
            case SessionRunnerFollowUpRequested():
                return await self._handle_follow_up_requested(
                    event=event,
                    session=session,
                    state=state,
                )
            case SessionRunnerPlaylistUpdated():
                return await self._handle_playlist_updated(
                    event=event,
                    session=session,
                )
            case SessionRunnerPlaylistTracksAdded():
                return await self._handle_playlist_tracks_added(
                    event=event,
                    session=session,
                )
            case SessionRunnerPlaylistTracksRemoved():
                return await self._handle_playlist_tracks_removed(
                    event=event,
                    session=session,
                )
            case SessionRunnerPlaylistTracksReplaced():
                return await self._handle_playlist_tracks_replaced(
                    event=event,
                    session=session,
                )
            case SessionRunnerCancelled():
                return await self._handle_runner_cancelled(
                    session=session,
                    state=state,
                )

    async def _handle_assistant_message_chunk(
        self,
        *,
        event: SessionRunnerAssistantMessageChunk,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        events = list(
            await self._ensure_assistant_message_started(
                session=session,
                state=state,
            )
        )
        message = self._require_current_run_assistant_message(state=state)

        session.append_to_current_assistant_message(event.chunk)
        events.append(
            SessionAssistantMessageChunk(
                message_id=message.id,
                chunk=event.chunk,
            )
        )
        return tuple(events)

    async def _handle_assistant_message(
        self,
        *,
        event: SessionRunnerAssistantMessage,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        events = list(
            await self._ensure_assistant_message_started(
                session=session,
                state=state,
            )
        )
        message = self._require_current_run_assistant_message(state=state)

        if event.content and message.content:
            message.content = event.content
        elif event.content:
            session.append_to_current_assistant_message(event.content)
            events.append(
                SessionAssistantMessageChunk(
                    message_id=message.id,
                    chunk=event.content,
                )
            )

        await self._persist_session(session=session)
        events.append(SessionAssistantMessageCompleted(message=message))
        state.current_assistant_message = None
        return tuple(events)

    async def _handle_tool_call_started(
        self,
        *,
        event: SessionRunnerToolCallStarted,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        events = list(
            await self._finish_current_assistant_message(
                session=session,
                state=state,
            )
        )
        sequence = session.add_tool_call(event.call)
        await self._persist_session(session=session)
        events.append(SessionToolCallSequenceAdded(sequence=sequence))
        return tuple(events)

    async def _handle_tool_call_completed(
        self,
        *,
        event: SessionRunnerToolCallCompleted,
        session: Session,
    ) -> tuple[SessionEvent, ...]:
        sequence = self._require_pending_tool_call_sequence(session=session)
        session.resolve_tool_call(
            tool_call_id=event.tool_call_id,
            result=event.result,
        )
        await self._persist_session(session=session)
        return self._to_tool_call_resolution_events(
            _ResolvedToolCall(
                sequence_id=sequence.id,
                tool_call_id=event.tool_call_id,
                result=event.result,
                sequence_completed=sequence.is_complete,
            )
        )

    async def _handle_follow_up_requested(
        self,
        *,
        event: SessionRunnerFollowUpRequested,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        group = session.add_follow_up_questions(event.questions)
        await self._persist_session(session=session)
        state.stopped = True
        return (SessionFollowUpGroupAdded(group=group),)

    async def _handle_playlist_updated(
        self,
        *,
        event: SessionRunnerPlaylistUpdated,
        session: Session,
    ) -> tuple[SessionEvent, ...]:
        playlist = session.set_playlist(
            tracks=list(event.playlist.tracks),
            name=event.playlist.name,
            id=event.playlist.id,
            created_time=event.playlist.created_at,
        )
        await self._persist_session(session=session)
        return (SessionPlaylistSet(playlist=playlist),)

    async def _handle_playlist_tracks_added(
        self,
        *,
        event: SessionRunnerPlaylistTracksAdded,
        session: Session,
    ) -> tuple[SessionEvent, ...]:
        had_playlist = session.playlist is not None
        if had_playlist:
            playlist = session.add_tracks(list(event.tracks))
        else:
            playlist = session.set_playlist(
                tracks=list(event.tracks),
                id=event.playlist_id,
            )

        await self._persist_session(session=session)
        if not had_playlist:
            return (SessionPlaylistSet(playlist=playlist),)

        return tuple(
            SessionPlaylistTrackAdded(
                playlist_id=playlist.id,
                track=track,
            )
            for track in event.tracks
        )

    async def _handle_playlist_tracks_removed(
        self,
        *,
        event: SessionRunnerPlaylistTracksRemoved,
        session: Session,
    ) -> tuple[SessionEvent, ...]:
        playlist = session.playlist
        for track_id in event.track_ids:
            session.remove_track(
                track_id=track_id,
                record_user_curation_event=False,
            )
        if playlist is None:
            playlist = session.playlist

        await self._persist_session(session=session)
        if playlist is None:
            return ()

        return tuple(
            SessionPlaylistTrackRemoved(
                playlist_id=playlist.id,
                track_id=track_id,
            )
            for track_id in event.track_ids
        )

    async def _handle_playlist_tracks_replaced(
        self,
        *,
        event: SessionRunnerPlaylistTracksReplaced,
        session: Session,
    ) -> tuple[SessionEvent, ...]:
        playlist = session.playlist
        for replacement in event.replacements:
            playlist = session.replace_track(
                track_id=replacement.track_id,
                track=replacement.track,
            )

        await self._persist_session(session=session)
        if playlist is None:
            return ()

        return tuple(
            SessionPlaylistTrackReplaced(
                playlist_id=playlist.id,
                track_id=replacement.track_id,
                track=replacement.track,
            )
            for replacement in event.replacements
        )

    async def _handle_runner_cancelled(
        self,
        *,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        state.cancelled = True
        state.stopped = True
        session.remove_last_pending_tool_call()

        message = state.current_assistant_message
        state.current_assistant_message = None
        await self._persist_session(session=session)
        if message is None:
            return ()

        return (SessionAssistantMessageCancelled(message_id=message.id),)

    async def _ensure_assistant_message_started(
        self,
        *,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        if state.current_assistant_message is not None:
            return ()

        message = session.add_assistant_message()
        state.current_assistant_message = message
        await self._persist_session(session=session)
        return (SessionAssistantMessageStarted(message=message),)

    async def _finish_current_assistant_message(
        self,
        *,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        message = state.current_assistant_message
        if message is None:
            return ()

        await self._persist_session(session=session)
        state.current_assistant_message = None
        return (SessionAssistantMessageCompleted(message=message),)

    def _require_current_run_assistant_message(
        self,
        *,
        state: _AgentRunState,
    ) -> AssistantMessage:
        if state.current_assistant_message is None:
            raise RuntimeError("Runner event did not start an assistant message.")
        return state.current_assistant_message

    async def _run_agent_and_consume_user_curation_events(
        self,
        *,
        session: Session,
    ) -> AsyncIterator[SessionEvent]:
        cancelled = False

        def _mark_cancelled() -> None:
            nonlocal cancelled
            cancelled = True

        async for event in self._run_agent(
            session=session, on_cancelled=_mark_cancelled
        ):
            yield event

        if cancelled:
            return

        events = session.unconsumed_user_curation_events
        if not events:
            return

        for event in events:
            event.mark_consumed()
        await self._session_repository.save(session=session)
