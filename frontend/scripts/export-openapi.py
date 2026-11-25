"""Export the backend's REST OpenAPI document without running an HTTP server.

SSE streams are left out: they use OpenAPI 3.2 stream schemas and get their own
fastapi-canon client from ``codegen.toml`` (``src/api/session-streams``).
"""

import json
import sys
from pathlib import Path
from typing import Any

from backend.main import app

_EVENT_STREAM = "text/event-stream"
_SCHEMA_REF = "#/components/schemas/"


def _is_stream(operation: dict[str, Any]) -> bool:
    responses = operation.get("responses", {}).values()
    return any(_EVENT_STREAM in response.get("content", {}) for response in responses)


def _rest_document() -> dict[str, Any]:
    document = app.openapi()
    rest: dict[str, Any] = {}
    streams: list[dict[str, Any]] = []
    for path, item in document["paths"].items():
        operations: dict[str, Any] = {}
        for method, operation in item.items():
            if isinstance(operation, dict) and _is_stream(operation):
                streams.append(operation)
            else:
                operations[method] = operation
        if any(isinstance(operation, dict) for operation in operations.values()):
            rest[path] = operations
    # Drop only the schemas that just the streams use; Canon also registers
    # problem schemas no path references.
    schemas = document["components"]["schemas"]
    stream_only = _referenced_schemas(streams, schemas) - _referenced_schemas(
        rest, schemas
    )
    components = {
        **document["components"],
        "schemas": {
            name: schema for name, schema in schemas.items() if name not in stream_only
        },
    }
    return {**document, "paths": rest, "components": components}


def _referenced_schemas(root: object, schemas: dict[str, Any]) -> set[str]:
    """Names of the component schemas reachable from ``root``."""
    found: set[str] = set()
    pending = [root]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith(_SCHEMA_REF):
                name = ref.removeprefix(_SCHEMA_REF)
                if name not in found:
                    found.add(name)
                    pending.append(schemas[name])
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    return found


target = Path(__file__).resolve().parents[1] / "openapi.json"
document = _rest_document()
if "--check" in sys.argv:
    if json.loads(target.read_text(encoding="utf-8")) != document:
        raise SystemExit(
            "OpenAPI drift: run pnpm run api:export and pnpm run api:generate"
        )
    print("OpenAPI specification matches the backend.")
else:
    target.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {target}")
