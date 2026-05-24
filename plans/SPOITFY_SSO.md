# Spotify SSO — Implementierungsplan

Ziel: Spotify zusätzlich zu Google als vollwertigen SSO-Provider für die
Authentifizierung anbieten. Google bleibt als Alternativstrategie bestehen.
Die existierende „Spotify-Connect"-Strategie aus `oauth_connections` bleibt
unverändert nutzbar, weil sie eine andere Semantik abdeckt (Tokens für
Wiedergabe, Playlist-Modify usw.).

---

## 1. Architektur-Übersicht & Begriffsklärung

Im Repo existieren bereits zwei klar getrennte Konzepte, die wir sauber halten:

| Konzept                  | Feature                                        | Zweck                                                                   | Tabelle              |
| ------------------------ | ---------------------------------------------- | ----------------------------------------------------------------------- | -------------------- |
| **Auth-Identity**        | `features/user/domain/auth_identity.py`        | Verknüpft einen `User` mit einem SSO-Subject (Login)                    | `auth_identities`    |
| **OAuth-Connection**     | `features/oauth_connections/domain`            | Persistiert verschlüsselte Refresh-Tokens für API-Zugriff (kein Login)  | `oauth_connections`  |

Spotify wird ab sofort in **beiden** Konzepten geführt:

1. **SSO (neu)** — Anlegen / Wiederfinden des Users über `auth_identities`
   mit `provider = 'spotify'`, ausgestellte JWT-Sitzung wie bei Google.
2. **Connect (bestehend)** — Anlegen / Aktualisieren des `oauth_connections`-
   Eintrags mit verschlüsseltem Refresh-Token. Bleibt vollständig erhalten.

**Wichtige Designentscheidung:** Wenn ein User sich via Spotify SSO einloggt,
übernehmen wir die zurückgegebenen Tokens **gleichzeitig** in `oauth_connections`.
Andernfalls müsste der User unmittelbar nach dem Login nochmals „Spotify
verbinden" klicken, obwohl wir die Tokens schon haben. Die User-Action ist
identisch (Spotify-Popup mit Consent) — die Tokens nicht zu nutzen wäre reine
UX-Reibung.

---

## 2. Backend — Domain-Änderungen

### 2.1 `AuthProvider`-Enum erweitern
Datei: `backend/src/backend/features/user/domain/auth_identity.py`

```python
class AuthProvider(StrEnum):
    GOOGLE = "google"
    SPOTIFY = "spotify"
```

Auswirkung: `UserRepository.get_by_auth_identity` funktioniert ohne Änderung,
weil es bereits `provider: AuthProvider` parametrisiert. Der Index
`ix_auth_identities_provider_subject` deckt den neuen Provider ab.

### 2.2 Keine Migration nötig
`auth_identities.provider` ist ein freier String. Keine Schema-Änderung.

---

## 3. Backend — Application-Schicht

### 3.1 Neuer Port `SpotifyOAuthProvider` für die Auth-Feature
Datei: `backend/src/backend/features/auth/application/ports.py`

Wir definieren in `auth` einen schmalen Port, der genau das beschreibt, was
der SSO-Flow braucht. Implementiert wird er vom existierenden
`SpotifyOAuthClient` aus `oauth_connections/infrastructure` — wir reichen
diesen via DI rein (siehe Abschnitt 6). Beide Features müssen denselben
Client nutzen, weil die Client-Credentials (`SPOTIFY_CLIENT_ID/SECRET`) global
sind.

```python
class SpotifyOAuthProvider(ABC):
    @abstractmethod
    def build_authorization_url(self, *, state: str) -> str: ...
    @abstractmethod
    async def exchange_code_for_tokens(
        self, *, authorization_code: str
    ) -> SpotifyTokens: ...
    @abstractmethod
    async def fetch_spotify_user_profile(
        self, *, access_token: str
    ) -> SpotifyUserProfile: ...
```

**Wichtig:** Diese Klasse ist strukturell identisch zur bestehenden in
`oauth_connections/application/ports.py`. Wir importieren das Original aus
`oauth_connections` und re-exportieren — kein doppelter Code. Das ist ein
zulässiger Querverweis von `auth` auf `oauth_connections`, weil
`oauth_connections` ohnehin auf `auth` aufbaut (es nutzt `AuthSettings`).
Alternative: gemeinsamer `shared/spotify`-Ort. Empfehlung **Import via
`oauth_connections`** — weniger Bewegung, klares Eigentum.

