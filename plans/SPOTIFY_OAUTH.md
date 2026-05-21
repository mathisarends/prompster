# Spotify OAuth Integration — Implementierungsplan

## Ziel & Abgrenzung

Wir wollen einem **bereits eingeloggten User** (Google-Login bleibt der einzige Login-Mechanismus) erlauben, optional sein Spotify-Konto zu verbinden. Nach der Verbindung speichern wir den Spotify-Refresh-Token verschlüsselt in einer **separaten `oauth_connections`-Tabelle** (nicht am `User`). Das Frontend bekommt für das Web-Playback-SDK kurzlebige Access-Tokens über einen authentifizierten Proxy-Endpoint — Refresh-Token verlässt das Backend nie.

**Wichtig:** Das ist kein Login-Flow wie Google. Das ist **Account-Linking** — der Endpoint, der den Flow startet, muss authentifiziert sein (`AuthenticatedUserId`). Spotify dient ausschließlich der Resource-Berechtigung (Playback, Playlists lesen/schreiben), nicht der Identifikation.

## Warum separate Tabelle?

- `users` bleibt clean — Spotify ist ein optionales, austauschbares Add-on, kein Kern-Attribut der User-Identität.
- Skaliert auf weitere Provider (Apple Music, SoundCloud, …) ohne Schema-Migration am User.
- Connection lässt sich revoken/neu anlegen ohne den User-Record zu touchen (kein Risiko Login-Daten zu beschädigen).
- Ein User könnte später mehrere Connections pro Provider haben (z.B. Privat/Business) — Tabellen-Struktur erlaubt das, falls fachlich gewünscht. Für MVP: Unique `(user_id, provider)`.

```
users                    oauth_connections
─────────────────        ──────────────────────────────────
id              ◄────────  user_id (FK, indexed)
email                      provider                  ("spotify")
name                       provider_user_id          (Spotify-User-ID)
google_subject             refresh_token_encrypted   (bytes)
created_at                 scope                     (granted scopes)
                           connected_at
                           created_at
```

## Architektur-Übersicht

```
1. CONNECT (Account-Linking, einmalig)

   User klickt "Connect Spotify" (Frontend, eingeloggt)
           │
           ▼
   GET /auth/spotify/connect          ← authentifiziert
           │ erstellt signed state-Cookie + user_id-Binding
           ▼
   Redirect → accounts.spotify.com/authorize
           │
           ▼
   GET /auth/spotify/callback?code&state
           │ validiert state, tauscht code gegen tokens,
           │ verschlüsselt refresh_token, schreibt in oauth_connections
           ▼
   HTML-Popup-Response → schließt sich + postMessage ans Frontend


2. TOKEN-PROXY (jedes Mal wenn FE Playback SDK starten will)

   Frontend ruft /auth/spotify/token (authentifiziert via Session-Cookie)
           │
           ▼
   Backend lädt OAuthConnection, entschlüsselt refresh_token
           │
           ▼
   Backend ruft Spotify /api/token (grant_type=refresh_token)
           │
           ▼
   Backend gibt { access_token, expires_in } ans Frontend zurück
   (kurzlebig, ~3600s, nur in-memory im Browser)
           │
           ▼
   Frontend gibt access_token an Spotify Web Playback SDK
   Frontend re-fetcht vor Ablauf
```

## Frontend-Exposure: Warum Token-Proxy?

Das Web-Playback-SDK läuft im Browser und braucht zwangsläufig einen gültigen Spotify-Access-Token im Client. Wir können das nicht vermeiden — aber wir können das Schadensfenster minimieren:

- **Refresh-Token verlässt das Backend nie** — der Browser sieht nur den Access-Token, der nach ~1h sowieso tot ist.
- **Access-Token wird nicht im LocalStorage persistiert** — nur in JS-Memory; bei Reload wird neu gefetcht.
- **Endpoint ist authentifiziert** über unser eigenes Session-Cookie — XSS-Risiko = vergleichbar mit dem Risiko, die App-Session selbst zu kompromittieren.
- **Scope minimal** — nur was die App tatsächlich braucht.

