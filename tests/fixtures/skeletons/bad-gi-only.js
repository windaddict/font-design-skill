// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a new italic key with no G counterpart.
var SKELETONS = function (G, GI, S, D, ring) {
  GI["@"] = [ring(330, 300, 220, 250)];
};
if (typeof module !== "undefined") module.exports = SKELETONS;
