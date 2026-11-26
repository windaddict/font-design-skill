// tests/cut_end_probe.js: draws glyphs with the generator under test and prints what a `cut` stroke end did to its edge samples,
// for tests/test_cut_ends.py and tests/test_cut_reach.py.
//
// WHAT IT'S FOR: 0.10.0 draws a `cut` end by moving the last point of each edge onto the cut line and leaving the edge samples before
// it where they were. On the edge whose corner moves back, those samples stand past the cut line: a spike. The Python tests hold the
// fix to what a reader of the outlines would check, so every assertion stays in Python and this script only measures. Everything is
// found from the OUTPUT (polygons, edge runs, branch records); nothing is computed from the generator's own formulas except the cut
// direction, which is `cut` of the parameters params() builds from the concept (the concept's own value, or the default when it sets none).
//
//   node tests/cut_end_probe.js MODE SCRIPTS_DIR SPEC_JSON
//
// SCRIPTS_DIR holds gen.js (the real scripts/ folder, or a scratch copy carrying one mutation).
//
// SPEC (one JSON object): files (concept files), inline (concept objects, for a concept that has no file), only (draw only the concept
// with this id), patch (an object assigned over every concept drawn, in every mode and for both generators of mode `glyphs`: a fixture
// that is a shipped concept with some parameters changed, so it cannot drift from the concept it copies), mults, styles ("roman" | "italic"; italic is drawn at 10 degrees and only for a concept that maps the "x" end), and
// for mode `glyphs` old (the path of another gen.js).
//
// Rules shared by every mode (they follow tests/joint_probe.js):
//   - a stroke's body is the one polygon with two edge runs; the bodies of a glyph, in order, pair with the skeleton's open strokes (a
//     path that is not a dot and not a ring), in order, and with the glyph's `sig` entries that start with "open". The probe throws
//     when those three counts differ.
//   - with runs = [[a0, a1], [b0, b1]], n = a1 - a0 + 1 and flipped = (a0 != 0): L(j) = flipped ? poly[a1 - j] : poly[a0 + j] and
//     R(j) = flipped ? poly[b0 + j] : poly[b1 - j]. End A's corners are L(0) and R(0), end B's are L(n-1) and R(n-1).
//   - the skeleton of a key is GI[key] in an italic drawing when it exists, else G[key], as glyph() chooses.
//   - a coordinate that is not finite, or a glyph that throws, ends the probe with a non-zero exit, never a skip.
//
// DEFINITIONS (mode `ends`)
//   uncut stroke   the same concept drawn by the same generator with every `cut` end mode replaced by `butt`. The two modes share every
//                  width rule, so the two bodies have the same point count (the probe throws if not) and differ only in what the cut
//                  moved. glyph() shifts a glyph by its sidebearing, so the x shift is the median over the bodies' points of
//                  x_cut - x_uncut, taken off the cut drawing.
//   a row          one EDGE (L or R) of every stroke end whose branch record reads A=cut or B=cut and whose `ends=` outcome is still
//                  `cut` (a cut end that became a corner or a joint is not a cut end), for every concept that maps an end to `cut`.
//   reach          the distance from the edge's end corner in the cut drawing to the same corner in the uncut drawing. 0 means the cut
//                  did not move the corner.
//   inReach        walking back from the end (the corner itself is not counted), how many samples stood within reach + 1e-6 of the
//                  uncut corner, measured along the uncut edge (the sum of the steps between consecutive uncut samples), before the
//                  first that did not. The walk stops at the middle of the stroke.
//   spike, run     over those inReach samples, in the cut drawing, skipping the leading samples equal to the corner: the run of
//                  consecutive samples that lie more than 1e-6 past the cut line (run is its length, spike the largest distance). The
//                  cut line passes through the edge's cut corner along [cos cut, sin cut]; "past" is the side the stroke's outward
//                  direction points to, read from the uncut drawing's centre line (from the midpoint of the two edges 4 samples in to
//                  the midpoint at the end). The run ends at the first sample that is not past the line. In words: having reached the
//                  cut corner, does the outline continue beyond the cut.
//   beyond         from the first sample outside the reach to the middle of the stroke, how many samples differ from the uncut drawing
//                  by more than 1e-6; beyondMax is the largest difference.
//   C, U0, u(j), n, out, Dv   in the entries below: C is the edge's end corner in the cut drawing, U0 the same corner in the uncut
//                  drawing, u(j) the uncut edge's samples counted in from the end, n the stroke's sample count, out the stroke's
//                  outward direction (unit) and Dv the cut direction.
//   back           the cut moved the corner back along the stroke: (C - U0) . out < -1e-6.
//   off            the distance from C to the uncut edge, the polyline u(0) ... u(n-1) (the whole edge). 0 means the corner lies on the
//                  edge the uncut stroke draws. This is the step of issue #27.
//   at             the distance along that polyline from U0 to the point nearest C (the first such point).
//   pastLine       the signed distance of C past the cut line through the middle of the uncut end (the midpoint of the two uncut
//                  corners), positive on the side the stroke points to. Negative: the corner stops short of the line, on the stroke's side of it (the cut took
//                  more than the line asks). A corner that stops before reaching the line from outside is positive.
//   beyondSpan, beyondSpanMax   as beyond and beyondMax, but counted from the first sample farther along the uncut edge than
//                  max(reach, at) + 1e-6. reach is a straight-line distance, and a corner on a curved edge sits farther along the edge.
//   lim            min(80, floor((n - 2) / 2)): the bound of the corner walk in the generator.
//   pinRun         the number of samples in the run counted in from the end, starting at the end sample, whose cut position equals C
//                  within 1e-9, not counting a sample whose UNCUT position also equals C (a stack the fold pin already made in the
//                  uncut drawing is not a pin the cut made; the run goes on through it). At least 1: the corner itself.
//   Per end, the same value on both rows:
//   exhausted      the first lim segments of the uncut edge, from U0, are together shorter than ask - 1e-6 (and ask > 0), on either edge
//                  of the end. Computed from the uncut drawing alone.
//   exhaustedEdge  the same measure for this row's own edge alone (a row's value, not the end's): the first lim segments of this uncut edge
//                  are together shorter than ask - 1e-6 (and ask > 0). tests/test_cut_short.py reads it, because an end can be exhausted
//                  on one edge only, and the other edge's walk then ends normally.
//   width          the distance between the two uncut corners.
//   ask            how far a straight stroke of this end's width and direction is shortened on one edge by a cut line through the middle
//                  of its end. With e the unit vector from the uncut R corner to the uncut L corner: 0 when |e . Dv| < 0.25, else
//                  min(width, width / 2 * |e x Dv| / |e . Dv|).
//   stacked        an uncut end sample equals its neighbour on the same edge within 1e-9 (the fold pin moved the end), on either edge.
//   tilt           the angle in degrees, 0 to 90, between the segment from the cut L corner to the cut R corner and Dv.
//
// MODES
//   cutconcepts  one row {file, concept} per concept of spec.files that maps an end to `cut`; with spec.all, one row per concept.
//   ends         the rows defined above: file, concept, style, mult, key, stroke, end, edge, n, reach, inReach, spike, run, beyond,
//                beyondMax, back, off, at, pastLine, beyondSpan, beyondSpanMax, lim, pinRun, exhausted, exhaustedEdge, width, ask, stacked, tilt.
//   glyphs       one row per drawn glyph of every concept of spec.files and spec.inline, cut end or not: file, concept, style, mult, key,
//                same (polygons, advance and both spacing profiles equal those of the generator at spec.old, exactly) and movedCut (the
//                glyph has an edge with reach > 1e-6, measured as above with the generator under test), adv (the advance drawn by the generator under test) and oldAdv (the advance drawn by the generator at spec.old).
//
// The generator is loaded afresh for each concept and style: its glyph cache is never freed, and a process that loads many generators
// runs out of heap (the Python side starts one process per concept).
// Copyright 2026 John Knox. MIT licence.
"use strict";
const path = require("path");

