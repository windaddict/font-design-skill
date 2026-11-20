// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a dot with a string coordinate.
var SKELETONS = function (G, GI, S, D, ring) {
  G.i[1] = { dot: [110, "680"] };
};
if (typeof module !== "undefined") module.exports = SKELETONS;