### 3.2 Neuer Use-Case `SpotifyOAuthFlow`
Datei: `backend/src/backend/features/auth/application/commands/spotify_oauth_flow.py`

Spiegelt `GoogleOAuthFlow`, mit drei Erweiterungen:
- holt **Tokens + Profil** (statt nur Identity)
- legt nach Bedarf eine **`OAuthConnection`** an / aktualisiert sie
- handelt die **E-Mail-Eindeutigkeit** wie Google (siehe Edge-Case 8.2)

```python
class SpotifyOAuthFlow:
    _STATE_TOKEN_BYTES = 32

    def __init__(
        self,
        user_repository: UserRepository,
        spotify_oauth_provider: SpotifyOAuthProvider,
        token_issuer: TokenIssuer,
        connection_repository: OAuthConnectionRepository,
        token_cipher: OAuthTokenCipher,
    ) -> None: ...

    def login(self) -> SpotifyAuthorizationRequest: ...

    async def callback(
        self,
        *,
        code: str | None,
        state: str,
        error: str | None,
        expected_oauth_state: str | None,
    ) -> SpotifyCallbackResult: ...
```

Ablauf von `callback`:

1. `error` / `code` / `state`-Validierung wie bei Google.
2. `exchange_code_for_tokens(authorization_code=code)` → `SpotifyTokens`.
3. `fetch_spotify_user_profile(access_token=tokens.access_token)` →
   `SpotifyUserProfile` (jetzt inkl. Email, siehe 4.2).
4. Existierenden User suchen: `get_by_auth_identity(SPOTIFY, profile.spotify_user_id)`.
5. Wenn nicht gefunden:
   - Email-Kollisionsprüfung via `get_by_email(profile.email)` →
     bei Treffer `InvalidCredentialsException("email_taken")`.
   - Neuen `User` + `AuthIdentity(provider=SPOTIFY, subject=spotify_user_id)`
     anlegen.
6. **OAuth-Connection persistieren** (immer, also auch beim Folge-Login):
   - Falls `tokens.refresh_token is None`: das ist beim Refresh-Flow normal,
     beim ersten Authorization-Code-Exchange jedoch ein Fehlerfall, weil wir
     beim ersten Connect den Refresh brauchen. Spotify gibt den Refresh nur
     beim allerersten Consent zurück. Lösungen siehe 8.4.
   - `connection_repository.save(...)` mit verschlüsseltem Refresh-Token,
     Scope, `is_premium`, `provider_user_id = profile.spotify_user_id`.
7. `_sync_profile_image` analog Google (Spotify liefert
   `images[0].url`, siehe 4.2).
8. JWT-Sitzung via `token_issuer.create_session(...)` ausgeben.

### 3.3 Neue Schemas
Datei: `backend/src/backend/features/auth/application/schemas.py`

```python
class SpotifyAuthorizationRequest(BaseModel):
    authorization_url: str
    state: str

class SpotifyCallbackResult(BaseModel):
    succeeded: bool
    session: AuthSession | None = None
    error_reason: str | None = None
    # success / error Factory-Methoden + Validator wie GoogleCallbackResult
```

### 3.4 Token-Persistenz teilen, nicht duplizieren
Datei: `backend/src/backend/features/oauth_connections/application/spotify_oauth_connection_service.py`

Wir refaktorieren `SpotifyOAuthConnectionService` so, dass eine private
Helper-Methode `_persist_connection(user_id, tokens, profile)` aus
`complete_connect` extrahiert wird und **auch vom SSO-Flow nutzbar** ist —
entweder über eine public Methode oder durch Auslagerung in einen kleinen
Helper, den beide Flows konsumieren. Empfehlung:

- Public Methode `upsert_from_tokens(user_id, tokens, profile)` auf
  `SpotifyOAuthConnectionService` einführen.
- `SpotifyOAuthFlow` bekommt `SpotifyOAuthConnectionService` injiziert und
  delegiert Schritt 6 dorthin (statt Repository + Cipher direkt zu kennen).

Damit bleibt `oauth_connections` der einzige Ort, der die
`OAuthConnection`-Schreibpfade kennt.

### 3.5 `__init__.py` der Auth-Application
- `SpotifyOAuthFlow` exportieren
- `SpotifyAuthorizationRequest`, `SpotifyCallbackResult` exportieren

