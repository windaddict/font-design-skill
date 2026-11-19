// tests/r_leg_junction.js: measures the capital R's leg where it leaves the bowl, for tests/test_r_leg_join.py.
//
// WHAT IT'S FOR: the R's leg started on the bowl's thin closing bar with a hidden-join disk that was wider than
// the bar, so a round lump showed in the counter (0.4.0 and every earlier version; docs/plan-r-leg.md section 0).
// The fix types the leg's start `i`, a T-join: the end is cut parallel to the bar on the bar's centre line, so the
// whole end is buried. This script draws the R with a given generator and reports, per concept, weight and slant,
// what a reader of the outline would check: how far any leg point pokes out of the bowl (the nub), whether the cut
// is level, on the centre line and buried, the cut's length against the leg's width, that the leg still reaches
// the bowl, the leg's angle and foot, the branch record's tee token, and the leg's width profile near its root.
// The Python side restates the expected values and asserts; this file computes and prints JSON only.
//
//   node tests/r_leg_junction.js measure   GEN.js CONCEPTS.js...   one record per concept x mult (1, 1.5) x slant
//   node tests/r_leg_junction.js dump      GEN.js CONCEPTS.js...   the R's polygons per drawing, for the union check
//   node tests/r_leg_junction.js control   GEN.js CONCEPTS.js      the 0.4.0 R skeleton installed, then measured once
//                                                                   (a FRESH process: gen.js caches a drawn glyph by
//                                                                   concept and key, so the swap must precede any draw)
//   node tests/r_leg_junction.js synthetic GEN.js CONCEPTS.js      the T-join on hand-built glyphs, every case under its
//                                                                   own concept copy so no case reads another's cache
//
// Coordinates are the generator's drawn ones (after the sidebearing shift); a drawing's bowl and stem polygons are
// compared with another generator's after aligning on the stem body's first point.
// Copyright 2026 John Knox. MIT licence.
"use strict";
const path = require("path");

const mode = process.argv[2], genPath = process.argv[3], files = process.argv.slice(4);
if (!mode || !genPath) { console.error("usage: node tests/r_leg_junction.js measure|dump|control|synthetic GEN.js CONCEPTS.js..."); process.exit(2); }
const m = require(path.resolve(genPath));

// the R as 0.4.0 drew it (scripts/gen.js at 598044b, lines 114-116 and 219-221), the literal the control measures
const OLD_R_ROMAN = [m.S("M 100 700 L 100 0", "s", "s"),
  m.S("M 100 700 L 330 700 C 470 700 540 630 540 520 C 540 410 470 340 330 340 L 100 340"),
  m.S("M 320 340 L 570 0", "", "s")];

// ---------- geometry ----------
function dist(a, b) { return Math.hypot(b[0] - a[0], b[1] - a[1]); }
function inside(p, poly) {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const a = poly[i], b = poly[j];
    if ((a[1] > p[1]) !== (b[1] > p[1]) && p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
  }
  return c;
}
function segDist(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2));
  return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
}
function centroid(poly) { return [poly.reduce((s, q) => s + q[0], 0) / poly.length, poly.reduce((s, q) => s + q[1], 0) / poly.length]; }
function boundaryDist(p, polys) {
  let d = Infinity;
  for (const poly of polys) for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) d = Math.min(d, segDist(p, poly[i], poly[j]));
  return d;
}
// the y of every crossing of the vertical through x with the polygons' edges, between lo and hi, ascending
function edgesAt(x, polys, lo, hi) {
  const ys = [];
  for (const poly of polys) for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const a = poly[i], b = poly[j];
    if ((a[0] <= x) !== (b[0] <= x)) { const y = a[1] + (x - a[0]) * (b[1] - a[1]) / (b[0] - a[0]); if (y > lo && y < hi) ys.push(y); }
  }
  return ys.sort((p, q) => p - q);
}

