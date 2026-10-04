import { mkdir, rm, writeFile } from "node:fs/promises";
import { basename, isAbsolute, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { generatedHeader, outputRoot, tags } from "../orval.config.mjs";

const repoRoot = fileURLToPath(new URL("../../", import.meta.url));
const target = resolve(outputRoot);
const relativeTarget = relative(repoRoot, target);

if (
  relativeTarget === "" ||
  relativeTarget.startsWith("..") ||
  isAbsolute(relativeTarget) ||
  basename(target) !== "generated"
) {
  throw new Error(`Refusing to replace generated files outside the workspace: ${target}`);
}

await rm(target, { recursive: true, force: true });
await mkdir(target, { recursive: true });
await writeFile(
  resolve(target, "index.ts"),
  generatedHeader +
    "\n\n" +
    tags
      .map((tag) => {
        const featureName = tag.replace(/[-_]([a-z0-9])/g, (_, character) =>
          character.toUpperCase(),
        );
        return `export * as ${featureName} from "./${tag.replaceAll("_", "-")}";`;
      })
      .join("\n") +
    "\n",
);