const mode = process.argv[2], scriptsDir = path.resolve(process.argv[3] || "");
const spec = JSON.parse(process.argv[4] || "{}");
if (!process.argv[2] || !process.argv[3] || !process.argv[4]) { console.error("usage: node tests/cut_end_probe.js MODE SCRIPTS_DIR SPEC_JSON"); process.exit(2); }
const genPath = path.join(scriptsDir, "gen.js");
const TINY = 1e-6;

function loadAt(p) { delete require.cache[p]; return require(p); }
function load() { return loadAt(genPath); }

const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
const midOf = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];

// ---- reading a drawn glyph ----------------------------------------------------------------------------------------
function skeletonOf(m, key, P) { return (P.italic && m.GI[key]) || m.G[key]; }
function openIndices(raw) {
  const out = [];
  raw.forEach((st, i) => { if (st.d && !st.closed) out.push(i); });
  return out;
}
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
function checkFinite(g, where) {
  if (!Number.isFinite(g.adv)) throw new Error(where + ": the advance is not finite: " + g.adv);
  g.polys.forEach((poly, i) => poly.forEach((q, j) => {
    if (!Number.isFinite(q[0]) || !Number.isFinite(q[1])) throw new Error(where + ": polygon " + i + " point " + j + " is not finite: " + String(q[0]) + ", " + String(q[1]));
  }));
}
function readGlyph(m, key, P) {
  const g = m.glyph(key, P);
  if (!g) return null;
  checkFinite(g, "glyph " + JSON.stringify(key));
  const raw = skeletonOf(m, key, P), open = openIndices(raw), bodies = bodiesOf(g), sigs = g.sig.filter((s) => s.indexOf("open") === 0);
  if (bodies.length !== open.length || sigs.length !== open.length) {
    throw new Error("glyph " + JSON.stringify(key) + ": " + bodies.length + " bodies, " + sigs.length + " open records, " + open.length + " open skeleton strokes");
  }
  bodies.forEach((b, bi) => { b.stroke = open[bi]; b.sig = sigs[bi]; });
  return { g, bodies };
}

