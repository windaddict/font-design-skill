// bounds.js: prints each glyph's vertical extent from the generator, to check alignment against the
// baseline, x-height and cap line while tuning a skeleton.
//
// WHAT IT'S FOR: a quick look at where a glyph's ink starts and stops before any font is built, so a
// stroke that hangs below the baseline or a mark that clips the win ascent is found in seconds.
//
// Usage: node bounds.js --font font.json [--concept ID] [--mult 1.5] [--italic] GLYPH...
//   e.g. node bounds.js --font examples/neutral/font.json --mult 1.5 H o g Á
// The generator module is scripts/gen.js beside this file (GEN=path overrides it, for a project that
// patched its own copy).
"use strict";
const path = require("path");
const m = require(process.env.GEN ? path.resolve(process.env.GEN) : path.join(__dirname, "gen.js"));
const { loadFontConfig } = require(path.join(__dirname, "export.js"));
const args = process.argv.slice(2);
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const fontPath = opt("--font");
if (!fontPath) { console.error("usage: node bounds.js --font font.json [--concept ID] [--mult N] [--italic] GLYPH..."); process.exit(2); }
const cfg = loadFontConfig(fontPath);
const concepts = m.loadConcepts(cfg._conceptsPath);
const concept = m.conceptById(concepts, opt("--concept", concepts[0].id));
const P = m.params(concept, +opt("--mult", 1), args.includes("--italic"));
const skip = new Set(["--font", "--concept", "--mult"]);
const glyphs = args.filter((a, i) => !a.startsWith("--") && !(i > 0 && skip.has(args[i - 1])));
const out = [];
for (const k of glyphs) {
  const g = m.glyph(k, P);
  if (!g) { out.push(`${k}:(no skeleton)`); continue; }
  let lo = 1e9, hi = -1e9;
  g.polys.forEach(p => p.forEach(q => { lo = Math.min(lo, q[1]); hi = Math.max(hi, q[1]); }));
  out.push(`${k}:${lo.toFixed(0)}/${hi.toFixed(0)} adv ${g.adv.toFixed(0)}`);
}
console.log(out.join("  "));
