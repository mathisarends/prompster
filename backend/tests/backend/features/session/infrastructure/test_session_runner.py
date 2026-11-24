import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from agent import AgentCheckpoint, AgentCommit
from agent import Phase as AgentPhase
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from spotifyify import SpotifyClient

from backend.features.llm.application import ChatModels
from backend.features.llm.domain import LLMRegistry
from backend.features.llm.domain.model_registry import (
    LLMConfig,
    LLMModelInfo,
    ModelPresentation,
)
from backend.features.session.application import SessionConversationService
from backend.features.session.application.ports import (
    ActiveSessionRunStore,
    MessageAttachmentStore,
    StoredAttachment,
)
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerAssistantMessage,
    SessionRunnerCancelled,
    SessionRunnerEvent,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import (
    Phase,
    Session,
    SessionRepository,
    UserCurationEvent,
    UserCurationEventType,
)
from backend.features.session.infrastructure.agent_checkpoint_store import (
    SqlAgentCheckpointStore,
)
from backend.features.session.infrastructure.agent_input import AgentInputBuilder
from backend.features.session.infrastructure.session_runner import (
    AgentRuntimeRegistry,
    AgentSessionRunner,
)


class _SessionRepositoryStub(SessionRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self.save_count = 0

    async def get_by_id(self, session_id):
        return self.session

    async def save(self, *, session: Session) -> Session:
        self.save_count += 1
        self.session = session
        return session

    async def update(self, session_id, title):
        return self.session

    async def delete(self, session_id) -> None:
        return None


class _EmptyRunner(SessionRunner):
    async def run(
        self,
        *,
        session: Session,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionRunnerEvent]:
        if False:
            yield


class _TitleGeneratorStub(SessionTitleGenerator):
    async def generate(self, initial_prompt: str) -> str:
        return "Deck"


class _CancelledRunner(SessionRunner):
    async def run(
        self,
        *,
        session: Session,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionRunnerEvent]:
        yield SessionRunnerCancelled()


class _MessageAttachmentStoreStub(MessageAttachmentStore):
    async def save_stashed_image_attachment(
        self,
        *,
        user_id,
        attachment_id,
        file_name,
        content_type,
        content,
    ) -> StoredAttachment:
        return StoredAttachment(
            storage_key=f"users/{user_id}/stash/{attachment_id}.png",
            content_type=content_type,
            file_name=file_name,
            size_bytes=len(content),
        )

    async def promote_stashed_image_attachment(
        self,
        *,
        user_id,
        session_id,
        stash_storage_key: str,
    ) -> str:
        file_name = stash_storage_key.rsplit("/", 1)[-1]
        return f"users/{user_id}/chat/{session_id}/{file_name}"

    async def save_image_attachment(
        self,
        *,
        session_id,
        message_id,
        attachment_id,
        file_name,
        content_type,
        content,
    ) -> StoredAttachment:
        return StoredAttachment(
            storage_key=f"sessions/{session_id}/{attachment_id}",
            content_type=content_type,
            file_name=file_name,
            size_bytes=len(content),
        )

    async def save_uploaded_image_attachment(
        self,
        *,
        session_id,
        attachment_id,
        file_name,
        content_type,
        content,
    ) -> StoredAttachment:
        return StoredAttachment(
            storage_key=f"sessions/{session_id}/uploads/{attachment_id}.png",
            content_type=content_type,
            file_name=file_name,
            size_bytes=len(content),
        )

    async def exists(self, *, storage_key: str) -> bool:
        return True

    async def load_bytes(self, *, storage_key: str) -> bytes:
        return b""

    async def create_signed_url(
        self,
        *,
        storage_key: str,
        expires_in_seconds: int,
    ) -> str:
        return f"https://example.com/{storage_key}"

    async def delete_session_attachments(self, *, user_id, session_id) -> None:
        return None

    async def delete_user_attachments(self, *, user_id) -> None:
        return None

    async def delete_unreferenced_uploaded_image_attachments(
        self,
        *,
        session_id,
        referenced_storage_keys: set[str],
    ) -> None:
        return None


class TestAgentPhaseMapping:
    @pytest.mark.parametrize("phase", list(Phase))
    def test_agent_understands_every_persisted_session_phase(
        self, phase: Phase
    ) -> None:
        assert AgentPhase(phase).value == phase.value


class TestSendMessageConsumesCurationEvents:
    def test_send_message_consumes_user_curation_events_after_runner(self) -> None:
        user_id = UUID(int=9)
        event = UserCurationEvent.create(
            event_type=UserCurationEventType.TRACK_ADDED,
            track_id=UUID(int=10),
            track_title="Umbrella",
            track_artist="Rihanna",
        )
        session = Session.restore(
            id=UUID(int=11),
            created_at=datetime.now(UTC),
            title="Deck",
            entries=[],
            owner_id=user_id,
            user_curation_events=[event],
        )
        repository = _SessionRepositoryStub(session=session)
        service = SessionConversationService(
            session_repository=repository,
            runner=_EmptyRunner(),
            message_attachment_store=_MessageAttachmentStoreStub(),
            title_generator=_TitleGeneratorStub(),
        )

        async def run() -> None:
            async for _ in service.send_message(
                session_id=session.id,
                user_id=user_id,
                content="weiter",
            ):
                pass

        asyncio.run(run())

        assert event.consumed is True

    def test_send_message_does_not_consume_user_curation_events_when_cancelled(
        self,
    ) -> None:
        user_id = UUID(int=12)
        event = UserCurationEvent.create(
            event_type=UserCurationEventType.TRACK_ADDED,
            track_id=UUID(int=13),
            track_title="Umbrella",
            track_artist="Rihanna",
        )
        session = Session.restore(
            id=UUID(int=14),
            created_at=datetime.now(UTC),
            title="Deck",
            entries=[],
            owner_id=user_id,
            user_curation_events=[event],
        )
        repository = _SessionRepositoryStub(session=session)
        service = SessionConversationService(
            session_repository=repository,
            runner=_CancelledRunner(),
            message_attachment_store=_MessageAttachmentStoreStub(),
            title_generator=_TitleGeneratorStub(),
        )

        async def run() -> None:
            async for _ in service.send_message(
                session_id=session.id,
                user_id=user_id,
                content="weiter",
            ):
                pass

        asyncio.run(run())

        assert event.consumed is False


class _MemoryCheckpointStore(SqlAgentCheckpointStore):
    def __init__(self) -> None:
        self.checkpoint: AgentCheckpoint | None = None

    async def load(self, *, session_id: UUID) -> AgentCheckpoint | None:
        return self.checkpoint

    async def save(self, *, session_id: UUID, commit: AgentCommit) -> None:
        state = commit.state
        if state is None:
            assert self.checkpoint is not None
            state = self.checkpoint.state
        self.checkpoint = AgentCheckpoint(state=state, execution=commit.execution)


class _MemoryActiveRuns(ActiveSessionRunStore):
    def __init__(self) -> None:
        self.runs: dict[UUID, UUID] = {}

    async def register(self, *, session_id: UUID, run_id: UUID) -> None:
        self.runs[session_id] = run_id

    async def complete(self, *, session_id: UUID, run_id: UUID) -> None:
        self.runs.pop(session_id, None)

    async def request_stop(self, *, session_id: UUID) -> bool:
        return False

    async def is_stop_requested(self, *, session_id: UUID, run_id: UUID) -> bool:
        return False


class _SpotifyHttp:
    async def open(self) -> None:
        return None


def _replying_model(prompts: list[list[str]], reply: str) -> FunctionModel:
    async def stream(
        messages: list[ModelMessage], _info: AgentInfo
    ) -> AsyncIterator[str]:
        prompts.append(
            [
                str(part.content)
                for message in messages
                if isinstance(message, ModelRequest)
                for part in message.parts
                if isinstance(part, UserPromptPart)
            ]
        )
        yield reply

    return FunctionModel(stream_function=stream, model_name="scripted")


def _runner(
    llm: FunctionModel, checkpoints: SqlAgentCheckpointStore
) -> AgentSessionRunner:
    model = LLMModelInfo(
        id="scripted",
        provider_model="scripted",
        presentation=ModelPresentation(label="Scripted", profile="test", order=0),
    )
    return AgentSessionRunner(
        llm=llm,
        chat_models=cast(ChatModels, None),
        spotify=cast(SpotifyClient, SimpleNamespace(http=_SpotifyHttp())),
        input_builder=AgentInputBuilder(_MessageAttachmentStoreStub()),
        checkpoints=checkpoints,
        active_runs=_MemoryActiveRuns(),
        runtime_registry=AgentRuntimeRegistry(),
        llm_registry=LLMRegistry(
            LLMConfig(version=1, default_model_id="scripted", models=(model,))
        ),
    )


async def _run(runner: AgentSessionRunner, session: Session) -> list[object]:
    return [event async for event in runner.run(session=session)]


class TestAgentSessionRunner:
    def test_next_run_continues_from_the_saved_checkpoint(self) -> None:
        checkpoints = _MemoryCheckpointStore()
        prompts: list[list[str]] = []
        session = Session.create(title="Deck", owner_id=UUID(int=20))
        session.add_user_message("Hallo")

        first = asyncio.run(
            _run(_runner(_replying_model(prompts, "Hi"), checkpoints), session)
        )
        session.add_assistant_message("Hi")
        session.add_user_message("Weiter")
        asyncio.run(_run(_runner(_replying_model(prompts, "Ok"), checkpoints), session))

        assert SessionRunnerAssistantMessage(content="Hi") in first
        assert checkpoints.checkpoint is not None
        assert prompts[1] == ["Hallo", "Weiter"]

    def test_controls_without_a_running_agent_do_nothing(self) -> None:
        registry = AgentRuntimeRegistry()

        assert registry.pause(session_id=UUID(int=21)) is False
        assert registry.resume(session_id=UUID(int=21)) is False
        assert registry.abort(session_id=UUID(int=21)) is False
