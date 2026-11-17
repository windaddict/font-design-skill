// eslint.config.js: the JavaScript lint for scripts/*.js and scripts/concepts/*.js.
//
// WHAT IT'S FOR: `node --check` (npm run check) proves only that each file parses. This catches the
// next class of mistake that still parses: a misspelt name (no-undef), a variable assigned and never
// read, an unreachable branch, a duplicate key in a parameter table. CI runs it as
// `npx --yes eslint@10.14.0`, so the skill keeps no npm dependencies; the rules are listed here rather
// than imported from @eslint/js for the same reason (a config import needs the package installed).
//
// The rules are eslint:recommended's correctness rules. Style is not linted.
"use strict";

const node = {
  require: "readonly", module: "writable", process: "readonly", console: "readonly", __dirname: "readonly",
  Buffer: "readonly", setTimeout: "readonly", clearTimeout: "readonly",
};

const browser = {
  window: "readonly", document: "readonly", console: "readonly", performance: "readonly",
  requestAnimationFrame: "readonly", setTimeout: "readonly", URLSearchParams: "readonly", fetch: "readonly",
};

const rules = {
  "no-undef": "error",
  "no-unused-vars": ["error", { args: "none", caughtErrors: "none" }],
  "no-unreachable": "error",
  "no-dupe-keys": "error",
  "no-dupe-args": "error",
  "no-duplicate-case": "error",
  "no-redeclare": "error",
  "no-self-assign": "error",
  "no-self-compare": "error",
  "no-const-assign": "error",
  "no-func-assign": "error",
  "no-unsafe-negation": "error",
  "no-cond-assign": ["error", "except-parens"],
  "no-constant-condition": ["error", { checkLoops: false }],
  "no-fallthrough": "error",
  "no-sparse-arrays": "error",
  "use-isnan": "error",
  "valid-typeof": "error",
  "getter-return": "error",
  "no-loss-of-precision": "error",
  "no-dupe-else-if": "error",
  "no-unsafe-finally": "error",
};

module.exports = [
  {
    files: ["scripts/*.js", "scripts/concepts/*.js", "eslint.config.js"],
    languageOptions: { ecmaVersion: 2022, sourceType: "commonjs", globals: node },
    rules,
  },
  {
    // render.js runs in the page: build-page.js splices gen.js (module.exports stripped), the
    // project's concepts.js and this file into one <script>, so gen.js's top-level functions are in
    // scope without an import. They are named here so a misspelling still fails.
    files: ["scripts/render.js"],
    languageOptions: { sourceType: "script", globals: { ...browser, glyph: "readonly", kern: "readonly", layWord: "readonly", wrap: "readonly" } },
  },
];
