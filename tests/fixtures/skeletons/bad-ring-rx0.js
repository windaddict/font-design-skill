// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a ring with rx 0.
var SKELETONS = function (G, GI, S, D, ring) {
  G.o[0] = ring(290, 250, 0, 260);
};
if (typeof module !== "undefined") module.exports = SKELETONS;
