from datetime import datetime
from uuid import UUID

from backend.features.session.domain import (
    ArtistReference,
    AssistantMessage,
    CompletedCall,
    FailedCall,
    ImageAttachment,
    OnboardingQuestion,
    PendingCall,
    Phase,
    Playlist,
    PlaylistReference,
    PlaylistTrack,
    Session,
    SessionEntry,
    ToolActionType,
    ToolCall,
    ToolCallSequence,
    ToolFunction,
    ToolResultItem,
    UserCurationEvent,
    UserCurationEventType,
    UserMessage,
    UserMessageAttachment,
    UserMessageAttachmentKind,
)
from backend.platform.database import (
    PlaylistTrackModel,
    SessionArtistReferenceModel,
    SessionAssistantMessageModel,
    SessionModel,
    SessionOnboardingQuestionModel,
    SessionPlaylistModel,
    SessionPlaylistReferenceModel,
    SessionToolCallModel,
    SessionToolCallSequenceModel,
    SessionUserCurationEventModel,
    SessionUserMessageAttachmentModel,
    SessionUserMessageImageAttachmentModel,
    SessionUserMessageModel,
)


class SessionOrmMapper:
    def to_domain(self, orm: SessionModel) -> Session:
        entries: list[tuple[int, SessionEntry]] = []
        for row in orm.user_messages:
            entries.append((row.position, self._to_domain_user_message(row)))
        for row in orm.assistant_messages:
            entries.append((row.position, self._to_domain_assistant_message(row)))
        for row in orm.tool_call_sequences:
            entries.append((row.position, self._to_domain_tool_call_sequence(row)))
        entries.sort(key=lambda item: item[0])
        user_curation_events = sorted(
            orm.user_curation_events,
            key=lambda item: item.position,
        )
        ordered_entries = [entry for _, entry in entries]
        domain_user_curation_events = [
            event
            for event in (
                self._to_domain_user_curation_event(event)
                for event in user_curation_events
            )
            if event is not None
        ]
        playlist_references = sorted(
            orm.playlist_references,
            key=lambda item: item.position,
        )
        artist_references = sorted(
            orm.artist_references,
            key=lambda item: item.position,
        )
        onboarding_questions = sorted(
            orm.onboarding_questions,
            key=lambda item: item.sequence_number,
        )
        self._hydrate_user_message_curation_events(
            entries=ordered_entries,
            events=domain_user_curation_events,
        )

        domain_playlist_references = [
            self._to_domain_playlist_reference(reference)
            for reference in playlist_references
        ]
        domain_artist_references = [
            self._to_domain_artist_reference(reference)
            for reference in artist_references
        ]
        domain_onboarding_questions = [
            self._to_domain_onboarding_question(question)
            for question in onboarding_questions
        ]
        return Session.restore(
            id=orm.id,
            created_at=orm.created_at,
            title=orm.title,
            entries=ordered_entries,
            owner_id=orm.owner_id,
            is_starred=orm.is_starred,
            phase=Phase(orm.phase or Phase.ONBOARDING),
            playlist=self._to_domain_playlist(orm.playlist),
            playlist_pdf_storage_key=orm.playlist_pdf_storage_key,
            playlist_pdf_fingerprint=orm.playlist_pdf_fingerprint,
            user_curation_events=domain_user_curation_events,
            playlist_references=domain_playlist_references,
            artist_references=domain_artist_references,
            onboarding_questions=domain_onboarding_questions,
        )

    def to_orm(self, domain: Session) -> SessionModel:
        orm = SessionModel(id=domain.id)
        self.sync(orm=orm, session=domain)
        return orm

    def sync(self, *, orm: SessionModel, session: Session) -> None:
        orm.title = session.title
        orm.owner_id = session.owner_id
        orm.is_starred = session.is_starred
        orm.phase = session.phase
        orm.playlist_pdf_storage_key = session.playlist_pdf_storage_key
        orm.playlist_pdf_fingerprint = session.playlist_pdf_fingerprint
        orm.created_at = session.created_at
        orm.last_activity_at = self._resolve_last_activity_at(session)

        session_id = orm.id or session.id
        self._sync_entries(orm=orm, session_id=session_id, entries=session.entries)
        self._sync_user_curation_events(
            orm=orm,
            session_id=session_id,
            events=session.user_curation_events,
        )
        self._sync_playlist_references(
            orm=orm,
            session_id=session_id,
            references=session.playlist_references,
        )
        self._sync_artist_references(
            orm=orm,
            session_id=session_id,
            references=session.artist_references,
        )
        self._sync_onboarding_questions(
            orm=orm,
            session_id=session_id,
            questions=session.onboarding_questions,
        )
        orm.playlist = self._to_orm_playlist(
            domain_playlist=session.playlist,
            session_id=session_id,
            existing_playlist=orm.playlist,
        )

    def _hydrate_user_message_curation_events(
        self,
        *,
        entries: list[SessionEntry],
        events: list[UserCurationEvent],
    ) -> None:
        for event in events:
            self._bind_user_curation_event_to_message(entries=entries, event=event)

    def _bind_user_curation_event_to_message(
        self,
        *,
        entries: list[SessionEntry],
        event: UserCurationEvent,
    ) -> None:
        if self._is_user_curation_event_bound(entries=entries, event_id=event.id):
            return

        message = self._find_target_user_message_for_event(entries=entries, event=event)
        if message is None:
            return

        message.user_curation_events = (*message.user_curation_events, event)

    def _find_target_user_message_for_event(
        self,
        *,
        entries: list[SessionEntry],
        event: UserCurationEvent,
    ) -> UserMessage | None:
        for entry in entries:
            if isinstance(entry, UserMessage) and entry.created_at >= event.created_at:
                return entry
        return None

    def _is_user_curation_event_bound(
        self,
        *,
        entries: list[SessionEntry],
        event_id: UUID,
    ) -> bool:
        for entry in entries:
            if not isinstance(entry, UserMessage):
                continue
            if any(event.id == event_id for event in entry.user_curation_events):
                return True
        return False

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
        user_rows: list[SessionUserMessageModel] = []
        assistant_rows: list[SessionAssistantMessageModel] = []
        tool_sequence_rows: list[SessionToolCallSequenceModel] = []

        for position, entry in enumerate(entries):
            match entry:
                case UserMessage():
                    user_rows.append(
                        self._to_orm_user_message(
                            message=entry,
                            session_id=session_id,
                            position=position,
                            existing_message=existing_user_rows.get(entry.id),
                        )
                    )
                case AssistantMessage():
                    row = existing_assistant_rows.get(entry.id)
                    if row is None:
                        row = SessionAssistantMessageModel(id=entry.id)
                    row.session_id = session_id
                    row.position = position
                    row.content = entry.content
                    row.created_at = entry.created_at
                    assistant_rows.append(row)
                case ToolCallSequence():
                    tool_sequence_rows.append(
                        self._to_orm_tool_call_sequence(
                            sequence=entry,
                            session_id=session_id,
                            position=position,
                            existing_sequence=existing_tool_sequence_rows.get(entry.id),
                        )
                    )

        orm.user_messages = user_rows
        orm.assistant_messages = assistant_rows
        orm.tool_call_sequences = tool_sequence_rows

    def _to_orm_user_message(
        self,
        *,
        message: UserMessage,
        session_id: UUID,
        position: int,
        existing_message: SessionUserMessageModel | None = None,
    ) -> SessionUserMessageModel:
        orm_message = (
            existing_message
            if existing_message is not None
            else SessionUserMessageModel(id=message.id)
        )
        orm_message.session_id = session_id
        orm_message.position = position
        orm_message.content = message.content
        orm_message.created_at = message.created_at

        existing_attachments = {row.position: row for row in orm_message.attachments}
        existing_image_attachments = {
            row.id: row for row in orm_message.image_attachments if row.id is not None
        }
        orm_message.attachments = [
            self._to_orm_user_message_attachment(
                attachment=attachment,
                user_message_id=message.id,
                position=attachment_position,
                existing_attachment=existing_attachments.get(attachment_position),
            )
            for attachment_position, attachment in enumerate(message.attachments)
        ]
        orm_message.image_attachments = [
            self._to_orm_user_message_image_attachment(
                attachment=attachment,
                user_message_id=message.id,
                existing_attachment=existing_image_attachments.get(attachment.id),
            )
            for attachment in message.image_attachments
        ]
        return orm_message

    def _to_orm_user_message_attachment(
        self,
        *,
        attachment: UserMessageAttachment,
        user_message_id: UUID,
        position: int,
        existing_attachment: SessionUserMessageAttachmentModel | None = None,
    ) -> SessionUserMessageAttachmentModel:
        orm_attachment = (
            existing_attachment
            if existing_attachment is not None
            else SessionUserMessageAttachmentModel()
        )
        orm_attachment.user_message_id = user_message_id
        orm_attachment.position = position
        orm_attachment.kind = attachment.kind.value
        orm_attachment.external_id = attachment.external_id
        orm_attachment.title = attachment.title
        orm_attachment.subtitle = attachment.subtitle
        orm_attachment.image_url = attachment.image_url
        orm_attachment.spotify_id = attachment.spotify_id
        return orm_attachment

    def _to_orm_user_message_image_attachment(
        self,
        *,
        attachment: ImageAttachment,
        user_message_id: UUID,
        existing_attachment: SessionUserMessageImageAttachmentModel | None = None,
    ) -> SessionUserMessageImageAttachmentModel:
        orm_attachment = (
            existing_attachment
            if existing_attachment is not None
            else SessionUserMessageImageAttachmentModel(id=attachment.id)
        )
        orm_attachment.user_message_id = user_message_id
        orm_attachment.storage_key = attachment.storage_key
        orm_attachment.content_type = attachment.content_type
        orm_attachment.file_name = attachment.file_name
        orm_attachment.size_bytes = attachment.size_bytes
        orm_attachment.created_at = attachment.created_at
        return orm_attachment

    def _sync_user_curation_events(
        self,
        *,
        orm: SessionModel,
        session_id: UUID,
        events: tuple[UserCurationEvent, ...],
    ) -> None:
        existing_user_curation_event_rows = {
            row.id: row for row in orm.user_curation_events if row.id is not None
        }

        user_curation_event_rows: list[SessionUserCurationEventModel] = []
        for position, event in enumerate(events):
            row = existing_user_curation_event_rows.get(event.id)
            if row is None:
                row = SessionUserCurationEventModel(id=event.id)
            row.session_id = session_id
            row.position = position
            row.event_type = event.event_type.value
            row.track_id = event.track_id
            row.track_title = event.track_title
            row.track_artist = event.track_artist
            row.track_year = event.track_year
            row.track_spotify_uri = event.track_spotify_uri
            row.track_cover_url = event.track_cover_url
            row.consumed = event.consumed
            row.created_at = event.created_at
            user_curation_event_rows.append(row)

        orm.user_curation_events = user_curation_event_rows

    def _sync_playlist_references(
        self,
        *,
        orm: SessionModel,
        session_id: UUID,
        references: tuple[PlaylistReference, ...],
    ) -> None:
        existing_rows = {row.id: row for row in orm.playlist_references if row.id}

        rows: list[SessionPlaylistReferenceModel] = []
        for position, reference in enumerate(references):
            row = existing_rows.get(reference.id)
            if row is None:
                row = SessionPlaylistReferenceModel(id=reference.id)
            row.session_id = session_id
            row.position = position
            row.spotify_playlist_id = reference.spotify_playlist_id
            row.name = reference.name
            row.owner = reference.owner
            row.cover_url = reference.cover_url
            row.total_tracks = reference.total_tracks
            row.created_at = reference.created_at
            rows.append(row)

        orm.playlist_references = rows

    def _sync_artist_references(
        self,
        *,
        orm: SessionModel,
        session_id: UUID,
        references: tuple[ArtistReference, ...],
    ) -> None:
        existing_rows = {row.id: row for row in orm.artist_references if row.id}

        rows: list[SessionArtistReferenceModel] = []
        for position, reference in enumerate(references):
            row = existing_rows.get(reference.id)
            if row is None:
                row = SessionArtistReferenceModel(id=reference.id)
            row.session_id = session_id
            row.position = position
            row.spotify_artist_id = reference.spotify_artist_id
            row.name = reference.name
            row.image_url = reference.image_url
            row.genres = list(reference.genres)
            row.followers = reference.followers
            row.popularity = reference.popularity
            row.created_at = reference.created_at
            rows.append(row)

        orm.artist_references = rows

    def _sync_onboarding_questions(
        self,
        *,
        orm: SessionModel,
        session_id: UUID,
        questions: tuple[OnboardingQuestion, ...],
    ) -> None:
        existing_rows = {row.id: row for row in orm.onboarding_questions if row.id}

        rows: list[SessionOnboardingQuestionModel] = []
        for question in questions:
            row = existing_rows.get(question.id)
            if row is None:
                row = SessionOnboardingQuestionModel(id=question.id)
            row.session_id = session_id
            row.sequence_number = question.sequence_number
            row.question_text = question.question_text
            row.hint = question.hint
            row.options = list(question.options)
            row.recommended_option = question.recommended_option
            row.selection_mode = question.selection_mode.value
            row.is_last_question = question.is_last_question
            row.answer = question.answer
            row.answers = list(question.answers)
            row.is_answered = question.is_answered
            row.answered_at = question.answered_at
            row.created_at = question.created_at
            rows.append(row)

        orm.onboarding_questions = rows

    def _resolve_last_activity_at(self, session: Session) -> datetime:
        latest = session.created_at
        for entry in session.entries:
            latest = max(latest, entry.created_at)
        for event in session.user_curation_events:
            latest = max(latest, event.created_at)
        for reference in (
            *session.playlist_references,
            *session.artist_references,
        ):
            latest = max(latest, reference.created_at)
        for question in session.onboarding_questions:
            latest = max(latest, question.created_at)
            if question.answered_at is not None:
                latest = max(latest, question.answered_at)
        return latest

    def _to_domain_user_curation_event(
        self, row: SessionUserCurationEventModel
    ) -> UserCurationEvent | None:
        try:
            event_type = UserCurationEventType(row.event_type)
        except ValueError:
            return None

        return UserCurationEvent.restore(
            id=row.id,
            created_at=row.created_at,
            event_type=event_type,
            track_id=row.track_id,
            track_title=row.track_title,
            track_artist=row.track_artist,
            track_year=row.track_year,
            track_spotify_uri=row.track_spotify_uri,
            track_cover_url=row.track_cover_url,
            consumed=row.consumed,
        )

    def _to_domain_playlist_reference(
        self, row: SessionPlaylistReferenceModel
    ) -> PlaylistReference:
        return PlaylistReference.restore(
            id=row.id,
            created_at=row.created_at,
            spotify_playlist_id=row.spotify_playlist_id,
            name=row.name,
            owner=row.owner,
            cover_url=row.cover_url,
            total_tracks=row.total_tracks,
        )

    def _to_domain_artist_reference(
        self, row: SessionArtistReferenceModel
    ) -> ArtistReference:
        return ArtistReference.restore(
            id=row.id,
            created_at=row.created_at,
            spotify_artist_id=row.spotify_artist_id,
            name=row.name,
            image_url=row.image_url,
            genres=tuple(row.genres or ()),
            followers=row.followers,
            popularity=row.popularity,
        )

    def _to_domain_onboarding_question(
        self, row: SessionOnboardingQuestionModel
    ) -> OnboardingQuestion:
        return OnboardingQuestion.restore(
            id=row.id,
            created_at=row.created_at,
            sequence_number=row.sequence_number,
            question_text=row.question_text,
            hint=row.hint,
            options=tuple(row.options or ()),
            recommended_option=row.recommended_option,
            selection_mode=row.selection_mode or "single_select",
            is_last_question=row.is_last_question,
            answer=row.answer,
            answers=tuple(row.answers or ()) or None,
            is_answered=row.is_answered,
            answered_at=row.answered_at,
        )

    def _to_domain_user_message(self, row: SessionUserMessageModel) -> UserMessage:
        attachments = sorted(row.attachments, key=lambda item: item.position)
        image_attachments = sorted(
            row.image_attachments,
            key=lambda item: item.created_at or row.created_at,
        )
        domain_attachments = [
            self._to_domain_user_message_attachment(attachment)
            for attachment in attachments
        ]
        domain_image_attachments = [
            self._to_domain_user_message_image_attachment(attachment)
            for attachment in image_attachments
        ]
        return UserMessage.restore(
            id=row.id,
            created_at=row.created_at,
            content=row.content,
            attachments=domain_attachments,
            image_attachments=domain_image_attachments,
        )

    def _to_domain_user_message_attachment(
        self,
        row: SessionUserMessageAttachmentModel,
    ) -> UserMessageAttachment:
        return UserMessageAttachment(
            kind=UserMessageAttachmentKind(row.kind),
            external_id=row.external_id,
            title=row.title,
            subtitle=row.subtitle,
            image_url=row.image_url,
            spotify_id=row.spotify_id,
        )

    def _to_domain_user_message_image_attachment(
        self,
        row: SessionUserMessageImageAttachmentModel,
    ) -> ImageAttachment:
        return ImageAttachment.restore(
            id=row.id,
            created_at=row.created_at,
            storage_key=row.storage_key,
            content_type=row.content_type,
            file_name=row.file_name,
            size_bytes=row.size_bytes,
        )

    def _to_domain_assistant_message(
        self, row: SessionAssistantMessageModel
    ) -> AssistantMessage:
        return AssistantMessage.restore(
            id=row.id, created_at=row.created_at, content=row.content
        )

    def _to_domain_tool_call_sequence(
        self, row: SessionToolCallSequenceModel
    ) -> ToolCallSequence:
        calls = sorted(row.calls, key=lambda c: c.position)
        domain_calls = [self._to_domain_tool_call(call) for call in calls]
        return ToolCallSequence.restore(
            id=row.id,
            created_at=row.created_at,
            calls=domain_calls,
            label=row.label,
        )

    def _to_domain_tool_call(self, row: SessionToolCallModel) -> ToolCall:
        function = ToolFunction(
            name=row.function_name,
            arguments=row.function_arguments or {},
            status_label=row.function_status_label,
            action_type=self._to_tool_action_type(row.function_action_type),
            is_onboarding_question=row.function_is_onboarding_question,
        )
        if row.state == _COMPLETED_STATE:
            return CompletedCall(
                id=row.call_id,
                function=function,
                result=row.result or "",
                items=self._to_domain_tool_result_items(row.result_items),
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
        orm = (
            existing_sequence
            if existing_sequence is not None
            else SessionToolCallSequenceModel(id=sequence.id)
        )
        orm.session_id = session_id
        orm.position = position
        orm.label = sequence.label
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
            result_items = self._to_orm_tool_result_items(call.items)
        elif isinstance(call, FailedCall):
            state, result, error = _FAILED_STATE, None, call.error
            result_items = None
        else:
            state, result, error = _PENDING_STATE, None, None
            result_items = None

        orm = existing_call if existing_call is not None else SessionToolCallModel()
        orm.sequence_id = sequence_id
        orm.position = position
        orm.call_id = call.id
        orm.function_name = call.function.name
        orm.function_arguments = dict(call.function.arguments)
        orm.function_status_label = call.function.status_label
        orm.function_action_type = (
            call.function.action_type.value if call.function.action_type else None
        )
        orm.function_is_onboarding_question = call.function.is_onboarding_question
        orm.state = state
        orm.result = result
        orm.error = error
        orm.result_items = result_items
        return orm

    def _to_orm_tool_result_items(
        self, items: tuple[ToolResultItem, ...]
    ) -> list[dict] | None:
        if not items:
            return None
        return [
            {
                "title": item.title,
                "cover_url": item.cover_url,
                "artist": item.artist,
                "track_uri": item.track_uri,
            }
            for item in items
        ]

    def _to_domain_tool_result_items(
        self, rows: list[dict] | None
    ) -> tuple[ToolResultItem, ...]:
        if not rows:
            return ()
        return tuple(
            ToolResultItem(
                title=row.get("title", ""),
                cover_url=row.get("cover_url"),
                artist=row.get("artist"),
                track_uri=row.get("track_uri"),
            )
            for row in rows
        )

    def _to_tool_action_type(self, value: str | None) -> ToolActionType | None:
        if value is None:
            return None
        try:
            return ToolActionType(value)
        except ValueError:
            return None

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
        orm_playlist.spotify_playlist_id = domain_playlist.spotify_playlist_id
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
        domain_tracks = [self._to_domain_track(track) for track in tracks]
        return Playlist.restore(
            id=orm_playlist.id,
            created_at=orm_playlist.created_at,
            name=orm_playlist.name,
            spotify_playlist_id=orm_playlist.spotify_playlist_id,
            tracks=domain_tracks,
        )

    def _to_orm_track(
        self,
        *,
        track: PlaylistTrack,
        playlist_id: UUID,
        position: int,
        existing_track: PlaylistTrackModel | None = None,
    ) -> PlaylistTrackModel:
        orm = (
            existing_track
            if existing_track is not None
            else PlaylistTrackModel(id=track.id)
        )
        orm.playlist_id = playlist_id
        orm.position = position
        orm.title = track.title
        orm.artist = track.artist
        orm.year = track.year
        orm.spotify_uri = track.spotify_uri
        orm.cover_url = track.cover_url
        orm.created_at = track.created_at
        return orm

    def _to_domain_track(self, orm_track: PlaylistTrackModel) -> PlaylistTrack:
        if orm_track.year is None:
            raise ValueError(f"Playlist track {orm_track.id} is missing required year.")

        return PlaylistTrack.restore(
            id=orm_track.id,
            created_at=orm_track.created_at,
            title=orm_track.title,
            artist=orm_track.artist,
            year=orm_track.year,
            spotify_uri=orm_track.spotify_uri,
            cover_url=orm_track.cover_url,
        )


_PENDING_STATE = "pending"
_COMPLETED_STATE = "completed"
_FAILED_STATE = "failed"
