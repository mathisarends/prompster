from collections.abc import Iterable

from pydantic import TypeAdapter

from backend.features.session.presentation.events import ServerEvent

_SERVER_EVENT_ADAPTER: TypeAdapter[ServerEvent] = TypeAdapter(ServerEvent)


def to_sse(event: ServerEvent) -> str:
    event_type = getattr(event, "type")
    event_name = getattr(event_type, "value", event_type)
    data = _SERVER_EVENT_ADAPTER.dump_json(event, by_alias=True).decode()
    return f"event: {event_name}\ndata: {data}\n\n"


def to_sse_many(events: Iterable[ServerEvent]) -> str:
    return "".join(to_sse(event) for event in events)
