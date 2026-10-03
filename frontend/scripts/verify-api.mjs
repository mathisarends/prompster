import { access, readdir } from "node:fs/promises";
import { join } from "node:path";
import { outputRoot, tags } from "../orval.config.mjs";

// Orval can print post-hook failures and still exit zero. Fail the build explicitly.
for (const tag of tags) {
  const directory = join(outputRoot, tag.replaceAll("_", "-"));
  for (const file of ["api.ts", "models.ts", "index.ts"]) {
    await access(join(directory, file));
  }
  if ((await readdir(directory)).includes("api.schemas.ts")) {
    throw new Error(`Incomplete code generation for ${tag}`);
  }
}
