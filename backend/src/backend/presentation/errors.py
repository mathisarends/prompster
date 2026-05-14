from pydantic import BaseModel


class ErrorDto(BaseModel):
    detail: str
