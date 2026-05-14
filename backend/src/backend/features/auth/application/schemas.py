from pydantic import BaseModel


class AuthSession(BaseModel):
    jwt_token: str
    refresh_token: str
