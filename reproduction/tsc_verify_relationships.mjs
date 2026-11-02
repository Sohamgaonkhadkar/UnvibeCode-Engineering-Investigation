#!/usr/bin/env node
/**
 * Verify a lost-relationship JSONL file with the official TypeScript resolver.
 *
 * Usage:
 *   npm install --no-save typescript@5.9.3
 *   node reproduction/tsc_verify_relationships.mjs \
 *     --root /path/to/repository \
 *     --input evidence/tsconfig-jsonc/lost_relationships.jsonl \
 *     --output evidence/tsconfig-jsonc/typescript_api_verification.json
 *
 * Each unique (source_file, import_specifier) is resolved once with
 * ts.resolveModuleName using options parsed by TypeScript from the source
 * tree's actual JSONC tsconfig. Every input row is then compared with the
 * compiler-resolved file. This is an independent cross-check of the Python
 * TypeScript-`paths` oracle used for aggregate classification.
 */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
let ts;
try {
  ts = require("typescript");
} catch {
  console.error("Install TypeScript first, e.g. npm install --no-save typescript@5.9.3");
  process.exit(2);
}

const args = process.argv.slice(2);
function valueAfter(flag) {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
}

const root = path.resolve(valueAfter("--root") ?? ".");
const input = valueAfter("--input");
const output = valueAfter("--output");
if (!input) {
  console.error("--input is required");
  process.exit(2);
}

const configPath = ts.findConfigFile(root, ts.sys.fileExists, "tsconfig.json");
if (!configPath) {
  console.error(`No tsconfig.json found at ${root}`);
  process.exit(2);
}
const read = ts.readConfigFile(configPath, ts.sys.readFile);
if (read.error) {
  console.error(ts.flattenDiagnosticMessageText(read.error.messageText, "\n"));
  process.exit(1);
}
const parsed = ts.parseJsonConfigFileContent(
  read.config,
  ts.sys,
  path.dirname(configPath),
  undefined,
  configPath,
);
const cache = ts.createModuleResolutionCache(
  root,
  (fileName) => fileName,
  parsed.options,
);

const rows = fs.readFileSync(input, "utf8")
  .split(/\r?\n/)
  .filter((line) => line.trim())
  .map((line) => JSON.parse(line));

const cacheByPair = new Map();
function resolve(row) {
  const key = `${row.source_file}\0${row.import_specifier}`;
  if (cacheByPair.has(key)) return cacheByPair.get(key);
  const result = ts.resolveModuleName(
    row.import_specifier,
    path.resolve(root, row.source_file),
    parsed.options,
    ts.sys,
    cache,
    undefined,
    ts.ModuleKind.ESNext,
  );
  const resolved = result.resolvedModule;
  const value = resolved
    ? path.relative(root, resolved.resolvedFileName).split(path.sep).join("/")
    : null;
  cacheByPair.set(key, value);
  return value;
}

let matched = 0;
const mismatches = [];
for (const row of rows) {
  const compilerTarget = resolve(row);
  if (compilerTarget === row.target_file) {
    matched += 1;
  } else if (mismatches.length < 50) {
    mismatches.push({
      source_file: row.source_file,
      source_line: row.source_line,
      import_specifier: row.import_specifier,
      graph_target: row.target_file,
      typescript_target: compilerTarget,
    });
  }
}

const summary = {
  typescript_version: ts.version,
  config_path: path.relative(root, configPath).split(path.sep).join("/"),
  paths_pattern_count: Object.keys(parsed.options.paths ?? {}).length,
  input_name: path.basename(input),
  rows_checked: rows.length,
  unique_source_specifier_pairs_checked: cacheByPair.size,
  matched_rows: matched,
  mismatched_rows: rows.length - matched,
  mismatch_examples: mismatches,
};

if (output) {
  fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
}
console.log(JSON.stringify(summary, null, 2));
process.exit(matched === rows.length ? 0 : 1);
