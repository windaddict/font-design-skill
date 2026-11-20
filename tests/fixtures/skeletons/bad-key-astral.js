// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a new key outside the Basic Multilingual Plane (two UTF-16 units; title layout reads text by unit; diff review F003).
var SKELETONS = function (G, GI, S, D, ring) {
  G["𝒜"] = [S("M 90 700 L 90 0", "s", "s")];
};
if (typeof module !== "undefined") module.exports = SKELETONS;
