// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a new key that is a lone UTF-16 surrogate, not a character (re-review of the diff, F003).
var SKELETONS = function (G, GI, S, D, ring) {
  G["\uD800"] = [S("M 90 700 L 90 0", "s", "s")];
};
if (typeof module !== "undefined") module.exports = SKELETONS;
