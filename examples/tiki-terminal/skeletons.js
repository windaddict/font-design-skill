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
// - `t`: the foot is shorter and lower (it ends at x 345, y 45), so at 40px it reads as part of the t, not
//   as a full stop after it.
// - diagonal stems: a 32 degree cut on a swelled diagonal drew a long shard (and issue #27's step). Every
//   stem end more than 8 degrees off vertical is square ("j", squareDiagonalStems below); vertical stems keep
//   the cut. The `7` bar starts square too: a cut on a level free end is a sliver.
// - `1`: the shared flag and stem are two strokes meeting at the top, and the join folded back 15.75 units after
//   decimation at Regular. This `1` is one stroke turning at the top (worst fold in the font 4.13 after it).
// - `0`: a slash inside the counter, so the zero cannot be read as an O beside capitals (the reviewer's
//   "console" fix). The slash ends square and touches neither side.
// - accents: Cane's 150-unit marks drew as round blobs, at swell 0.35 and after the x-height map squeezed
//   the band above x 500 (references/generator.md, `xh`). The acute and grave are about 200 units and rise
//   past 740, which the map leaves alone. The circumflex is design C of round 3: two strokes, wider and
//   lower; the caron of `š` is the same mark turned over. Each accented letter is rebuilt here from this
//   file's bases, so it also follows the redrawn `a`, `e`.
var SKELETONS = function (G, GI, S, D, ring) {
  G[">"] = [S("M 80 470 L 460 260", "j", ""), S("M 460 260 L 80 50", "", "j")];
  G["_"] = [S("M 30 -110 L 500 -110", "j", "j")];
  G.e = [S("M 90 260 L 480 260"),
    S("M 480 260 C 490 400 410 510 290 510 C 160 510 80 400 80 250 C 80 100 170 -10 300 -10 C 400 -10 470 40 475 130", "", "t")];
  G.a = [S("M 105 390 C 105 470 190 510 270 510 C 380 510 440 460 440 360 L 440 0", "t", "s")].concat(G.a.slice(1));
  G.c = [S("M 470 380 C 470 460 380 510 290 510 C 160 510 80 400 80 250 C 80 100 160 -10 290 -10 C 400 -10 470 40 475 130", "t", "t")];
  G.t = [S("M 170 640 L 170 110 C 170 30 205 -10 265 -10 C 310 -10 335 10 345 45", "x", "t"), S("M 50 490 L 350 490", "j", "j")];
  G.T = [S("M 300 700 L 300 0", "j", "s"), S("M 40 700 L 560 700", "j", "j")];
  G.r = [G.r[0], S("M 90 380 C 135 465 200 505 275 505 C 320 505 350 495 365 470", "", "t")];

  G["7"] = [S("M 60 700 L 480 700", "j", ""), G["7"][1]];
  G["1"] = [S("M 150 580 L 290 700 L 290 0", "j", "s")];
  G["0"] = [G["0"][0], S("M 215 190 L 345 510", "j", "j")];
  squareDiagonalStems(G, S);

  function acute(cx, dy) { return [S("M " + (cx - 40) + " " + (600 + dy) + " L " + (cx + 60) + " " + (790 + dy), "j", "j")]; }
  function grave(cx, dy) { return [S("M " + (cx + 40) + " " + (600 + dy) + " L " + (cx - 60) + " " + (790 + dy), "j", "j")]; }
  function circ(cx, dy) {
    return [S("M " + (cx - 160) + " " + (610 + dy) + " L " + cx + " " + (690 + dy), "j", ""),
      S("M " + cx + " " + (690 + dy) + " L " + (cx + 160) + " " + (610 + dy), "", "j")];
  }
  var marks = { "́": acute, "̀": grave, "̂": circ };
  var low = { a: 270, e: 280, o: 290, u: 275 }, cap = { A: 330, E: 290, I: 120, O: 380, U: 340 };
  var dotless = [S("M 110 500 L 110 0", "s", "s")];
  Object.keys(marks).forEach(function (cm) {
    Object.keys(low).forEach(function (b) { var k = (b + cm).normalize("NFC"); if (G[k]) G[k] = G[b].concat(marks[cm](low[b], 0)); });
    var ki = ("i" + cm).normalize("NFC"); if (G[ki]) G[ki] = dotless.concat(marks[cm](110, 0));
    Object.keys(cap).forEach(function (b) { var k = (b + cm).normalize("NFC"); if (G[k]) G[k] = G[b].concat(marks[cm](cap[b], 170)); });
  });
  G["š"] = G.s.concat([S("M 100 700 L 260 620", "j", ""), S("M 260 620 L 420 700", "", "j")]);
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
