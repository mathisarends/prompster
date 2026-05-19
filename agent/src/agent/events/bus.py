import logging
import asyncio
from collections.abc import Awaitable, Callable

from agent.events.views import Event


logger = logging.getLogger(__name__)


type EventHandler[T: Event] = Callable[[T], Awaitable[None]]


class EventBus:
    def __init__(self):
        self._handlers: dict[type[Event], list[EventHandler]] = {}
        self._wildcard_handlers: list[Callable[[Event], Awaitable[None]]] = []

    def subscribe[T: Event](
        self, event_type: type[T], handler: EventHandler[T]
    ) -> None:
        self._handlers.setdefault(event_type, []).append(handler)
        logger.debug(f"Subscribed to {event_type.__name__}")

    def subscribe_all(self, handler: Callable[[Event], Awaitable[None]]) -> None:
        self._wildcard_handlers.append(handler)

    def unsubscribe[T: Event](
        self, event_type: type[T], handler: EventHandler[T]
    ) -> None:
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

    async def dispatch[T: Event](self, event: T) -> T:
        event_type = type(event)

        handlers = self._handlers.get(event_type, []) + self._wildcard_handlers

        if not handlers:
            return event

        results = await asyncio.gather(
            *[handler(event) for handler in handlers],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    f"Handler failed for {event_type.__name__}: {result}",
                    exc_info=result,
                )
                if hasattr(event, "reject"):
                    event.reject(result)

        return event
