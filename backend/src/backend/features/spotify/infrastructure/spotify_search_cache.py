import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic

from backend.features.spotify.domain import SpotifyUnifiedSearchResult

_DEFAULT_DEBOUNCE_SECONDS = 0.12
_DEFAULT_CACHE_TTL_SECONDS = 6.0
_DEFAULT_MAX_ENTRIES = 256


@dataclass(slots=True)
class _SearchCacheEntry:
    result: SpotifyUnifiedSearchResult
    expires_at: float


class SpotifySearchCache:
    def __init__(
        self,
        *,
        debounce_seconds: float = _DEFAULT_DEBOUNCE_SECONDS,
        cache_ttl_seconds: float = _DEFAULT_CACHE_TTL_SECONDS,
        max_entries: int = _DEFAULT_MAX_ENTRIES,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._debounce_seconds = debounce_seconds
        self._cache_ttl_seconds = cache_ttl_seconds
        self._max_entries = max_entries
        self._clock = clock

        self._lock = asyncio.Lock()
        self._cache: dict[str, _SearchCacheEntry] = {}
        self._inflight: dict[str, asyncio.Task[SpotifyUnifiedSearchResult]] = {}
        self._latest_nonce: dict[str, tuple[int, str]] = {}
        self._nonce = 0

    async def is_superseded_search(
        self, *, debounce_scope: str, cache_key: str
    ) -> bool:
        async with self._lock:
            self._nonce += 1
            nonce = self._nonce
            self._latest_nonce[debounce_scope] = (nonce, cache_key)

        await asyncio.sleep(self._debounce_seconds)

        async with self._lock:
            latest = self._latest_nonce.get(debounce_scope)
            if latest is None:
                return False

            latest_nonce, latest_cache_key = latest
            if latest_nonce == nonce:
                return False

            return latest_cache_key != cache_key

    async def get_cached_result(
        self,
        *,
        cache_key: str,
    ) -> SpotifyUnifiedSearchResult | None:
        async with self._lock:
            entry = self._cache.get(cache_key)
            if entry is None:
                return None

            if entry.expires_at <= self._clock():
                self._cache.pop(cache_key, None)
                return None

            return entry.result

    async def run_with_cache(
        self,
        *,
        cache_key: str,
        producer: Callable[[], Awaitable[SpotifyUnifiedSearchResult]],
    ) -> SpotifyUnifiedSearchResult:
        cached_result = await self.get_cached_result(cache_key=cache_key)
        if cached_result is not None:
            return cached_result

        created_task = False
        async with self._lock:
            in_flight = self._inflight.get(cache_key)
            if in_flight is None:
                in_flight = asyncio.create_task(producer())
                self._inflight[cache_key] = in_flight
                created_task = True

        try:
            result = await asyncio.shield(in_flight)
        except Exception:
            if created_task:
                async with self._lock:
                    if self._inflight.get(cache_key) is in_flight:
                        self._inflight.pop(cache_key, None)
            raise

        if created_task:
            async with self._lock:
                self._cache[cache_key] = _SearchCacheEntry(
                    result=result,
                    expires_at=self._clock() + self._cache_ttl_seconds,
                )
                self._prune_cache()
                if self._inflight.get(cache_key) is in_flight:
                    self._inflight.pop(cache_key, None)

        return result

    def _prune_cache(self) -> None:
        now = self._clock()
        expired_keys = [
            key for key, entry in self._cache.items() if entry.expires_at <= now
        ]
        for key in expired_keys:
            self._cache.pop(key, None)

        if len(self._cache) <= self._max_entries:
            return

        overflow = len(self._cache) - self._max_entries
        oldest_keys = sorted(
            self._cache,
            key=lambda key: self._cache[key].expires_at,
        )[:overflow]
        for key in oldest_keys:
            self._cache.pop(key, None)
