// tests/wonk_amount_probe.js: draws glyphs with the generator under test and prints what it drew, for tests/test_wonk_amount.py
// and tests/test_wonk_default.py.
//
// WHAT IT'S FOR: `wonkAmount` (a concept setting, references/generator.md section 4) sets how far the letters a concept names in
// `wonk` lean back. The Python tests hold it to what a reader of the outlines would check, so every assertion stays in Python and
// this script only reports and asserts nothing. The lean of a stem is found from the OUTPUT, never from the generator's formulas:
//   - a stroke body is a polygon with two edge runs; with runs = [[a0, a1], [b0, b1]], n = a1 - a0 + 1 and flipped = (a0 != 0):
//     L(j) = flipped ? poly[a1 - j] : poly[a0 + j] and R(j) = flipped ? poly[b0 + j] : poly[b1 - j], the same index on the two
//     edges of the stroke (tests/head_sink_probe.js bodiesOf);
//   - `centre` is two points of the centre line of the first body of a glyph: the midpoints of L(j) and R(j) at a quarter and at
//     three quarters of the run (j = round(0.25 (n - 1)) and round(0.75 (n - 1))), or null when the glyph has no body.
//
//   node tests/wonk_amount_probe.js GEN.js MODE SPEC_JSON
//
// MODE and SPEC_JSON:
//   keys                          prints every key of G.
//   concepts  {files}             per concept {file, id, xs, ends, serif, shear, bend}: `serif` is true when a value of `ends` is
//                                 "serif"; `shear` and `bend` are true when the concept sets a non-zero one.
//   draw      {file, id, set, wonk, amounts, styles, mults, keys}
//                                 `set` is merged over the concept; `wonk` is a string, "ALL" (every key of G joined) or absent
//                                 (the concept's own); each entry of `amounts` is a number or "undef" (the key deleted); with
//                                 `amounts` absent the concept keeps its own wonkAmount. `styles` are "roman" and/or "italic"
//                                 (italic is drawn at 10 degrees); `keys` absent means every key of G. Per glyph draw it prints
//                                 {concept, style, mult, amount, key, xs, adv, counts, runs, sig, pHash, L, R, centre}.
//   refusals  {file, id, cases}   each case is {label, value} or {label, token} with token one of NaN, Infinity, -Infinity,
//                                 undefined, absent (JSON cannot carry those). Per case it prints {label, delivered, message}:
//                                 `delivered` is typeof v + ":" + String(v) of the value handed to params() ("absent" for a
//                                 deleted key), `message` the error text or null.
//   old       {file, styles, mults, old}
//                                 for every concept of the file, with `wonk` set to every key and `wonkAmount` absent, draws every
//                                 key with the generator under test and with the generator at the path `old`. Per glyph draw it
//                                 prints {concept, style, mult, key, same, leaning, first}: `same` is exact equality of polys, adv,
//                                 L, R, sig and runs; `leaning` is whether the old generator's drawing differs from its own
//                                 drawing of the concept with wonk "" ; `first` names the first field that differs, or null.
//                                 Italic only for a concept that maps the "x" end, at 10 degrees.
//
// The generator is loaded afresh for each concept and style: its glyph cache is never freed, and one process that drew 27
// concepts without the reload ran out of a 4 GB heap. A glyph or a params() call that throws outside `refusals` ends the probe
// with a non-zero exit, never a skip.
// Copyright 2026 John Knox. MIT licence.
"use strict";
const path = require("path");
const crypto = require("crypto");

const genPath = path.resolve(process.argv[2] || "");
const mode = process.argv[3];
if (!process.argv[2] || !mode || !process.argv[4]) { console.error("usage: node tests/wonk_amount_probe.js GEN.js MODE SPEC_JSON"); process.exit(2); }
const spec = JSON.parse(process.argv[4]);

function load(p) {
  const file = p || genPath;
  delete require.cache[require.resolve(file)];
  return require(file);
}
const sha = (x) => crypto.createHash("sha256").update(JSON.stringify(x)).digest("hex");
const conceptOf = (m, file, id) => m.loadConcepts(path.resolve(file)).filter((c) => c.id === id)[0];
const hasSerifEnd = (c) => Object.keys(c.ends || {}).map((k) => c.ends[k]).indexOf("serif") >= 0;

function centreOf(g) {
  for (let i = 0; i < g.polys.length; i++) {
    const runs = g.runs[i];
    if (runs.length !== 2) continue;
    const poly = g.polys[i], flipped = runs[0][0] !== 0, n = runs[0][1] - runs[0][0] + 1;
    const L = (j) => flipped ? poly[runs[0][1] - j] : poly[runs[0][0] + j];
    const R = (j) => flipped ? poly[runs[1][0] + j] : poly[runs[1][1] - j];
    const at = (f) => { const j = Math.round(f * (n - 1)), a = L(j), b = R(j); return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; };
    return [at(0.25), at(0.75)];
  }
  return null;
}

