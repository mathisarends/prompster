# Integration `transcriptify` — Batch-Transcription als Alternative zu Realtime

## Ziel

`transcriptify` (OpenAI Whisper / GPT-4o, ganzer Kontext up-front) als **stabilere,
nicht-streamende Alternative** zur bestehenden Realtime-WebSocket-Transcription
(`realtime_whisper`) im `transcription`-Feature anbieten.

Beide Wege existieren parallel:

| Weg | Transport | Lib | Wann |
| --- | --- | --- | --- |
| Realtime (bestehend) | WebSocket `/transcription/realtime` | `realtime_whisper` | Live-Diktat, niedrige Latenz, VAD |
| **Batch (neu)** | HTTP `POST /transcription` | `transcriptify` | Datei/komplettes Audio liegt vor → stabiler, einfacher |

---

## Frage a) — uv install im Backend

**Ja.** `transcriptify` ist ein PyPI-Paket (kein Workspace-Member, analog zu
`realtime-whisper`). Im Backend-Package hinzufügen:

```bash
# vom Repo-Root, --package adressiert das Workspace-Member "backend"
uv add transcriptify --package backend
```

Das ergänzt `backend/pyproject.toml` → `dependencies` um `transcriptify>=…` und
aktualisiert das Root-`uv.lock`. **Kein `mic`-Extra** nötig (Server hat kein
Mikrofon; wir nutzen `BytesAudioDevice` für hochgeladene Bytes).

API-Key: `transcriptify.OpenAIWhisper()` liest `OPENAI_API_KEY` aus der Env —
ist im Backend bereits vorhanden (von `realtime_whisper` mitgenutzt). Kein neuer
Key nötig.

---

## Architektur — Clean-Architecture-Konvention des Features beibehalten

Das Feature ist nach `application` (Ports/Protocols) → `infrastructure` (Adapter)
→ `presentation` (Router/Schemas/Mapper) → `di` geschnitten. Die Batch-Variante
bekommt **eigene Ports/Adapter/Schemas**, teilt sich nur das Feature-Verzeichnis.

### Neue / geänderte Dateien

```
backend/src/backend/features/transcription/
├── application/
│   ├── ports.py            (+) BatchTranscriber, BatchTranscriptionOptions/-Result
│   └── __init__.py         (+) Re-Exports
├── infrastructure/
│   ├── transcriptify_transcriber.py   (NEU) Adapter auf transcriptify.OpenAIWhisper
│   ├── settings.py         (+) BatchTranscriptionSettings (model, language, prompt)
│   └── di.py               (+) provide BatchTranscriber + Settings
└── presentation/
    ├── router.py           (+) POST /transcription  (Multipart-Upload)
    ├── schemas.py          (+) BatchTranscriptionResponse
    └── mapper.py           (+) to_batch_transcription_response
```

---

## Schritt-für-Schritt

### 1. Dependency

`uv add transcriptify --package backend` (siehe oben). Verifizieren: Import von
`transcriptify` und `transcriptify.audio.BytesAudioDevice` läuft im `.venv`.

### 2. Application-Port (`application/ports.py`)

Neue Abstraktion analog zu `TranscriptionSession`, aber für One-Shot-Batch.
Bewusst lib-agnostisch (kein `transcriptify`-Typ leakt in die application-Schicht):

```python
class BatchTranscriptionModel(StrEnum):
    WHISPER_1 = "whisper-1"
    GPT_4O_TRANSCRIBE = "gpt-4o-transcribe"
    GPT_4O_MINI_TRANSCRIBE = "gpt-4o-mini-transcribe"

class AudioEncoding(StrEnum):
    WAV = "wav"
    MP3 = "mp3"
    M4A = "m4a"
    WEBM = "webm"
    OGG = "ogg"
    FLAC = "flac"

@dataclass(frozen=True)
class BatchTranscriptionOptions:
    language: str | None = None
    model: BatchTranscriptionModel = BatchTranscriptionModel.GPT_4O_TRANSCRIBE
    prompt: str | None = None

@dataclass(frozen=True)
class BatchTranscriptionResult:
    text: str

class BatchTranscriber(Protocol):
    async def transcribe(
        self,
        *,
        audio: bytes,
        encoding: AudioEncoding,
        sample_rate: int,
        options: BatchTranscriptionOptions,
    ) -> BatchTranscriptionResult: ...
```