Das ist der Standard-Pattern (Spotify dokumentiert es so selbst für "Authorization Code with PKCE"; wir machen denselben Effekt server-seitig mit unserem Refresh-Token-Store).

## Änderungen im Detail

### 1. Settings — `auth_settings.py`

Die `SpotifyAuthSettings`-Klasse ist bereits angelegt, aber unvollständig. Ergänzen analog zu `GoogleAuthSettings`:

```python
class SpotifyAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="SPOTIFY_",
    )

    client_id: str = Field(
        default="",
        validation_alias=AliasChoices("SPOTIFY_CLIENT_ID", "spotify_client_id"),
    )
    client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("SPOTIFY_CLIENT_SECRET", "spotify_client_secret"),
    )
    redirect_uri: str = Field(
        default="",
        validation_alias=AliasChoices("SPOTIFY_REDIRECT_URI", "spotify_redirect_uri"),
    )
    authorization_endpoint: str = Field(
        default="https://accounts.spotify.com/authorize",
    )
    token_endpoint: str = Field(
        default="https://accounts.spotify.com/api/token",
    )
    userinfo_endpoint: str = Field(
        default="https://api.spotify.com/v1/me",
    )
    scope: str = Field(
        default=(
            "user-read-email "
            "streaming "
            "user-read-private "
            "playlist-modify-private playlist-modify-public"
        ),
    )

    @field_validator("redirect_uri", "authorization_endpoint", "token_endpoint", "userinfo_endpoint")
    @classmethod
    def validate_spotify_urls(cls, v: str) -> str:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("Spotify URLs must start with http:// or https://")
        return v.rstrip("/") if v else v
```

> `streaming` + `user-read-email` + `user-read-private` sind die Mindest-Scopes für das Web-Playback-SDK. `playlist-modify-*` für die App-Feature-Logik.

Zusätzlich am `AuthSettings`:

```python
spotify_oauth_state_cookie_name: str = "spotify_oauth_state"
spotify_token_encryption_key: str = ""  # Fernet-Key, MUSS in Prod gesetzt sein
```

`.env.example` ergänzen:
```
SPOTIFY_REDIRECT_URI=http://localhost:8000/auth/spotify/callback
SPOTIFY_TOKEN_ENCRYPTION_KEY=<fernet-key>
# Generiere via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Domain — neues `OAuthConnection`-Aggregate

Eigenes Feature-Modul `backend/src/backend/features/oauth_connections/` (parallel zu `auth`, `user`, `session`). Aufbau analog zu den anderen Features (`domain/`, `application/`, `infrastructure/`, `presentation/`).

`features/oauth_connections/domain/oauth_connection.py`:

```python
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.shared.ddd import Aggregate


class OAuthProvider(StrEnum):
    SPOTIFY = "spotify"


