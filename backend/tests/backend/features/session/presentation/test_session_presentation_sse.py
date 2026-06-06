import asyncio
from typing import Literal, get_args, get_origin

from backend.features.session.domain import InvalidSessionPhaseTransitionError
from backend.features.session.presentation.sse import SessionServerEvent
from backend.features.session.presentation.sse.events import (
    DoneEvent,
    PlaylistPayload,
    ServerEvent,
    SessionEventType,
    SessionSnapshotPayload,
    _SessionEventSchema,
)
from backend.features.session.presentation.sse.stream import _stream, _to_sse


class TestSessionServerEvent:
    def test_union_events_share_required_type_base(self) -> None:
        union = get_args(ServerEvent)[0]
        event_classes = get_args(union)

        assert _SessionEventSchema.model_fields["type"].is_required()
        assert all(
            issubclass(event_class, _SessionEventSchema)
            for event_class in event_classes
        )
        assert all(
            "type" in event_class.__annotations__ for event_class in event_classes
        )
        assert all(
            get_origin(event_class.__annotations__["type"]) is Literal
            for event_class in event_classes
        )
        assert "type" not in PlaylistPayload.model_fields
        assert "type" not in SessionSnapshotPayload.model_fields

    def test_wraps_discriminated_server_event_union(self) -> None:
        schema = SessionServerEvent(DoneEvent())

        assert schema.root is not None
        assert schema.root.type == SessionEventType.DONE

    def test_allows_empty_schema_payload(self) -> None:
        schema = SessionServerEvent(None)

        assert schema.root is None


class TestServerSentEvents:
    def test_formats_done_event_with_enum_value(self) -> None:
        event = DoneEvent()

        assert event.type == SessionEventType.DONE
        assert _to_sse(event) == 'event: done\ndata: {"type":"done"}\n\n'

    def test_emits_error_event_when_onboarding_cannot_be_completed(self) -> None:
        async def _events():
            raise InvalidSessionPhaseTransitionError("questions unanswered")
            yield

        async def _collect() -> list[str]:
            return [event async for event in _stream(_events())]

        events = asyncio.run(_collect())

        assert events == [
            'event: error\ndata: {"type":"error","code":"InvalidSessionPhaseTransitionError","message":"questions unanswered","correlationId":null}\n\n',
            'event: done\ndata: {"type":"done"}\n\n',
        ]
