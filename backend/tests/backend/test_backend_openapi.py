from backend.main import app
from backend.features.session.presentation.rpc.router import contract


def test_compiles_canonical_success_response_contracts() -> None:
    document = app.openapi()
    paths = document["paths"]

    assert "/health" in paths
    assert "/api/v1/health" not in paths

    health = document["components"]["schemas"]["HealthResponse"]
    assert health["properties"]["status"]["const"] == "ok"

    assert "/api/v1/sessions/{session_id}/messages" not in paths
    assert any(
        route.path == "/api/v1/sessions/{session_id}/stream" for route in app.routes
    )
    assert [server["name"] for server in contract.to_openrpc()["servers"]] == [
        "session"
    ]

    pdf = paths["/api/v1/sessions/{session_id}/playlist/pdf"]["get"]["responses"]["200"]
    assert set(pdf["content"]) == {"application/pdf"}
    assert "Content-Disposition" in pdf["headers"]

    pdf_responses = paths["/api/v1/sessions/{session_id}/playlist/pdf"]["get"][
        "responses"
    ]
    assert pdf_responses["401"]["content"]["application/problem+json"]
    assert pdf_responses["404"]["content"]["application/problem+json"]
    assert pdf_responses["403"]["content"]["application/problem+json"]
    assert pdf_responses["400"]["content"]["application/problem+json"]

    empty = paths["/api/v1/sessions/{session_id}/messages/stop"]["post"]["responses"][
        "204"
    ]
    assert "content" not in empty

    redirect = paths["/api/v1/auth/google/login"]["get"]["responses"]["307"]
    assert "content" not in redirect
    assert "Location" in redirect["headers"]

    assert "x-fastapi-canon" not in str(document)
