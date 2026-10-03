import { mkdtemp, readFile, readdir, rm } from "node:fs/promises";
import { isAbsolute, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { readConfigFileAndWriteSchema } from "@lit/localize-tools/lib/config.js";
import { RuntimeLitLocalizer } from "@lit/localize-tools/lib/modes/runtime.js";

const root = fileURLToPath(new URL("../", import.meta.url));
const config = readConfigFileAndWriteSchema(join(root, "lit-localize.json"));
const temporary = await mkdtemp(join(root, ".codegen-check-i18n-"));
const generated = join(temporary, "generated");
const codes = join(temporary, "locale-codes.ts");
try {
  const localizer = new RuntimeLitLocalizer({
    ...config,
    output: { ...config.output, outputDir: generated, localeCodesModule: codes },
  });
  const { messages, errors } = localizer.extractSourceMessages();
  if (errors.length) {
    throw new Error(`Cannot extract translations: ${errors.length} source errors.`);
  }
  const sourceIds = new Set(messages.map((message) => message.name));
  const { translations } = localizer.readTranslationsSync();
  for (const locale of config.targetLocales) {
    const translated = translations.get(locale) ?? [];
    const ids = new Set(translated.map((message) => message.name));
    const missing = [...sourceIds].filter((id) => !ids.has(id));
    const obsolete = [...ids].filter((id) => !sourceIds.has(id));
    const empty = translated.filter(
      (message) =>
        !message.contents.some((part) => (typeof part === "string" ? part.trim() : true)),
    );
    if (missing.length || obsolete.length || empty.length || ids.size !== translated.length) {
      throw new Error(
        `${locale}: ${missing.length} missing, ${obsolete.length} obsolete, ${empty.length} empty translations. Run npm run i18n:extract and translate every target.`,
      );
    }
  }
  // Also validates placeholder count/content with Lit's official validator.
  await localizer.build();
  const committed = config.resolve(config.output.outputDir);
  const files = (await readdir(generated)).sort();
  if (JSON.stringify(files) !== JSON.stringify((await readdir(committed)).sort())) {
    throw new Error("Generated locale file list differs. Run npm run i18n:build.");
  }
  const pairs = files.map((file) => [join(generated, file), join(committed, file)]);
  pairs.push([codes, config.resolve(config.output.localeCodesModule)]);
  for (const [expected, actual] of pairs) {
    const normalize = (text) => text.replaceAll("\r\n", "\n");
    if (normalize(await readFile(expected, "utf8")) !== normalize(await readFile(actual, "utf8"))) {
      throw new Error(`Stale translations: ${relative(root, actual)}. Run npm run i18n:build.`);
    }
  }
  process.stdout.write(
    `${sourceIds.size} messages complete in ${config.targetLocales.join(", ")}; generated locales match.\n`,
  );
} finally {
  const target = relative(root, temporary);
  if (isAbsolute(target) || target.startsWith("..") || !target.startsWith(".codegen-check-i18n-")) {
    throw new Error("Refusing to remove a directory outside the i18n check workspace.");
  }
  await rm(temporary, { recursive: true, force: true });
}
