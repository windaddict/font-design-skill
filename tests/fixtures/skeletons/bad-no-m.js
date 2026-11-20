// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a path that does not start with M.
var SKELETONS = function (G, GI, S, D, ring) {
  G.n[1] = S("L 90 380 L 460 0", "", "s");
};
if (typeof module !== "undefined") module.exports = SKELETONS;
