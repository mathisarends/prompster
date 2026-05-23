import asyncio
import logging
from contextlib import suppress

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from backend.features.transcription.application import (
    TranscriptionOptions,
    TranscriptionSession,
    TranscriptionSessionFactory,
)
from backend.features.transcription.presentation.mapper import (
    parse_client_command,
    to_socket_error_event,
    to_transcription_server_event,
)
from backend.features.transcription.presentation.schemas import (
    FlushCommand,
    StopCommand,
)

logger = logging.getLogger(__name__)


class RealtimeTranscriptionSocketHandler:
    def __init__(self, *, session_factory: TranscriptionSessionFactory) -> None:
        self._session_factory = session_factory

    async def handle(
        self, *, websocket: WebSocket, options: TranscriptionOptions
    ) -> None:
        await websocket.accept()
        session = self._session_factory.create(options=options)

        forward_task = asyncio.create_task(
            self._forward_transcription_events(websocket=websocket, session=session)
        )
        receive_task = asyncio.create_task(
            self._receive_client_messages(websocket=websocket, session=session)
        )

        try:
            done, pending = await asyncio.wait(
                {forward_task, receive_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            await self._cancel_pending_tasks(pending)
            await self._handle_done_tasks(done=done, websocket=websocket)
        finally:
            await session.stop()

    async def _forward_transcription_events(
        self,
        *,
        websocket: WebSocket,
        session: TranscriptionSession,
    ) -> None:
        try:
            async for event in session.stream():
                payload = to_transcription_server_event(event)
                await websocket.send_json(
                    payload.model_dump(mode="json", by_alias=True)
                )
        except WebSocketDisconnect:
            return

    async def _receive_client_messages(
        self,
        *,
        websocket: WebSocket,
        session: TranscriptionSession,
    ) -> None:
        while True:
            message = await websocket.receive()
            message_type = message.get("type")

            if message_type == "websocket.disconnect":
                return

            if message_type != "websocket.receive":
                continue

            chunk = message.get("bytes")
            if chunk is not None:
                await session.push_audio_chunk(chunk)
                continue

            raw_text = message.get("text")
            if raw_text is None:
                continue

            try:
                command = parse_client_command(raw_message=raw_text)
            except ValidationError:
                await self._send_socket_error(
                    websocket,
                    'Invalid command. Use {"type": "flush"} or {"type": "stop"}.',
                )
                continue

            if isinstance(command, FlushCommand):
                try:
                    await session.flush()
                except RuntimeError as exc:
                    await self._send_socket_error(websocket, str(exc))
                continue

            if isinstance(command, StopCommand):
                await session.stop()
                return

    async def _send_socket_error(self, websocket: WebSocket, message: str) -> None:
        payload = to_socket_error_event(message)
        await websocket.send_json(payload.model_dump(mode="json", by_alias=True))

    async def _cancel_pending_tasks(self, pending: set[asyncio.Task[None]]) -> None:
        for task in pending:
            task.cancel()

        if pending:
            with suppress(asyncio.CancelledError):
                await asyncio.gather(*pending, return_exceptions=True)

    async def _handle_done_tasks(
        self,
        *,
        done: set[asyncio.Task[None]],
        websocket: WebSocket,
    ) -> None:
        for task in done:
            if task.cancelled():
                continue

            exc = task.exception()
            if exc is None:
                continue

            if isinstance(exc, WebSocketDisconnect):
                continue

            logger.exception("Transcription websocket stopped unexpectedly.")
            with suppress(Exception):
                await self._send_socket_error(
                    websocket, "Transcription stream interrupted"
                )
