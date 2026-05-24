import asyncio

from backend.features.spotify.application.ports import SpotifyUnifiedSearchResult
from backend.features.spotify.infrastructure.spotify_search_cache import (
    SpotifySearchCache,
)


def _empty_result() -> SpotifyUnifiedSearchResult:
    return SpotifyUnifiedSearchResult(tracks=[], playlists=[], artists=[])


class TestSpotifySearchCache:
    def test_run_with_cache_reuses_cached_result_until_ttl(self) -> None:
        cache = SpotifySearchCache(
            debounce_seconds=0.0,
            cache_ttl_seconds=60.0,
            max_entries=16,
        )
        producer_calls = 0

        async def producer() -> SpotifyUnifiedSearchResult:
            nonlocal producer_calls
            producer_calls += 1
            return _empty_result()

        async def run() -> tuple[
            SpotifyUnifiedSearchResult, SpotifyUnifiedSearchResult
        ]:
            first = await cache.run_with_cache(cache_key="q:muse", producer=producer)
            second = await cache.run_with_cache(cache_key="q:muse", producer=producer)
            return first, second

        first, second = asyncio.run(run())

        assert first is second
        assert producer_calls == 1

    def test_run_with_cache_expires_entry_after_ttl(self) -> None:
        cache = SpotifySearchCache(
            debounce_seconds=0.0,
            cache_ttl_seconds=0.01,
            max_entries=16,
        )
        producer_calls = 0

        async def producer() -> SpotifyUnifiedSearchResult:
            nonlocal producer_calls
            producer_calls += 1
            return _empty_result()

        async def run() -> None:
            await cache.run_with_cache(cache_key="q:muse", producer=producer)
            await asyncio.sleep(0.02)
            await cache.run_with_cache(cache_key="q:muse", producer=producer)

        asyncio.run(run())

        assert producer_calls == 2

    def test_run_with_cache_coalesces_identical_inflight_requests(self) -> None:
        cache = SpotifySearchCache(
            debounce_seconds=0.0,
            cache_ttl_seconds=60.0,
            max_entries=16,
        )
        producer_calls = 0

        async def producer() -> SpotifyUnifiedSearchResult:
            nonlocal producer_calls
            producer_calls += 1
            await asyncio.sleep(0.02)
            return _empty_result()

        async def run() -> tuple[
            SpotifyUnifiedSearchResult, SpotifyUnifiedSearchResult
        ]:
            first = asyncio.create_task(
                cache.run_with_cache(cache_key="q:muse", producer=producer)
            )
            second = asyncio.create_task(
                cache.run_with_cache(cache_key="q:muse", producer=producer)
            )
            return await asyncio.gather(first, second)

        first, second = asyncio.run(run())

        assert first is second
        assert producer_calls == 1

    def test_is_superseded_search_returns_true_for_older_different_query(self) -> None:
        cache = SpotifySearchCache(
            debounce_seconds=0.05,
            cache_ttl_seconds=60.0,
            max_entries=16,
        )

        async def run() -> tuple[bool, bool]:
            first = asyncio.create_task(
                cache.is_superseded_search(
                    debounce_scope="user-1|8|track",
                    cache_key="sk|8|track",
                )
            )
            await asyncio.sleep(0.01)
            second = asyncio.create_task(
                cache.is_superseded_search(
                    debounce_scope="user-1|8|track",
                    cache_key="ski|8|track",
                )
            )
            return await asyncio.gather(first, second)

        first_is_superseded, second_is_superseded = asyncio.run(run())

        assert first_is_superseded is True
        assert second_is_superseded is False

    def test_is_superseded_search_does_not_supersede_identical_key(self) -> None:
        cache = SpotifySearchCache(
            debounce_seconds=0.05,
            cache_ttl_seconds=60.0,
            max_entries=16,
        )

        async def run() -> tuple[bool, bool]:
            first = asyncio.create_task(
                cache.is_superseded_search(
                    debounce_scope="user-1|8|track",
                    cache_key="muse|8|track",
                )
            )
            await asyncio.sleep(0.01)
            second = asyncio.create_task(
                cache.is_superseded_search(
                    debounce_scope="user-1|8|track",
                    cache_key="muse|8|track",
                )
            )
            return await asyncio.gather(first, second)

        first_is_superseded, second_is_superseded = asyncio.run(run())

        assert first_is_superseded is False
        assert second_is_superseded is False
