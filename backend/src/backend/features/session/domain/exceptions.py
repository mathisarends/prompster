class SessionNotFoundError(Exception):
    pass


class SessionAccessDeniedError(Exception):
    pass


class PlaylistTrackNotFoundError(Exception):
    pass


class SessionPlaylistEmptyError(Exception):
    pass


class SessionPlaylistMissingSpotifyTracksError(Exception):
    pass


class SessionExportRequiresSpotifyConnectionError(Exception):
    pass


class ToolCallNotFoundError(Exception):
    pass


class ToolCallAlreadyResolvedError(Exception):
    pass


class NoPendingToolCallSequenceError(Exception):
    pass


class PendingToolCallsError(Exception):
    pass


class NoCurrentAssistantMessageError(Exception):
    pass


class FollowUpQuestionNotFoundError(Exception):
    pass


class FollowUpQuestionAlreadyResolvedError(Exception):
    pass


class FollowUpQuestionOutOfOrderError(Exception):
    pass


class FollowUpOptionNotFoundError(Exception):
    pass


class EmptyFollowUpAnswerError(Exception):
    pass


class NoPendingFollowUpGroupError(Exception):
    pass


class PendingFollowUpQuestionsError(Exception):
    pass