function keysMode() {
  process.stdout.write(JSON.stringify(Object.keys(load().G)));
}

function conceptsMode() {
  const m = load(), out = [];
  for (const file of spec.files) {
    for (const c of m.loadConcepts(path.resolve(file))) {
      out.push({ file: path.basename(path.dirname(path.resolve(file))) + "/" + path.basename(file), id: c.id, xs: c.xs, ends: c.ends,
                 serif: hasSerifEnd(c), shear: !!c.shear, bend: !!c.bend });
    }
  }
  process.stdout.write(JSON.stringify(out));
}

function drawMode() {
  const out = [];
  for (const style of spec.styles) {
    const m = load();   // a fresh generator, and so a fresh glyph cache, for each style
    const c0 = conceptOf(m, spec.file, spec.id);
    if (!c0) throw new Error("no concept " + spec.id + " in " + spec.file);
    const keys = spec.keys || Object.keys(m.G);
    for (const mult of spec.mults) for (const amount of (spec.amounts || [null])) {
      const c = Object.assign({}, c0, spec.set || {});
      if (spec.wonk === "ALL") c.wonk = Object.keys(m.G).join("");
      else if (typeof spec.wonk === "string") c.wonk = spec.wonk;
      if (amount !== null) { delete c.wonkAmount; if (amount !== "undef") c.wonkAmount = amount; }
      const P = m.params(c, mult, style === "italic" ? 10 : false);
      for (const k of keys) {
        const g = m.glyph(k, P);
        if (!g) continue;
        out.push({ concept: c.id, style, mult, amount, key: k, xs: c.xs, adv: g.adv, counts: g.polys.map((p) => p.length), runs: g.runs, sig: g.sig,
                   pHash: g.polys.map(sha), L: g.L, R: g.R, centre: centreOf(g) });
      }
    }
  }
  process.stdout.write(JSON.stringify(out));
}

function refusalsMode() {
  const m = load(), c0 = conceptOf(m, spec.file, spec.id), out = [];
  if (!c0) throw new Error("no concept " + spec.id + " in " + spec.file);
  const tokens = { NaN: NaN, Infinity: Infinity, "-Infinity": -Infinity, undefined: undefined };
  for (const cs of spec.cases) {
    const c = Object.assign({}, c0);
    delete c.wonkAmount;
    let delivered;
    if (cs.token === "absent") delivered = "absent";
    else {
      const v = cs.token !== undefined ? tokens[cs.token] : cs.value;
      c.wonkAmount = v;
      delivered = typeof v + ":" + String(v);
    }
    let message = null;
    try { m.params(c, 1, false); } catch (e) { message = String(e && e.message || e); }
    out.push({ label: cs.label, delivered, message });
  }
  process.stdout.write(JSON.stringify(out));
}

const FIELDS = ["polys", "adv", "L", "R", "sig", "runs"];
function firstDiff(a, b) {
  if (!a || !b) return (!a && !b) ? null : "null";
  for (const f of FIELDS) if (JSON.stringify(a[f]) !== JSON.stringify(b[f])) return f;
  return null;
}

function oldMode() {
  const out = [], oldPath = path.resolve(spec.old);
  const ids = load().loadConcepts(path.resolve(spec.file)).map((c) => c.id);
  for (const id of ids) for (const style of spec.styles) {
    const mNew = load(), mOld = load(oldPath);   // fresh copies of both generators for each concept and style
    const c0 = conceptOf(mNew, spec.file, id);
    if (style === "italic" && !(c0.ends && c0.ends.x)) continue;
    const keys = Object.keys(mNew.G), all = keys.join("");
    for (const mult of spec.mults) {
      const slant = style === "italic" ? 10 : false;
      const cWonk = Object.assign({}, c0, { wonk: all }), cPlain = Object.assign({}, c0, { wonk: "" });
      delete cWonk.wonkAmount; delete cPlain.wonkAmount;
      const Pn = mNew.params(cWonk, mult, slant), Po = mOld.params(cWonk, mult, slant), Pp = mOld.params(cPlain, mult, slant);
      for (const k of keys) {
        const gn = mNew.glyph(k, Pn), go = mOld.glyph(k, Po), gp = mOld.glyph(k, Pp);
        if (!gn && !go) continue;
        const first = firstDiff(gn, go);
        out.push({ concept: id, style, mult, key: k, same: first === null, leaning: firstDiff(go, gp) !== null, first });
      }
    }
  }
  process.stdout.write(JSON.stringify(out));
}

try {
  ({ keys: keysMode, concepts: conceptsMode, draw: drawMode, refusals: refusalsMode, old: oldMode }[mode] || (() => { throw new Error("unknown mode " + mode); }))();
} catch (e) { console.error("wonk_amount_probe.js: " + (e && e.stack || e)); process.exitCode = 1; }
