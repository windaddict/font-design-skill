// tests/joint_probe.js: draws glyphs with the generator under test and prints what it drew at the joints, for
// tests/test_serif_joints.py.
//
// WHAT IT'S FOR: 0.10.0 changes how scripts/gen.js draws a serif bracket on a leaning stroke, the end of a leaning
// serif stem, the stem end under a head sink, the corner where a bar meets another stroke, the capital G and the
// italic r's arm. The Python tests hold each to what a reader of the outlines would check, so every assertion stays in
// Python and this script only measures. Everything is found from the OUTPUT (polygons, edge runs, branch records);
// nothing is computed from the generator's own formulas.
//
//   node tests/joint_probe.js MODE SCRIPTS_DIR SPEC_JSON
//
// SCRIPTS_DIR holds gen.js and export.js (the real scripts/ folder, or a scratch copy carrying one mutation).
//
// Rules shared by every mode:
//   - a stroke's body is the one polygon with two edge runs; the bodies of a glyph, in order, pair with the skeleton's
//     open strokes (a path that is not a dot and not a ring), in order, and with the glyph's `sig` entries that start
//     with "open". The probe throws when those three counts differ.
//   - with runs = [[a0, a1], [b0, b1]], n = a1 - a0 + 1 and flipped = (a0 != 0): L(j) = flipped ? poly[a1 - j] : poly[a0 + j]
//     and R(j) = flipped ? poly[b0 + j] : poly[b1 - j]. End A's corners are L(0) and R(0), end B's are L(n-1) and R(n-1).
//   - a body's serif polygons are the one-run polygons after it up to the next body; a serif end's polygon is the one of
//     15 or 26 points among them whose nearest vertex is closest to the midpoint of the end's two corners. Its bracket
//     tips are its first and last vertex (reversing a polygon for orientation keeps them first and last).
//   - "straight" is whether the skeleton segment at an end is an `L`; the skeleton of a key is GI[key] in an italic
//     drawing when it exists, else G[key], as glyph() chooses.
//
// MODES (SPEC is one JSON object)
//   serifs   one row per head, foot or diag serif end of every serif concept of the given files. Spec: files, mults,
//            styles ("roman" | "italic", italic at 10 degrees and only for a concept that maps the "x" end), extra (concept
//            keys merged after swell 0 and wob 0, which are always set so a straight stroke's edges are straight lines).
//            Row: file, concept, style, mult, key, end, kind, out (the larger distance of the two tips outside the body
//            polygon, 0 when inside), lean (x drift per unit of y from the end's midpoint to the midpoint 12 samples in),
//            tilt (the y difference of the end's two corners), straight, lowestY (of the body), body.
//   sink     as serifs, but for every lowercase head end, the same concept drawn with headSink 0.6 and without the key:
//            sinkOut is the largest distance outside the unsunk body polygon of a point that the sink moved. Row: file,
//            concept, style, mult, key, end, lean, moved (how many points the sink moved), sinkOut.
//   corners  one row per end whose branch outcome is "corner" and whose stroke is shallow at that end (the centre line
//            between samples 6 and 12 in rises by at most half its length, the generator's own steep test), for every concept with ends.s "serif" or joints true
//            (spec: files, mults, styles, extra, swell and wob off), or, with spec.font, for every master of every group of
//            that font.json with the concepts as shipped. Row adds: tooth (the larger distance of the end's two corners
//            outside the body of the stroke it meets), partnerCurved (the skeleton segment of the meeting stroke at the
//            meeting end is a `C`).
//   edges    for one glyph and one skeleton stroke, every master of every group of spec.font: per body edge `w3`, the
//            largest absolute sum of three consecutive turning angles in degrees over the edge's points from sample 3 to
//            sample n-4 with repeated points skipped; `lo` and `hi` name the edge with the lower and the higher y at sample
//            `joint` (the number of leading skeleton segments whose sample counts add up to it). With spec.centre,
//            centreFall (the largest fall of the centre line, the midpoints of the two edges, below its highest level since
//            the joint sample) and jointTurn (the largest single turn of the lower edge within 12 samples of the joint).
//            Spec: font, glyph, stroke, joint, italicOnly, centre.
//
// The generator is loaded afresh for each concept and style: its glyph cache is never freed. A glyph that throws ends the
// probe with a non-zero exit, never a skip.
// Copyright 2026 John Knox. MIT licence.
"use strict";
const path = require("path");

const mode = process.argv[2], scriptsDir = path.resolve(process.argv[3] || "");
const spec = JSON.parse(process.argv[4] || "{}");
if (!process.argv[2] || !process.argv[3] || !process.argv[4]) { console.error("usage: node tests/joint_probe.js MODE SCRIPTS_DIR SPEC_JSON"); process.exit(2); }
const genPath = path.join(scriptsDir, "gen.js");

