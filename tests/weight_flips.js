// weight_flips.js: the node half of tests/test_weight_decisions.py. Draws one concept of one concept file, roman or italic, with the
// generator named on the command line, and prints what weight did to each glyph's structure and branch record.
//
// WHAT IT'S FOR: a branch decision that reads drawn, weight-dependent geometry (the `xs` widening of heavier masters, the vertical
// fit's half-width) flips between the masters of a group and the exporter refuses the group (docs/plan-italic-bold.md section 0.1:
// 44 cases over the five concept files at 0.5.0). Since 0.6.0 every decision reads the geometry at mult 1 and xh 500, so a glyph's
// polygon count, point counts, edge runs and record at any multiplier must equal its mult-1 ones. One node process per concept and
// slant: a single process holding every drawing of every concept ran out of heap (measured at 4 GB while planning).
//
//   node tests/weight_flips.js flips GEN.js CONCEPTS.js ID ITALIC            {compared, flips: {key: [mults]}} against mult 1,
//                                                                             mults 0.8 to 2.0 in steps of 0.05
//   node tests/weight_flips.js records GEN.js CONCEPTS.js ID ITALIC KEY M...  per mult: {sig, polys, runs} of one glyph, as drawn
//
// ITALIC is `roman` or `italic` (10 degrees, the examples' slant). Copyright 2026 John Knox. MIT licence.
"use strict";
const [mode, genPath, conceptsPath, id, slant, ...rest] = process.argv.slice(2);
if (!mode || !genPath || !conceptsPath || !id || !slant) {
  console.error("usage: node tests/weight_flips.js flips|records GEN.js CONCEPTS.js ID roman|italic [KEY MULT...]");
  process.exit(2);
}
const m = require(require("path").resolve(genPath));
const concept = m.conceptById(m.loadConcepts(conceptsPath), id);
const italic = slant === "italic";
const sig = g => JSON.stringify([g.polys.map(p => p.length), g.runs, g.sig]);
const keys = Array.from(new Set(Object.keys(m.G).concat(italic ? Object.keys(m.GI) : [])));

if (mode === "flips") {
  const mults = [];
  for (let x = 80; x <= 200; x += 5) if (x !== 100) mults.push(x / 100);
  const ref = {};
  const P1 = m.params(concept, 1, italic);
  for (const k of keys) { const g = m.glyph(k, P1); if (g) ref[k] = sig(g); }
  let compared = 0;
  const flips = {};
  for (const mult of mults) {
    const P = m.params(concept, mult, italic);
    for (const k of Object.keys(ref)) {
      const g = m.glyph(k, P);
      compared++;
      if (!g || sig(g) !== ref[k]) (flips[k] = flips[k] || []).push(mult);
    }
  }
  console.log(JSON.stringify({ compared, flips }));
} else if (mode === "records") {
  const [key, ...mults] = rest;
  const out = {};
  for (const ms of mults) {
    const g = m.glyph(key, m.params(concept, +ms, italic));
    out[ms] = g ? { sig: g.sig, polys: g.polys, runs: g.runs } : null;
  }
  console.log(JSON.stringify(out));
} else {
  console.error(`weight_flips.js: unknown mode ${mode}`);
  process.exit(2);
}
