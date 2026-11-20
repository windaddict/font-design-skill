// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a C with five numbers.
var SKELETONS = function (G, GI, S, D, ring) {
  G.n[1] = S("M 90 380 C 140 470 210 510 290 L 460 0", "", "s");
};
if (typeof module !== "undefined") module.exports = SKELETONS;
