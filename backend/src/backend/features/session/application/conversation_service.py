import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from uuid import UUID

from backend.features.session.application.events import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCancelled,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionEvent,
    SessionOnboardingQuestionAsked,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionPlaylistTrackReplaced,
    SessionSnapshot,
    SessionSuspendedForInput,
    SessionTitleGenerated,
    SessionToolCallSequenceAdded,
    SessionToolCallSequenceCompleted,
    SessionToolCallResolved,
    SuspensionKind,
)
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerCancelled,
    SessionRunnerEvent,
    SessionRunnerPlaylistTracksAdded,
    SessionRunnerPlaylistTracksRemoved,
    SessionRunnerPlaylistTracksReplaced,
    SessionRunnerPlaylistUpdated,
    SessionRunnerQuestionAsked,
    SessionRunnerSuspendedForInput,
    SessionRunnerToolCallCompleted,
    SessionRunnerToolCallStarted,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.domain import (
    AssistantMessage,
    ImageAttachment,
    NoPendingToolCallSequenceError,
    Session,
    SessionRepository,
    ToolCallSequence,
    UserMessageAttachment,
    UserMessageAttachmentKind,
)
from backend.features.user.application import UserMessageRateLimitService

logger = logging.getLogger(__name__)

_ALLOWED_IMAGE_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
_MAX_IMAGE_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024
_MAX_IMAGE_ATTACHMENTS_PER_MESSAGE = 5


@dataclass(frozen=True)
class SessionMessageAttachment:
    kind: str
    external_id: str
    title: str
    subtitle: str | None = None
    image_url: str | None = None
    spotify_id: str | None = None


@dataclass(frozen=True)
class SessionImageAttachmentUpload:
    file_name: str
    content_type: str
    content: bytes


@dataclass(frozen=True)
class _ResolvedToolCall:
    sequence_id: UUID
    tool_call_id: str
    result: str
    sequence_completed: bool


@dataclass
class _AgentRunState:
    current_assistant_message: AssistantMessage | None = None
    skipped_onboarding_tool_call_ids: set[str] = field(default_factory=set)
    cancelled: bool = False
    stopped: bool = False


