import { writeFile } from "node:fs/promises";
const response = await fetch(process.env.OPENAPI_URL ?? "http://127.0.0.1:8000/openapi.json");
if (!response.ok) {
  throw new Error(`OpenAPI download failed: HTTP ${response.status}`);
}
const spec = await response.json();
if (!spec.openapi || !spec.paths) {
  throw new Error("The response is not an OpenAPI document");
}
await writeFile(new URL("../openapi.json", import.meta.url), JSON.stringify(spec, null, 2) + "\n");
