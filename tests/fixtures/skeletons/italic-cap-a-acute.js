// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// The remedy for the limit in italic-cap-a.js: the override assigns the italic A-acute itself.
var SKELETONS = function (G, GI, S, D, ring) {
  GI.A[2] = S("M 180 300 L 520 300");
  GI["Á"] = GI.A.concat([S("M 330 780 L 430 890", "j", "t")]);
};
if (typeof module !== "undefined") module.exports = SKELETONS;
