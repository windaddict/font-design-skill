// tests/skeleton_probe.js: applies a per-face skeleton override to a generator and prints what it drew, for
// tests/test_skeleton_overrides.py.
//
// WHAT IT'S FOR: a face may name a `skeletons` file in font.json whose function edits the generator's skeleton
// tables before anything is drawn (scripts/gen.js applySkeletons; references/generator.md, "Per-face skeletons").
// The Python tests hold the mechanism to what a reader of the tables and the outlines would check: which keys the
// override reached, whether a derived glyph followed its base, whether the italic fell back to the roman entry,
// whether a malformed override was refused, and how the shoulder of n, m, h and r meets its stem. This script
// loads the gen.js it is given (a scratch copy carrying a mutation, or the real one), applies the override, and
// prints JSON only; every expected value is restated on the Python side.
//
//   node tests/skeleton_probe.js apply    GEN.js SKEL.js                      the report and the key order before and after
//   node tests/skeleton_probe.js twice    GEN.js SKEL.js SKEL2.js             two applications in one process (the second must throw)
//   node tests/skeleton_probe.js draw     GEN.js SKEL.js|- CONCEPTS.js KEYS   the registered derivations, the tables' entries and the drawings of KEYS (comma-
//                                                                             separated) for every concept at mult 1 and 1.5, roman,
//                                                                             and italic where the concept maps the "x" end
//   node tests/skeleton_probe.js stale    GEN.js SKEL.js CONCEPTS.js KEY      draws KEY with the first concept, applies the override, draws
//                                                                             it again in the same process: the glyph cache must not serve the
//                                                                             first drawing after the tables changed
//   node tests/skeleton_probe.js shoulder GEN.js SKEL.js|- CONCEPTS.js MASTERS [KEYS]
//                                                                             the top edge of n, m and r (MASTERS is concept:mult,...;
//                                                                             KEYS default n,m,r; h has no nick, its serif sits at 740): the
//                                                                             serif top at the stem edge, where the arch leaves, the peak, the nick
//
// A refusal prints the generator's message on stderr and exits 1, so the Python side reads the exact text.
// Copyright 2026 John Knox. MIT licence.
"use strict";
const path = require("path");

const [mode, genPath, skelPath, ...rest] = process.argv.slice(2);
if (!mode || !genPath) { console.error("usage: node tests/skeleton_probe.js apply|twice|draw|shoulder GEN.js SKEL.js|- ..."); process.exit(2); }
const m = require(path.resolve(genPath));

function keyOrder() { return { G: Object.keys(m.G), GI: Object.keys(m.GI) }; }
function apply(file) { return m.applySkeletons(require(path.resolve(file)), path.basename(file)); }

function run() {
  if (mode === "apply") {
    const before = keyOrder();
    const report = apply(skelPath);
    return { report, before, after: keyOrder() };
  }
  if (mode === "twice") {
    apply(skelPath);
    apply(rest[0]);
    return { secondCallAccepted: true };
  }
  if (mode === "draw") {
    const [conceptsPath, keyList] = rest;
    const keys = keyList.split(",");
    const before = keyOrder();
    const report = skelPath === "-" ? null : apply(skelPath);
    const out = { report, before, after: keyOrder(), derived: m.DERIVED, tables: { G: {}, GI: {} }, drawings: {} };
    for (const k of keys) { out.tables.G[k] = m.G[k] || null; out.tables.GI[k] = m.GI[k] || null; }
    for (const c of m.loadConcepts(path.resolve(conceptsPath))) {
      const slants = c.ends && c.ends.x ? [false, true] : [false];
      for (const mult of [1, 1.5]) for (const it of slants) {
        const P = m.params(c, mult, it);
        const rec = {};
        for (const k of keys) {
          const g = m.glyph(k, P);
          rec[k] = g ? { adv: g.adv, polys: g.polys, sig: g.sig } : null;
        }
        out.drawings[`${c.id}@${mult}${it ? "i" : ""}`] = rec;
      }
    }
    return out;
  }
  if (mode === "stale") {
    const [conceptsPath, key] = rest;
    const P = m.params(m.loadConcepts(path.resolve(conceptsPath))[0], 1, false);
    const first = m.glyph(key, P).polys;
    const report = apply(skelPath);
    return { report, first, second: m.glyph(key, P).polys };
  }
  if (mode === "shoulder") return shoulder(rest[0], rest[1], (rest[2] || "n,m,r").split(","));
  throw new Error("unknown mode " + mode);
}