class SessionConversationService:
    def __init__(
        self,
        session_repository: SessionRepository,
        runner: SessionRunner,
        message_attachment_store: MessageAttachmentStore,
        user_message_rate_limit_service: UserMessageRateLimitService,
        title_generator: SessionTitleGenerator,
    ) -> None:
        self._session_repository = session_repository
        self._runner = runner
        self._message_attachment_store = message_attachment_store
        self._user_message_rate_limit_service = user_message_rate_limit_service
        self._title_generator = title_generator

    async def send_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        content: str,
        attachments: list[SessionMessageAttachment] | None = None,
        image_attachments: list[SessionImageAttachmentUpload] | None = None,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        await self._user_message_rate_limit_service.consume(user_id=user_id)

        message_id = uuid4()
        stored_images = await self._store_image_attachments(
            session_id=session.id,
            message_id=message_id,
            image_attachments=image_attachments or [],
        )
        session.add_user_message(
            content=content,
            message_id=message_id,
            attachments=self._to_user_message_attachments(attachments or []),
            image_attachments=stored_images,
        )
        title_task = self._maybe_start_title_generation(
            session=session,
            prompt=content,
        )
        async for event in self._persist_and_resume_agent(
            session=session,
            title_task=title_task,
            model_id=model_id,
        ):
            yield event

    async def submit_onboarding_answer(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        question_id: UUID,
        answer: str | None = None,
        answers: list[str] | None = None,
    ) -> Session:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        session.answer_onboarding_question(
            question_id=question_id,
            answer=answer,
            answers=answers,
        )
        return await self._persist_session(session=session)

    async def complete_onboarding(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        session.advance_to_building_phase()
        await self._persist_session(session=session)
        yield SessionSnapshot(session=session)

        async for event in self._run_agent_and_consume_user_curation_events(
            session=session,
            model_id=model_id,
        ):
            yield event

    def _maybe_start_title_generation(
        self,
        *,
        session: Session,
        prompt: str,
    ) -> asyncio.Task[str] | None:
        if session.title.strip():
            return None

        return asyncio.create_task(
            self._title_generator.generate(initial_prompt=prompt)
        )

    async def _persist_and_resume_agent(
        self,
        *,
        session: Session,
        title_task: asyncio.Task[str] | None = None,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionEvent]:
        try:
            await self._persist_session(session=session)
            async for event in self._run_agent_and_consume_user_curation_events(
                session=session,
                model_id=model_id,
            ):
                yield event
                for title_event in await self._emit_title_if_ready(
                    session=session,
                    title_task=title_task,
                ):
                    yield title_event
            for title_event in await self._flush_title(
                session=session,
                title_task=title_task,
            ):
                yield title_event
        finally:
            if title_task is not None and not title_task.done():
                title_task.cancel()
            elif title_task is not None and title_task.done():
                self._consume_title_task_exception(title_task)

    async def _emit_title_if_ready(
        self,
        *,
        session: Session,
        title_task: asyncio.Task[str] | None,
    ) -> tuple[SessionEvent, ...]:
        if title_task is None or not title_task.done() or session.title.strip():
            return ()

        return await self._apply_title(
            session=session,
            raw_title=self._title_from_task(title_task),
        )

    async def _flush_title(
        self,
        *,
        session: Session,
        title_task: asyncio.Task[str] | None,
    ) -> tuple[SessionEvent, ...]:
        if title_task is None or session.title.strip():
            return ()

        try:
            raw_title = await title_task
        except asyncio.CancelledError:
            return ()
        except Exception:
            raw_title = "New Session"

        return await self._apply_title(session=session, raw_title=raw_title)

    async def _apply_title(
        self,
        *,
        session: Session,
        raw_title: str,
    ) -> tuple[SessionEvent, ...]:
        title = (raw_title.strip() or "New Session")[:120]
        session.title = title
        await self._persist_session(session=session)
        return (SessionTitleGenerated(title=title),)

    def _title_from_task(self, title_task: asyncio.Task[str]) -> str:
        try:
            return title_task.result()
        except asyncio.CancelledError:
            return "New Session"
        except Exception:
            return "New Session"

    def _consume_title_task_exception(self, title_task: asyncio.Task[str]) -> None:
        try:
            title_task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def stop_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
    ) -> bool:
        await self._get_authorized(session_id=session_id, user_id=user_id)
        return await self._runner.stop(session_id=session_id)

    async def _persist_session(self, *, session: Session) -> Session:
        return await self._session_repository.save(session=session)

    async def _persisted_events(
        self,
        *,
        session: Session,
        events: tuple[SessionEvent, ...] = (),
    ) -> tuple[SessionEvent, ...]:
        await self._persist_session(session=session)
        return events

    def _to_user_message_attachments(
        self,
        attachments: list[SessionMessageAttachment],
    ) -> list[UserMessageAttachment]:
        return [
            UserMessageAttachment(
                kind=UserMessageAttachmentKind(attachment.kind),
                external_id=attachment.external_id,
                title=attachment.title,
                subtitle=attachment.subtitle,
                image_url=attachment.image_url,
                spotify_id=attachment.spotify_id,
            )
            for attachment in attachments
        ]

    async def _store_image_attachments(
        self,
        *,
        session_id: UUID,
        message_id: UUID,
        image_attachments: list[SessionImageAttachmentUpload],
    ) -> list[ImageAttachment]:
        self._validate_image_attachments(image_attachments=image_attachments)
        created_at = datetime.now(timezone.utc)
        result: list[ImageAttachment] = []

        for image in image_attachments:
            attachment_id = uuid4()
            normalized_content_type = self._normalize_content_type(image.content_type)
            stored = await self._message_attachment_store.save_image_attachment(
                session_id=session_id,
                message_id=message_id,
                attachment_id=attachment_id,
                file_name=image.file_name,
                content_type=normalized_content_type,
                content=image.content,
            )
            result.append(
                ImageAttachment(
                    id=attachment_id,
                    storage_key=stored.storage_key,
                    content_type=stored.content_type,
                    file_name=stored.file_name,
                    size_bytes=stored.size_bytes,
                    created_time=created_at,
                )
            )

        return result

    def _validate_image_attachments(
        self,
        *,
        image_attachments: list[SessionImageAttachmentUpload],
    ) -> None:
        if len(image_attachments) > _MAX_IMAGE_ATTACHMENTS_PER_MESSAGE:
            raise ValueError(
                f"A maximum of {_MAX_IMAGE_ATTACHMENTS_PER_MESSAGE} images is allowed per message."
            )

        for image in image_attachments:
            content_type = self._normalize_content_type(image.content_type)
            if content_type not in _ALLOWED_IMAGE_CONTENT_TYPES:
                raise ValueError(f"Unsupported image content type: {content_type}.")
            if len(image.content) > _MAX_IMAGE_ATTACHMENT_SIZE_BYTES:
                raise ValueError(
                    f"Image '{image.file_name}' exceeds the maximum allowed size of "
                    f"{_MAX_IMAGE_ATTACHMENT_SIZE_BYTES // (1024 * 1024)} MB."
                )

    def _normalize_content_type(self, content_type: str) -> str:
        return content_type.split(";", 1)[0].strip().lower()

    async def _get_authorized(self, *, session_id: UUID, user_id: UUID) -> Session:
        session = await self._session_repository.get_by_id(session_id=session_id)
        session.has_access(user_id)
        return session

    def _require_pending_tool_call_sequence(
        self, *, session: Session
    ) -> ToolCallSequence:
        sequence = session.pending_tool_call_sequence()
        if sequence is None or not sequence.pending_calls:
            raise NoPendingToolCallSequenceError(
                f"Session {session.id} has no pending tool call sequence."
            )
        return sequence

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
        model_id: str | None = None,
        on_cancelled: Callable[[], None] | None = None,
    ) -> AsyncIterator[SessionEvent]:
        state = _AgentRunState()

        async for event in self._runner.run(session=session, model_id=model_id):
            if not isinstance(event, SessionRunnerAssistantMessageChunk):
                logger.debug(
                    "Runner event received for session %s: %s",
                    session.id,
                    type(event).__name__,
                )
            session_events = await self._handle_runner_event(
                event=event,
                session=session,
                state=state,
            )

            if state.cancelled and on_cancelled is not None:
                on_cancelled()

            for session_event in session_events:
                if not isinstance(session_event, SessionAssistantMessageChunk):
                    logger.debug(
                        "Session event emitted for session %s: %s",
                        session.id,
                        type(session_event).__name__,
                    )
                yield session_event

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
            case SessionRunnerQuestionAsked():
                return await self._handle_question_asked(
                    event=event,
                    session=session,
                )
            case SessionRunnerSuspendedForInput():
                return await self._handle_suspended_for_input(
                    event=event,
                    session=session,
                    state=state,
                )
        raise TypeError(f"Unsupported runner event: {event!r}")

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

        events.append(SessionAssistantMessageCompleted(message=message))
        state.current_assistant_message = None
        return await self._persisted_events(session=session, events=tuple(events))

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
        if event.call.function.is_onboarding_question:
            state.skipped_onboarding_tool_call_ids.add(event.call.id)
            return tuple(events)

        sequence = session.add_tool_call(event.call)
        events.append(SessionToolCallSequenceAdded(sequence=sequence))
        return await self._persisted_events(session=session, events=tuple(events))

    async def _handle_tool_call_completed(
        self,
        *,
        event: SessionRunnerToolCallCompleted,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        if event.tool_call_id in state.skipped_onboarding_tool_call_ids:
            state.skipped_onboarding_tool_call_ids.remove(event.tool_call_id)
            return ()

        sequence = self._require_pending_tool_call_sequence(session=session)
        session.resolve_tool_call(
            tool_call_id=event.tool_call_id,
            result=event.result,
        )
        return await self._persisted_events(
            session=session,
            events=self._to_tool_call_resolution_events(
                _ResolvedToolCall(
                    sequence_id=sequence.id,
                    tool_call_id=event.tool_call_id,
                    result=event.result,
                    sequence_completed=sequence.is_complete,
                )
            ),
        )

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
        return await self._persisted_events(
            session=session,
            events=(SessionPlaylistSet(playlist=playlist),),
        )

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

        if not had_playlist:
            return await self._persisted_events(
                session=session,
                events=(SessionPlaylistSet(playlist=playlist),),
            )

        return await self._persisted_events(
            session=session,
            events=tuple(
                SessionPlaylistTrackAdded(
                    playlist_id=playlist.id,
                    track=track,
                )
                for track in event.tracks
            ),
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

        if playlist is None:
            return await self._persisted_events(session=session)

        return await self._persisted_events(
            session=session,
            events=tuple(
                SessionPlaylistTrackRemoved(
                    playlist_id=playlist.id,
                    track_id=track_id,
                )
                for track_id in event.track_ids
            ),
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

        if playlist is None:
            return await self._persisted_events(session=session)

        return await self._persisted_events(
            session=session,
            events=tuple(
                SessionPlaylistTrackReplaced(
                    playlist_id=playlist.id,
                    track_id=replacement.track_id,
                    track=replacement.track,
                )
                for replacement in event.replacements
            ),
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
        if message is None:
            return await self._persisted_events(session=session)

        return await self._persisted_events(
            session=session,
            events=(SessionAssistantMessageCancelled(message_id=message.id),),
        )

    async def _handle_question_asked(
        self,
        *,
        event: SessionRunnerQuestionAsked,
        session: Session,
    ) -> tuple[SessionEvent, ...]:
        if event.question is None:
            return ()

        question = session.add_onboarding_question(
            question_text=event.question,
            hint=event.hint,
            options=tuple(event.options or []),
            selection_mode=event.selection_mode,
        )
        return await self._persisted_events(
            session=session,
            events=(
                SessionOnboardingQuestionAsked(
                    question=question.question_text,
                    options=list(question.options),
                    hint=question.hint,
                    selection_mode=question.selection_mode,
                    question_id=question.id,
                    is_last_question=question.is_last_question,
                ),
            ),
        )

    async def _handle_suspended_for_input(
        self,
        *,
        event: SessionRunnerSuspendedForInput,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        events = list(
            await self._finish_current_assistant_message(
                session=session,
                state=state,
            )
        )
        question_id = None
        suspended_options = list(event.options or [])
        if event.question is not None:
            question = session.add_onboarding_question(
                question_text=event.question,
                hint=event.hint,
                options=tuple(event.options or []),
                selection_mode=event.selection_mode,
                is_last_question=event.is_last_question,
            )
            question_id = question.id
            suspended_options = list(question.options)
        events.append(
            SessionSuspendedForInput(
                kind=SuspensionKind.ONBOARDING_QUESTION,
                question=event.question,
                hint=event.hint,
                options=suspended_options,
                selection_mode=event.selection_mode,
                question_id=question_id,
                is_last_question=event.is_last_question,
            )
        )
        return await self._persisted_events(session=session, events=tuple(events))

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
        return await self._persisted_events(
            session=session,
            events=(SessionAssistantMessageStarted(message=message),),
        )

    async def _finish_current_assistant_message(
        self,
        *,
        session: Session,
        state: _AgentRunState,
    ) -> tuple[SessionEvent, ...]:
        message = state.current_assistant_message
        if message is None:
            return ()

        state.current_assistant_message = None
        return await self._persisted_events(
            session=session,
            events=(SessionAssistantMessageCompleted(message=message),),
        )

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
        model_id: str | None = None,
    ) -> AsyncIterator[SessionEvent]:
        cancelled = False

        def _mark_cancelled() -> None:
            nonlocal cancelled
            cancelled = True

        async for event in self._run_agent(
            session=session,
            model_id=model_id,
            on_cancelled=_mark_cancelled,
        ):
            yield event

        if cancelled:
            return

        events = session.unconsumed_user_curation_events
        if not events:
            return

        for event in events:
            event.mark_consumed()
        await self._persist_session(session=session)