function load() { delete require.cache[genPath]; return require(genPath); }

// ---- geometry -------------------------------------------------------------------------------------------------------
function segDist(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2));
  return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
}
function inside(p, poly) {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const a = poly[i], b = poly[j];
    if ((a[1] > p[1]) !== (b[1] > p[1]) && p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
  }
  return c;
}
// how far p stands outside poly: 0 when inside, else the distance to the nearest edge
function outside(p, poly) {
  if (inside(p, poly)) return 0;
  let d = Infinity;
  for (let i = 0; i < poly.length; i++) d = Math.min(d, segDist(p, poly[i], poly[(i + 1) % poly.length]));
  return d;
}
const midOf = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];

// ---- reading a drawn glyph ----------------------------------------------------------------------------------------
function skeletonOf(m, key, P) { return (P.italic && m.GI[key]) || m.G[key]; }
function openIndices(raw) {
  const out = [];
  raw.forEach((st, i) => { if (st.d && !st.closed) out.push(i); });
  return out;
}
function letters(d) { return d.trim().split(/[\s,]+/).filter((t) => /^[MLC]$/.test(t)); }
// the letter of the skeleton segment at end "a" (the start) or "b" (the end) of a path
function endLetter(d, which) { const l = letters(d); return which === "a" ? l[1] : l[l.length - 1]; }

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
  out.forEach((b, bi) => { b.serifs = []; const next = bi + 1 < out.length ? out[bi + 1].idx : g.polys.length;
    for (let i = b.idx + 1; i < next; i++) if (g.runs[i].length === 1 && (g.polys[i].length === 15 || g.polys[i].length === 26)) b.serifs.push(g.polys[i]); });
  return out;
}
// the glyph's bodies, with the count checks the header promises
function readGlyph(m, key, P) {
  const g = m.glyph(key, P);
  if (!g) return null;
  const raw = skeletonOf(m, key, P), open = openIndices(raw), bodies = bodiesOf(g), sigs = g.sig.filter((s) => s.indexOf("open") === 0);
  if (bodies.length !== open.length || sigs.length !== open.length) {
    throw new Error("glyph " + JSON.stringify(key) + ": " + bodies.length + " bodies, " + sigs.length + " open records, " + open.length + " open skeleton strokes");
  }
  bodies.forEach((b, bi) => { b.stroke = open[bi]; b.sig = sigs[bi]; b.d = raw[open[bi]].d; });
  return { g, raw, bodies };
}
function cornersOf(b, which) { // [corner on the L edge, corner on the R edge]
  const j = which === "A" ? 0 : b.n - 1;
  return [b.L(j), b.R(j)];
}
function endMid(b, which, j) { const k = which === "A" ? j : b.n - 1 - j; return midOf(b.L(k), b.R(k)); }
function serifPolyOf(b, which) {
  const c = cornersOf(b, which), mid = midOf(c[0], c[1]);
  let best = null, bd = Infinity;
  b.serifs.forEach((p) => { const d = Math.min.apply(null, p.map((q) => Math.hypot(q[0] - mid[0], q[1] - mid[1]))); if (d < bd) { bd = d; best = p; } });
  return best;
}
function leanOf(b, which, steps) {
  const j1 = Math.min(steps, b.n - 1), p0 = endMid(b, which, 0), p1 = endMid(b, which, j1), dy = p1[1] - p0[1];
  return Math.abs(dy) < 1e-9 ? 0 : (p1[0] - p0[0]) / dy;
}
function serifKinds(b) { // {A: kind, B: kind} from the branch record
  const out = {}, a = / serifA=(\w+)/.exec(b.sig), z = / serifB=(\w+)/.exec(b.sig);
  if (a) out.A = a[1];
  if (z) out.B = z[1];
  return out;
}

// ---- sweeps over concepts -----------------------------------------------------------------------------------------
function conceptRuns(fn) {
  const out = [];
  for (const file of spec.files) {
    const ids = load().loadConcepts(path.resolve(file)).map((c) => c.id);
    for (const id of ids) for (const style of spec.styles) {
      const m = load(); // a fresh generator, and so a fresh glyph cache, for each concept and style
      const c0 = m.loadConcepts(path.resolve(file)).filter((c) => c.id === id)[0];
      const wanted = mode === "corners" ? (c0.ends.s === "serif" || c0.joints === true) : c0.ends && c0.ends.s === "serif";
      if (!wanted) continue;
      if (style === "italic" && !(c0.ends && c0.ends.x)) continue;
      for (const mult of spec.mults) {
        const c = Object.assign({}, c0, { swell: 0, wob: 0 }, spec.extra || {});
        const P = m.params(c, mult, style === "italic" ? 10 : false);
        const meta = { file: path.basename(path.dirname(path.resolve(file))) + "/" + path.basename(file), concept: id, style, mult };
        fn(m, P, meta, out, c);
      }
    }
  }
  return out;
}

