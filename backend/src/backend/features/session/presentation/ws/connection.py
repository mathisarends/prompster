import logging
from uuid import UUID

from dishka import AsyncContainer
from fastapi import WebSocket, WebSocketDisconnect, status
from pydantic import TypeAdapter, ValidationError
from starlette.websockets import WebSocketState

from backend.features.session.application import (
    AddPlaylistTrackHandler,
    AnswerFollowUpWithOptionHandler,
    AnswerFollowUpWithTextHandler,
    AppendUserMessageHandler,
    RemovePlaylistTrackHandler,
    SessionEvent,
    SkipFollowUpHandler,
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
        session: Session,
    ) -> None:
        self._websocket = websocket
        self._container = container
        self._session_id = session_id
        self._session = session
        self._persistence = SessionPersistenceDaemon(
            container=container,
            session_id=session_id,
        )

    async def run(self) -> None:
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

    async def _send_snapshot(self) -> None:
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
            session_events = await self._handle(event)
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

    async def _handle(self, event: ClientEvent) -> tuple[SessionEvent, ...]:
        match event:
            case SendMessageCommand():
                return await self._handle_send_message(event)
            case AnswerFollowUpWithOptionCommand():
                return await self._handle_answer_follow_up_option(event)
            case AnswerFollowUpWithTextCommand():
                return await self._handle_answer_follow_up_text(event)
            case SkipFollowUpCommand():
                return await self._handle_skip_follow_up(event)
            case AddPlaylistTrackCommand():
                return await self._handle_add_track(event)
            case RemovePlaylistTrackCommand():
                return await self._handle_remove_track(event)

        raise TypeError(f"Unsupported client event: {type(event).__name__}")

    async def _handle_send_message(
        self,
        event: SendMessageCommand,
    ) -> tuple[SessionEvent, ...]:
        async with self._container() as request_container:
            handler = await request_container.get(AppendUserMessageHandler)
            return await handler.handle(
                session=self._session,
                content=event.content,
            )

    async def _handle_answer_follow_up_option(
        self,
        event: AnswerFollowUpWithOptionCommand,
    ) -> tuple[SessionEvent, ...]:
        async with self._container() as request_container:
            handler = await request_container.get(AnswerFollowUpWithOptionHandler)
            return await handler.handle(
                session=self._session,
                question_id=event.question_id,
                option_id=event.option_id,
            )

    async def _handle_answer_follow_up_text(
        self,
        event: AnswerFollowUpWithTextCommand,
    ) -> tuple[SessionEvent, ...]:
        async with self._container() as request_container:
            handler = await request_container.get(AnswerFollowUpWithTextHandler)
            return await handler.handle(
                session=self._session,
                question_id=event.question_id,
                text=event.text,
            )

    async def _handle_skip_follow_up(
        self,
        event: SkipFollowUpCommand,
    ) -> tuple[SessionEvent, ...]:
        async with self._container() as request_container:
            handler = await request_container.get(SkipFollowUpHandler)
            return await handler.handle(
                session=self._session,
                question_id=event.question_id,
            )

    async def _handle_add_track(
        self,
        event: AddPlaylistTrackCommand,
    ) -> tuple[SessionEvent, ...]:
        async with self._container() as request_container:
            handler = await request_container.get(AddPlaylistTrackHandler)
            return await handler.handle(
                session=self._session,
                title=event.title,
                artist=event.artist,
                year=event.year,
                cover_url=event.cover_url,
            )

    async def _handle_remove_track(
        self,
        event: RemovePlaylistTrackCommand,
    ) -> tuple[SessionEvent, ...]:
        async with self._container() as request_container:
            handler = await request_container.get(RemovePlaylistTrackHandler)
            return await handler.handle(
                session=self._session,
                track_id=event.track_id,
            )

    async def _publish(self, events: tuple[SessionEvent, ...]) -> None:
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
