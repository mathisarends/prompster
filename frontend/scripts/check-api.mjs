import { mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = fileURLToPath(new URL("../", import.meta.url));
const temporary = await mkdtemp(join(root, ".codegen-check-"));
async function files(directory, prefix = "") {
  const entries = await readdir(directory, { withFileTypes: true });
  const result = [];
  for (const entry of entries) {
    const relative = join(prefix, entry.name);
    if (entry.isDirectory()) {
      result.push(...(await files(join(directory, entry.name), relative)));
    } else {
      result.push(relative);
    }
  }
  return result.sort();
}
try {
  const generated = join(temporary, "generated");
  const result = spawnSync(process.execPath, [process.env.npm_execpath, "run", "api:generate"], {
    cwd: root,
    env: { ...process.env, ORVAL_OUTPUT_ROOT: generated },
    stdio: "inherit",
  });
  if (result.status !== 0) {
    throw new Error("API generation failed");
  }
  const committed = join(root, "src/api/generated");
  const expected = await files(generated);
  if (JSON.stringify(await files(committed)) !== JSON.stringify(expected)) {
    throw new Error("Generated API file list differs. Run npm run api:generate.");
  }
  for (const file of expected) {
    const left = (await readFile(join(committed, file), "utf8")).replaceAll("\r\n", "\n");
    const right = (await readFile(join(generated, file), "utf8")).replaceAll("\r\n", "\n");
    if (left !== right) {
      throw new Error(`Generated API drift: ${file}`);
    }
  }
  process.stdout.write("Generated HTTP client matches the OpenAPI specification.\n");
} finally {
  await rm(temporary, { recursive: true, force: true });
}
