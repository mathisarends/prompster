from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionRpcContext:
    """Authenticated identity and session shared by calls on one socket."""

    session_id: UUID
    user_id: UUID
