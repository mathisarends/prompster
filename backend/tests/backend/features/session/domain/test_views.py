from backend.features.session.domain import Phase


class TestPhase:
    def test_values_match_persisted_agent_contract(self) -> None:
        assert Phase.ONBOARDING == "onboarding"
        assert Phase.BUILD == "build"
