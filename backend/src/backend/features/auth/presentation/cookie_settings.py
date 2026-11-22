from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class AuthCookieSettings:
    access_token_name: str
    refresh_token_name: str
    access_token_max_age_seconds: int
    refresh_token_max_age_seconds: int
    same_site_dev: Literal["lax", "strict", "none"]
    same_site_prod: Literal["lax", "strict", "none"]
