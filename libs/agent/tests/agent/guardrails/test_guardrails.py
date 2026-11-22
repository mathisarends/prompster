import pytest

from agent.deck import (
    DeckDraft,
    DeckDraftTrack,
    DeckDraftTracksRemoved,
    DeckStore,
)
from agent.guardrails import Guardrail, PostRunGuardrails


def _track(title: str, uri: str) -> DeckDraftTrack:
    return DeckDraftTrack(
        title=title,
        artist="a-ha",
        year=1985,
        spotify_uri=uri,
        cover_url=f"https://i.scdn.co/image/{title}.jpg",
    )


def _store_with_tracks(*tracks: DeckDraftTrack) -> DeckStore:
    store = DeckStore(DeckDraft(name="Deck", tracks=list(tracks)))
    store.drain_deck_draft_updates()
    return store


class TestPostRunGuardrailsDefaults:
    @pytest.mark.asyncio
    async def test_default_guardrail_removes_duplicate_tracks(self) -> None:
        original = _track("Take On Me", "spotify:track:1")
        duplicate = _track("Take On Me", "spotify:track:1")
        other = _track("Billie Jean", "spotify:track:2")
        store = _store_with_tracks(original, duplicate, other)
        guardrails = PostRunGuardrails(store)

        updates = await guardrails.run()

        assert len(updates) == 1
        assert isinstance(updates[0], DeckDraftTracksRemoved)
        assert updates[0].track_ids == [duplicate.id]
        assert store.draft is not None
        assert [track.id for track in store.draft.tracks] == [original.id, other.id]

    @pytest.mark.asyncio
    async def test_run_returns_no_updates_when_deck_already_clean(self) -> None:
        store = _store_with_tracks(
            _track("Take On Me", "spotify:track:1"),
            _track("Billie Jean", "spotify:track:2"),
        )
        guardrails = PostRunGuardrails(store)

        updates = await guardrails.run()

        assert updates == []

    @pytest.mark.asyncio
    async def test_run_returns_no_updates_when_no_draft_exists(self) -> None:
        store = DeckStore()
        guardrails = PostRunGuardrails(store)

        updates = await guardrails.run()

        assert updates == []

    @pytest.mark.asyncio
    async def test_run_drains_updates_so_a_second_run_is_empty(self) -> None:
        original = _track("Take On Me", "spotify:track:1")
        duplicate = _track("Take On Me", "spotify:track:1")
        store = _store_with_tracks(original, duplicate)
        guardrails = PostRunGuardrails(store)

        first = await guardrails.run()
        second = await guardrails.run()

        assert len(first) == 1
        assert second == []


class TestPostRunGuardrailsRegistration:
    @pytest.mark.asyncio
    async def test_registered_guardrails_run_in_registration_order(self) -> None:
        store = _store_with_tracks(_track("Take On Me", "spotify:track:1"))
        guardrails = PostRunGuardrails(store)
        calls: list[str] = []

        @guardrails.guardrail
        def first(store: DeckStore) -> None:
            calls.append("first")

        @guardrails.guardrail
        def second(store: DeckStore) -> None:
            calls.append("second")

        await guardrails.run()

        assert calls == ["first", "second"]

    @pytest.mark.asyncio
    async def test_async_guardrail_is_awaited(self) -> None:
        store = _store_with_tracks(_track("Take On Me", "spotify:track:1"))
        guardrails = PostRunGuardrails(store)
        calls: list[str] = []

        @guardrails.guardrail
        async def record(store: DeckStore) -> None:
            calls.append("async")

        await guardrails.run()

        assert calls == ["async"]

    @pytest.mark.asyncio
    async def test_guardrail_receives_the_deck_store(self) -> None:
        store = _store_with_tracks(_track("Take On Me", "spotify:track:1"))
        guardrails = PostRunGuardrails(store)
        seen: list[DeckStore] = []

        @guardrails.guardrail
        def capture(store: DeckStore) -> None:
            seen.append(store)

        await guardrails.run()

        assert seen == [store]

    def test_guardrail_decorator_defaults_name_to_function_name(self) -> None:
        guardrails = PostRunGuardrails(DeckStore())

        @guardrails.guardrail
        def cap_to_limit(store: DeckStore) -> None:
            pass

        assert cap_to_limit.__name__ == "cap_to_limit"

    @pytest.mark.asyncio
    async def test_guardrail_decorator_honors_explicit_name(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        guardrails = PostRunGuardrails(DeckStore())

        @guardrails.guardrail(name="custom_name")
        def some_fn(store: DeckStore) -> None:
            raise RuntimeError("boom")

        with caplog.at_level("ERROR"):
            await guardrails.run()

        assert "custom_name" in caplog.text


class TestPostRunGuardrailsFailureIsolation:
    @pytest.mark.asyncio
    async def test_failing_guardrail_does_not_block_later_guardrails(self) -> None:
        store = _store_with_tracks(_track("Take On Me", "spotify:track:1"))
        guardrails = PostRunGuardrails(store)
        calls: list[str] = []

        @guardrails.guardrail
        def boom(store: DeckStore) -> None:
            calls.append("boom")
            raise RuntimeError("guardrail exploded")

        @guardrails.guardrail
        def after(store: DeckStore) -> None:
            calls.append("after")

        updates = await guardrails.run()

        assert calls == ["boom", "after"]
        assert updates == []


class TestGuardrail:
    @pytest.mark.asyncio
    async def test_apply_invokes_sync_callable(self) -> None:
        store = DeckStore()
        seen: list[DeckStore] = []
        guardrail = Guardrail(name="g", fn=lambda store: seen.append(store))

        await guardrail.apply(store)

        assert seen == [store]

    @pytest.mark.asyncio
    async def test_apply_awaits_async_callable(self) -> None:
        store = DeckStore()
        seen: list[DeckStore] = []

        async def fn(store: DeckStore) -> None:
            seen.append(store)

        guardrail = Guardrail(name="g", fn=fn)

        await guardrail.apply(store)

        assert seen == [store]

    def test_guardrails_are_equal_by_name(self) -> None:
        a = Guardrail(name="same", fn=lambda store: None)
        b = Guardrail(name="same", fn=lambda store: None)
        c = Guardrail(name="other", fn=lambda store: None)

        assert a == b
        assert a != c
        assert hash(a) == hash(b)
