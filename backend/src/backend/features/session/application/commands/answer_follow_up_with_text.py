from uuid import UUID

from backend.features.session.application.events import (
    SessionEvent,
    SessionFollowUpAnswered,
)
from backend.features.session.domain import Session


class AnswerFollowUpWithTextHandler:
    async def handle(
        self,
        *,
        session: Session,
        question_id: UUID,
        text: str,
    ) -> tuple[SessionEvent, ...]:
        group = session.require_pending_follow_up_group()
        question = session.answer_follow_up_with_text(
            question_id=question_id, text=text
        )
        return (SessionFollowUpAnswered(group_id=group.id, question=question),)
