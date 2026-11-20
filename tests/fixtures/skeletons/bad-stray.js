// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a stroke whose path holds a stray token.
var SKELETONS = function (G, GI, S, D, ring) {
  G.n[1] = S("M 90 380 L 460 330 x L 460 0", "", "s");
};
if (typeof module !== "undefined") module.exports = SKELETONS;
