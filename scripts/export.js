// export.js: runs the generator for every master of one group and writes one JSON that build.py
// turns into a variable font.
//
// WHAT IT'S FOR: the step between the generator and fontTools. It (1) draws every glyph in every
// master of the group, (2) refuses to continue unless the masters are interpolation-compatible, point
// for point and branch for branch, (3) decimates every outline with Ramer-Douglas-Peucker using ONE
// kept-index set per edge run shared by all masters, so decimation cannot break that compatibility,
// (4) records the minimum interior stroke width per master and the fold measure on the raw and the
// decimated edges, (5) emits the same kern pair list in every master, so the GPOS structure
// interpolates too, and (6) with --requirements, fails early when a required character has no
// skeleton, naming the code points.
//
// Usage:  node export.js --font font.json [--group roman] [--eps 1] [--requirements requirements.json] OUT.json
// The JSON shape is templates/export.schema.json: per master, advances, decimated polygons ("polys"),
// undecimated polygons ("raw", for build.py's before/after raster check), edge runs, kept indices,
// branch signatures, minimum stroke width, kern pairs, word space, and the laid width of the
// project's titles.
//
// Copyright 2026 John Knox. MIT licence. Derived from the author's Bract exporter (hopsafari.com,
// commit 90a085c) and Driftwood exporter (movingavg.com, commit 67a4e5b).
"use strict";
const fs = require("fs");
const path = require("path");

const EXPORT_SCHEMA = "font-design/export/v1";
// Thresholds, in units, for the fold guard below. Raw edges: a fold of consequence measured 4.9-90
// in Bract's round 1 and the corner residue of a pinned edge at most 3.6, so 4. Decimated edges: the
// same walk over the kept points only, where a step that spans a sharp corner's apex reads up to 7.8
// on a sound edge, while a decimation defect (a kept point out of order) reads in the hundreds, so 10.
// A font.json may override them (fold_units); build.py checks the two agree.
const FOLD_UNITS_DEFAULT = { raw: 4, decimated: 10 };

// --- the fold guard --------------------------------------------------------------------------------
// Measured on the OUTPUT polygons, independently of the generator's pin: for every stroke body (a
// polygon with two edge runs) the centre line is the midpoint of the two edges; walking an edge, the
// backward component of each step against the centre line's direction is accumulated over consecutive
// backward steps. A fold runs back by its own width; a sharp skeleton corner leaves at most one or two
// short backward steps. Measured on the undecimated polygons AND on the decimated ones that ship,
// every segment included.
function excursionAlong(points, chords) {
  let worst = 0, acc = 0;
  for (let i = 0; i + 1 < points.length; i++) {
    const [tx, ty] = chords[i], tl = Math.hypot(tx, ty) || 1;
    const c = ((points[i + 1][0] - points[i][0]) * tx + (points[i + 1][1] - points[i][1]) * ty) / tl;
    if (c < -1e-9) { acc -= c; if (acc > worst) worst = acc; } else if (c > 1e-9) acc = 0;
  }
  return worst;
}
function backwardExcursion(raw, runs, dec, keptIdx) {
  // raw: the undecimated polygon with its two edge runs; dec: the decimated polygon; keptIdx: the raw
  // index of each decimated point. The direction of a step from raw index j1 to j2 is the raw centre
  // line from one sample before j1 to j2, a two-sided local direction that tells a fold (many short
  // backward steps) from a sharp skeleton corner (one or two steps). Unequal edge runs are an error,
  // never a silent 0 (a Bract mutation survived until this threw).
  if (runs.length !== 2) return { raw: 0, decimated: 0 };
  const [[a0, a1], [b0, b1]] = runs, n = a1 - a0 + 1;
  if (b1 - b0 + 1 !== n) throw new Error("edge runs of unequal length");
  const C = [];
  for (let i = 0; i < n; i++) C.push([(raw[a0 + i][0] + raw[b1 - i][0]) / 2, (raw[a0 + i][1] + raw[b1 - i][1]) / 2]);
  const posL = i => i - a0, posR = i => b1 - i;
  const worst = { raw: 0, decimated: 0 };
  for (const [lo, hi, pos] of [[a0, a1, posL], [b0, b1, posR]]) {
    const rawIdx = []; for (let i = lo; i <= hi; i++) rawIdx.push(i);
    if (pos === posR) rawIdx.reverse();
    const dir = (i1, i2) => { const p0 = C[Math.max(0, pos(i1) - 1)], p1 = C[pos(i2)]; return [p1[0] - p0[0], p1[1] - p0[1]]; };
    worst.raw = Math.max(worst.raw, excursionAlong(rawIdx.map(i => raw[i]), rawIdx.slice(0, -1).map((i, q) => dir(i, rawIdx[q + 1]))));
    const kept = []; keptIdx.forEach((i, m) => { if (i >= lo && i <= hi) kept.push([i, m]); });
    kept.sort((x, y) => pos(x[0]) - pos(y[0]));
    worst.decimated = Math.max(worst.decimated, excursionAlong(kept.map(([i, m]) => dec[m]), kept.slice(0, -1).map(([i], q) => dir(i, kept[q + 1][0]))));
  }
  return worst;
}