// ---- the cut ends of one glyph --------------------------------------------------------------------------------------
function median(a) {
  const s = a.slice().sort((x, y) => x - y), h = s.length >> 1;
  return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
}
const buttOf = (c) => Object.assign({}, c, { ends: Object.fromEntries(Object.entries(c.ends).map(([k, v]) => [k, v === "cut" ? "butt" : v])) });

// the rows of one glyph: cut drawing `cr` and uncut drawing `ur` (readGlyph results), the concept's cut angle `cutAngle`
function edgeRowsOf(cr, ur, cutAngle, key) {
  const rows = [], where = "glyph " + JSON.stringify(key);
  if (cr.bodies.length !== ur.bodies.length) throw new Error(where + ": the cut drawing has " + cr.bodies.length + " bodies, the uncut one " + ur.bodies.length);
  const dx = [];
  cr.bodies.forEach((cb, bi) => {
    const ub = ur.bodies[bi];
    if (cb.poly.length !== ub.poly.length || cb.n !== ub.n) throw new Error(where + " stroke " + cb.stroke + ": the cut body has " + cb.poly.length + " points, the uncut one " + ub.poly.length);
    cb.poly.forEach((q, i) => dx.push(q[0] - ub.poly[i][0]));
  });
  const shift = dx.length ? median(dx) : 0;
  const Dv = [Math.cos(cutAngle), Math.sin(cutAngle)];
  cr.bodies.forEach((cb, bi) => {
    const ub = ur.bodies[bi], n = cb.n, half = Math.floor((n - 1) / 2);
    const ends = / A=(\w+) B=(\w+)/.exec(cb.sig), outc = / ends=([^/\s]*)\/(\S*)/.exec(cb.sig);
    if (!ends || !outc) throw new Error(where + ": no A= B= or ends= in " + cb.sig);
    ["A", "B"].forEach((which, wi) => {
      if (ends[wi + 1] !== "cut" || outc[wi + 1] !== "cut") return;
      const at = (j) => which === "A" ? j : n - 1 - j; // j samples in from the end
      const cL = (j) => { const q = cb.L(at(j)); return [q[0] - shift, q[1]]; }, cR = (j) => { const q = cb.R(at(j)); return [q[0] - shift, q[1]]; };
      const uL = (j) => ub.L(at(j)), uR = (j) => ub.R(at(j));
      // the stroke's outward direction, from the uncut drawing's centre line
      const mIn = midOf(uL(4), uR(4)), mEnd = midOf(uL(0), uR(0));
      const out = [mEnd[0] - mIn[0], mEnd[1] - mIn[1]];
      const nrm = [-Dv[1], Dv[0]], sgn = (nrm[0] * out[0] + nrm[1] * out[1]) >= 0 ? 1 : -1;
      // per end, from the uncut drawing alone (and the two cut corners for `tilt`)
      const outLen = Math.hypot(out[0], out[1]), outU = [out[0] / outLen, out[1] / outLen];
      const lim = Math.min(80, Math.floor((n - 2) / 2));
      const e0 = [uL(0)[0] - uR(0)[0], uL(0)[1] - uR(0)[1]], width = Math.hypot(e0[0], e0[1]), eU = [e0[0] / width, e0[1] / width];
      const eDot = eU[0] * Dv[0] + eU[1] * Dv[1], eCross = eU[0] * Dv[1] - eU[1] * Dv[0];
      const ask = Math.abs(eDot) < 0.25 ? 0 : Math.min(width, width / 2 * Math.abs(eCross) / Math.abs(eDot));
      const walked = (u) => { let s = 0; for (let j = 0; j < lim && j + 1 < n; j++) s += dist(u(j), u(j + 1)); return s; };
      const exhausted = ask > 0 && (walked(uL) < ask - 1e-6 || walked(uR) < ask - 1e-6);
      const stacked = n > 1 && (dist(uL(0), uL(1)) < 1e-9 || dist(uR(0), uR(1)) < 1e-9);
      const seg = [cR(0)[0] - cL(0)[0], cR(0)[1] - cL(0)[1]], segLen = Math.hypot(seg[0], seg[1]);
      const tilt = segLen > 0 ? Math.acos(Math.min(1, Math.abs((seg[0] * Dv[0] + seg[1] * Dv[1]) / segLen))) * 180 / Math.PI : 0;
      const endMid = midOf(uL(0), uR(0));
      [["L", cL, uL], ["R", cR, uR]].forEach(([edge, c, u]) => {
        const C = c(0), U0 = u(0), reach = dist(C, U0);
        // the uncut edge as a polyline, counted in from the end: the corner's distance to it, and where along it the nearest point is
        let off = Infinity, at = 0, cum = 0;
        const alongU = [0];
        for (let j = 0; j + 1 < n; j++) {
          const a = u(j), b = u(j + 1), l = dist(a, b);
          let t = 0;
          if (l > 0) t = Math.max(0, Math.min(1, ((C[0] - a[0]) * (b[0] - a[0]) + (C[1] - a[1]) * (b[1] - a[1])) / (l * l)));
          const d = Math.hypot(C[0] - (a[0] + (b[0] - a[0]) * t), C[1] - (a[1] + (b[1] - a[1]) * t));
          if (d < off - 1e-12) { off = d; at = cum + t * l; }
          cum += l; alongU.push(cum);
        }
        if (n === 1) off = dist(C, u(0));
        const exhaustedEdge = ask > 0 && walked(u) < ask - 1e-6;
        const back = ((C[0] - U0[0]) * outU[0] + (C[1] - U0[1]) * outU[1]) < -1e-6;
        const pastLine = sgn * (nrm[0] * (C[0] - endMid[0]) + nrm[1] * (C[1] - endMid[1]));
        let pinRun = 1;
        for (let j = 1; j < n && dist(c(j), C) < 1e-9; j++) if (dist(u(j), C) > 1e-9) pinRun++;
        let beyondSpan = 0, beyondSpanMax = 0;
        for (let j = 1; j <= half; j++) {
          if (!(alongU[j] > Math.max(reach, at) + TINY)) continue;
          const d = dist(c(j), u(j));
          if (d > TINY) { beyondSpan++; beyondSpanMax = Math.max(beyondSpanMax, d); }
        }
        let along = 0, prev = U0, inReach = 0;
        for (let j = 1; j <= half; j++) {
          along += dist(prev, u(j)); prev = u(j);
          if (along > reach + TINY) break;
          inReach = j;
        }
        let spike = 0, run = 0, leading = true, ended = false;
        for (let j = 1; j <= inReach && !ended; j++) {
          const q = c(j);
          if (leading && dist(q, C) < 1e-9) continue;
          leading = false;
          const past = sgn * (nrm[0] * (q[0] - C[0]) + nrm[1] * (q[1] - C[1]));
          if (past > TINY) { run++; spike = Math.max(spike, past); } else ended = true;
        }
        let beyond = 0, beyondMax = 0;
        for (let j = inReach + 1; j <= half; j++) {
          const d = dist(c(j), u(j));
          if (d > TINY) { beyond++; beyondMax = Math.max(beyondMax, d); }
        }
        rows.push({ key, stroke: cb.stroke, end: which, edge, n, reach, inReach, spike, run, beyond, beyondMax, back, off, at, pastLine, beyondSpan, beyondSpanMax, lim, pinRun, exhausted, exhaustedEdge, width, ask, stacked, tilt });
      });
    });
  });
  return rows;
}

