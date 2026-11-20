// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// The derivation and italic-fallback cases (plan sections 2.4, 2.5 and 2.7): Driftwood's a bowl, roman and italic, edited in
// place; t's stem given a head serif (GI has no t, so the italic draws this one slanted); n-tilde assigned whole (the
// override's, never re-derived); the copyright's inner stroke edited in place (an authored glyph, never re-derived).
var SKELETONS = function (G, GI, S, D, ring) {
  G.a[1] = S("M 440 270 C 350 300 90 260 90 130 C 90 40 150 -10 230 -10 C 320 -10 400 40 440 110");
  GI.a[1] = S("M 440 360 C 390 470 330 510 260 510 C 140 510 70 400 70 250 C 70 100 140 -10 250 -10 C 330 -10 400 40 440 120");
  G.t[0].a = "s";
  G["ñ"] = [S("M 90 500 L 90 0", "s", "s"), S("M 90 380 C 140 470 210 510 290 510 C 410 510 460 440 460 330 L 460 0", "", "s"),
            S("M 150 650 L 400 650", "j", "j")];
  G["©"][1].d = "M 425 425 C 400 465 370 490 333 490 C 265 490 220 420 220 330 C 220 240 265 170 333 170 C 370 170 400 195 428 235";
};
if (typeof module !== "undefined") module.exports = SKELETONS;
