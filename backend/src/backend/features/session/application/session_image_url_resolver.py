import asyncio
from collections.abc import Mapping
from itertools import chain

from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.domain import Session, UserMessage

_SIGNED_URL_TTL_SECONDS = 60 * 60 * 24


class SessionImageUrlResolver:
    """Resolves the private image references in a session for API delivery."""

    def __init__(self, message_attachment_store: MessageAttachmentStore) -> None:
        self._message_attachment_store = message_attachment_store

    async def resolve(self, *, session: Session) -> Mapping[str, str]:
        attachments = chain.from_iterable(
            entry.image_attachments
            for entry in session.entries
            if isinstance(entry, UserMessage)
        )
        storage_keys = tuple(
            dict.fromkeys(attachment.storage_key for attachment in attachments)
        )
        urls = await asyncio.gather(
            *(
                self._message_attachment_store.create_signed_url(
                    storage_key=storage_key,
                    expires_in_seconds=_SIGNED_URL_TTL_SECONDS,
                )
                for storage_key in storage_keys
            )
        )
        return dict(zip(storage_keys, urls, strict=True))
