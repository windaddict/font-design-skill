// tests/joint_spacing_probe.js: compares what two generators measure for spacing, for tests/test_joint_spacing.py.
//
// WHAT IT'S FOR: 0.10.0 draws several ends differently from 0.9.0 (a slanted corner cut, a level cut on a leaning serif end, a bracket
// on a leaning edge) but reads each glyph's sidebearings, advance and kerns from the 0.9.0 outline (`prof` in scripts/gen.js), so
// that nothing but the G and the italic r moves a width. This script is the measure of that promise at full precision: it draws the
// same masters with the generator under test and with the 0.9.0 generator and prints every difference, unrounded. export.js rounds
// advances and kerns to whole units and lists only the kern pairs above a threshold, so it can hide a change this reports.
//
//   node tests/joint_spacing_probe.js GEN_UNDER_TEST GEN_0_9_0 FONT_JSON
//
// For every master of every group of FONT_JSON, for every key of G the generator draws: the advance `adv` and the two 54-bin spacing
// profiles `L` and `R` (leftmost and rightmost x per 20 unit bin from y -260, null where a bin is empty) of glyph(); and for every
// ordered pair of those keys the automatic kern(), with the font's own sparse cap. Differences larger than 1e-9 are listed:
//   glyphs  [{group, italic, master, key, what: "adv" | "L" | "R" | "presence", old, new}]   one entry per glyph and measure
//   kerns   [{group, italic, master, a, b, old, new}]
// A non-finite advance, profile bin or kern on either side ends the probe with a non-zero exit, because `Math.abs(NaN) > EPS` is
// false and a NaN would otherwise read as no difference (Impasse review serif-joint-review-c4bf3d9 F003; watch W18 in
// references/testing.md section 11).
// `checked` counts what was compared, so a test can tell a clean run from an empty one. The export.js beside GEN_UNDER_TEST reads
// font.json (its loadFontConfig), so that folder must be a whole copy of scripts/.
// Copyright 2026 John Knox. MIT licence.
"use strict";
const path = require("path");

if (process.argv.length < 5) { console.error("usage: node tests/joint_spacing_probe.js GEN_UNDER_TEST GEN_0_9_0 FONT_JSON"); process.exit(2); }
const genNew = path.resolve(process.argv[2]), genOld = path.resolve(process.argv[3]), fontPath = path.resolve(process.argv[4]);
if (genNew === genOld) { console.error("joint_spacing_probe.js: both generators are the same file; the comparison would read one module twice"); process.exit(2); }
const EPS = 1e-9;

function finite(v, where) { if (!Number.isFinite(v)) throw new Error(where + " is not finite: " + String(v)); return v; }

function main() {
  const mNew = require(genNew), mOld = require(genOld);
  const cfg = require(path.join(path.dirname(genNew), "export.js")).loadFontConfig(fontPath);
  const cNew = mNew.loadConcepts(cfg._conceptsPath), cOld = mOld.loadConcepts(cfg._conceptsPath);
  if (cfg._skeletonsPath) { mNew.applySkeletons(require(cfg._skeletonsPath), cfg.skeletons); mOld.applySkeletons(require(cfg._skeletonsPath), cfg.skeletons); }
  const keys = Object.keys(mNew.G);
  if (JSON.stringify(keys) !== JSON.stringify(Object.keys(mOld.G))) throw new Error("the two generators draw different sets of keys");
  const out = { glyphs: [], kerns: [], masters: [], checked: { glyphs: 0, pairs: 0 } };
  const sparse = cfg.kerning.sparse_cap;
  for (const gname of Object.keys(cfg.groups)) {
    const group = cfg.groups[gname], italic = group.italic ? (group.italic_angle || 10) : false;
    for (const mname of Object.keys(group.masters)) {
      const spec = group.masters[mname];
      const PN = mNew.params(mNew.conceptById(cNew, spec.concept), spec.mult, italic), PO = mOld.params(mOld.conceptById(cOld, spec.concept), spec.mult, italic);
      const meta = { group: gname, italic: !!italic, master: mname };
      out.masters.push(gname + "/" + mname);
      const gN = {}, gO = {};
      for (const k of keys) {
        gN[k] = mNew.glyph(k, PN); gO[k] = mOld.glyph(k, PO);
        if (!gN[k] !== !gO[k]) { out.glyphs.push(Object.assign({ key: k, what: "presence", old: !!gO[k], new: !!gN[k] }, meta)); continue; }
        if (!gN[k]) continue;
        out.checked.glyphs++;
        for (const [label, g] of [["new", gN[k]], ["0.9.0", gO[k]]]) {
          const where = meta.group + "/" + meta.master + " glyph " + JSON.stringify(k) + " (" + label + ")";
          finite(g.adv, where + " advance");
          for (const side of ["L", "R"]) g[side].forEach((v, i) => { if (v !== null) finite(v, where + " profile " + side + " bin " + i); });
        }
        if (Math.abs(gN[k].adv - gO[k].adv) > EPS) out.glyphs.push(Object.assign({ key: k, what: "adv", old: gO[k].adv, new: gN[k].adv }, meta));
        for (const side of ["L", "R"]) {
          const a = gO[k][side], b = gN[k][side];
          const bin = a.findIndex((v, i) => (v === null) !== (b[i] === null) || (v !== null && Math.abs(v - b[i]) > EPS));
          if (bin >= 0) out.glyphs.push(Object.assign({ key: k, what: side, bin, old: a[bin], new: b[bin] }, meta));
        }
      }
      const live = keys.filter((k) => gN[k]);
      for (const a of live) for (const b of live) {
        out.checked.pairs++;
        const pair = meta.group + "/" + meta.master + " kern " + JSON.stringify(a) + "|" + JSON.stringify(b);
        const kn = finite(mNew.kern(gN[a], gN[b], PN, sparse), pair + " (new)"), ko = finite(mOld.kern(gO[a], gO[b], PO, sparse), pair + " (0.9.0)");
        if (Math.abs(kn - ko) > EPS) out.kerns.push(Object.assign({ a, b, old: ko, new: kn }, meta));
      }
    }
  }
  process.stdout.write(JSON.stringify(out));
}

try { main(); } catch (e) { console.error("joint_spacing_probe.js: " + (e && e.stack || e)); process.exitCode = 1; }
