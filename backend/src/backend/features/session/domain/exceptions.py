class SessionNotFoundError(Exception):
    pass


class SessionAccessDeniedError(Exception):
    pass


class PlaylistTrackNotFoundError(Exception):
    pass


class ToolCallNotFoundError(Exception):
    pass


class ToolCallAlreadyResolvedError(Exception):
    pass


class NoPendingToolCallGroupError(Exception):
    pass


class PendingToolCallsError(Exception):
    pass


class NoCurrentAssistantMessageError(Exception):
    pass
