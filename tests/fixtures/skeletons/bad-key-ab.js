// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a new key the cmap cannot map (two characters, not a LIGS name).
var SKELETONS = function (G, GI, S, D, ring) {
  G.ab = [S("M 90 500 L 90 0", "s", "s")];
};
if (typeof module !== "undefined") module.exports = SKELETONS;
