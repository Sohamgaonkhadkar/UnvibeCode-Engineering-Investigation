#!/usr/bin/env node
// Differential oracle helper used only to generate validation evidence.
// Set TSCONFIG_ORACLE_PACKAGE_JSON to a package.json in an environment where
// typescript and jsonc-parser are installed, then send {"cases": [...]} on
// stdin.  The helper mirrors the production choices made by Node tools:
// strip one BOM before jsonc-parser and enable allowTrailingComma.
import { createRequire } from 'node:module';

const packageJson = process.env.TSCONFIG_ORACLE_PACKAGE_JSON;
if (!packageJson) {
  throw new Error('TSCONFIG_ORACLE_PACKAGE_JSON is required');
}
const require = createRequire(packageJson);
const ts = require('typescript');
const jsonc = require('jsonc-parser');

let input = '';
for await (const chunk of process.stdin) input += chunk;
const payload = JSON.parse(input);
const results = payload.cases.map(({ name, text }) => {
  const tsResult = ts.parseConfigFileTextToJson('tsconfig.json', text);
  const errors = [];
  const value = jsonc.parse(text.replace(/^\uFEFF/, ''), errors, {
    allowTrailingComma: true,
  });
  return {
    name,
    typescript: {
      config: tsResult.config,
      error: tsResult.error
        ? ts.flattenDiagnosticMessageText(tsResult.error.messageText, ' ')
        : null,
    },
    jsonc_parser: {
      value,
      errors: errors.map((error) => ({
        code: jsonc.printParseErrorCode(error.error),
        offset: error.offset,
        length: error.length,
      })),
    },
  };
});

process.stdout.write(
  JSON.stringify(
    {
      typescript_version: ts.version,
      jsonc_parser_version: require('jsonc-parser/package.json').version,
      results,
    },
    null,
    2,
  ) + '\n',
);