---

## 4. Backend — Infrastructure-Schicht

### 4.1 Spotify-Scope um `user-read-email` erweitern
Datei: `backend/src/backend/features/oauth_connections/infrastructure/spotify_scopes.py`

```python
class SpotifyScope(StrEnum):
    USER_READ_PRIVATE = "user-read-private"
    USER_READ_EMAIL = "user-read-email"      # NEU
    PLAYLIST_MODIFY_PUBLIC = "playlist-modify-public"
    ...
```

Hinweis: Spotify zeigt dem Nutzer dann zusätzlich „Zugriff auf deine
E-Mail-Adresse". Akzeptabel für SSO.

### 4.2 `SpotifyUserProfile` um Email & Profilbild erweitern
Datei: `backend/src/backend/features/oauth_connections/application/schemas.py`

```python
class SpotifyUserProfile(BaseModel):
    spotify_user_id: str
    is_premium: bool
    email: str | None = None
    display_name: str | None = None
    profile_image_url: str | None = None
```

Datei: `backend/src/backend/features/oauth_connections/infrastructure/spotify_oauth_client.py`

`_SpotifyUserProfileResponse` und das Mapping in `fetch_spotify_user_profile`
erweitern:

```python
class _SpotifyUserProfileResponse(BaseModel):
    id: str = Field(min_length=1)
    product: str | None = None
    email: str | None = None
    display_name: str | None = None
    images: list[dict] = Field(default_factory=list)
```

Profilbild via `payload.images[0]["url"]` (falls Liste nicht leer). Email
nur weiterreichen — die Email-Pflicht-Prüfung gehört in den SSO-Flow.

### 4.3 Cookie-Klasse für SSO-State
Datei: `backend/src/backend/features/auth/presentation/oauth_state_cookies.py`

Neue Klasse hinzufügen (Subklasse für DI-Diskriminierung, analog
`GoogleOAuthStateCookies`):

```python
class SpotifyLoginOAuthStateCookies(OAuthStateCookies):
    """OAuth state cookie for the Spotify SSO login flow."""
```

**Cookie-Name absichtlich unterschiedlich** vom Connect-Flow
(`spotify_oauth_state`), z. B. `spotify_login_state`. Sonst overschreiben
sich die Flows gegenseitig, wenn ein User parallel verbindet und sich
einloggt.

### 4.4 `SpotifyAuthSettings` ergänzen
Datei: `backend/src/backend/features/oauth_connections/infrastructure/spotify_auth_settings.py`

```python
login_redirect_uri: str = Field(default="")
login_state_cookie_name: str = "spotify_login_state"
```

`login_redirect_uri` muss in der Spotify-Developer-Console als zusätzlicher
Allowed Redirect URI eingetragen werden. `validate_redirect_host` analog
für die neue URL aufrufen.

### 4.5 Neue Settings-Klasse statt eigener Settings?
Alternative: ein neues `SpotifySsoSettings` in `features/auth/infrastructure/`.
**Empfehlung dagegen** — alle Spotify-Endpoints und Credentials sind global
identisch, nur Redirect-URI + Cookie-Name unterscheiden sich. Doppelte
ENV-Variablen würden Deployment unnötig verkomplizieren.

---

## 5. Backend — Presentation-Schicht

### 5.1 Neue Routes in `auth_router`
Datei: `backend/src/backend/features/auth/presentation/router.py`

```python
@auth_router.get("/spotify/login", ...)
async def spotify_login(
    spotify_oauth_flow: FromDishka[SpotifyOAuthFlow],
    spotify_login_state_cookies: FromDishka[SpotifyLoginOAuthStateCookies],
) -> RedirectResponse: ...

@auth_router.get("/spotify/callback", include_in_schema=False, ...)
async def spotify_callback(
    request: Request,
    spotify_oauth_flow: FromDishka[SpotifyOAuthFlow],
    auth_cookies: FromDishka[AuthCookies],
    spotify_login_state_cookies: FromDishka[SpotifyLoginOAuthStateCookies],
    auth_settings: FromDishka[AuthSettings],
    code: str | None = Query(...),
    state: str = Query(...),
    error: str | None = Query(...),
) -> HTMLResponse: ...
```