class OAuthConnection(Aggregate):
    def __init__(
        self,
        *,
        user_id: UUID,
        provider: OAuthProvider,
        provider_user_id: str,
        encrypted_refresh_token: bytes,
        scope: str,
        connected_at: datetime,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.user_id = user_id
        self.provider = provider
        self.provider_user_id = provider_user_id
        self.encrypted_refresh_token = encrypted_refresh_token
        self.scope = scope
        self.connected_at = connected_at

    def rotate_refresh_token(self, *, new_encrypted_refresh_token: bytes) -> None:
        # Spotify rotiert den refresh_token nicht garantiert, aber falls doch,
        # speichern wir den neuen.
        self.encrypted_refresh_token = new_encrypted_refresh_token
```

`features/oauth_connections/domain/repository.py`:

```python
from abc import ABC, abstractmethod
from uuid import UUID

from .oauth_connection import OAuthConnection, OAuthProvider


class OAuthConnectionRepository(ABC):
    @abstractmethod
    async def get(self, *, user_id: UUID, provider: OAuthProvider) -> OAuthConnection | None: ...

    @abstractmethod
    async def save(self, *, connection: OAuthConnection) -> OAuthConnection: ...

    @abstractmethod
    async def delete(self, *, user_id: UUID, provider: OAuthProvider) -> bool: ...

    @abstractmethod
    async def exists(self, *, user_id: UUID, provider: OAuthProvider) -> bool: ...
```

> Der `User`-Aggregate bleibt **komplett unverändert**. Keine Spotify-Felder dort.

### 3. Persistenz — neue Tabelle + Migration

**ORM** (`infrastructure/database/orm.py`):

```python
class OAuthConnectionModel(DatabaseEntity, table=True):
    __tablename__ = "oauth_connections"
    __table_args__ = (
        Index("ix_oauth_connections_user_provider", "user_id", "provider", unique=True),
    )

    user_id: UUID = Field(foreign_key="users.id", index=True)
    provider: str  # StrEnum-Wert, "spotify"
    provider_user_id: str = Field(index=True)
    refresh_token_encrypted: bytes
    scope: str
    connected_at: datetime = Field(sa_type=DateTime(timezone=True))
```

**Alembic-Migration** `0006_add_oauth_connections.py`:

```python
def upgrade() -> None:
    op.create_table(
        "oauth_connections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_user_id", sa.String(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_oauth_connections_user_provider",
        "oauth_connections",
        ["user_id", "provider"],
        unique=True,
    )
    op.create_index(
        "ix_oauth_connections_provider_user_id",
        "oauth_connections",
        ["provider_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_oauth_connections_provider_user_id", table_name="oauth_connections")
    op.drop_index("ix_oauth_connections_user_provider", table_name="oauth_connections")
    op.drop_table("oauth_connections")
```

> `ondelete="CASCADE"` — wenn ein User gelöscht wird, fliegen seine Connections automatisch raus.
> `unique=True` auf `(user_id, provider)` — pro User+Provider genau eine Verbindung. Reconnect ⇒ Upsert.

**Repository** `features/oauth_connections/infrastructure/repository.py` analog zu `SqlUserRepository`, baut auf der existierenden `Repository[ORM, Domain]`-Basis auf.

### 4. Verschlüsselung — `OAuthTokenCipher`

`features/oauth_connections/infrastructure/token_cipher.py`. Nutzt `cryptography.fernet` (symmetrisch, authenticated). Key aus `AuthSettings.spotify_token_encryption_key` (Name evtl. zu `oauth_token_encryption_key` umbenennen, da provider-agnostisch).

```python
from cryptography.fernet import Fernet, InvalidToken


class OAuthTokenCipher:
    def __init__(self, encryption_key: str) -> None:
        if not encryption_key:
            raise ValueError("OAuth token encryption key is not configured")
        self._fernet = Fernet(encryption_key.encode("utf-8"))

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("OAuth refresh token could not be decrypted") from exc
```

`cryptography` in `backend/pyproject.toml` als Dependency aufnehmen.

### 5. Application-Layer — Ports, Schemas, Handler, TokenService

**Schemas** (`features/oauth_connections/application/schemas.py`):

```python
class SpotifyTokens(BaseModel):
    access_token: str
    refresh_token: str | None  # bei Refresh-Call optional!
    expires_in: int
    scope: str
    token_type: str

class SpotifyAuthorizationRequest(BaseModel):
    authorization_url: str
    state: str

class SpotifyCallbackResult(BaseModel):
    succeeded: bool
    error_reason: str | None = None
    @classmethod
    def success(cls): return cls(succeeded=True)
    @classmethod
    def error(cls, *, reason): return cls(succeeded=False, error_reason=reason)

class SpotifyAccessToken(BaseModel):
    """DTO für den Frontend-Token-Proxy. NUR access_token, kein refresh."""
    access_token: str
    expires_in: int
    scope: str
```

**Port** (`features/oauth_connections/application/ports.py`):

```python
class SpotifyOAuthProvider(ABC):
    @abstractmethod
    def build_authorization_url(self, *, state: str) -> str: ...

    @abstractmethod
    async def exchange_code_for_tokens(self, *, authorization_code: str) -> SpotifyTokens: ...

    @abstractmethod
    async def fetch_spotify_user_id(self, *, access_token: str) -> str: ...

    @abstractmethod
    async def refresh_access_token(self, *, refresh_token: str) -> SpotifyTokens: ...
```

**Connect-Handler** `features/oauth_connections/application/commands/connect_spotify.py`:

```python
class ConnectSpotifyHandler:
    _STATE_TOKEN_BYTES = 32

    def __init__(
        self,
        connection_repository: OAuthConnectionRepository,
        spotify_oauth_provider: SpotifyOAuthProvider,
        token_cipher: OAuthTokenCipher,
    ) -> None:
        self._repo = connection_repository
        self._provider = spotify_oauth_provider
        self._cipher = token_cipher

    def start(self, *, user_id: UUID) -> SpotifyAuthorizationRequest:
        # State enthält user_id → bindet den Flow an den eingeloggten User.
        state_payload = f"{user_id}:{secrets.token_urlsafe(self._STATE_TOKEN_BYTES)}"
        url = self._provider.build_authorization_url(state=state_payload)
        return SpotifyAuthorizationRequest(authorization_url=url, state=state_payload)

    async def complete(
        self,
        *,
        authenticated_user_id: UUID,
        code: str | None,
        state: str,
        error: str | None,
        expected_oauth_state: str | None,
    ) -> SpotifyCallbackResult:
        if error is not None:
            return SpotifyCallbackResult.error(reason=error)
        if code is None:
            return SpotifyCallbackResult.error(reason="missing_code")
        if expected_oauth_state is None or not secrets.compare_digest(expected_oauth_state, state):
            return SpotifyCallbackResult.error(reason="invalid_state")

        state_user_id_str, _ = state.split(":", maxsplit=1)
        if state_user_id_str != str(authenticated_user_id):
            return SpotifyCallbackResult.error(reason="user_mismatch")

        try:
            tokens = await self._provider.exchange_code_for_tokens(authorization_code=code)
            if tokens.refresh_token is None:
                return SpotifyCallbackResult.error(reason="no_refresh_token")
            spotify_user_id = await self._provider.fetch_spotify_user_id(
                access_token=tokens.access_token,
            )
        except ValueError:
            return SpotifyCallbackResult.error(reason="spotify_exchange_failed")

        # Upsert: existierende Connection ersetzen (Reconnect-Case)
        connection = OAuthConnection(
            user_id=authenticated_user_id,
            provider=OAuthProvider.SPOTIFY,
            provider_user_id=spotify_user_id,
            encrypted_refresh_token=self._cipher.encrypt(tokens.refresh_token),
            scope=tokens.scope,
            connected_at=datetime.now(timezone.utc),
        )
        existing = await self._repo.get(user_id=authenticated_user_id, provider=OAuthProvider.SPOTIFY)
        if existing is not None:
            connection.id = existing.id  # gleicher Primärschlüssel → Update
        await self._repo.save(connection=connection)
        return SpotifyCallbackResult.success()
```

**Disconnect-Handler**:
```python
class DisconnectSpotifyHandler:
    def __init__(self, connection_repository: OAuthConnectionRepository):
        self._repo = connection_repository

    async def handle(self, *, user_id: UUID) -> None:
        await self._repo.delete(user_id=user_id, provider=OAuthProvider.SPOTIFY)
```

**Neuer `SpotifyTokenService`** (`features/oauth_connections/application/spotify_token_service.py`) — Token-Proxy für FE:

```python
class SpotifyConnectionNotFoundException(Exception): ...
class SpotifyTokenRevokedException(Exception): ...


class SpotifyTokenService:
    """Liefert kurzlebige Spotify-Access-Tokens für authentifizierte User.

    Refresh-Token verlässt das Backend nicht. Jeder Call refresht gegen Spotify
    (~ 1 HTTP-Roundtrip). Optionales In-Memory-Caching ist ein Folge-Step.
    """

    def __init__(
        self,
        connection_repository: OAuthConnectionRepository,
        spotify_oauth_provider: SpotifyOAuthProvider,
        token_cipher: OAuthTokenCipher,
    ) -> None:
        self._repo = connection_repository
        self._provider = spotify_oauth_provider
        self._cipher = token_cipher

    async def get_valid_access_token(self, *, user_id: UUID) -> SpotifyAccessToken:
        connection = await self._repo.get(
            user_id=user_id, provider=OAuthProvider.SPOTIFY,
        )
        if connection is None:
            raise SpotifyConnectionNotFoundException()

        refresh_token = self._cipher.decrypt(connection.encrypted_refresh_token)

        try:
            tokens = await self._provider.refresh_access_token(refresh_token=refresh_token)
        except ValueError as exc:
            # Spotify gibt invalid_grant zurück, wenn der User die App revoked hat
            # → Connection löschen und Frontend muss reconnecten
            await self._repo.delete(user_id=user_id, provider=OAuthProvider.SPOTIFY)
            raise SpotifyTokenRevokedException() from exc

        # Spotify rotiert den refresh_token manchmal — wenn ja, persistieren
        if tokens.refresh_token is not None and tokens.refresh_token != refresh_token:
            connection.rotate_refresh_token(
                new_encrypted_refresh_token=self._cipher.encrypt(tokens.refresh_token),
            )
            await self._repo.save(connection=connection)

        return SpotifyAccessToken(
            access_token=tokens.access_token,
            expires_in=tokens.expires_in,
            scope=tokens.scope,
        )
```

### 6. Infrastructure — `SpotifyOAuthClient`

`features/oauth_connections/infrastructure/spotify_oauth_client.py`, analog zu `GoogleOAuthClient`. Wichtige Unterschiede:

- Spotify-Tokenendpoint will `client_id`/`client_secret` als **HTTP Basic Auth** Header.
- Refresh-Endpoint nimmt `grant_type=refresh_token` + `refresh_token`.
- `/v1/me` für Profil → `id`-Feld als `provider_user_id`.
- Beim Refresh: `refresh_token` ist im Response **optional** — fällt aufgrund Spotify-Verhalten ggf. weg.

```python
class SpotifyOAuthClient(SpotifyOAuthProvider):
    def __init__(self, settings: SpotifyAuthSettings) -> None:
        self._settings = settings

    def build_authorization_url(self, *, state: str) -> str:
        self._validate_configuration()
        query = urlencode({
            "client_id": self._settings.client_id,
            "response_type": "code",
            "redirect_uri": self._settings.redirect_uri,
            "scope": self._settings.scope,
            "state": state,
            "show_dialog": "false",
        })
        return f"{self._settings.authorization_endpoint}?{query}"

    async def exchange_code_for_tokens(self, *, authorization_code: str) -> SpotifyTokens:
        return await self._post_token({
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self._settings.redirect_uri,
        })

    async def refresh_access_token(self, *, refresh_token: str) -> SpotifyTokens:
        return await self._post_token({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })

    async def fetch_spotify_user_id(self, *, access_token: str) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                self._settings.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code >= 400:
            raise ValueError("Spotify /me request failed")
        spotify_user_id = response.json().get("id")
        if not isinstance(spotify_user_id, str) or not spotify_user_id:
            raise ValueError("Spotify /me response did not include id")
        return spotify_user_id

    async def _post_token(self, form: dict[str, str]) -> SpotifyTokens:
        basic_auth = base64.b64encode(
            f"{self._settings.client_id}:{self._settings.client_secret}".encode()
        ).decode()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self._settings.token_endpoint,
                data=form,
                headers={
                    "Authorization": f"Basic {basic_auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
        if response.status_code >= 400:
            raise ValueError("Spotify token exchange failed")
        try:
            return SpotifyTokens.model_validate(response.json())
        except ValidationError as exc:
            raise ValueError("Spotify token payload is invalid") from exc
```

### 7. Presentation — Router, Cookies, Token-Endpoint

**Cookies** (`features/auth/presentation/cookies.py`): analog zu Google-State, eigenständiger Cookie-Name `spotify_oauth_state`. Refactor: gemeinsamer Helper `_set_signed_state_cookie(name, state)`.

**Router** — eigener Router `features/oauth_connections/presentation/router.py` (mounted unter `/auth/spotify` damit es semantisch zum Auth-Stack passt):

```python
spotify_router = APIRouter(
    route_class=DishkaRoute, prefix="/auth/spotify", tags=["spotify"],
)

@spotify_router.get(
    "/connect",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    response_model=None,
    operation_id="spotify_connect",
)
async def spotify_connect(
    authenticated_user_id: AuthenticatedUserId,  # erfordert App-Login!
    handler: FromDishka[ConnectSpotifyHandler],
    auth_cookies: FromDishka[AuthCookies],
) -> RedirectResponse:
    req = handler.start(user_id=authenticated_user_id)
    response = RedirectResponse(url=req.authorization_url, status_code=307)
    auth_cookies.set_spotify_oauth_state(response=response, state=req.state)
    return response


@spotify_router.get(
    "/callback",
    response_model=None,
    operation_id="spotify_callback",
    include_in_schema=False,
)
async def spotify_callback(
    request: Request,
    authenticated_user_id: AuthenticatedUserId,
    handler: FromDishka[ConnectSpotifyHandler],
    auth_cookies: FromDishka[AuthCookies],
    auth_settings: FromDishka[AuthSettings],
    code: str | None = Query(default=None, min_length=1, max_length=4096),
    state: str = Query(min_length=1, max_length=4096),
    error: str | None = Query(default=None, min_length=1, max_length=256),
) -> HTMLResponse:
    result = await handler.complete(
        authenticated_user_id=authenticated_user_id,
        code=code, state=state, error=error,
        expected_oauth_state=auth_cookies.read_spotify_oauth_state(request=request),
    )
    response = OAuthPopupResponse.for_spotify(
        target_origin=auth_settings.frontend_base_url,
        succeeded=result.succeeded,
        reason=result.error_reason,
    )
    auth_cookies.clear_spotify_oauth_state(response)
    return response


@spotify_router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    operation_id="spotify_disconnect",
)
async def spotify_disconnect(
    authenticated_user_id: AuthenticatedUserId,
    handler: FromDishka[DisconnectSpotifyHandler],
) -> None:
    await handler.handle(user_id=authenticated_user_id)


@spotify_router.get(
    "/token",
    response_model=SpotifyAccessTokenResponse,
    status_code=status.HTTP_200_OK,
    operation_id="spotify_get_access_token",
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorDto, "description": "Spotify not connected"},
        status.HTTP_410_GONE: {"model": ErrorDto, "description": "Spotify access revoked, reconnect required"},
    },
)
async def spotify_get_access_token(
    authenticated_user_id: AuthenticatedUserId,
    token_service: FromDishka[SpotifyTokenService],
) -> SpotifyAccessTokenResponse:
    """Liefert kurzlebigen Spotify-Access-Token für das Web-Playback-SDK.

    Frontend ruft das vor SDK-Init UND bei `onTokenExpired` erneut.
    Refresh-Token bleibt im Backend.
    """
    try:
        access_token = await token_service.get_valid_access_token(user_id=authenticated_user_id)
    except SpotifyConnectionNotFoundException:
        raise HTTPException(status_code=409, detail="Spotify is not connected")
    except SpotifyTokenRevokedException:
        raise HTTPException(status_code=410, detail="Spotify access revoked, please reconnect")
    return SpotifyAccessTokenResponse(
        access_token=access_token.access_token,
        expires_in=access_token.expires_in,
        scope=access_token.scope,
    )
```

`SpotifyAccessTokenResponse` (Presentation-Schema) ist 1:1 das `SpotifyAccessToken`-DTO — enthält **explizit keinen** Refresh-Token.

**HTTP-Caching für `/token`**: `Cache-Control: no-store` auf der Response setzen, damit der Token nicht in Browser- oder Proxy-Caches landet.

### 8. `User /me`-Response erweitern

`UserMeResponse` bekommt einen abgeleiteten Flag:

```python
class UserMeResponse(Schema):
    id: UUID
    name: str
    email: str
    created_at: datetime
    spotify_connected: bool  # NEU
```

`UserService.get_me` braucht zusätzlich den `OAuthConnectionRepository`:

```python
async def get_me(self, *, user_id: UUID) -> UserMeDto:
    user = await self._user_repo.get_by_id(user_id=user_id)
    if user is None:
        raise SessionInvalidException("Invalid user")
    spotify_connected = await self._oauth_repo.exists(
        user_id=user_id, provider=OAuthProvider.SPOTIFY,
    )
    return UserMeDto(user=user, spotify_connected=spotify_connected)
```

> Falls `/me` häufig aufgerufen wird: das ist ein zusätzlicher DB-Hit pro Call. Akzeptabel — der ist auf einem indexed `(user_id, provider)` und nur `SELECT 1`.

### 9. DI-Wiring

Neuer Provider `features/oauth_connections/infrastructure/di.py`:

```python
class OAuthConnectionsProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_spotify_auth_settings(self) -> SpotifyAuthSettings:
        return SpotifyAuthSettings()

    @provide(scope=Scope.APP)
    def provide_token_cipher(self, auth_settings: AuthSettings) -> OAuthTokenCipher:
        return OAuthTokenCipher(encryption_key=auth_settings.spotify_token_encryption_key)

    @provide(scope=Scope.APP)
    def provide_spotify_oauth_provider(
        self, spotify_auth_settings: SpotifyAuthSettings,
    ) -> SpotifyOAuthProvider:
        return SpotifyOAuthClient(settings=spotify_auth_settings)

    @provide(scope=Scope.REQUEST)
    def provide_connection_repository(
        self, session: AsyncSession,
    ) -> OAuthConnectionRepository:
        return SqlOAuthConnectionRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def provide_connect_handler(
        self,
        repo: OAuthConnectionRepository,
        provider: SpotifyOAuthProvider,
        cipher: OAuthTokenCipher,
    ) -> ConnectSpotifyHandler:
        return ConnectSpotifyHandler(
            connection_repository=repo,
            spotify_oauth_provider=provider,
            token_cipher=cipher,
        )

    @provide(scope=Scope.REQUEST)
    def provide_disconnect_handler(
        self, repo: OAuthConnectionRepository,
    ) -> DisconnectSpotifyHandler:
        return DisconnectSpotifyHandler(connection_repository=repo)

    @provide(scope=Scope.REQUEST)
    def provide_token_service(
        self,
        repo: OAuthConnectionRepository,
        provider: SpotifyOAuthProvider,
        cipher: OAuthTokenCipher,
    ) -> SpotifyTokenService:
        return SpotifyTokenService(
            connection_repository=repo,
            spotify_oauth_provider=provider,
            token_cipher=cipher,
        )
```

Provider in der App-Container-Konfiguration registrieren. `UserService` Dishka-Provider erweitert um `OAuthConnectionRepository`.

### 10. Frontend-Integration (Skizze)

1. **Connect/Disconnect-UI** in Settings:
   - Button „Connect Spotify" → öffnet `/auth/spotify/connect` in Popup.
   - PostMessage-Listener `prompster-spotify-oauth` → bei `success` `/users/me` re-fetchen.
   - Bei `spotify_connected === true` Button „Disconnect" → `DELETE /auth/spotify`.

2. **Playback-SDK-Init**:
   ```ts
   // useSpotifyToken Hook
   async function getInitialToken() {
     const res = await fetch("/auth/spotify/token", { credentials: "include" });
     if (res.status === 409) throw new SpotifyNotConnectedError();
     if (res.status === 410) throw new SpotifyReconnectRequiredError();
     return (await res.json()) as { access_token: string; expires_in: number };
   }

   // Spotify SDK Init
   const player = new Spotify.Player({
     name: "Prompster Player",
     getOAuthToken: async (callback) => {
       const { access_token } = await getInitialToken();
       callback(access_token);
     },
   });
   ```
   Das SDK selbst ruft `getOAuthToken` bei Bedarf erneut — wir machen jedes Mal einen frischen Backend-Call. Kein Token-Caching im Frontend.

3. **Error-States**:
   - `409` (nicht verbunden) → UI zeigt „Connect Spotify" CTA.
   - `410` (Token revoked) → UI zeigt „Reconnect Spotify" CTA, alte Connection ist server-seitig schon weg.

## Sicherheitsüberlegungen

- **Refresh-Token nur encrypted in DB** (Fernet/AES-GCM). Plaintext lebt nur kurz im Speicher beim Refresh.
- **Access-Token wandert ans FE**, aber kurzlebig (~1h) und `Cache-Control: no-store`. Refresh-Token niemals.
- **Encryption-Key** kommt aus ENV / Secret-Manager, nicht in Code. Key-Rotation = separates Thema (würde alle bestehenden Connections invalidieren → User müssten reconnecten).
- **CSRF**: signed State-Cookie + `user_id`-Binding im State (s. Handler). Verhindert „Attacker triggert Connect, Victim verbindet versehentlich seinen Spotify-Account in Attacker-Session".
- **Connect-Endpoint braucht App-Auth** — sonst könnte ein Angreifer den Flow für unangemeldete Besucher anstoßen und über CSRF die Account-Zuordnung manipulieren.
- **Token-Endpoint braucht App-Auth** + Rate-Limit (Folge-PR). Sonst kann ein Angreifer mit gestohlenem Session-Cookie unbegrenzt Access-Tokens minten.
- **Scope minimal halten** — `streaming` ist die einzige Eskalation gegenüber rein lesendem Setup, brauchen wir aber fürs Playback.
- **Niemals Tokens loggen** — explizite Redaction in HTTP-Logging.

## Reihenfolge der PRs (Empfehlung)

1. **PR 1 — Foundation**: `SpotifyAuthSettings` vervollständigen, `OAuthTokenCipher`, ENV-Doku, Dependency `cryptography`.
2. **PR 2 — Domain + Persistenz**: `oauth_connections`-Tabelle (Alembic), `OAuthConnection`-Aggregate, Repository, kein User-Touch.
3. **PR 3 — Connect-Flow**: Ports, Schemas, `SpotifyOAuthClient`, `ConnectSpotifyHandler` + `DisconnectSpotifyHandler`, Cookies-Erweiterung, Router (`/connect`, `/callback`, `DELETE /`).
4. **PR 4 — Token-Proxy**: `SpotifyTokenService`, `/auth/spotify/token`-Endpoint, `Cache-Control: no-store`.
5. **PR 5 — UserMe**: `spotify_connected`-Flag in `/users/me`.
6. **PR 6 — Frontend**: Connect/Disconnect-UI, Playback-SDK-Hook, Error-States.
7. **PR 7 (später)** — Optionales In-Memory-/Redis-Caching im `SpotifyTokenService`, Rate-Limit auf `/token`.

Jeder PR liefert isoliert sinnvolle Tests + ist gefahrlos mergebar.

## Offene Fragen

- **Encryption-Key-Management**: Lokal via `.env`, in Prod via Secret-Manager? Welcher Standard im Rest des Repos?
- **Token-Caching**: Reicht „pro Call frisch refreshen" für die erwartete Last? Oder direkt mit In-Memory-LRU starten (`user_id → (token, expires_at)`, TTL = `expires_in - 60s`)? — Empfehlung: erst messen, dann optimieren.
- **Mehrere Provider später**: Domain ist generisch über `OAuthProvider`-Enum. Falls Apple Music dazukommt: neues Enum-Value + neuer `AppleMusicOAuthProvider`-Port + neue Settings/Router. Tabelle bleibt unverändert.
- **Reconnect mit anderem Spotify-Account**: Aktuell `(user_id, provider)` unique → Reconnect überschreibt. Reicht das, oder wollen wir Multi-Account pro Provider (z.B. Privat/Business)? — Erste Version: überschreiben.