function serifRows(m, P, meta, out) {
  for (const key of Object.keys(m.G)) {
    const r = readGlyph(m, key, P);
    if (!r) continue;
    r.bodies.forEach((b) => {
      const kinds = serifKinds(b);
      ["A", "B"].forEach((which) => {
        const kind = kinds[which];
        if (kind !== "head" && kind !== "foot" && kind !== "diag") return;
        const sp = serifPolyOf(b, which);
        if (!sp) throw new Error("glyph " + JSON.stringify(key) + " stroke " + b.stroke + " end " + which + ": no serif polygon found");
        const c = cornersOf(b, which);
        const tips = [sp[0], sp[sp.length - 1]];
        out.push(Object.assign({}, meta, {
          key, end: which, kind, body: b.stroke,
          out: Math.max.apply(null, tips.map((t) => outside(t, b.poly))),
          lean: leanOf(b, which, 12), tilt: Math.abs(c[0][1] - c[1][1]),
          straight: endLetter(b.d, which === "A" ? "a" : "b") === "L",
          lowestY: Math.min.apply(null, b.poly.map((q) => q[1])),
        }));
      });
    });
  }
}

function sinkRows(m, P, meta, out, c) {
  const sunkP = m.params(Object.assign({}, c, { headSink: 0.6 }), meta.mult, meta.style === "italic" ? 10 : false);
  const plain = m.params(Object.assign({}, c, { headSink: undefined }), meta.mult, meta.style === "italic" ? 10 : false);
  for (const key of Object.keys(m.G)) {
    if (m.UPPERISH.test(key)) continue;
    const a = readGlyph(m, key, plain), s = readGlyph(m, key, sunkP);
    if (!a) continue;
    a.bodies.forEach((b, bi) => {
      const sb = s.bodies[bi], kinds = serifKinds(b);
      ["A", "B"].forEach((which) => {
        if (kinds[which] !== "head") return;
        if (b.poly.length !== sb.poly.length) throw new Error("glyph " + key + ": the sink changed the point count");
        let moved = 0, worst = 0;
        sb.poly.forEach((q, i) => {
          const p = b.poly[i];
          if (Math.hypot(q[0] - p[0], q[1] - p[1]) < 1e-9) return;
          moved++;
          worst = Math.max(worst, outside(q, b.poly));
        });
        out.push(Object.assign({}, meta, { key, end: which, lean: leanOf(b, which, 12), moved, sinkOut: worst }));
      });
    });
  }
}

function cornerRowsFor(m, P, meta, out) {
  for (const key of Object.keys(m.G)) {
    const r = readGlyph(m, key, P);
    if (!r) continue;
    const byStroke = {};
    r.bodies.forEach((b) => { byStroke[b.stroke] = b; });
    r.bodies.forEach((b) => {
      const ends = / ends=([^/\s]*)\/(\S*)/.exec(b.sig), joins = / joins=(\S+?)\/(\S+)/.exec(b.sig);
      if (!ends || !joins) throw new Error("glyph " + JSON.stringify(key) + ": no ends= or joins= in " + b.sig);
      ["A", "B"].forEach((which, wi) => {
        if (ends[wi + 1] !== "corner") return;
        // shallow as the generator reads it (|ty| of the end's tangent at most 0.5), taken on the drawn centre line between samples
        // 6 and 12, past the few points a corner cut pins. A level cut moves the end's own corners sideways, so a measure that
        // started at the end would call a steep stroke shallow (the 2's bowl on the Blind concept).
        const p0 = endMid(b, which, 6), p1 = endMid(b, which, Math.min(12, b.n - 1)), tl = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) || 1;
        if (Math.abs(p1[1] - p0[1]) / tl > 0.5) return; // steep at this end: the stroke that is cut level, not the one that moved
        const id = joins[wi + 1], pm = /^(\d+)([ab])$/.exec(id);
        if (!pm) throw new Error("glyph " + JSON.stringify(key) + ": a corner end with no partner id (" + id + ")");
        const pb = byStroke[+pm[1]];
        if (!pb) throw new Error("glyph " + JSON.stringify(key) + ": partner stroke " + pm[1] + " has no body");
        const c = cornersOf(b, which);
        out.push(Object.assign({}, meta, {
          key, end: which, body: b.stroke, partner: +pm[1],
          tooth: Math.max.apply(null, c.map((q) => outside(q, pb.poly))),
          partnerCurved: endLetter(pb.d, pm[2]) === "C",
        }));
      });
    });
  }
}

