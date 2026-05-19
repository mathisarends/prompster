from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.features.session.presentation.schemas import (
    FollowUpAction,
    FollowUpAnswerRequest,
    FollowUpRequest,
    SendMessageRequest,
)


class TestSendMessageRequest:
    def test_accepts_content(self) -> None:
        request = SendMessageRequest(content="spiele house")

        assert request.content == "spiele house"


class TestFollowUpRequest:
    def test_answer_accepts_list_with_single_item(self) -> None:
        question_id = uuid4()

        request = FollowUpRequest(
            action=FollowUpAction.ANSWER,
            answers=[
                FollowUpAnswerRequest(
                    question_id=question_id,
                    option_id="house",
                )
            ],
        )

        assert len(request.answers) == 1
        assert request.answers[0].question_id == question_id
        assert request.answers[0].option_id == "house"

    def test_answer_rejects_option_and_text_together(self) -> None:
        with pytest.raises(ValidationError, match="exactly one"):
            FollowUpRequest(
                action=FollowUpAction.ANSWER,
                answers=[
                    FollowUpAnswerRequest(
                        question_id=uuid4(),
                        option_id="house",
                        text="techno",
                    )
                ],
            )

    def test_answer_requires_at_least_one_item(self) -> None:
        with pytest.raises(ValidationError, match="at least one answer"):
            FollowUpRequest(action=FollowUpAction.ANSWER, answers=[])

    def test_skip_remaining_rejects_answer_fields(self) -> None:
        with pytest.raises(ValidationError, match="skip action"):
            FollowUpRequest(
                action=FollowUpAction.SKIP_REMAINING,
                answers=[
                    FollowUpAnswerRequest(
                        question_id=uuid4(),
                        text="skip this",
                    )
                ],
            )