// --- shared-index decimation ------------------------------------------------------------------------
function rdpKeep(pts, a, b, eps, keep) {
  // Ramer-Douglas-Peucker on pts[a..b] (inclusive); marks kept indices in `keep`. a and b are kept.
  keep.add(a); keep.add(b);
  const stack = [[a, b]];
  while (stack.length) {
    const [i, j] = stack.pop();
    if (j - i < 2) continue;
    const [x0, y0] = pts[i], [x1, y1] = pts[j], dx = x1 - x0, dy = y1 - y0, L = Math.hypot(dx, dy);
    let best = -1, bestD = -1;
    for (let q = i + 1; q < j; q++) {
      const [x, y] = pts[q];
      const d = L > 1e-9 ? Math.abs((x - x0) * dy - (y - y0) * dx) / L : Math.hypot(x - x0, y - y0);
      if (d > bestD) { bestD = d; best = q; }
    }
    if (bestD > eps) { keep.add(best); stack.push([i, best], [best, j]); }
  }
}

// --- config --------------------------------------------------------------------------------------------
function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch (e) { throw new Error(`cannot read ${file}: ${e.message}`); }
}
function loadFontConfig(fontPath) {
  const cfg = readJson(fontPath);
  const dir = path.dirname(path.resolve(fontPath));
  for (const k of ["family", "concepts", "groups", "charset", "kerning"]) if (!(k in cfg)) throw new Error(`font.json lacks "${k}"`);
  cfg._dir = dir;
  cfg._conceptsPath = path.resolve(dir, cfg.concepts);
  return cfg;
}
function kernSetFor(cfg, keys, LIGS) {
  const re = new RegExp(cfg.kerning.set);
  return keys.filter(k => (k.length === 1 && re.test(k)) || LIGS.includes(k));
}
// Characters a requirements file names, as generator keys (NBSP and U+2019/U+0027 are cmap decisions
// made in build.py; ligatures are glyphs, not characters).
function missingCharacters(required, keys, cfg) {
  const have = new Set(keys);
  const out = [];
  for (const ch of [...new Set(required)]) {
    if (ch === " " || (ch === " " && cfg.charset.nbsp_to_space)) continue;
    if ((ch === "’" || ch === "'") && have.has("'")) continue;
    if ((ch === "‘" || ch === '"' || ch === "“" || ch === "”") && have.has("'")) continue; // derived from the apostrophe
    if (!have.has(ch)) out.push(ch);
  }
  return out;
}

module.exports = { backwardExcursion, excursionAlong, FOLD_UNITS_DEFAULT, EXPORT_SCHEMA, missingCharacters, loadFontConfig };

// --- main -----------------------------------------------------------------------------------------------
function arg(args, name, dflt) { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; }