`AudioEncoding` ist die Single-Source-of-Truth für unterstützte Formate: der
Router leitet daraus ab (Schritt 6 / `_encoding_from_upload`), unbekannte Formate
→ `422`. Werte = von OpenAI/Whisper akzeptierte Container-Endungen.

In `application/__init__.py` re-exportieren (`__all__` erweitern).

### 3. Infrastructure-Adapter (`infrastructure/transcriptify_transcriber.py`) — NEU

Implementiert `BatchTranscriber` mit `transcriptify`:

```python
from transcriptify import OpenAIWhisper, WhisperModel
from transcriptify.audio import BytesAudioDevice

class TranscriptifyBatchTranscriber(BatchTranscriber):
    async def transcribe(self, *, audio, encoding, sample_rate, options):
        whisper = OpenAIWhisper(
            model=_to_whisper_model(options.model),
            language=options.language,
            prompt=options.prompt,
        )
        device = BytesAudioDevice(audio, sample_rate=sample_rate, encoding=encoding)
        chunk = await device.read()
        result = await whisper.transcribe(chunk)
        return BatchTranscriptionResult(text=result.text)
```

`_to_whisper_model(...)`: `match`-Mapping `BatchTranscriptionModel` →
`transcriptify.WhisperModel` (gleiches Muster wie `_to_realtime_delay` in
`realtime_whisper_session.py`).

> Offen: `OpenAIWhisper` pro Request neu instanziieren (stateless, einfach) vs.
> einmal in DI (APP-Scope) cachen und `model`/`language` pro Request übergeben.
> Falls `OpenAIWhisper` Optionen nur im Konstruktor nimmt → pro Request bauen
> (günstig, nur HTTP-Client-Setup). **Default: pro Request** für klare Semantik.

### 4. Settings (`infrastructure/settings.py`)

Defaults für die Batch-Variante (eigener Prefix, damit Realtime-Settings nicht
kollidieren):

```python
class BatchTranscriptionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="BATCH_TRANSCRIPTION_", extra="ignore"
    )
    language: str | None = None
    model: BatchTranscriptionModel = BatchTranscriptionModel.GPT_4O_TRANSCRIBE
    prompt: str | None = None
    max_upload_bytes: int = 25 * 1024 * 1024  # OpenAI-Limit ~25 MB
    default_sample_rate: int = 16_000
```

### 5. DI (`infrastructure/di.py`)

Im bestehenden `TranscriptionProvider` ergänzen:

```python
@provide(scope=Scope.APP)
def provide_batch_settings(self) -> BatchTranscriptionSettings:
    return BatchTranscriptionSettings()

@provide(scope=Scope.APP)
def provide_batch_transcriber(self) -> BatchTranscriber:
    return TranscriptifyBatchTranscriber()
```

(Settings als Default-Quelle für `BatchTranscriptionOptions` im Router, analog zu
`provide_transcription_options`.)

### 6. Presentation

**`schemas.py`** — Response (Request kommt als Multipart, kein Body-Schema nötig):

```python
class BatchTranscriptionResponse(Schema):
    transcript: str
```

**`mapper.py`**:

```python
def to_batch_transcription_response(r: BatchTranscriptionResult) -> BatchTranscriptionResponse:
    return BatchTranscriptionResponse(transcript=r.text)
```

**`router.py`** — neue HTTP-Route am bestehenden `transcription_router`:

```python
@transcription_router.post("", response_model=BatchTranscriptionResponse)
async def transcribe_batch(
    _authenticated_user_id: AuthenticatedUserId,
    transcriber: FromDishka[BatchTranscriber],
    settings: FromDishka[BatchTranscriptionSettings],
    file: Annotated[UploadFile, File(...)],
    language: Annotated[str | None, Form()] = None,
) -> BatchTranscriptionResponse:
    audio = await file.read()
    # Validierung: settings.max_upload_bytes, Content-Type/encoding ableiten
    encoding = _encoding_from_upload(file)   # AudioEncoding aus Suffix/content_type, sonst 422
    result = await transcriber.transcribe(
        audio=audio,
        encoding=encoding,
        sample_rate=settings.default_sample_rate,
        options=BatchTranscriptionOptions(
            language=language or settings.language,
            model=settings.model,
            prompt=settings.prompt,
        ),
    )
    return to_batch_transcription_response(result)
```

> Hinweis: Router nutzt `DishkaRoute` (route_class). Für DI in HTTP-Handlern
> `FromDishka[...]` aus `dishka.integrations.fastapi` verwenden (nicht der
> `dishka_ws_dep`-Pfad, der ist WS-spezifisch). Auth über bestehendes
> `AuthenticatedUserId`.

### 7. Fehlerbehandlung

- Upload > `max_upload_bytes` → `413`/`422` (Domain-/HTTP-Exception nach
  Feature-Konvention).
- Nicht unterstütztes `encoding` → `422`.
- `transcriptify`/OpenAI-Fehler → in eine Feature-Exception übersetzen, nicht
  roh durchreichen (Mapper/Exception-Handler-Muster prüfen).

---

## API-Contract (Ergebnis)

```
POST /api/v1/transcription
Content-Type: multipart/form-data
Auth: erforderlich (AuthenticatedUserId)

Felder:
  file: <audio>           (required)  .wav / .mp3 / .m4a / ...
  language: "de"          (optional)  ISO-639-1, überschreibt Default

200 → { "transcript": "..." }   (PascalCase je nach PascalCaseRouter)
```

Routing: `PascalCaseRouter(prefix="/api/v1")` + `prefix="/transcription"` →
finaler Pfad `/api/v1/transcription`.

---

## Tests

Spiegeln der bestehenden Test-Struktur unter
`backend/tests/backend/features/transcription/`:

- **Adapter**: `TranscriptifyBatchTranscriber` mit gemocktem `OpenAIWhisper`
  (kein echter API-Call) — prüft Model-Mapping + `BytesAudioDevice`-Aufbau.
- **Mapper**: `to_batch_transcription_response`.
- **Router**: FastAPI-`TestClient`, Multipart-Upload, gemockter `BatchTranscriber`
  via Dishka-Override → prüft 200-Pfad, Auth-Pflicht, Size-Limit (413/422).

---

## Optionale Erweiterung (später, nicht Teil dieses Plans)

`transcriptify` kann mit `gpt-4o-transcribe` auch streamen (`whisper.stream()`).
Falls gewünscht, ließe sich ein SSE-Endpoint `POST /transcription/stream` mit
denselben Ports ergänzen (Port um `stream()`-Methode erweitern). Bewusst
**ausgeklammert** — Ziel hier ist die stabile Batch-Variante mit Kontext up-front.

---

## Entscheidungen (festgelegt)

1. **`OpenAIWhisper` pro Request** instanziieren (stateless, klare Semantik;
   Overhead nur HTTP-Client-Setup). Falls Profiling später Druck zeigt → in DI
   cachen.
2. **Endpoint-Pfad `POST /transcription`** (Resource-Style). Liest sich sauber
   neben dem WS-Pfad `/transcription/realtime` und braucht kein `/batch`-Suffix.
3. **`encoding`-Ableitung in `_encoding_from_upload`**: zuerst Datei-Suffix, dann
   `content_type` als Fallback, gematcht gegen `AudioEncoding`. Kein Treffer →
   `422` (kein stiller `wav`-Fallback, da falsches Format sonst kryptische
   OpenAI-Fehler erzeugt).
4. **`sample_rate`**: nur für WAV relevant; bei komprimierten Formaten
   (mp3/m4a/webm/ogg/flac) liegt die Rate im Container und wird von
   `BytesAudioDevice` ignoriert. `settings.default_sample_rate` (16 kHz) als
   Default durchreichen — beim Adapter in Schritt 3 gegen das tatsächliche
   `BytesAudioDevice`-Verhalten verifizieren.
