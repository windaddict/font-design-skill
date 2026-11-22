// tests/head_sink_probe.js: draws glyphs with the generator under test and prints what it drew, for tests/test_head_sink.py.
//
// WHAT IT'S FOR: `headSink` (scripts/gen.js, references/generator.md section 4) sinks the stem end under a lowercase head serif
// below the serif's sloped top edge, so the stem's corner no longer shows above the wedge. The Python tests hold it to what a
// reader of the outlines would check, so every assertion stays in Python and this script only reports. For each glyph it prints
// the advance, the spacing profile (L and R), the branch record, the point count and edge runs of every polygon, a sha256 of
// every polygon, and, for each stem end that sits under a lowercase head serif, the end's two corner points and the 15 points of
// the wedge drawn over it. The corners and the wedge are found from the OUTPUT, never from the generator's formulas:
//   - a stroke body is a polygon with two edge runs; the bodies of a glyph, in order, pair with the glyph's `sig` entries that
//     start with `open`, in order;
//   - a body has a lowercase head at end A (B) when its record holds ` serifA=head` (` serifB=head`) and the glyph is not upper;
//   - with runs = [[a0, a1], [b0, b1]], n = a1 - a0 + 1 and flipped = (a0 != 0): L(j) = flipped ? poly[a1 - j] : poly[a0 + j] and
//     R(j) = flipped ? poly[b0 + j] : poly[b1 - j]; end A's corners are L(0) and R(0), end B's are L(n - 1) and R(n - 1);
//   - the wedge is the first polygon after the body with one edge run and 15 points whose x range holds the mean x of the corners.
//
//   node tests/head_sink_probe.js GEN.js SPEC_JSON
//
// SPEC_JSON, one object:
//   files     [paths]   concepts files to draw
//   ids       [ids]     optional: only these concept ids
//   serifOnly bool      only concepts that map an end to "serif"
//   runs      [{style: "roman" | "italic", mults: [..]}]   italic only for a concept that maps the "x" end, at a 10 degree slant
//   variants  [{name, set}]   optional: parameter overrides applied to every concept, one drawing per variant (default one, empty)
//   headSinks ["undef" | number]   "undef" leaves the key absent
//   keys      "lower" | "all"   "lower" is every key the generator's UPPERISH does not match
//   spacing   bool      also print L and R
//   kernKeys  "chars"   also print the automatic kern of every ordered pair of these keys, in pair order
//
// The generator is loaded afresh for each concept and style: its glyph cache is never freed, and one process that drew 27
// concepts without the reload ran out of a 4 GB heap. A glyph that throws ends the probe with a non-zero exit, never a skip.
// Copyright 2026 John Knox. MIT licence.
"use strict";
const path = require("path");
const crypto = require("crypto");

const genPath = path.resolve(process.argv[2] || "");
const spec = JSON.parse(process.argv[3] || "{}");
if (!process.argv[2] || !process.argv[3]) { console.error("usage: node tests/head_sink_probe.js GEN.js SPEC_JSON"); process.exit(2); }

function load() {
  delete require.cache[genPath];
  return require(genPath);
}
const sha = (x) => crypto.createHash("sha256").update(JSON.stringify(x)).digest("hex");

function bodiesOf(g) {
  const out = [];
  g.polys.forEach((poly, i) => {
    if (g.runs[i].length !== 2) return;
    const runs = g.runs[i], flipped = runs[0][0] !== 0, n = runs[0][1] - runs[0][0] + 1;
    out.push({
      idx: i, poly, n,
      L: (j) => flipped ? poly[runs[0][1] - j] : poly[runs[0][0] + j],
      R: (j) => flipped ? poly[runs[1][0] + j] : poly[runs[1][1] - j],
    });
  });
  return out;
}

function endsOf(g) {
  if (g.upper) return [];
  const opens = g.sig.filter((s) => s.indexOf("open") === 0), bodies = bodiesOf(g), out = [];
  if (opens.length !== bodies.length) throw new Error("glyph " + JSON.stringify(g.key) + ": " + bodies.length + " bodies but " + opens.length + " open records");
  bodies.forEach((b, bi) => {
    [["A", 0], ["B", b.n - 1]].forEach(([letter, j]) => {
      if (opens[bi].indexOf(" serif" + letter + "=head") < 0) return;
      const corners = [b.L(j), b.R(j)], mx = (corners[0][0] + corners[1][0]) / 2;
      let wedge = null;
      for (let i = b.idx + 1; i < g.polys.length && !wedge; i++) {
        const p = g.polys[i];
        if (g.runs[i].length !== 1 || p.length !== 15) continue;
        const xs = p.map((q) => q[0]);
        if (Math.min.apply(null, xs) <= mx && mx <= Math.max.apply(null, xs)) wedge = p;
      }
      out.push({ body: b.idx, end: letter, corners, wedge });
    });
  });
  return out;
}

function main() {
  const out = [];
  for (const file of spec.files) {
    const ids = load().loadConcepts(path.resolve(file)).map((c) => c.id);
    for (const id of ids) {
      if (spec.ids && spec.ids.indexOf(id) < 0) continue;
      for (const run of spec.runs) {
        const m = load();   // a fresh generator, and so a fresh glyph cache, for each concept and style
        const c0 = m.loadConcepts(path.resolve(file)).filter((c) => c.id === id)[0];
        if (spec.serifOnly && Object.keys(c0.ends).map((k) => c0.ends[k]).indexOf("serif") < 0) continue;
        if (run.style === "italic" && !(c0.ends && c0.ends.x)) continue;
        for (const variant of spec.variants || [{ name: "", set: {} }]) {
          for (const mult of run.mults) for (const hs of spec.headSinks) {
            const c = Object.assign({}, c0, variant.set);
            delete c.headSink;
            if (hs !== "undef") c.headSink = hs;
            const P = m.params(c, mult, run.style === "italic" ? 10 : false);
            const rec = { file: path.basename(path.dirname(path.resolve(file))) + "/" + path.basename(file), concept: id, style: run.style, mult, variant: variant.name,
                          headSink: hs, W0: c.W, serifH: c.serifH, serifGrow: c.serifGrow || 0, glyphs: {} };
            const keys = Object.keys(m.G).filter((k) => spec.keys === "all" || !m.UPPERISH.test(k));
            const drawn = {};
            for (const k of keys) {
              const g = m.glyph(k, P);
              if (!g) continue;
              drawn[k] = g;
              rec.glyphs[k] = { adv: g.adv, sig: g.sig, counts: g.polys.map((p) => p.length), runs: g.runs, pHash: g.polys.map(sha), upper: g.upper, ends: endsOf(g) };
              if (spec.spacing) { rec.glyphs[k].L = g.L; rec.glyphs[k].R = g.R; }
            }
            if (spec.kernKeys) {
              rec.kern = [];
              for (const a of spec.kernKeys) for (const b of spec.kernKeys) rec.kern.push(m.kern(m.glyph(a, P), m.glyph(b, P), P));
            }
            out.push(rec);
          }
        }
      }
    }
  }
  process.stdout.write(JSON.stringify(out));
}

try { main(); } catch (e) { console.error("head_sink_probe.js: " + (e && e.stack || e)); process.exitCode = 1; }