// ---------- the shoulder measure (docs/plan-skeleton-overrides.md section 0) ----------
// The top profile of a glyph is the maximum y of every polygon edge crossing a vertical line, which is the filled
// union's upper edge because these glyphs have no holes above the x-height.
function topAt(polys, x) {
  let best = -Infinity;
  for (const p of polys) {
    for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
      const a = p[j], b = p[i];
      if ((a[0] <= x && b[0] >= x) || (b[0] <= x && a[0] >= x)) {
        if (a[0] === b[0]) { best = Math.max(best, a[1], b[1]); continue; }
        const y = a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]);
        if (y > best) best = y;
      }
    }
  }
  return best;
}
function bbox(p) {
  const a = [Infinity, Infinity, -Infinity, -Infinity];
  for (const q of p) { a[0] = Math.min(a[0], q[0]); a[1] = Math.min(a[1], q[1]); a[2] = Math.max(a[2], q[0]); a[3] = Math.max(a[3], q[1]); }
  return a;
}
function shoulder(conceptsPath, masterList, keys) {
  if (skelPath !== "-") apply(skelPath);
  const concepts = m.loadConcepts(path.resolve(conceptsPath));
  const out = {};
  for (const spec of masterList.split(",")) {
    const [cid, mult] = spec.split(":");
    const P = m.params(m.conceptById(concepts, cid), +mult, false);
    for (const k of keys) {
      const g = m.glyph(k, P);
      // the stem's body is the glyph's first polygon; its head serif a small polygon over the stem's top, no wider than the
      // stem plus 60; the arch's body the large polygon that starts left of the stem's right edge and runs 100 past it
      const stem = g.polys[0], sb = bbox(stem), sx = sb[2], stemTop = sb[3];
      let head = null, arch = null;
      g.polys.forEach((p, i) => {
        if (i === 0) return;
        const b = bbox(p);
        if (!arch && p.length > 100 && b[0] < sx && b[2] > sx + 100 && b[3] > stemTop - 200) arch = p;
        else if (!head && b[1] > stemTop - 150 && b[0] < sx && b[2] <= sx + 60 && p.length <= 70) head = p;
      });
      if (!arch) throw new Error(`${spec} ${k}: no arch body found`);
      const headPolys = head ? [head, stem] : [stem];
      const serifTop = topAt(headPolys, sx - 0.01);
      const leaves = topAt([arch], sx + 0.5);
      let peak = -Infinity, peakX = 0;
      for (const q of arch) if (q[1] > peak) { peak = q[1]; peakX = q[0]; }
      let lowest = Infinity, regain = null;
      for (let x = sx + 1; x <= peakX; x += 1) {
        const y = topAt(g.polys, x);
        if (y < lowest) lowest = y;
        if (regain === null && y >= serifTop - 0.01 && x > sx + 2) regain = x;
      }
      // a join cap or cut poking above the serif, stem and arch near the stem is a nub
      let nub = 0;
      for (let x = sb[0]; x <= sx + 60; x += 1) nub = Math.max(nub, topAt(g.polys, x) - topAt(headPolys.concat([arch]), x));
      out[`${spec} ${k}`] = { serifTop, leaves, peak, nick: serifTop - lowest, nickWidth: regain === null ? null : regain - sx, nub };
    }
  }
  return out;
}

try {
  process.stdout.write(JSON.stringify(run()));
} catch (e) {
  console.error(e.message);
  process.exit(1);
}
