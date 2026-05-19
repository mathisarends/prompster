from backend.presentation.schema import Schema


class ErrorDto(Schema):
    detail: str
