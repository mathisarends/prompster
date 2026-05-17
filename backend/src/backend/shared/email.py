from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailMessage:
    to: str
    subject: str
    html: str
    from_email: str = "noreply@yourdomain.com"


class EmailSender(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> None: ...