**Wichtig:** Pfad-Trennung von der bestehenden Connect-Route:
- SSO-Login:   `GET /api/v1/auth/spotify/login`
- SSO-Callback: `GET /api/v1/auth/spotify/callback`
- Connect (alt): `GET /api/v1/auth/spotify/connect`   (bleibt unverändert)
- Connect-Callback (alt): `GET /api/v1/auth/spotify/callback`

⚠️ Pfadkollision! `spotify_router` hat bereits `/auth/spotify/callback`.
Konfliktauflösung: **Connect-Route auf `/auth/spotify/connect/callback`
umstellen** (saubere REST-Hierarchie) oder den neuen SSO-Callback auf
`/auth/spotify/login/callback`. **Empfehlung:**
- `/auth/spotify/login` + `/auth/spotify/login/callback` (neu, SSO)
- `/auth/spotify/connect` + `/auth/spotify/connect/callback`
  (rename bestehender Routes — Spotify Dashboard Allowed Redirect URI muss
  ebenfalls aktualisiert werden!)

### 5.2 `OAuthPopupResponse` um SSO-Variante erweitern
Datei: `backend/src/backend/features/auth/presentation/oauth_popup.py`

```python
_SPOTIFY_LOGIN_POPUP_MESSAGE_TYPE = "prompster-spotify-login"

@classmethod
def for_spotify_login(cls, *, target_origin, succeeded, reason) -> HTMLResponse:
    ...
```

Begründung: Der existierende `prompster-spotify-oauth`-Typ steht für die
Connect-Aktion (Tokens gespeichert). Ein SSO-Erfolg bedeutet semantisch
**„User ist eingeloggt"** — Frontend muss `signIn()` triggern, nicht den
Connect-Status aktualisieren. Eigener Message-Type vermeidet Verwechslung.

Falls gewünscht: das `<title>` von `Google sign-in` dynamisch nach Provider
benennen (kosmetisch).

### 5.3 Callback-Handler analog Google
Im SSO-Callback: bei `result.succeeded` `AuthCookies.set(response, session)`
und Popup-Response mit Erfolgs-Message. Bei Fehler: Popup mit
`error_reason`.

---

## 6. Backend — Dependency Injection

### 6.1 `features/auth/infrastructure/di.py`

Zusätzliche Providers:

```python
@provide(scope=Scope.APP)
def provide_spotify_oauth_provider_for_auth(
    self,
    spotify_oauth_client: SpotifyOAuthProvider,   # aus oauth_connections-Provider
) -> SpotifyOAuthProvider:
    return spotify_oauth_client

@provide(scope=Scope.REQUEST)
def provide_spotify_oauth_flow(
    self,
    user_repository: UserRepository,
    spotify_oauth_provider: SpotifyOAuthProvider,
    token_issuer: TokenIssuer,
    spotify_connection_service: SpotifyOAuthConnectionService,
) -> SpotifyOAuthFlow: ...

@provide(scope=Scope.REQUEST)
def provide_spotify_login_state_cookies(
    self,
    auth_settings: AuthSettings,
    spotify_auth_settings: SpotifyAuthSettings,
    oauth_state_settings: OAuthStateSettings,
    env_config: EnvSettings,
) -> SpotifyLoginOAuthStateCookies: ...
```

Da `SpotifyAuthSettings` und `SpotifyOAuthProvider` bereits vom
`OAuthConnectionsProvider` bereitgestellt werden, sind keine Duplikate
nötig. Reihenfolge der Provider-Registrierung in der App-Composition prüfen
(`oauth_connections` muss vor `auth` greifbar sein oder Cross-Module-Imports
funktionieren über Dishka-App-Scope).

---

## 7. Frontend

### 7.1 Landing-Page um Spotify-Button erweitern
Datei: `frontend/src/pages/landing-page.tsx`

- Neuen Message-Type-Konstanten: `OAUTH_GOOGLE_MESSAGE_TYPE`,
  `OAUTH_SPOTIFY_LOGIN_MESSAGE_TYPE`.
- Discriminated Union für `OAuthPopupMessage`.
- `handleSpotifySignIn` analog `handleGoogleSignIn`, zeigt auf
  `/api/v1/auth/spotify/login`.
- Separater Loading-State (`isSpotifyOAuthLoading`).
- Reusable Hook extrahieren empfohlen: `useOAuthPopup({ url, messageType })`
  (es gibt bereits `useSpotifyOAuthPopup.ts` für den Connect-Flow — ggf.
  generalisieren).