// ---- sweeps over concepts -------------------------------------------------------------------------------------------
const hasCut = (c) => !!c.ends && Object.values(c.ends).indexOf("cut") >= 0;
const label = (file) => path.basename(path.dirname(path.resolve(file))) + "/" + path.basename(file);

// every (generator, concept, style) of the spec, a fresh generator for each; fn(m, c, style, meta)
function sweep(fn) {
  const sources = (spec.files || []).map((f) => ({ file: label(f), path: path.resolve(f) })).concat((spec.inline || []).map((c) => ({ file: "inline", concept: c })));
  for (const src of sources) {
    const ids = src.path ? load().loadConcepts(src.path).map((c) => c.id) : [src.concept.id];
    for (const id of ids) {
      if (spec.only && id !== spec.only) continue;
      for (const style of spec.styles) {
        const m = load(); // a fresh generator, and so a fresh glyph cache, for each concept and style
        const c = src.path ? m.loadConcepts(src.path).filter((x) => x.id === id)[0] : JSON.parse(JSON.stringify(src.concept));
        if (spec.patch) Object.assign(c, JSON.parse(JSON.stringify(spec.patch)));
        if (style === "italic" && !(c.ends && c.ends.x)) continue;
        fn(m, c, style, { file: src.file, concept: id, style, src });
      }
    }
  }
}