function main(argv) {
  const args = argv.slice(2);
  const outPath = args.filter((a, i) => !a.startsWith("--") && !(i > 0 && args[i - 1].startsWith("--")))[0];
  const fontPath = arg(args, "--font");
  if (!fontPath || !outPath) { console.error("usage: node export.js --font font.json [--group NAME] [--eps units] [--requirements requirements.json] OUT.json"); return 2; }
  const cfg = loadFontConfig(fontPath);
  const groupName = arg(args, "--group", Object.keys(cfg.groups)[0]);
  const group = cfg.groups[groupName];
  if (!group) { console.error(`export.js: no group "${groupName}" in ${fontPath} (have ${Object.keys(cfg.groups).join(", ")})`); return 2; }
  const EPS = +arg(args, "--eps", cfg.decimation_eps !== undefined ? cfg.decimation_eps : 1);
  const FOLD_UNITS = cfg.fold_units || FOLD_UNITS_DEFAULT;
  const m = require(path.resolve(__dirname, "gen.js"));
  const concepts = m.loadConcepts(cfg._conceptsPath);
  const keys = Object.keys(m.G);

  // --- 0. required characters (review finding F011): fail before drawing anything ----------------
  const reqPath = arg(args, "--requirements");
  if (reqPath) {
    const req = readJson(reqPath);
    const missing = missingCharacters(req.required_characters || "", keys, cfg);
    if (missing.length) {
      console.error(`export.js: ${missing.length} required character(s) have no skeleton in gen.js: ${missing.map(c => `${JSON.stringify(c)} U+${c.codePointAt(0).toString(16).toUpperCase().padStart(4, "0")}`).join(", ")}. Add a skeleton to G (and GI for an italic) or a composite rule; see references/generator.md.`);
      return 1;
    }
  }

  // --- 1. draw -----------------------------------------------------------------------------------------
  const italic = group.italic ? (group.italic_angle || 10) : false;
  const drawn = {};
  for (const [name, spec] of Object.entries(group.masters)) {
    const P = m.params(m.conceptById(concepts, spec.concept), spec.mult, italic);
    const glyphs = {};
    for (const k of keys) { const g = m.glyph(k, P); if (g) glyphs[k] = g; }
    drawn[name] = { P, glyphs, spec };
  }
  const names = Object.keys(drawn), ref = drawn[names[0]];
  if (names.length < 2) { console.error(`export.js: group "${groupName}" has ${names.length} master(s); a variable font needs at least two`); return 1; }

  // --- 2. compatibility: same polygons, same point counts, same edge runs, same branch outcomes ----
  const incompatible = [];
  for (const k of keys) {
    const sigs = names.map(n => { const g = drawn[n].glyphs[k]; return JSON.stringify([g.polys.map(p => p.length), g.runs, g.sig]); });
    if (new Set(sigs).size !== 1) incompatible.push(k);
  }
  if (incompatible.length) {
    console.error(`export.js: ${incompatible.length} glyph(s) differ in structure or branch outcome between masters of group ${groupName}: ${incompatible.join(" ")}`);
    for (const k of incompatible.slice(0, 3)) for (const n of names) console.error(`  ${n} ${k}: ${drawn[n].glyphs[k].sig.join(" | ")}`);
    return 1;
  }

  // --- 3. shared-index decimation per edge run ---------------------------------------------------------
  let rawPoints = 0, keptPoints = 0;
  for (const k of keys) {
    const g0 = ref.glyphs[k];
    g0.polys.forEach((poly, pi) => {
      const keep = new Set();
      for (const [a, b] of g0.runs[pi]) for (const n of names) rdpKeep(drawn[n].glyphs[k].polys[pi], a, b, EPS, keep);
      if (keep.size < 3) keep.add(Math.floor(poly.length / 2)); // a polygon needs three points to have an area
      const idx = [...keep].sort((x, y) => x - y);
      for (const n of names) {
        const g = drawn[n].glyphs[k];
        g.raw = g.raw || g.polys.map(p => p.map(q => [+q[0].toFixed(1), +q[1].toFixed(1)]));
        g.dec = g.dec || [];
        g.dec[pi] = idx.map(i => [+g.polys[pi][i][0].toFixed(1), +g.polys[pi][i][1].toFixed(1)]);
        g.keptIdx = g.keptIdx || [];
        g.keptIdx[pi] = idx;
      }
      rawPoints += poly.length; keptPoints += idx.length;
    });
  }
  const folds = {};
  for (const n of names) {
    folds[n] = { foldedEdges: 0, max: { raw: 0, decimated: 0 }, worstAt: { raw: null, decimated: null } };
    for (const k of keys) {
      const g = drawn[n].glyphs[k];
      g.polys.forEach((poly, pi) => {
        const e = backwardExcursion(poly, g.runs[pi], g.dec[pi], g.keptIdx[pi]);
        for (const kind of ["raw", "decimated"]) {
          if (e[kind] > FOLD_UNITS[kind]) folds[n].foldedEdges++;
          if (e[kind] > folds[n].max[kind]) { folds[n].max[kind] = +e[kind].toFixed(2); folds[n].worstAt[kind] = `${k} poly ${pi}`; }
        }
      });
    }
  }

  // --- 4. kerning: one pair list for every master -------------------------------------------------------
  // A pair is emitted when its automatic value reaches the threshold in ANY master, and then every
  // master emits its own value for it, zero included. Hand pairs replace the automatic value; word-space
  // pairs are added because the automatic pass never sees the space. An italic group adds its own lists.
  const KERN_SET = kernSetFor(cfg, keys, m.LIGS);
  const THRESHOLD = cfg.kerning.threshold !== undefined ? cfg.kerning.threshold : 12;
  const HAND = Object.assign({}, cfg.kerning.hand || {}, italic ? (cfg.kerning.italic_hand || {}) : {});
  const SPACE = (cfg.kerning.space || []).concat(italic ? (cfg.kerning.italic_space || []) : []);
  const auto = {};
  for (const n of names) {
    const { P, glyphs } = drawn[n];
    auto[n] = {};
    for (const a of KERN_SET) for (const b of KERN_SET) {
      if (/^[0-9]$/.test(a) && /^[0-9]$/.test(b)) continue; // figures keep their own spacing
      auto[n][a + "|" + b] = Math.round(m.kern(glyphs[a], glyphs[b], P));
    }
  }
  const pairList = [];
  for (const a of KERN_SET) for (const b of KERN_SET) {
    const id = a + "|" + b;
    if (id in HAND) continue;
    if (names.some(n => Math.abs(auto[n][id] || 0) >= THRESHOLD)) pairList.push([a, b]);
  }
  for (const [id, v] of Object.entries(HAND)) if (v) pairList.push(id.split("|"));
  for (const [a, b] of SPACE) pairList.push([a, b]);
  for (const [a, b] of pairList) for (const k of [a, b]) if (k !== " " && !ref.glyphs[k]) throw new Error(`kerning names a glyph the generator lacks: ${JSON.stringify(k)}`);
  const kernsFor = n => pairList.map(([a, b]) => {
    const id = a + "|" + b;
    const v = id in HAND ? HAND[id] : a === " " || b === " " ? SPACE.find(s => s[0] === a && s[1] === b)[2] : auto[n][id];
    return [a, b, v];
  });

  // --- 5. titles laid with the emitted metrics, for the kerning test --------------------------------------
  const TITLES = cfg.titles || [];
  function layTitle(title, glyphs, kerns, space) {
    const table = {}; for (const [a, b, v] of kerns) table[a + "|" + b] = v;
    const seq = []; const w = title.replace(/[‘’]/g, "'").replace(/ /g, " ");
    for (let i = 0; i < w.length; i++) {
      const two = w.substr(i, 2);
      if (m.LIGS.includes(two)) { seq.push(two); i++; } else seq.push(w[i]);
    }
    let x = 0, prev = null;
    for (const k of seq) {
      if (k !== " " && !glyphs[k]) throw new Error(`title ${JSON.stringify(title)} uses ${JSON.stringify(k)}, which the generator lacks`);
      if (prev !== null) x += table[prev + "|" + k] || 0;
      x += k === " " ? space : Math.round(glyphs[k].adv);
      prev = k;
    }
    return x;
  }

  // --- 6. write ---------------------------------------------------------------------------------------------
  const out = { schema: EXPORT_SCHEMA, family: cfg.family, group: groupName, italic: !!italic, italicAngle: italic ? +italic : 0, eps: EPS, foldUnits: FOLD_UNITS, masters: {} };
  for (const n of names) {
    const { P, glyphs, spec } = drawn[n];
    const space = Math.round(210 + 0.3 * P.W + 2 * P.track);
    const kerns = kernsFor(n);
    let minw = Infinity, minwAt = null;
    const G = {};
    for (const k of keys) {
      const g = glyphs[k];
      G[k] = { adv: Math.round(g.adv), polys: g.dec, raw: g.raw, runs: g.runs, keptIdx: g.keptIdx, sig: g.sig, minw: +g.minw.toFixed(2), minwStroke: g.minwStroke };
      if (g.minw < minw) { minw = g.minw; minwAt = `${k} stroke ${g.minwStroke}`; }
    }
    out.masters[n] = {
      concept: P.id, mult: spec.mult, location: spec.location, W: P.W, thin: P.thin, track: P.track, space,
      minStrokeWidth: +minw.toFixed(2), minStrokeAt: minwAt,
      foldedEdges: folds[n].foldedEdges, maxBackwardExcursion: folds[n].max, worstFoldAt: folds[n].worstAt,
      glyphs: G, kerns,
      titles: Object.fromEntries(TITLES.map(t => [t, layTitle(t, glyphs, kerns, space)])),
    };
    console.error(`${groupName}/${n}: ${Object.keys(G).length} glyphs, ${kerns.length} kern pairs, min interior stroke ${minw.toFixed(1)} units at ${minwAt}, ${folds[n].foldedEdges} folded edges (worst raw ${folds[n].max.raw} at ${folds[n].worstAt.raw}, decimated ${folds[n].max.decimated} at ${folds[n].worstAt.decimated})`);
  }
  console.error(`decimation eps ${EPS}: ${rawPoints} -> ${keptPoints} points per master`);
  fs.mkdirSync(path.dirname(path.resolve(outPath)), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(out));
  return 0;
}

if (require.main === module) {
  try { process.exit(main(process.argv)); } catch (e) { console.error(`export.js: ${e.message}`); process.exit(1); }
}
