from uuid import UUID

from backend.features.session.application.events import (
    SessionEvent,
    SessionFollowUpSkipped,
)
from backend.features.session.domain import Session


class SkipFollowUpHandler:
    async def handle(
        self,
        *,
        session: Session,
        question_id: UUID,
    ) -> tuple[SessionEvent, ...]:
        group = session.require_pending_follow_up_group()
        question = session.skip_follow_up(question_id=question_id)
        return (SessionFollowUpSkipped(group_id=group.id, question_id=question.id),)