### 7.2 Generierter API-Client
Die OpenAPI-Generierung läuft automatisch — sobald die neuen Routes
existieren, taucht `spotify_login` / `spotify_callback` (sofern
`include_in_schema=True`) im generierten Client auf. Für `spotify_callback`
empfohlen: `include_in_schema=False` analog Google.

### 7.3 Optisches
- Spotify-Logo als SVG / `lucide-react` (kein Spotify-Icon vorhanden → SVG-
  Asset hinzufügen oder Markenrichtlinie beachten).
- Button-Styling konsistent (z. B. schwarzer Button, grüner Akzent).

---

## 8. Edge Cases & Designentscheidungen

### 8.1 User-Tabelle: `email` ist `unique`
Spotify liefert die hinterlegte Email. Wenn ein User bereits via Google mit
gleicher Email existiert: **Reject** mit `error_reason="email_taken"`
(Mirror Google-Verhalten). Im UI Hinweis: „Diese E-Mail ist bereits mit
Google verknüpft. Bitte mit Google anmelden und Spotify dort verbinden."

**Alternative (später):** Auto-Linking — bei verifizierter Email-Übereinstimmung
zweite `AuthIdentity` an existierenden User hängen. Bewusst out-of-scope
für v1, weil Spotify-Emails nicht im OpenID-Sinn verifiziert sind.

### 8.2 Spotify liefert keine Email
Theoretisch möglich, wenn `user-read-email` nicht gewährt wurde (sollte mit
Required-Scope erzwungen werden). Wenn dennoch `email is None`:
`InvalidCredentialsException("email_missing")`. Kein Fallback auf
synthetische Emails (würde NULL-Constraint verletzen UND späteres Linking
verhindern).

### 8.3 Bestehende `oauth_connections`-Zeile beim ersten SSO-Login
Szenario: User war früher via Google eingeloggt und hat Spotify connected.
Account-Löschung. Neuer Login mit Spotify SSO.
- `get_by_auth_identity(SPOTIFY, subject)` → nichts (auth_identity wurde nie
  angelegt).
- `get_by_email(email)` → nichts (User wurde gelöscht).
→ Sauberer Neu-Anlage-Pfad. Keine Sonderbehandlung nötig.

Szenario: User war via Google eingeloggt, hat Spotify connected, ist aber
noch aktiv. Will sich jetzt mit Spotify einloggen.
- `get_by_email` trifft den existierenden Google-User → reject (siehe 8.1).
- Linking ist hier wünschenswert, aber out-of-scope (siehe oben).

### 8.4 Spotify gibt beim Folge-Login keinen `refresh_token` zurück
Spotify gibt den Refresh-Token nur beim **ersten** Consent (oder wenn
`show_dialog=true` einen erneuten Consent erzwingt). Bei SSO-Folge-Logins
kommt ggf. `refresh_token=None` zurück.
- Wenn bestehende `oauth_connections`-Zeile vorhanden → Refresh-Token NICHT
  überschreiben, nur `is_premium` + `scope` aktualisieren.
- Wenn keine bestehende Zeile + `refresh_token is None` → Edge-Case, der
  praktisch nicht eintritt, weil Erst-Login = Erst-Consent. Defensiv:
  `error_reason="no_refresh_token"`, User muss nochmal versuchen
  (mit `show_dialog=true` ist das gelöst).

`upsert_from_tokens` muss diese Logik kennen — der bestehende
`complete_connect` rejected bei `None` aktuell pauschal. Verhalten für den
neuen Helper anpassen: „rotate token nur wenn neuer Token vorhanden".

### 8.5 Account-Löschung
`UserService.delete_me` muss prüfen, dass `oauth_connections` (per FK auf
`users.id`) korrekt cascadet werden — bereits gegeben durch existierende
Logik (Spotify-Disconnect wird bei Account-Delete getriggert).

### 8.6 Profile-Bild
Spotify liefert Bilder als Array unterschiedlicher Größen. Wir nehmen
`images[0]["url"]` (Spotify sortiert größtes zuerst). `_sync_profile_image`
aus dem Google-Flow lässt sich identisch übernehmen.

---

## 9. Konfiguration / Deployment

### 9.1 Spotify Developer Dashboard
Im bestehenden Spotify-App-Eintrag zwei zusätzliche Redirect-URIs anlegen:

