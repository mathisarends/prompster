import logging
from uuid import UUID

from dishka import AsyncContainer
from fastapi import WebSocket, WebSocketDisconnect, status
from pydantic import TypeAdapter, ValidationError
from starlette.websockets import WebSocketState

from backend.features.session.application import (
    SessionEvent,
    SessionFollowUpAnswered,
    SessionFollowUpSkipped,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionService,
    SessionUserMessageAppended,
)
from backend.features.session.domain import (
    EmptyFollowUpAnswerError,
    FollowUpOptionNotFoundError,
    FollowUpQuestionAlreadyResolvedError,
    FollowUpQuestionNotFoundError,
    NoPendingFollowUpGroupError,
    PendingFollowUpQuestionsError,
    PendingToolCallsError,
    PlaylistTrackNotFoundError,
    Session,
    SessionAccessDeniedError,
    SessionNotFoundError,
)
from backend.features.session.presentation.ws.event_mapper import to_server_event
from backend.features.session.presentation.ws.events import (
    AddPlaylistTrackCommand,
    AnswerFollowUpWithOptionCommand,
    AnswerFollowUpWithTextCommand,
    ClientEvent,
    ErrorEvent,
    RemovePlaylistTrackCommand,
    SendMessageCommand,
    ServerEvent,
    SessionSnapshotEvent,
    SkipFollowUpCommand,
)
from backend.features.session.presentation.ws.mapper import to_session_snapshot_payload
from backend.features.session.presentation.ws.persistence import (
    SessionPersistenceDaemon,
)

logger = logging.getLogger(__name__)

_CLIENT_EVENT_ADAPTER: TypeAdapter[ClientEvent] = TypeAdapter(ClientEvent)
_SERVER_EVENT_ADAPTER: TypeAdapter[ServerEvent] = TypeAdapter(ServerEvent)

_COMMAND_ERRORS = (
    EmptyFollowUpAnswerError,
    FollowUpOptionNotFoundError,
    FollowUpQuestionAlreadyResolvedError,
    FollowUpQuestionNotFoundError,
    NoPendingFollowUpGroupError,
    PendingFollowUpQuestionsError,
    PendingToolCallsError,
    PlaylistTrackNotFoundError,
)