// ---------- the parts of a drawn R ----------
// A stroke body is the polygon with two edge runs; the bodies come in stroke order, so the stem is the first, the bowl the
// second and the leg the last. The polygons between two bodies are the earlier stroke's terminals.
// A glyph with one stroke before the leg (the synthetic cases) has the partner stroke's polygons from index 0.
function parts(g) {
  const bodies = [];
  g.polys.forEach((p, i) => { if (g.runs[i].length === 2) bodies.push(i); });
  const legBody = bodies[bodies.length - 1], bowlStart = bodies.length >= 3 ? bodies[1] : 0;
  return { bodies, legBody, stem: g.polys.slice(0, bowlStart), bowl: g.polys.slice(bowlStart, legBody), leg: g.polys.slice(legBody), body: g.polys[legBody], runs: g.runs[legBody] };
}
// the leg body's edges by sample index, whichever way glyph() oriented the polygon (strokePolys builds it as Lp then Rp reversed,
// gen.js line 700, and glyph() reverses the whole polygon when its area is negative, lines 961-972, flipping the runs with it):
// L(j) and R(j) are the two edge points of sample j, and the cut's two corners are the body's closing seam, its first and last
// points, which the runs mark as the lowest index of one run and the highest of the other. Not "the first two points": those are
// two samples of one edge.
function edges(body, runs) {
  const flipped = runs[0][0] !== 0, n = runs[0][1] - runs[0][0] + 1;
  const lo = Math.min(runs[0][0], runs[1][0]), hi = Math.max(runs[0][1], runs[1][1]);
  return {
    n,
    L: j => flipped ? body[runs[0][1] - j] : body[runs[0][0] + j],
    R: j => flipped ? body[runs[1][0] + j] : body[runs[1][1] - j],
    corners: [body[lo], body[hi]],
  };
}
function nubOf(leg, body, bowl) {
  let nub = 0, below = 0, overlap = 0, at = null;
  leg.forEach(poly => poly.forEach(p => {
    if (p[1] < 150) return;                                   // the foot and the lower leg are outside the bowl by design
    if (bowl.some(q => inside(p, q))) { if (poly === body) overlap++; return; }
    const ys = edgesAt(p[0], bowl, 150, 650);
    if (!ys.length) return;                                   // no bowl above or below: the leg's own territory
    if (p[1] <= ys[0] + 1e-9) return;                         // under the bowl's lower edge: the leg emerging, which is right
    const d = boundaryDist(p, bowl);
    if (d > nub) { nub = d; at = p.map(v => +v.toFixed(2)); }
    if (p[1] <= (ys.length > 1 ? ys[1] : ys[0])) below = Math.max(below, d);
  }));
  return { nub, below, overlap, at };
}
function measureR(g, P) {
  const { bodies, legBody, bowl, leg, body, runs } = parts(g);
  const E = edges(body, runs), n = E.n;
  const { nub, below, overlap, at } = nubOf(leg, body, bowl);
  const [c0, c1] = E.corners;
  // the bar's edges at the ROOT (the cut's midpoint): the cut lies on the partner's centre line through the root, parallel to its
  // tangent there; on a curved partner the centre line bends away from the cut towards the corners, so the corners are judged
  // by their burial margin, not by the local centre
  const rootX = (c0[0] + c1[0]) / 2, ysR = edgesAt(rootX, bowl, 150, 650);
  const centreOffset = ysR.length >= 2 ? Math.abs((c0[1] + c1[1]) / 2 - (ysR[0] + ysR[1]) / 2) : null;
  const halfBar = ysR.length >= 2 ? (ysR[1] - ysR[0]) / 2 : null;
  const marginOf = c => (bowl.some(q => inside(c, q)) ? 1 : -1) * boundaryDist(c, bowl);
  const margin = Math.min(marginOf(c0), marginOf(c1));
  // the leg's width well past any pinned sample, and its direction and foot from the centre line
  const mid = j => [(E.L(j)[0] + E.R(j)[0]) / 2, (E.L(j)[1] + E.R(j)[1]) / 2];
  const w = dist(E.L(Math.min(40, n - 1)), E.R(Math.min(40, n - 1))), foot = mid(n - 1), back = mid(Math.max(0, n - 31));
  const legAngle = Math.atan2(foot[1] - back[1], foot[0] - back[0]) * 180 / Math.PI;
  // a 64-point polygon of the leg's centred within one width of the root is a disk at the root (a ball at the other end is not)
  const root = [(c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2];
  const diskAtRoot = leg.some((poly, i) => i > 0 && poly.length === 64 && dist(centroid(poly), root) < w);
  // the width profile near the root, for the taper check: sample j's width, tangent angle, arc length from the root, total
  const prof = [], s = [0];
  for (let j = 1; j < n; j++) s.push(s[j - 1] + dist(mid(j - 1), mid(j)));
  for (const j of [20, 23, 26, 40, 60]) {
    const a = mid(Math.max(0, j - 1)), b = mid(Math.min(n - 1, j + 1));
    prof.push({ j, width: dist(E.L(j), E.R(j)), theta: Math.atan2(b[1] - a[1], b[0] - a[0]), s: s[j] });
  }
  const legSig = g.sig[g.sig.length - 1], tee = (legSig.match(/ tee=(\S+)/) || [])[1] || null;
  const pinnedL = (() => { let k = 1; while (k < n && dist(E.L(k), E.L(0)) < 1e-9) k++; return k - 1; })();
  const pinnedR = (() => { let k = 1; while (k < n && dist(E.R(k), E.R(0)) < 1e-9) k++; return k - 1; })();
  return {
    nub: +nub.toFixed(4), below: +below.toFixed(4), nubAt: at, overlap, bodies: bodies.length, legBody,
    corners: [c0, c1].map(c => c.map(v => +v.toFixed(3))), tilt: +Math.abs(c0[1] - c1[1]).toFixed(4),
    centreOffset: centreOffset === null ? null : +centreOffset.toFixed(4), halfBar: halfBar === null ? null : +halfBar.toFixed(3),
    margin: +margin.toFixed(3), cutLen: +dist(c0, c1).toFixed(3), w: +w.toFixed(3), legAngle: +legAngle.toFixed(3), footY: +foot[1].toFixed(3),
    diskAtRoot, legPolys: leg.length, polys: g.polys.length, points: g.polys.reduce((t, p) => t + p.length, 0),
    adv: +g.adv.toFixed(3), tee, legSig, pinned: [pinnedL, pinnedR], profile: prof.map(r => ({ j: r.j, width: +r.width.toFixed(4), theta: +r.theta.toFixed(6), s: +r.s.toFixed(3) })),
    total: +s[n - 1].toFixed(3), W: P.W, W0: P.W0, thin: P.thin, nib: P.nib, pow: P.pow, swell: P.swell || 0, italic: P.italic, xs: P.xs || 1, shear: P.shear || 0, optical: !!P.optical,
  };
}

function drawings(cb) {
  const out = {};
  for (const f of files) for (const c of m.loadConcepts(f)) for (const mult of [1, 1.5]) for (const it of [false, true]) {
    if (it && !(c.ends && c.ends.x)) continue;
    const key = `${path.basename(path.dirname(f))}/${path.basename(f)}:${c.id}@${mult}${it ? "i" : ""}`;
    try { const P = m.params(c, mult, it); out[key] = cb(m.glyph("R", P), P); } catch (e) { out[key] = { error: String(e.message) }; }
  }
  return out;
}

if (mode === "measure") {
  console.log(JSON.stringify(drawings(measureR)));
} else if (mode === "dump") {
  console.log(JSON.stringify(drawings(g => { const { bodies } = parts(g); const sh = g.polys[0][0][0]; return { bodies, polys: g.polys.map(p => p.map(q => [+(q[0] - sh).toFixed(4), +q[1].toFixed(4)])) }; })));
} else if (mode === "control") {
  // the 0.4.0 skeleton, installed before any draw (FD_R_CONTROL_WARM=1 draws the R first, the mutation that shows why)
  const c = m.loadConcepts(files[0])[0], P = m.params(c, 1, false);
  if (process.env.FD_R_CONTROL_WARM) m.glyph("R", P);
  m.G.R = OLD_R_ROMAN;
  console.log(JSON.stringify(measureR(m.glyph("R", P), P)));
} else if (mode === "synthetic") {
  // hand-built glyphs under lowercase-shaped keys (so the x-height map applies to them), drawn with the first concept of the
  // file with serif stems, at mult 1 and 1.5, at xh 400 and 600, and at the italic slant
  const base = Object.assign({}, m.loadConcepts(files[0])[0]);
  base.ends = Object.assign({}, base.ends, { s: "serif", "": "disk" });
  const S = m.S, ring = m.ring;
  // the same ring drawn the other way round: a hand-written closed path (ring() always draws clockwise, and fitSkeleton rebuilds a
  // stroke that carries `r` from its parameters, so this one carries none). fitSkeleton keeps a closed path's `closed` only when it
  // returns the skeleton untouched, which it does with `overshoot` unset or 0 and `xh` 500 (re-review of the diff, R3); with the fit on,
  // the rebuilt stroke is open. So the reversed ring runs in the `nofit` variant, where the two directions exist side by side.
  function reversed(rg) {
    const t = rg.d.trim().split(/\s+/).map(Number).filter(v => !Number.isNaN(v));
    const pts = []; for (let i = 0; i < t.length; i += 2) pts.push([t[i], t[i + 1]]);
    let out = "M " + pts[12].join(" ");
    for (let seg = 3; seg >= 0; seg--) { const a = pts[seg * 3 + 2], b = pts[seg * 3 + 1], c = pts[seg * 3]; out += " C " + a.join(" ") + " " + b.join(" ") + " " + c.join(" "); }
    return { d: out, closed: true };
  }
  // a concept copy for the reviewer's crossing construction (re-review R1): a wide pen, no x-scaling and a strong shear, so the leg's
  // drawn angle to the level bar passes through perpendicular between mult 1 and 1.5 and clipPast pins the left edge in one master and
  // the right edge in the other
  const CROSS = { xs: 1, shear: 0.77, W: 200 };
  // a wavy partner: crests at x 215, 320 and 425 (y 540), troughs between them 80 lower; an `i` stroke at 23 degrees from the middle
  // crest has its cut's corners on the outer crests, inside the stroke, while the cut's middle spans a trough, outside it
  const wave = "M 215 540 C 241.25 540 241.25 460 267.5 460 C 293.75 460 293.75 540 320 540 C 346.25 540 346.25 460 372.5 460 C 398.75 460 398.75 540 425 540";
  // the same wave with troughs only 38 deep and pulled narrow (the controls 9.19 from each anchor): the partner's edge dips across the
  // cut over a few units, between two of nine probes spaced 26 apart along a 210-unit cut. The exact check (the cut crosses the edge)
  // refuses it at both weights; nine probes drew it (re-review of the diff, R2; found by search over amplitude, angle and narrowness)
  const trough = "M 215 540 C 224.19 540 258.31 502 267.5 502 C 276.69 502 310.81 540 320 540 C 329.19 540 363.31 502 372.5 502 C 381.69 502 415.81 540 425 540";
  // the bars are 441 units long: sampled every 3 units from x 100, so the root at 320 is 1 unit from sample 73 and 2 from sample 74 in
  // every master (a 440-unit bar put the root exactly midway between two samples, and float rounding chose a different one per weight,
  // which is what the record's sample index exists to refuse)
  const CASES = {
    bar: [S("M 100 340 L 541 340"), S("M 320 340 L 570 0", "i", "s")],                               // 1: a level bar, a 54 degree stroke
    ring: [ring(320, 340, 200, 120), S("M 461.4 424.9 L 300 160", "i", "s")],                         // 1r: on a ring at its 45 degree point, running in along the normal
    slope: [S("M 100 200 L 540 454"), S("M 320 327 L 500 0", "i", "s")],                              // 2: a 30 degree bar
    end: [S("M 320 340 L 540 340"), S("M 320 340 L 570 0", "i", "s")],                                // 3: on the bar's END: a joint, refused
    off: [S("M 100 340 L 541 340"), S("M 320 343 L 570 0", "i", "s")],                                // 4: three units off the bar: refused
    edge: [S("M 317.5 340 L 540 340"), S("M 320 340 L 570 0", "i", "s")],                              // 4b: 2.5 units from the bar's END: no joint partner, a sample found, but the cut cannot fit inside the bar: refused
    parallel: [S("M 100 340 L 541 340"), S("M 320 340 L 540 379", "i", "t")],                          // 5: ten degrees to the bar: refused
    shallow15: [S("M 100 340 L 541 340"), S("M 320 340 L 540 399", "i", "t")],                         // 5b: fifteen degrees: the widest reach that draws
    shallow16: [S("M 100 340 L 541 340"), S("M 320 340 L 540 403", "i", "t")],                         // 5c: sixteen degrees: the map at xh 400 takes it under the refusal
    wave: [S(wave), S("M 320 540 L 540.9 446.2", "i", "s")],                                                // 4c: corners inside, the cut's middle outside: refused
    trough: [S(trough), S("M 320 540 L 540.9 446.2", "i", "s")],                                            // 4d: a dip narrower than a probe spacing: refused by the exact check only
    ringrev: [reversed(ring(320, 340, 200, 120)), S("M 461.4 424.9 L 300 160", "i", "s")],              // 1r2: the ring the other way round (nofit variant only)
    cross: [S("M 100 340 L 900 340"), S("M 500 340 L 750 0", "i", "s")],                                  // 1c: with CROSS, perpendicular crossed between weights: the two records must differ
    midgap: [S("M 100 340 L 540 340"), S("M 320 340 L 570 0", "i", "s")],                                // 1m: a 440-unit bar, the root exactly midway between two samples
    mirror: [S("M 100 340 L 541 340"), S("M 320 340 L 70 0", "i", "s")],                                 // 1x: the stroke comes from the other side: the token's side letter flips
    disk: [S("M 100 340 L 541 340"), S("M 320 340 L 570 0", "", "s")],                                  // 6: the hidden-join end draws its disk
    square: [S("M 100 340 L 541 340"), S("M 320 340 L 570 0", "j", "s")],                               // 6: the square end draws no token
  };
  const out = {};
  for (const [variant, extra, it] of [["500", {}, false], ["400", { xh: 400 }, false], ["600", { xh: 600 }, false], ["italic", {}, true], ["wide", { xs: 1.12 }, false], ["nofit", { overshoot: 0 }, false]]) {
    for (const mult of [1, 1.5]) for (const name in CASES) {
      if (variant === "wide" && mult !== 1.5) continue; // the widest drawing the generator's range allows: xs 1.12 at mult 1.5
      if (name === "ringrev" && variant !== "nofit") continue; // a hand-written closed path survives fitSkeleton only without the fit
      if (name === "cross" && variant !== "500") continue;
      const key = "rt" + name;
      m.G[key] = CASES[name];
      const c = Object.assign({}, base, extra, name === "cross" ? CROSS : {}, { _case: name + variant + mult }); // its own cache key per case and variant
      const id = `${variant}/${mult}/${name}`;
      try {
        const P = m.params(c, mult, it), g = m.glyph(key, P);
        const { bowl: partner, leg, body, runs } = parts(g);
        const E = edges(body, runs), [c0, c1] = E.corners, n = E.n;
        // the partner stroke's drawn tangent at the point nearest the stroke's root (the closing seam's midpoint)
        const root = [(c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2], pp = partner[0];
        let bk = 0, bd = Infinity;
        for (let k = 0; k < pp.length; k++) { const d = dist(pp[k], root); if (d < bd) { bd = d; bk = k; } }
        const ta = pp[(bk - 1 + pp.length) % pp.length], tb = pp[(bk + 1) % pp.length];
        const tang = Math.atan2(tb[1] - ta[1], tb[0] - ta[0]), cutAng = Math.atan2(c1[1] - c0[1], c1[0] - c0[0]);
        let dAng = Math.abs(((cutAng - tang) * 180 / Math.PI) % 180); dAng = Math.min(dAng, 180 - dAng);
        const w = dist(E.L(Math.min(40, n - 1)), E.R(Math.min(40, n - 1))), mid = j => [(E.L(j)[0] + E.R(j)[0]) / 2, (E.L(j)[1] + E.R(j)[1]) / 2];
        const legSig = g.sig[g.sig.length - 1];
        const pinnedL = (() => { let k = 1; while (k < n && dist(E.L(k), E.L(0)) < 1e-9) k++; return k - 1; })();
        const pinnedR = (() => { let k = 1; while (k < n && dist(E.R(k), E.R(0)) < 1e-9) k++; return k - 1; })();
        // the ring case: the partner's centre-line tangent at the root, restated from the ring's parameters through the concept's
        // transforms (xs with the weight widening and the italic narrowing, the shear, the x-height map's y scale), so the cut's
        // direction is judged against the skeleton and not against the ring's offset outline, whose tangent differs
        let expectedDeg = null;
        if (name === "ring" || name === "ringrev") {
          const xsE = (P.xs || 1) * (1 + 0.16 * (P.W / P.W0 - 1)) * (it ? 0.95 : 1), ky = (c.xh || 500) / 500, th = Math.PI / 4;
          const tx = -200 * Math.sin(th) * xsE + P.italic * 120 * ky * Math.cos(th), ty = 120 * ky * Math.cos(th);
          expectedDeg = +(Math.atan2(ty, tx) * 180 / Math.PI).toFixed(3);
        }
        out[id] = { ok: true, expectedDeg, cutDeg: +(cutAng * 180 / Math.PI).toFixed(3), pinned: [pinnedL, pinnedR], tee: (legSig.match(/ tee=(\S+)/) || [])[1] || null, ends: (legSig.match(/ ends=(\S+)/) || [])[1], tilt: +Math.abs(c0[1] - c1[1]).toFixed(4),
          cutY: +((c0[1] + c1[1]) / 2).toFixed(3), barY: +pp.reduce((s, q) => s + q[1], 0) / pp.length, cutLen: +dist(c0, c1).toFixed(3), w: +w.toFixed(3),
          cutVsPartnerDeg: +dAng.toFixed(3), legPolys: leg.length, diskAtRoot: leg.some((poly, i) => i > 0 && poly.length === 64 && dist(centroid(poly), root) < w),
          legDeg: +(Math.atan2(mid(n - 1)[1] - mid(Math.max(0, n - 31))[1], mid(n - 1)[0] - mid(Math.max(0, n - 31))[0]) * 180 / Math.PI).toFixed(3),
          partnerDeg: +(tang * 180 / Math.PI).toFixed(3), sig: legSig };
      } catch (e) { out[id] = { ok: false, error: String(e.message) }; }
    }
  }
  console.log(JSON.stringify(out));
} else {
  console.error("unknown mode " + mode); process.exit(2);
}
