import { readFile, readdir, writeFile } from "node:fs/promises";
import { extname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import ts from "typescript";

const root = fileURLToPath(new URL("../", import.meta.url));
const extensions = new Set([".ts", ".tsx", ".js", ".mjs"]);
const mode = process.argv[2];
if (mode !== "--check" && mode !== "--write") {
  throw new Error("Usage: node scripts/curly.mjs --check|--write [files...]");
}

async function collect(path) {
  if (path === join(root, "src", "api", "session-rpc")) {
    return [];
  }
  const entries = await readdir(path, { withFileTypes: true });
  const files = await Promise.all(
    entries.map(async (entry) => {
      const name = join(path, entry.name);
      if (entry.isDirectory()) {
        return collect(name);
      }
      return entry.isFile() && extensions.has(extname(name)) ? [name] : [];
    }),
  );
  return files.flat();
}

const paths =
  process.argv.length > 3
    ? process.argv.slice(3).map((path) => resolve(path))
    : (await Promise.all(["src", "scripts"].map((directory) => collect(join(root, directory)))))
        .flat()
        .concat([join(root, "vite.config.ts"), join(root, "orval.config.mjs")]);

let violations = 0;
for (const path of paths.filter(
  (path) =>
    extensions.has(extname(path)) &&
    path !== join(root, "src", "shared", "api", "session-rpc-client.ts"),
)) {
  const source = await readFile(path, "utf8");
  const sourceFile = ts.createSourceFile(
    path,
    source,
    ts.ScriptTarget.Latest,
    true,
    extname(path) === ".tsx"
      ? ts.ScriptKind.TSX
      : extname(path) === ".ts"
        ? ts.ScriptKind.TS
        : ts.ScriptKind.JS,
  );
  if (sourceFile.parseDiagnostics.length) {
    throw new Error(`Cannot parse ${relative(root, path)}`);
  }

  const insertions = [];
  function requireBlock(statement, depth) {
    if (ts.isBlock(statement)) {
      return;
    }
    violations += 1;
    const { line } = sourceFile.getLineAndCharacterOfPosition(statement.getStart(sourceFile));
    if (mode === "--check") {
      process.stderr.write(`${relative(root, path)}:${line + 1}: missing {}\n`);
    }
    insertions.push({ position: statement.getStart(sourceFile), value: "{\n", depth });
    insertions.push({ position: statement.end, value: "\n}", depth });
  }

  function visit(node, depth = 0) {
    if (ts.isIfStatement(node)) {
      requireBlock(node.thenStatement, depth);
      if (node.elseStatement && !ts.isIfStatement(node.elseStatement)) {
        requireBlock(node.elseStatement, depth);
      }
    } else if (
      ts.isForStatement(node) ||
      ts.isForInStatement(node) ||
      ts.isForOfStatement(node) ||
      ts.isWhileStatement(node) ||
      ts.isDoStatement(node)
    ) {
      requireBlock(node.statement, depth);
    }
    ts.forEachChild(node, (child) => visit(child, depth + 1));
  }
  visit(sourceFile);

  if (mode === "--write" && insertions.length) {
    insertions.sort((left, right) => right.position - left.position || left.depth - right.depth);
    let output = source;
    for (const { position, value } of insertions) {
      output = output.slice(0, position) + value + output.slice(position);
    }
    await writeFile(path, output);
  }
}

if (mode === "--check" && violations) {
  process.stderr.write(`${violations} control-flow statement(s) need braces.\n`);
  process.exitCode = 1;
} else if (mode === "--write") {
  process.stdout.write(`Added braces to ${violations} control-flow statement(s).\n`);
}
