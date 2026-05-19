"""Split session_messages into per-kind entry tables.

Revision ID: 0004_split_session_entries
Revises: 0003_normalize_session_storage
Create Date: 2026-05-19 12:00:00
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Sequence, Union
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0004_split_session_entries"
down_revision: Union[str, Sequence[str], None] = "0003_normalize_session_storage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_user_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_user_messages_session_position",
        "session_user_messages",
        ["session_id", "position"],
        unique=False,
    )

    op.create_table(
        "session_assistant_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_assistant_messages_session_position",
        "session_assistant_messages",
        ["session_id", "position"],
        unique=False,
    )

    op.create_table(
        "session_tool_call_groups",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_tool_call_groups_session_position",
        "session_tool_call_groups",
        ["session_id", "position"],
        unique=False,
    )

    op.create_table(
        "session_tool_calls",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("session_tool_call_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("call_id", sa.Text(), nullable=False),
        sa.Column("function_name", sa.Text(), nullable=False),
        sa.Column(
            "function_arguments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "session_follow_up_question_groups",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_follow_up_question_groups_session_position",
        "session_follow_up_question_groups",
        ["session_id", "position"],
        unique=False,
    )

    op.create_table(
        "session_follow_up_questions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("session_follow_up_question_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column(
            "options",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("answered_option_id", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    _backfill_entries_from_session_messages()

    op.drop_index(
        "ix_session_messages_session_id_position", table_name="session_messages"
    )
    op.drop_table("session_messages")


def downgrade() -> None:
    op.create_table(
        "session_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "tool_call_group", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "follow_up_group", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_messages_session_id_position",
        "session_messages",
        ["session_id", "position"],
        unique=False,
    )

    _rebuild_session_messages_from_entries()

    op.drop_table("session_follow_up_questions")
    op.drop_index(
        "ix_session_follow_up_question_groups_session_position",
        table_name="session_follow_up_question_groups",
    )
    op.drop_table("session_follow_up_question_groups")

    op.drop_table("session_tool_calls")
    op.drop_index(
        "ix_session_tool_call_groups_session_position",
        table_name="session_tool_call_groups",
    )
    op.drop_table("session_tool_call_groups")

    op.drop_index(
        "ix_session_assistant_messages_session_position",
        table_name="session_assistant_messages",
    )
    op.drop_table("session_assistant_messages")

    op.drop_index(
        "ix_session_user_messages_session_position",
        table_name="session_user_messages",
    )
    op.drop_table("session_user_messages")


def _backfill_entries_from_session_messages() -> None:
    conn = op.get_bind()

    sessions = conn.execute(sa.text("SELECT id FROM sessions")).scalars().all()

    select_messages = sa.text(
        """
        SELECT id, created_at, role, content, tool_call_group, follow_up_group
        FROM session_messages
        WHERE session_id = :session_id
        ORDER BY position
        """
    )
    insert_user = sa.text(
        """
        INSERT INTO session_user_messages (id, created_at, session_id, position, content)
        VALUES (:id, :created_at, :session_id, :position, :content)
        """
    )
    insert_assistant = sa.text(
        """
        INSERT INTO session_assistant_messages (id, created_at, session_id, position, content)
        VALUES (:id, :created_at, :session_id, :position, :content)
        """
    )
    insert_tool_group = sa.text(
        """
        INSERT INTO session_tool_call_groups (id, created_at, session_id, position)
        VALUES (:id, :created_at, :session_id, :position)
        """
    )
    insert_tool_call = sa.text(
        """
        INSERT INTO session_tool_calls (
            id, created_at, group_id, position, call_id, function_name,
            function_arguments, state, result, error
        ) VALUES (
            :id, :created_at, :group_id, :position, :call_id, :function_name,
            CAST(:function_arguments AS jsonb), :state, :result, :error
        )
        """
    )
    insert_follow_group = sa.text(
        """
        INSERT INTO session_follow_up_question_groups (
            id, created_at, session_id, position
        ) VALUES (:id, :created_at, :session_id, :position)
        """
    )
    insert_follow_question = sa.text(
        """
        INSERT INTO session_follow_up_questions (
            id, created_at, group_id, position, question, options, state,
            answer_text, answered_option_id
        ) VALUES (
            :id, :created_at, :group_id, :position, :question,
            CAST(:options AS jsonb), :state, :answer_text, :answered_option_id
        )
        """
    )

    for session_id in sessions:
        rows = (
            conn.execute(select_messages, {"session_id": session_id}).mappings().all()
        )
        next_position = 0
        for row in rows:
            created_at = _as_datetime(row["created_at"]) or datetime.now(timezone.utc)
            role = (row["role"] or "").lower()
            content = row["content"] or ""
            tool_group_payload = row["tool_call_group"]
            follow_group_payload = row["follow_up_group"]

            tool_group_payload = _coerce_json(tool_group_payload)
            follow_group_payload = _coerce_json(follow_group_payload)

            if isinstance(tool_group_payload, dict):
                group_id = _as_uuid(tool_group_payload.get("id")) or uuid4()
                group_created_at = (
                    _as_datetime(tool_group_payload.get("created_at")) or created_at
                )
                conn.execute(
                    insert_tool_group,
                    {
                        "id": group_id,
                        "created_at": group_created_at,
                        "session_id": session_id,
                        "position": next_position,
                    },
                )
                next_position += 1
                calls = tool_group_payload.get("calls")
                if isinstance(calls, list):
                    for call_position, call_payload in enumerate(calls):
                        if not isinstance(call_payload, dict):
                            continue
                        function_payload = call_payload.get("function")
                        if not isinstance(function_payload, dict):
                            function_payload = {}
                        arguments = function_payload.get("arguments")
                        if not isinstance(arguments, dict):
                            arguments = {}
                        state_value = call_payload.get("state") or "pending"
                        conn.execute(
                            insert_tool_call,
                            {
                                "id": uuid4(),
                                "created_at": group_created_at,
                                "group_id": group_id,
                                "position": call_position,
                                "call_id": str(call_payload.get("id", "")),
                                "function_name": str(function_payload.get("name", "")),
                                "function_arguments": json.dumps(arguments),
                                "state": str(state_value),
                                "result": (
                                    str(call_payload.get("result"))
                                    if isinstance(call_payload.get("result"), str)
                                    else None
                                ),
                                "error": (
                                    str(call_payload.get("error"))
                                    if isinstance(call_payload.get("error"), str)
                                    else None
                                ),
                            },
                        )

            if role == "user":
                conn.execute(
                    insert_user,
                    {
                        "id": _as_uuid(row["id"]) or uuid4(),
                        "created_at": created_at,
                        "session_id": session_id,
                        "position": next_position,
                        "content": content,
                    },
                )
                next_position += 1
            elif role == "assistant":
                if content or not isinstance(tool_group_payload, dict):
                    conn.execute(
                        insert_assistant,
                        {
                            "id": _as_uuid(row["id"]) or uuid4(),
                            "created_at": created_at,
                            "session_id": session_id,
                            "position": next_position,
                            "content": content,
                        },
                    )
                    next_position += 1

            if isinstance(follow_group_payload, dict):
                follow_group_id = _as_uuid(follow_group_payload.get("id")) or uuid4()
                follow_group_created_at = (
                    _as_datetime(follow_group_payload.get("created_at")) or created_at
                )
                conn.execute(
                    insert_follow_group,
                    {
                        "id": follow_group_id,
                        "created_at": follow_group_created_at,
                        "session_id": session_id,
                        "position": next_position,
                    },
                )
                next_position += 1
                questions = follow_group_payload.get("questions")
                if isinstance(questions, list):
                    for q_position, q_payload in enumerate(questions):
                        if not isinstance(q_payload, dict):
                            continue
                        options = q_payload.get("options")
                        if not isinstance(options, list):
                            options = []
                        conn.execute(
                            insert_follow_question,
                            {
                                "id": _as_uuid(q_payload.get("id")) or uuid4(),
                                "created_at": follow_group_created_at,
                                "group_id": follow_group_id,
                                "position": q_position,
                                "question": str(q_payload.get("question", "")),
                                "options": json.dumps(options),
                                "state": str(q_payload.get("state") or "pending"),
                                "answer_text": (
                                    str(q_payload.get("answer_text"))
                                    if isinstance(q_payload.get("answer_text"), str)
                                    else None
                                ),
                                "answered_option_id": (
                                    str(q_payload.get("answered_option_id"))
                                    if isinstance(
                                        q_payload.get("answered_option_id"), str
                                    )
                                    else None
                                ),
                            },
                        )


def _rebuild_session_messages_from_entries() -> None:
    """Best-effort downgrade: flatten entry tables back into session_messages.

    Synthesizes one assistant row per assistant message and attaches the
    nearest preceding tool_call_group / following follow_up_group payloads.
    This is not perfectly lossless when groups are not adjacent to messages
    in the new model.
    """

    conn = op.get_bind()

    sessions = conn.execute(sa.text("SELECT id FROM sessions")).scalars().all()

    insert_message = sa.text(
        """
        INSERT INTO session_messages (
            id, created_at, session_id, position, role, content,
            tool_call_group, follow_up_group
        ) VALUES (
            :id, :created_at, :session_id, :position, :role, :content,
            CAST(:tool_call_group AS jsonb), CAST(:follow_up_group AS jsonb)
        )
        """
    )

    for session_id in sessions:
        entries = _load_entries_for_downgrade(conn, session_id)
        entries.sort(key=lambda e: (e["position"], e["kind"]))

        position = 0
        pending_tool_group: dict | None = None
        for entry in entries:
            kind = entry["kind"]
            if kind == "tool_call_group":
                pending_tool_group = entry["payload"]
                continue
            if kind == "follow_up_group":
                conn.execute(
                    insert_message,
                    {
                        "id": uuid4(),
                        "created_at": entry["created_at"],
                        "session_id": session_id,
                        "position": position,
                        "role": "assistant",
                        "content": "",
                        "tool_call_group": (
                            json.dumps(pending_tool_group)
                            if pending_tool_group is not None
                            else None
                        ),
                        "follow_up_group": json.dumps(entry["payload"]),
                    },
                )
                pending_tool_group = None
                position += 1
                continue
            role = "user" if kind == "user" else "assistant"
            conn.execute(
                insert_message,
                {
                    "id": entry["id"],
                    "created_at": entry["created_at"],
                    "session_id": session_id,
                    "position": position,
                    "role": role,
                    "content": entry["content"],
                    "tool_call_group": (
                        json.dumps(pending_tool_group)
                        if pending_tool_group is not None and role == "assistant"
                        else None
                    ),
                    "follow_up_group": None,
                },
            )
            if role == "assistant":
                pending_tool_group = None
            position += 1


def _load_entries_for_downgrade(conn: Any, session_id: UUID) -> list[dict]:
    entries: list[dict] = []

    rows = conn.execute(
        sa.text(
            "SELECT id, created_at, position, content FROM session_user_messages "
            "WHERE session_id = :session_id"
        ),
        {"session_id": session_id},
    ).mappings()
    for row in rows:
        entries.append(
            {
                "kind": "user",
                "id": row["id"],
                "position": row["position"],
                "created_at": row["created_at"],
                "content": row["content"],
            }
        )

    rows = conn.execute(
        sa.text(
            "SELECT id, created_at, position, content FROM session_assistant_messages "
            "WHERE session_id = :session_id"
        ),
        {"session_id": session_id},
    ).mappings()
    for row in rows:
        entries.append(
            {
                "kind": "assistant",
                "id": row["id"],
                "position": row["position"],
                "created_at": row["created_at"],
                "content": row["content"],
            }
        )

    rows = conn.execute(
        sa.text(
            "SELECT id, created_at, position FROM session_tool_call_groups "
            "WHERE session_id = :session_id"
        ),
        {"session_id": session_id},
    ).mappings()
    for row in rows:
        calls = conn.execute(
            sa.text(
                "SELECT position, call_id, function_name, function_arguments, "
                "state, result, error FROM session_tool_calls "
                "WHERE group_id = :group_id ORDER BY position"
            ),
            {"group_id": row["id"]},
        ).mappings()
        call_payloads = [
            {
                "id": c["call_id"],
                "function": {
                    "name": c["function_name"],
                    "arguments": c["function_arguments"] or {},
                },
                "state": c["state"],
                "result": c["result"],
                "error": c["error"],
            }
            for c in calls
        ]
        entries.append(
            {
                "kind": "tool_call_group",
                "position": row["position"],
                "created_at": row["created_at"],
                "payload": {
                    "id": str(row["id"]),
                    "created_at": _to_iso(row["created_at"]),
                    "calls": call_payloads,
                },
            }
        )

    rows = conn.execute(
        sa.text(
            "SELECT id, created_at, position FROM session_follow_up_question_groups "
            "WHERE session_id = :session_id"
        ),
        {"session_id": session_id},
    ).mappings()
    for row in rows:
        questions = conn.execute(
            sa.text(
                "SELECT id, position, question, options, state, answer_text, "
                "answered_option_id FROM session_follow_up_questions "
                "WHERE group_id = :group_id ORDER BY position"
            ),
            {"group_id": row["id"]},
        ).mappings()
        question_payloads = [
            {
                "id": str(q["id"]),
                "question": q["question"],
                "options": q["options"] or [],
                "state": q["state"],
                "answer_text": q["answer_text"],
                "answered_option_id": q["answered_option_id"],
            }
            for q in questions
        ]
        entries.append(
            {
                "kind": "follow_up_group",
                "position": row["position"],
                "created_at": row["created_at"],
                "payload": {
                    "id": str(row["id"]),
                    "created_at": _to_iso(row["created_at"]),
                    "questions": question_payloads,
                },
            }
        )

    return entries


def _coerce_json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return None


def _as_uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str) and value:
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _to_iso(value: Any) -> str:
    parsed = _as_datetime(value)
    if parsed is None:
        return datetime.now(timezone.utc).isoformat()
    return parsed.isoformat()
