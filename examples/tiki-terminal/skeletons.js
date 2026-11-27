// skeletons.js: Tiki Terminal's own glyph skeletons, applied over gen.js's shared tables.
//
// WHAT IT'S FOR: the glyphs this face needs that the shared generator does not draw, or draws in a form
// that fails this face's concepts (references/generator.md, "Per-face skeletons"). It runs once per
// export or concept page, before any glyph is drawn, and the build hashes it into the manifest.
//
// - `>` and `_`: a terminal prompt ("C:>_") needs both; the operator chose to carry them on 2026-11-24
//   (gate decision 1). `>` is two strokes meeting at a point at the x-height middle; `_` is a level bar
//   below the baseline. Both end square ("j") at their free ends.
// - `e`: the shared `e` ends its lower terminal leaving at about 45 degrees. The round-1b concepts cut
//   every free end at 30 to 35 degrees, nearly along that stroke, which drew a separate-looking shard at
//   136px. This `e` ends its terminal rising straight up, so the cut crosses the stroke.
// - `a` and `c`: the same fault as the `e` at their free terminals, which left at 30 to 50 degrees. Each now
//   starts or ends on a vertical tangent, so a 22 to 35 degree cut crosses the stroke at 55 degrees or more.
// - `t`: its foot left at about 25 degrees and, with Cane's swell of 0.35, thickened into a hooked blob that
//   read as a separate mark after "Last" (the Sampler fault again). This foot ends rising, like the `e`, and
//   the crossbar ends square, where the shared bar's unmapped ends drew a round disc at Cane's swell.
// - `T`: the shared bar ends in free terminals (`t`), which an angled cut turns into a sliver on a level
//   stroke. This bar ends square.
//
// Round 3 fixes (the operator approved the design on 2026-11-26; the list is the round-3 reviewer's):
// - `r`: the shared arm reaches x 405 and ran into the next letter ("rm" fused at 84px, "rr" at 40px). This
//   arm ends at x 365, lower and rounder.
// - `t`: the foot is shorter and lower, so at 40px it reads as part of the t, not
//   as a full stop after it. Design review round 1 (2026-11-26): at 115 to 140 px Bold Lean the rising free end
//   still swelled into a hooked blob that read as a comma ("Last, Call at, the"), and a tighter turn folded the
//   inner edge into a notch at Bold (the bend radius was under half the stroke width). The foot is now a wide
//   sweep from y 230 that rises to x 355, y 50 and ends square ("j"): the swell has no free end to round off, and
//   the rise tilts the square end so its lower corner stays above the baseline (a level end stood 80 units below).
// - diagonal stems: a 32 degree cut on a swelled diagonal drew a long shard (and issue #27's step). Every
//   stem end more than 8 degrees off vertical is square ("j", squareDiagonalStems below); vertical stems keep
//   the cut. The `7` bar starts square too: a cut on a level free end is a sliver.
// - `1`: the shared flag and stem are two strokes meeting at the top, and the join folded back 15.75 units after
//   decimation at Regular. This `1` is one stroke turning at the top (worst fold in the font 4.13 after it).
// - `0`: a slash inside the counter, so the zero cannot be read as an O beside capitals (the reviewer's
//   "console" fix). The slash ends square. Round 1 of the design review shortened it (235,230 to 325,470): the
//   longer slash nearly filled the Bold counter at 40 to 48 px. Round 2 (2026-11-27) found that one still welded
//   to the Bold bowl (1.3 units apart): the Bold stroke is about 200 units wide in a 260-unit counter, so no long
//   slash fits; a short bar inside the counter (round 3, 277,290 to 283,410) read as a theta at Bold (round 4).
//   The operator chose a classic slashed zero on 2026-11-27: one diagonal (170,90 to 410,610) that crosses the
//   counter and ends inside the bowl, so it needs no clearance and reads the same at both weights. The two
//   counters it leaves were about 1 px wide at 40 px Regular, so "04:00" read a weight heavier than its line
//   (round 5): the bowl is 60 units wider than the shared one (half-width 230, centre x 310) and the slash
//   runs from 195,90 to 425,610.
// - `I`: the shared `I` is a bare stem, the same as `l` but 40 units shorter, so "Il1" read "ll1" on the console
//   page. The operator chose bars (2026-11-27): a stem at x 160 with square-ended bars from x 40 to 280 at the
//   cap height and the baseline.
// - `[` and `]`: at Bold the shared arms (130 units) stood out only about 40 units past the stem, so "[y/n]" read
//   as "ly/nl" (round 3). The arms are 210 units long.
// - `i`, `j`, `!`: at Bold the shared dot (y 680) overlapped the stem by 23 units and the `!` dot met its
//   stem, so "Painkiller" drew its `i` as one mark (round 2). The `i` and `j` dots sit at y 760 and the `!`
//   stem ends at y 240.
// - accents: Cane's 150-unit marks drew as round blobs, at swell 0.35 and after the x-height map squeezed
//   the band above x 500 (references/generator.md, `xh`). The acute and grave are about 200 units and rise
//   past 740, which the map leaves alone. The circumflex is design C of round 3: two strokes, wider and
//   lower; the caron of `š` is the same mark turned over. Over `u` the circumflex stands 60 units higher: its
//   ends landed on the two stems, so "brûlée" drew the `û` as one closed shape (design review round 4); over
//   `a`, `e`, `o` it stands 60 higher, and over capitals 50 higher than the acute and grave. The diaeresis is
//   rebuilt here with its dots at y 720, 760 over `u` (the shared 650 met the Bold `a` and `u`), and the caron of `š` is 60
//   higher: at Bold each of these marks came within 4 units of its letter (round 4, measured, not on the pages). Each accented letter is rebuilt here from this
//   file's bases, so it also follows the redrawn `a`, `e`.
var SKELETONS = function (G, GI, S, D, ring) {
  G[">"] = [S("M 80 470 L 460 260", "j", ""), S("M 460 260 L 80 50", "", "j")];
  G["_"] = [S("M 30 -110 L 500 -110", "j", "j")];
  G.e = [S("M 90 260 L 480 260"),
    S("M 480 260 C 490 400 410 510 290 510 C 160 510 80 400 80 250 C 80 100 170 -10 300 -10 C 400 -10 470 40 475 130", "", "t")];
  G.a = [S("M 105 390 C 105 470 190 510 270 510 C 380 510 440 460 440 360 L 440 0", "t", "s")].concat(G.a.slice(1));
  G.c = [S("M 470 380 C 470 460 380 510 290 510 C 160 510 80 400 80 250 C 80 100 160 -10 290 -10 C 400 -10 470 40 475 130", "t", "t")];
  G.t = [S("M 170 640 L 170 230 C 170 80 220 10 300 10 C 325 10 340 20 355 50", "x", "j"), S("M 50 490 L 350 490", "j", "j")];
  G.T = [S("M 300 700 L 300 0", "j", "s"), S("M 40 700 L 560 700", "j", "j")];
  G.r = [G.r[0], S("M 90 380 C 135 465 200 505 275 505 C 320 505 350 495 365 470", "", "t")];

  G["7"] = [S("M 60 700 L 480 700", "j", ""), G["7"][1]];
  G["1"] = [S("M 150 580 L 290 700 L 290 0", "j", "s")];
  G["0"] = [ring(310, 350, 230, 360), S("M 195 90 L 425 610", "j", "j")];
  G.I = [S("M 40 700 L 280 700", "j", "j"), S("M 160 700 L 160 0"), S("M 40 0 L 280 0", "j", "j")];
  G.i = [G.i[0], D(110, 760)];
  G.j = [G.j[0], D(130, 760)];
  G["!"] = [S("M 120 700 L 120 240", "s", "t"), D(120, 45)];
  G["["] = [S("M 350 760 L 140 760", "j", ""), S("M 140 760 L 140 -170"), S("M 140 -170 L 350 -170", "", "j")];
  G["]"] = [S("M 50 760 L 260 760", "j", ""), S("M 260 760 L 260 -170"), S("M 260 -170 L 50 -170", "", "j")];
  squareDiagonalStems(G, S);

  function acute(cx, dy) { return [S("M " + (cx - 40) + " " + (600 + dy) + " L " + (cx + 60) + " " + (790 + dy), "j", "j")]; }
  function grave(cx, dy) { return [S("M " + (cx + 40) + " " + (600 + dy) + " L " + (cx - 60) + " " + (790 + dy), "j", "j")]; }
  function circ(cx, dy) {
    return [S("M " + (cx - 160) + " " + (610 + dy) + " L " + cx + " " + (690 + dy), "j", ""),
      S("M " + cx + " " + (690 + dy) + " L " + (cx + 160) + " " + (610 + dy), "", "j")];
  }
  function diaer(cx, dy) { return [D(cx - 95, 720 + dy), D(cx + 95, 720 + dy)]; }
  var marks = { "́": acute, "̀": grave, "̂": circ, "̈": diaer };
  var low = { a: 270, e: 280, o: 290, u: 275 }, cap = { A: 330, E: 290, I: 160, O: 380, U: 340 };
  var dotless = [S("M 110 500 L 110 0", "s", "s")];
  Object.keys(marks).forEach(function (cm) {
    Object.keys(low).forEach(function (b) { var k = (b + cm).normalize("NFC"); if (G[k]) G[k] = G[b].concat(marks[cm](low[b], cm === "̂" ? (b === "u" ? 80 : 60) : cm === "̈" && b === "u" ? 40 : 0)); });
    var ki = ("i" + cm).normalize("NFC"); if (G[ki]) G[ki] = dotless.concat(marks[cm](110, 0));
    Object.keys(cap).forEach(function (b) { var k = (b + cm).normalize("NFC"); if (G[k]) G[k] = G[b].concat(marks[cm](cap[b], cm === "̂" ? 220 : 170)); });
  });
  G["š"] = G.s.concat([S("M 100 760 L 260 680", "j", ""), S("M 260 680 L 420 760", "", "j")]);
};
// Every stem end ("s") on a stroke that arrives more than 8 degrees off vertical becomes square ("j"), in every
// letter and figure of G; vertical stems keep the cut. On 2026-11-26 this squared x, X, Y, k, K, v, w, y, A,
// V, W, the R leg and the 7 foot. It reads each end's direction from the path's end point and the coordinate
// pair before it, which is the end tangent for an L segment and a C segment's last control point.
function squareDiagonalStems(G, S) {
  Object.keys(G).forEach(function (k) {
    if (!/^[A-Za-z0-9]$/.test(k)) return;
    G[k] = G[k].map(function (st) {
      if (!st.d) return st;
      var n = st.d.match(/-?\d+(\.\d+)?/g).map(Number), m = n.length;
      function off(x, y, px, py) { var a = Math.abs(Math.atan2(x - px, y - py) * 180 / Math.PI) % 180; return Math.min(a, 180 - a); }
      var a = st.a === "s" && off(n[0], n[1], n[2], n[3]) > 8 ? "j" : st.a;
      var b = st.b === "s" && off(n[m - 2], n[m - 1], n[m - 4], n[m - 3]) > 8 ? "j" : st.b;
      return a === st.a && b === st.b ? st : S(st.d, a, b);
    });
  });
}
if (typeof module !== "undefined") module.exports = SKELETONS;
