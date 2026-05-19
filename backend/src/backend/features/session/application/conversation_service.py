from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from backend.features.session.application.events import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionEvent,
)
from backend.features.session.application.ports.session_runner import SessionRunner
from backend.features.session.domain import Session, SessionRepository


@dataclass(frozen=True)
class FollowUpAnswer:
    question_id: UUID
    option_id: str | None
    text: str | None


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
        self._prepare_follow_up_context_for_message(session=session)
        session.add_user_message(content=content)
        await self._session_repository.save(session=session)
        async for event in self._run_llm(session=session):
            yield event

    async def answer_follow_ups(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        answers: list[FollowUpAnswer],
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
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
        await self._session_repository.save(session=session)
        async for event in self._run_llm(session=session):
            yield event

    async def skip_remaining_follow_ups(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
    ) -> AsyncIterator[SessionEvent]:
        session = await self._get_authorized(session_id=session_id, user_id=user_id)
        self._prepare_follow_up_context_for_message(session=session)
        await self._session_repository.save(session=session)
        async for event in self._run_llm(session=session):
            yield event

    async def _get_authorized(self, *, session_id: UUID, user_id: UUID) -> Session:
        session = await self._session_repository.get_by_id(session_id=session_id)
        session.has_access(user_id)
        return session

    def _prepare_follow_up_context_for_message(
        self, *, session: Session
    ) -> UUID | None:
        pending_group = session.pending_follow_up_group()
        if pending_group is None:
            return None

        current_question = pending_group.current_question
        if current_question is None:
            return None

        session.skip_remaining_follow_ups(question_id=current_question.id)
        return pending_group.id

    async def _run_llm(self, *, session: Session) -> AsyncIterator[SessionEvent]:
        message = session.add_assistant_message()
        yield SessionAssistantMessageStarted(message=message)
        async for chunk in self._runner.run(session=session):
            session.append_to_current_assistant_message(chunk)
            yield SessionAssistantMessageChunk(message_id=message.id, chunk=chunk)
        await self._session_repository.save(session=session)
        yield SessionAssistantMessageCompleted(message=message)