class SessionWebSocketConnection:
    def __init__(
        self,
        *,
        websocket: WebSocket,
        container: AsyncContainer,
        session_id: UUID,
        user_id: UUID,
    ) -> None:
        self._websocket = websocket
        self._container = container
        self._session_id = session_id
        self._user_id = user_id
        self._session: Session | None = None
        self._persistence = SessionPersistenceDaemon(
            container=container,
            session_id=session_id,
        )

    async def run(self) -> None:
        try:
            self._session = await self._load_session()
        except SessionNotFoundError:
            await self._websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Session not found",
            )
            return
        except SessionAccessDeniedError:
            await self._websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Session access denied",
            )
            return

        await self._websocket.accept()
        await self._send_snapshot()
        self._persistence.start()

        try:
            await self._receive_commands()
        except WebSocketDisconnect:
            return
        except Exception:
            logger.exception(
                "Unhandled error on session WebSocket %s", self._session_id
            )
            if self._websocket.client_state == WebSocketState.CONNECTED:
                await self._websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        finally:
            await self._persistence.close()

    async def _load_session(self) -> Session:
        async with self._container() as request_container:
            service = await request_container.get(SessionService)
            return await service.get_by_id(
                session_id=self._session_id,
                user_id=self._user_id,
            )

    async def _send_snapshot(self) -> None:
        assert self._session is not None
        await _send(
            self._websocket,
            SessionSnapshotEvent(session=to_session_snapshot_payload(self._session)),
        )

    async def _receive_commands(self) -> None:
        while True:
            event = await self._receive_event()
            if event is not None:
                await self._dispatch(event)

    async def _receive_event(self) -> ClientEvent | None:
        raw_event = await self._websocket.receive_json()
        try:
            return _CLIENT_EVENT_ADAPTER.validate_python(raw_event)
        except ValidationError as exc:
            await self._send_error(
                code="invalid_event",
                message=f"Invalid client event: {exc.errors(include_url=False)}",
            )
            return None

    async def _dispatch(self, event: ClientEvent) -> None:
        try:
            session_events = self._handle(event)
        except _COMMAND_ERRORS as exc:
            await self._send_command_error(event=event, error=exc)
            return
        except SessionAccessDeniedError as exc:
            await self._send_error(
                code="session_access_denied",
                message=str(exc) or "Session access denied",
                correlation_id=getattr(event, "correlation_id", None),
            )
            return

        await self._publish(session_events)

    def _handle(self, event: ClientEvent) -> tuple[SessionEvent, ...]:
        assert self._session is not None
        session = self._session
        match event:
            case SendMessageCommand(content=content):
                message = session.add_user_message(content=content)
                return (SessionUserMessageAppended(message=message),)

            case AnswerFollowUpWithOptionCommand(
                question_id=question_id,
                option_id=option_id,
            ):
                group = session.require_pending_follow_up_group()
                question = session.answer_follow_up_with_option(
                    question_id=question_id,
                    option_id=option_id,
                )
                return (SessionFollowUpAnswered(group_id=group.id, question=question),)

            case AnswerFollowUpWithTextCommand(question_id=question_id, text=text):
                group = session.require_pending_follow_up_group()
                question = session.answer_follow_up_with_text(
                    question_id=question_id,
                    text=text,
                )
                return (SessionFollowUpAnswered(group_id=group.id, question=question),)

            case SkipFollowUpCommand(question_id=question_id):
                group = session.require_pending_follow_up_group()
                question = session.skip_follow_up(question_id=question_id)
                return (
                    SessionFollowUpSkipped(group_id=group.id, question_id=question.id),
                )

            case AddPlaylistTrackCommand() as cmd:
                playlist_existed = session.playlist is not None
                track = session.add_track(
                    title=cmd.title,
                    artist=cmd.artist,
                    year=cmd.year,
                    cover_url=cmd.cover_url,
                )
                playlist = session.playlist
                if playlist is None:
                    return ()
                if not playlist_existed:
                    return (SessionPlaylistSet(playlist=playlist),)
                return (
                    SessionPlaylistTrackAdded(playlist_id=playlist.id, track=track),
                )

            case RemovePlaylistTrackCommand(track_id=track_id):
                playlist = session.playlist
                session.remove_track(track_id=track_id)
                if playlist is None:
                    return ()
                return (
                    SessionPlaylistTrackRemoved(
                        playlist_id=playlist.id,
                        track_id=track_id,
                    ),
                )

        raise TypeError(f"Unsupported client event: {type(event).__name__}")

    async def _publish(self, events: tuple[SessionEvent, ...]) -> None:
        assert self._session is not None
        try:
            for event in events:
                await _send(self._websocket, to_server_event(event))
        finally:
            self._persistence.persist(self._session)

    async def _send_command_error(
        self, *, event: ClientEvent, error: Exception
    ) -> None:
        await self._send_error(
            code=type(error).__name__,
            message=str(error) or type(error).__name__,
            correlation_id=getattr(event, "correlation_id", None),
        )

    async def _send_error(
        self,
        *,
        code: str,
        message: str,
        correlation_id: str | None = None,
    ) -> None:
        await _send(
            self._websocket,
            ErrorEvent(
                code=code,
                message=message,
                correlation_id=correlation_id,
            ),
        )


async def _send(websocket: WebSocket, event: ServerEvent) -> None:
    if websocket.client_state != WebSocketState.CONNECTED:
        return
    await websocket.send_json(_SERVER_EVENT_ADAPTER.dump_python(event, mode="json"))