```
http://localhost:8000/api/v1/auth/spotify/login/callback        (dev)
https://<prod-domain>/api/v1/auth/spotify/login/callback        (prod)
http://localhost:8000/api/v1/auth/spotify/connect/callback      (dev, neu nach Rename)
https://<prod-domain>/api/v1/auth/spotify/connect/callback      (prod, neu nach Rename)
```

### 9.2 ENV-Variablen
- `SPOTIFY_LOGIN_REDIRECT_URI` — neu, z. B.
  `http://localhost:8000/api/v1/auth/spotify/login/callback`
- `SPOTIFY_REDIRECT_URI` — ggf. Update nach Pfad-Rename auf
  `…/connect/callback`.
- Keine neuen Client-IDs / Secrets nötig.

### 9.3 README / .env.example
Beides aktualisieren mit den neuen Variablen.

---

## 10. Tests

### 10.1 Unit
- `SpotifyOAuthFlow.callback`:
  - Erfolgsfall (neuer User) inkl. OAuth-Connection-Persistenz.
  - Erfolgsfall (existierender User) — kein neues AuthIdentity-Insert,
    Tokens werden aktualisiert.
  - `error != None` → Reject mit übergebenem Grund.
  - `code is None` → `missing_code`.
  - State-Mismatch → `invalid_credentials`.
  - Email-Kollision → `email_taken`.
  - Spotify liefert keine Email → `email_missing`.
  - Spotify-Profil-Fetch wirft `ValueError` → `invalid_credentials`.
- `SpotifyOAuthConnectionService.upsert_from_tokens`:
  - Tokens vorhanden, keine bestehende Connection → Insert.
  - Tokens vorhanden, bestehende Connection → Update inkl. Refresh-Rotation.
  - `refresh_token=None`, bestehende Connection → Update ohne
    Token-Rotation.

### 10.2 Integration / Router
- `GET /auth/spotify/login` → Redirect mit korrekter URL + State-Cookie.
- `GET /auth/spotify/login/callback` mit gemocktem Provider → JWT-Cookies
  gesetzt, Popup-HTML mit Spotify-Login-Message.
- Pfad-Trennung: Connect-Routes verhalten sich unverändert.

### 10.3 Frontend
- LandingPage rendert beide Buttons.
- Klick auf Spotify-Button öffnet Popup mit korrekter URL.
- `postMessage` mit `prompster-spotify-login` triggert `signIn`.

---

## 11. Schritt-für-Schritt-Reihenfolge (Empfehlung)

1. **Backend Domain** — `AuthProvider.SPOTIFY` hinzufügen.
2. **Backend Infrastructure** — Scope `user-read-email`, Profile-Schema
   erweitern (Email, Bild), Settings um Login-Redirect & Cookie-Name.
3. **Backend Application** — `SpotifyOAuthFlow` + Schemas; Refactor von
   `SpotifyOAuthConnectionService.upsert_from_tokens`.
4. **Backend Presentation** — Cookie-Klasse, Popup-Message-Type, Routes
   (inkl. Rename bestehender Connect-Routes wenn Pfad-Kollision aufgelöst
   werden soll).
5. **Backend DI** — Provider verkabeln.
6. **Tests** — Unit + Integration.
7. **Frontend** — Button, Hook generalisieren, Message-Listener.
8. **Deployment** — Spotify Dashboard Redirect-URIs ergänzen, ENV setzen.

---

## 12. Offene Punkte zur Bestätigung

1. **Pfad-Strategie**: Connect-Routes auf `/connect/callback` umbenennen
   (sauberer) oder SSO-Callback auf `/login/callback` ohne Rename
   (weniger invasiv)? Empfehlung: **beides explizit machen**
   (`/login/callback` + `/connect/callback`) für gleichmäßige Hierarchie.
2. **Email-Kollision**: Reject (v1, vorgeschlagen) oder Auto-Linking?
3. **`show_dialog=true`** beim SSO-Login? Vorteil: garantierter Refresh-Token
   bei jedem Login. Nachteil: User muss bei jedem Login Consent bestätigen
   (UX-Reibung). Empfehlung: `show_dialog=false` für SSO, `true` nur für
   Connect-Reauthorize.
4. **Provider-Subject-Quelle**: `spotify_user_id` aus `/me` ist stabil.
   Bestätigt — keine Alternative nötig.
