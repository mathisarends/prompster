class SessionNotFoundError(Exception):
    pass


class SessionAccessDeniedError(Exception):
    pass


class InvalidSessionPhaseTransitionError(Exception):
    pass


class PlaylistTrackNotFoundError(Exception):
    pass


class PlaylistTrackPinnedError(Exception):
    pass


class PlaylistTrackLimitExceededError(Exception):
    pass


class PlaylistReferenceNotFoundError(Exception):
    pass


class ArtistReferenceNotFoundError(Exception):
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


class UserCurationEventNotFoundError(Exception):
    pass


class UserCurationEventAlreadyConsumedError(Exception):
    pass


class UserCurationEventMissingTrackYearError(Exception):
    pass
