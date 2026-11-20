// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a path that is an M alone.
var SKELETONS = function (G, GI, S, D, ring) {
  G.n[1] = S("M 90 380", "", "s");
};
if (typeof module !== "undefined") module.exports = SKELETONS;
