import { readdir, rm, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as prettier from "prettier";

const rootDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const generatedDir = path.join(rootDir, "src", "api", "generated");

const tagClients = [
  ["auth", "auth-api.ts"],
  ["sessions", "session-api.ts"],
  ["users", "user-api.ts"],
];

for (const [tagName, targetFileName] of tagClients) {
  const tagDir = path.join(generatedDir, tagName);
  const sourcePath = path.join(tagDir, `${tagName}.ts`);
  const targetPath = path.join(generatedDir, targetFileName);

  let source;
  try {
    source = await readFile(sourcePath, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") {
      continue;
    }

    throw error;
  }

  const normalizedSource = source
    .replaceAll("from '../model'", "from './model'")
    .replaceAll('from "../model"', 'from "./model"')
    .replaceAll("from '../../http-client'", "from '../http-client'")
    .replaceAll('from "../../http-client"', 'from "../http-client"');

  await writeFile(sourcePath, normalizedSource);
  await rm(targetPath, { force: true });
  await rename(sourcePath, targetPath);
  await rm(tagDir, { recursive: true, force: true });
}

const getTypeScriptFiles = async (directory) => {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(directory, entry.name);

      if (entry.isDirectory()) {
        return getTypeScriptFiles(entryPath);
      }

      if (entry.isFile() && entry.name.endsWith(".ts")) {
        return [entryPath];
      }

      return [];
    }),
  );

  return files.flat();
};

const formatGeneratedFiles = async () => {
  const typeScriptFiles = await getTypeScriptFiles(generatedDir);

  await Promise.all(
    typeScriptFiles.map(async (filePath) => {
      const source = await readFile(filePath, "utf8");
      const prettierConfig = await prettier.resolveConfig(filePath);
      const formatted = await prettier.format(source, {
        ...(prettierConfig ?? {}),
        filepath: filePath,
      });

      if (formatted !== source) {
        await writeFile(filePath, formatted);
      }
    }),
  );
};

await formatGeneratedFiles();
