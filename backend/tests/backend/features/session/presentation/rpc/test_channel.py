import asyncio
from typing import get_args
from unittest.mock import Mock
from uuid import uuid4

import pytest

from backend.features.session.application import (
    SessionAssistantMessageChunk,
    SessionConversationService,
)
from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerAssistantMessageChunk,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import (
    InvalidSessionPhaseTransitionError,
    Session,
    SessionRepository,
)
from backend.features.session.presentation.rpc.channel import (
    complete_onboarding,
    send_message,
)
from backend.features.session.presentation.rpc.context import SessionRpcContext
from backend.features.session.presentation.rpc.events import (
    DoneEvent,
    ErrorEvent,
    PlaylistPayload,
    SessionSnapshotPayload,
    SessionStreamEvent,
)
from backend.features.session.presentation.rpc.params import (
    CompleteOnboardingParams,
    SendMessageParams,
)
from backend.features.session.presentation.rpc.stream import session_events


def test_event_union_has_discriminated_model_members() -> None:
    event_classes = get_args(get_args(SessionStreamEvent.__value__)[0])
    assert all("type" in cls.model_fields for cls in event_classes)
    assert "type" not in PlaylistPayload.model_fields
    assert "type" not in SessionSnapshotPayload.model_fields


def test_command_error_is_followed_by_done() -> None:
    async def failing_events():
        raise InvalidSessionPhaseTransitionError("questions unanswered")
        yield

    async def collect():
        return [event async for event in session_events(failing_events())]

    events = asyncio.run(collect())
    assert events == [
        ErrorEvent(
            code="InvalidSessionPhaseTransitionError",
            message="questions unanswered",
        ),
        DoneEvent(),
    ]


def test_unexpected_error_is_sanitized_and_followed_by_done() -> None:
    async def failing_events():
        raise RuntimeError("sensitive detail")
        yield

    async def collect():
        return [event async for event in session_events(failing_events())]

    events = asyncio.run(collect())
    assert events == [
        ErrorEvent(
            code="InternalError", message="Die Antwort konnte nicht geladen werden."
        ),
        DoneEvent(),
    ]


@pytest.mark.parametrize("operation", ["send_message", "complete_onboarding"])
def test_closing_subscription_closes_application_stream_immediately(operation) -> None:
    closed = False

    async def source():
        nonlocal closed
        try:
            yield SessionAssistantMessageChunk(message_id=uuid4(), chunk="Hallo")
            await asyncio.Event().wait()
        finally:
            closed = True

    service = Mock(spec=SessionConversationService)
    getattr(service, operation).return_value = source()
    context = SessionRpcContext(session_id=uuid4(), user_id=uuid4())

    async def run():
        stream = (
            send_message(SendMessageParams(content="Hallo"), context, service)
            if operation == "send_message"
            else complete_onboarding(CompleteOnboardingParams(), context, service)
        )
        event = await anext(stream)
        await stream.aclose()
        return event

    event = asyncio.run(run())

    assert event.chunk == "Hallo"
    assert closed


def test_closing_rpc_stream_closes_runner_and_awaits_title_task():
    owner_id = uuid4()
    session = Session.create(title="", owner_id=owner_id)
    repository = Mock(spec=SessionRepository)
    repository.get_by_id.return_value = session
    repository.save.return_value = session
    runner = Mock(spec=SessionRunner)
    title_generator = Mock(spec=SessionTitleGenerator)
    runner_closed = False
    title_closed = False

    async def runner_events(**kwargs):
        nonlocal runner_closed
        try:
            await asyncio.sleep(0)
            yield SessionRunnerAssistantMessageChunk(chunk="Hallo")
            await asyncio.Event().wait()
        finally:
            runner_closed = True

    async def generate_title(**kwargs):
        nonlocal title_closed
        try:
            await asyncio.Event().wait()
        finally:
            title_closed = True

    runner.run.side_effect = runner_events
    title_generator.generate.side_effect = generate_title
    service = SessionConversationService(
        session_repository=repository,
        runner=runner,
        message_attachment_store=Mock(spec=MessageAttachmentStore),
        title_generator=title_generator,
    )

    async def run():
        stream = send_message(
            SendMessageParams(content="Hallo"),
            SessionRpcContext(session_id=session.id, user_id=owner_id),
            service,
        )
        event = await anext(stream)
        await stream.aclose()
        return event

    event = asyncio.run(run())

    assert event.type == "message.assistant_started"
    assert runner_closed
    assert title_closed
