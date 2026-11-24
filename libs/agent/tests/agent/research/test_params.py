from agent.research.params import SearchParams


def test_research_params_have_no_status_field() -> None:
    assert "status" not in SearchParams.model_json_schema()["properties"]
