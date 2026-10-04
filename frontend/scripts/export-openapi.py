"""Export the backend's canonical OpenAPI document without running an HTTP server."""

import json
import sys
from pathlib import Path

from backend.main import app

target = Path(__file__).resolve().parents[1] / "openapi.json"
document = app.openapi()
if "--check" in sys.argv:
    if json.loads(target.read_text(encoding="utf-8")) != document:
        raise SystemExit(
            "OpenAPI drift: run npm run api:export and npm run api:generate"
        )
    print("OpenAPI specification matches the backend.")
else:
    target.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {target}")
