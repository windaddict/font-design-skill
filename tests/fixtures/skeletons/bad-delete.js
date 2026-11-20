// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a key present before the call is deleted.
var SKELETONS = function (G, GI, S, D, ring) {
  delete G.n;
};
if (typeof module !== "undefined") module.exports = SKELETONS;
