from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.features.session.domain import (
    AssistantMessage,
    CompletedCall,
    FailedCall,
    FollowUpOption,
    FollowUpQuestion,
    FollowUpQuestionGroup,
    FollowUpQuestionState,
    PendingCall,
    Playlist,
    PlaylistTrack,
    Session,
    SessionEntry,
    SessionNotFoundError,
    SessionRepository,
    ToolCall,
    ToolCallSequence,
    ToolFunction,
    UserMessage,
)
from backend.infrastructure.database.orm import (
    PlaylistTrackModel,
    SessionAssistantMessageModel,
    SessionFollowUpQuestionGroupModel,
    SessionFollowUpQuestionModel,
    SessionModel,
    SessionPlaylistModel,
    SessionToolCallSequenceModel,
    SessionToolCallModel,
    SessionUserMessageModel,
)
from backend.infrastructure.database.repository import Repository


_PENDING_STATE = "pending"
_COMPLETED_STATE = "completed"
_FAILED_STATE = "failed"


class SqlSessionRepository(Repository[SessionModel, Session], SessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=SessionModel)

    async def get_by_id(self, *, session_id: UUID) -> Session:
        session = await self.session.scalar(self._detail_query(session_id=session_id))
        if session is None:
            raise SessionNotFoundError
        return self._to_domain(session)

    async def update(
        self,
        *,
        session_id: UUID,
        title: str | None,
    ) -> Session:
        session = await self.get_by_id(session_id=session_id)
        if title is not None:
            session.title = title
        return await self.save(session=session)

    async def delete(self, *, session_id: UUID) -> None:
        deleted = await self.delete_by_id(session_id)
        if not deleted:
            raise SessionNotFoundError

    async def save(self, *, session: Session) -> Session:
        orm = await self.session.scalar(self._detail_query(session_id=session.id))
        if orm is None:
            orm = SessionModel(id=session.id)
            self.session.add(orm)

        orm.title = session.title
        orm.owner_id = session.owner_id
        orm.is_starred = session.is_starred
        orm.created_at = session.created_at
        orm.last_activity_at = self._resolve_last_activity_at(session)

        session_id = orm.id or session.id
        self._sync_entries(orm=orm, session_id=session_id, entries=session.entries)
        orm.playlist = self._to_orm_playlist(
            domain_playlist=session.playlist,
            session_id=session_id,
            existing_playlist=orm.playlist,
        )

        await self.session.flush()
        return self._to_domain(orm)

    def _to_domain(self, orm: SessionModel) -> Session:
        entries: list[tuple[int, SessionEntry]] = []
        for row in orm.user_messages:
            entries.append((row.position, self._to_domain_user_message(row)))
        for row in orm.assistant_messages:
            entries.append((row.position, self._to_domain_assistant_message(row)))
        for row in orm.tool_call_sequences:
            entries.append((row.position, self._to_domain_tool_call_sequence(row)))
        for row in orm.follow_up_question_groups:
            entries.append((row.position, self._to_domain_follow_up_group(row)))
        entries.sort(key=lambda item: item[0])

        return Session(
            id=orm.id,
            title=orm.title,
            entries=[entry for _, entry in entries],
            owner_id=orm.owner_id,
            is_starred=orm.is_starred,
            playlist=self._to_domain_playlist(orm.playlist),
            created_time=orm.created_at,
        )

    def _to_orm(self, domain: Session) -> SessionModel:
        orm = SessionModel(
            id=domain.id,
            title=domain.title,
            owner_id=domain.owner_id,
            is_starred=domain.is_starred,
            created_at=domain.created_at,
            last_activity_at=self._resolve_last_activity_at(domain),
        )
        session_id = domain.id
        self._sync_entries(orm=orm, session_id=session_id, entries=domain.entries)
        orm.playlist = self._to_orm_playlist(
            domain_playlist=domain.playlist,
            session_id=session_id,
            existing_playlist=None,
        )
        return orm

    def _sync_entries(
        self,
        *,
        orm: SessionModel,
        session_id: UUID,
        entries: tuple[SessionEntry, ...],
    ) -> None:
        existing_user_rows = {
            row.id: row for row in orm.user_messages if row.id is not None
        }
        existing_assistant_rows = {
            row.id: row for row in orm.assistant_messages if row.id is not None
        }
        existing_tool_sequence_rows = {
            row.id: row for row in orm.tool_call_sequences if row.id is not None
        }
        existing_follow_up_group_rows = {
            row.id: row for row in orm.follow_up_question_groups if row.id is not None
        }

        user_rows: list[SessionUserMessageModel] = []
        assistant_rows: list[SessionAssistantMessageModel] = []
        tool_sequence_rows: list[SessionToolCallSequenceModel] = []
        follow_group_rows: list[SessionFollowUpQuestionGroupModel] = []

        for position, entry in enumerate(entries):
            if isinstance(entry, UserMessage):
                row = existing_user_rows.get(entry.id)
                if row is None:
                    row = SessionUserMessageModel(id=entry.id)
                row.session_id = session_id
                row.position = position
                row.content = entry.content
                row.created_at = entry.created_at
                user_rows.append(row)
            elif isinstance(entry, AssistantMessage):
                row = existing_assistant_rows.get(entry.id)
                if row is None:
                    row = SessionAssistantMessageModel(id=entry.id)
                row.session_id = session_id
                row.position = position
                row.content = entry.content
                row.created_at = entry.created_at
                assistant_rows.append(row)
            elif isinstance(entry, ToolCallSequence):
                tool_sequence_rows.append(
                    self._to_orm_tool_call_sequence(
                        sequence=entry,
                        session_id=session_id,
                        position=position,
                        existing_sequence=existing_tool_sequence_rows.get(entry.id),
                    )
                )
            elif isinstance(entry, FollowUpQuestionGroup):
                follow_group_rows.append(
                    self._to_orm_follow_up_group(
                        group=entry,
                        session_id=session_id,
                        position=position,
                        existing_group=existing_follow_up_group_rows.get(entry.id),
                    )
                )

        orm.user_messages = user_rows
        orm.assistant_messages = assistant_rows
        orm.tool_call_sequences = tool_sequence_rows
        orm.follow_up_question_groups = follow_group_rows

    def _detail_query(self, *, session_id: UUID):
        return (
            select(SessionModel)
            .where(SessionModel.id == session_id)
            .options(
                selectinload(SessionModel.user_messages),
                selectinload(SessionModel.assistant_messages),
                selectinload(SessionModel.tool_call_sequences).selectinload(
                    SessionToolCallSequenceModel.calls
                ),
                selectinload(SessionModel.follow_up_question_groups).selectinload(
                    SessionFollowUpQuestionGroupModel.questions
                ),
                selectinload(SessionModel.playlist).selectinload(
                    SessionPlaylistModel.tracks
                ),
            )
        )

    def _resolve_last_activity_at(self, session: Session) -> datetime:
        latest = session.created_at
        for entry in session.entries:
            created_at = getattr(entry, "created_at", None)
            if isinstance(created_at, datetime) and created_at > latest:
                latest = created_at
        return latest

    def _to_domain_user_message(self, row: SessionUserMessageModel) -> UserMessage:
        return UserMessage(id=row.id, content=row.content, created_time=row.created_at)

    def _to_domain_assistant_message(
        self, row: SessionAssistantMessageModel
    ) -> AssistantMessage:
        return AssistantMessage(
            id=row.id, content=row.content, created_time=row.created_at
        )

    def _to_domain_tool_call_sequence(
        self, row: SessionToolCallSequenceModel
    ) -> ToolCallSequence:
        calls = sorted(row.calls, key=lambda c: c.position)
        return ToolCallSequence(
            id=row.id,
            calls=[self._to_domain_tool_call(call) for call in calls],
            created_time=row.created_at,
        )

    def _to_domain_tool_call(self, row: SessionToolCallModel) -> ToolCall:
        function = ToolFunction(
            name=row.function_name, arguments=row.function_arguments or {}
        )
        if row.state == _COMPLETED_STATE:
            return CompletedCall(
                id=row.call_id, function=function, result=row.result or ""
            )
        if row.state == _FAILED_STATE:
            return FailedCall(id=row.call_id, function=function, error=row.error or "")
        return PendingCall(id=row.call_id, function=function)

    def _to_orm_tool_call_sequence(
        self,
        *,
        sequence: ToolCallSequence,
        session_id: UUID,
        position: int,
        existing_sequence: SessionToolCallSequenceModel | None = None,
    ) -> SessionToolCallSequenceModel:
        orm = existing_sequence or SessionToolCallSequenceModel(id=sequence.id)
        orm.session_id = session_id
        orm.position = position
        orm.created_at = sequence.created_at

        existing_calls = {call.call_id: call for call in orm.calls}
        orm.calls = [
            self._to_orm_tool_call(
                call=call,
                sequence_id=sequence.id,
                position=call_position,
                existing_call=existing_calls.get(call.id),
            )
            for call_position, call in enumerate(sequence.calls)
        ]
        return orm

    def _to_orm_tool_call(
        self,
        *,
        call: ToolCall,
        sequence_id: UUID,
        position: int,
        existing_call: SessionToolCallModel | None = None,
    ) -> SessionToolCallModel:
        if isinstance(call, CompletedCall):
            state, result, error = _COMPLETED_STATE, call.result, None
        elif isinstance(call, FailedCall):
            state, result, error = _FAILED_STATE, None, call.error
        else:
            state, result, error = _PENDING_STATE, None, None

        orm = existing_call or SessionToolCallModel()
        orm.sequence_id = sequence_id
        orm.position = position
        orm.call_id = call.id
        orm.function_name = call.function.name
        orm.function_arguments = dict(call.function.arguments)
        orm.state = state
        orm.result = result
        orm.error = error
        return orm

    def _to_domain_follow_up_group(
        self, row: SessionFollowUpQuestionGroupModel
    ) -> FollowUpQuestionGroup:
        questions = sorted(row.questions, key=lambda q: q.position)
        return FollowUpQuestionGroup(
            id=row.id,
            questions=[self._to_domain_follow_up_question(q) for q in questions],
            created_time=row.created_at,
        )

    def _to_domain_follow_up_question(
        self, row: SessionFollowUpQuestionModel
    ) -> FollowUpQuestion:
        options_payload = row.options or []
        options = [
            FollowUpOption(id=str(item.get("id", "")), label=str(item.get("label", "")))
            for item in options_payload
            if isinstance(item, dict)
        ]
        return FollowUpQuestion(
            id=row.id,
            question=row.question,
            options=options,
            state=FollowUpQuestionState(row.state),
            answer_text=row.answer_text,
            answered_option_id=row.answered_option_id,
            created_time=row.created_at,
        )

    def _to_orm_follow_up_group(
        self,
        *,
        group: FollowUpQuestionGroup,
        session_id: UUID,
        position: int,
        existing_group: SessionFollowUpQuestionGroupModel | None = None,
    ) -> SessionFollowUpQuestionGroupModel:
        orm = existing_group or SessionFollowUpQuestionGroupModel(id=group.id)
        orm.session_id = session_id
        orm.position = position
        orm.created_at = group.created_at

        existing_questions = {question.id: question for question in orm.questions}
        orm.questions = [
            self._to_orm_follow_up_question(
                question=question,
                group_id=group.id,
                position=question_position,
                existing_question=existing_questions.get(question.id),
            )
            for question_position, question in enumerate(group.questions)
        ]
        return orm

    def _to_orm_follow_up_question(
        self,
        *,
        question: FollowUpQuestion,
        group_id: UUID,
        position: int,
        existing_question: SessionFollowUpQuestionModel | None = None,
    ) -> SessionFollowUpQuestionModel:
        orm = existing_question or SessionFollowUpQuestionModel(id=question.id)
        orm.group_id = group_id
        orm.position = position
        orm.question = question.question
        orm.options = [
            {"id": option.id, "label": option.label} for option in question.options
        ]
        orm.state = question.state.value
        orm.answer_text = question.answer_text
        orm.answered_option_id = question.answered_option_id
        orm.created_at = question.created_at
        return orm

    def _to_orm_playlist(
        self,
        *,
        domain_playlist: Playlist | None,
        session_id: UUID,
        existing_playlist: SessionPlaylistModel | None = None,
    ) -> SessionPlaylistModel | None:
        if domain_playlist is None:
            return None

        orm_playlist = (
            existing_playlist
            if existing_playlist is not None
            and existing_playlist.id == domain_playlist.id
            else SessionPlaylistModel(id=domain_playlist.id)
        )
        orm_playlist.session_id = session_id
        orm_playlist.name = domain_playlist.name
        orm_playlist.created_at = domain_playlist.created_at

        existing_tracks = {track.id: track for track in orm_playlist.tracks}
        orm_playlist.tracks = [
            self._to_orm_track(
                track=track,
                playlist_id=domain_playlist.id,
                position=index,
                existing_track=existing_tracks.get(track.id),
            )
            for index, track in enumerate(domain_playlist.tracks)
        ]
        return orm_playlist

    def _to_domain_playlist(
        self,
        orm_playlist: SessionPlaylistModel | None,
    ) -> Playlist | None:
        if orm_playlist is None:
            return None

        tracks = sorted(orm_playlist.tracks, key=lambda item: item.position)
        return Playlist(
            id=orm_playlist.id,
            name=orm_playlist.name,
            tracks=[self._to_domain_track(track) for track in tracks],
            created_time=orm_playlist.created_at,
        )

    def _to_orm_track(
        self,
        *,
        track: PlaylistTrack,
        playlist_id: UUID,
        position: int,
        existing_track: PlaylistTrackModel | None = None,
    ) -> PlaylistTrackModel:
        orm = existing_track or PlaylistTrackModel(id=track.id)
        orm.playlist_id = playlist_id
        orm.position = position
        orm.title = track.title
        orm.artist = track.artist
        orm.year = track.year
        orm.cover_url = track.cover_url
        orm.created_at = track.created_at
        return orm

    def _to_domain_track(self, orm_track: PlaylistTrackModel) -> PlaylistTrack:
        return PlaylistTrack(
            id=orm_track.id,
            title=orm_track.title,
            artist=orm_track.artist,
            year=orm_track.year,
            cover_url=orm_track.cover_url,
            created_time=orm_track.created_at,
        )