function endsRows() {
  const out = [];
  sweep((m, c, style, meta) => {
    if (!hasCut(c)) return;
    for (const mult of spec.mults) {
      const deg = style === "italic" ? 10 : false, P = m.params(c, mult, deg), PB = m.params(buttOf(c), mult, deg);
      for (const key of Object.keys(m.G)) {
        const cr = readGlyph(m, key, P), ur = readGlyph(m, key, PB);
        if (!cr !== !ur) throw new Error("glyph " + JSON.stringify(key) + ": drawn in one mode and not in the other");
        if (!cr) continue;
        edgeRowsOf(cr, ur, P.cut, key).forEach((r) => out.push(Object.assign({ file: meta.file, concept: meta.concept, style, mult }, r)));
      }
    }
  });
  return out;
}

function glyphRows() {
  if (!spec.old) throw new Error("mode glyphs needs spec.old, the path of the other gen.js");
  const out = [], oldPath = path.resolve(spec.old);
  sweep((m, c, style, meta) => {
    const o = loadAt(oldPath);
    const oc = meta.src.path ? o.loadConcepts(meta.src.path).filter((x) => x.id === c.id)[0] : JSON.parse(JSON.stringify(meta.src.concept));
    if (spec.patch) Object.assign(oc, JSON.parse(JSON.stringify(spec.patch)));
    for (const mult of spec.mults) {
      const deg = style === "italic" ? 10 : false, P = m.params(c, mult, deg), PO = o.params(oc, mult, deg);
      const PB = hasCut(c) ? m.params(buttOf(c), mult, deg) : null;
      for (const key of Object.keys(m.G)) {
        const g = m.glyph(key, P), og = o.glyph(key, PO);
        if (!g !== !og) throw new Error("glyph " + JSON.stringify(key) + ": drawn by one generator and not by the other");
        if (!g) continue;
        checkFinite(g, "glyph " + JSON.stringify(key));
        const same = JSON.stringify([g.polys, g.adv, g.L, g.R]) === JSON.stringify([og.polys, og.adv, og.L, og.R]);
        let movedCut = false;
        if (PB) {
          const cr = readGlyph(m, key, P), ur = readGlyph(m, key, PB);
          movedCut = edgeRowsOf(cr, ur, P.cut, key).some((r) => r.reach > TINY);
        }
        out.push({ file: meta.file, concept: c.id, style, mult, key, same, movedCut, adv: g.adv, oldAdv: og.adv });
      }
    }
  });
  return out;
}

function main() {
  let rows;
  if (mode === "cutconcepts") {
    rows = [];
    for (const f of spec.files) load().loadConcepts(path.resolve(f)).forEach((c) => { if (spec.all || hasCut(c)) rows.push({ file: label(f), concept: c.id }); });
  } else if (mode === "ends") rows = endsRows();
  else if (mode === "glyphs") rows = glyphRows();
  else throw new Error("unknown mode " + mode);
  process.stdout.write(JSON.stringify(rows));
}

try { main(); } catch (e) { console.error("cut_end_probe.js: " + (e && e.stack || e)); process.exitCode = 1; }