function shippedMasters(fn) {
  const out = [], exporter = require(path.join(scriptsDir, "export.js")), cfg = exporter.loadFontConfig(path.resolve(spec.font));
  const m = load();
  if (cfg._skeletonsPath) m.applySkeletons(require(cfg._skeletonsPath), cfg.skeletons);
  const concepts = m.loadConcepts(cfg._conceptsPath);
  for (const gname of Object.keys(cfg.groups)) {
    const group = cfg.groups[gname], italic = group.italic ? (group.italic_angle || 10) : false;
    if (spec.italicOnly && !italic) continue;
    for (const mname of Object.keys(group.masters)) {
      const ms = group.masters[mname], P = m.params(m.conceptById(concepts, ms.concept), ms.mult, italic);
      fn(m, P, { font: path.basename(path.dirname(path.resolve(spec.font))), group: gname, master: mname, concept: ms.concept, mult: ms.mult, italic: !!italic }, out);
    }
  }
  return out;
}

// ---- edges ----------------------------------------------------------------------------------------------------------
function dedupe(pts) {
  const out = [];
  pts.forEach((p) => { if (!out.length || Math.hypot(p.q[0] - out[out.length - 1].q[0], p.q[1] - out[out.length - 1].q[1]) > 1e-9) out.push(p); });
  return out;
}
function turns(pts) { // signed turning angle in degrees at every interior point of a point list
  const t = [];
  for (let i = 1; i + 1 < pts.length; i++) {
    const a = pts[i - 1].q, b = pts[i].q, c = pts[i + 1].q;
    const ux = b[0] - a[0], uy = b[1] - a[1], vx = c[0] - b[0], vy = c[1] - b[1];
    t.push({ idx: pts[i].idx, deg: Math.atan2(ux * vy - uy * vx, ux * vx + uy * vy) * 180 / Math.PI });
  }
  return t;
}
function w3Of(edge) { // edge: [point] by sample
  const n = edge.length, sel = [];
  for (let j = 3; j <= n - 4; j++) sel.push({ idx: j, q: edge[j] });
  const t = turns(dedupe(sel));
  let worst = 0;
  for (let i = 0; i + 2 < t.length; i++) worst = Math.max(worst, Math.abs(t[i].deg + t[i + 1].deg + t[i + 2].deg));
  return worst;
}
function edgeRows(m, P, meta, out) {
  const key = spec.glyph, r = readGlyph(m, key, P);
  if (!r) throw new Error("no glyph " + key);
  const bi = r.bodies.findIndex((b) => b.stroke === spec.stroke);
  if (bi < 0) throw new Error("glyph " + key + " has no open stroke " + spec.stroke);
  const b = r.bodies[bi], counts = m.sampleCounts(b.d), J = counts.slice(0, spec.joint).reduce((a, c) => a + c, 0);
  if (b.n !== counts.reduce((a, c) => a + c, 0) + 1) throw new Error("glyph " + key + ": " + b.n + " samples against the sample counts " + counts);
  const L = [], R = [];
  for (let j = 0; j < b.n; j++) { L.push(b.L(j)); R.push(b.R(j)); }
  const loIsL = L[J][1] <= R[J][1], lo = loIsL ? L : R, hi = loIsL ? R : L;
  const row = Object.assign({}, meta, { key, stroke: spec.stroke, joint: J, samples: b.n, lo: { w3: w3Of(lo) }, hi: { w3: w3Of(hi) } });
  if (spec.centre) {
    let run = -Infinity, fall = 0;
    for (let j = J; j < b.n; j++) {
      const y = (L[j][1] + R[j][1]) / 2;
      run = Math.max(run, y); fall = Math.max(fall, run - y);
    }
    const near = [];
    for (let j = Math.max(0, J - 12 - 3); j <= Math.min(b.n - 1, J + 12 + 3); j++) near.push({ idx: j, q: lo[j] });
    const tt = turns(dedupe(near)).filter((x) => Math.abs(x.idx - J) <= 12);
    row.centreFall = fall;
    row.jointTurn = Math.max.apply(null, tt.map((x) => Math.abs(x.deg)).concat([0]));
  }
  out.push(row);
}

function main() {
  let rows;
  if (mode === "serifs") rows = conceptRuns(serifRows);
  else if (mode === "sink") rows = conceptRuns(sinkRows);
  else if (mode === "corners") rows = spec.font ? shippedMasters(cornerRowsFor) : conceptRuns(cornerRowsFor);
  else if (mode === "edges") rows = shippedMasters(edgeRows);
  else throw new Error("unknown mode " + mode);
  process.stdout.write(JSON.stringify(rows));
}

try { main(); } catch (e) { console.error("joint_probe.js: " + (e && e.stack || e)); process.exitCode = 1; }
