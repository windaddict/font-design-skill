// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// The limit of plan section 2.2 (review F009): an override of the italic capital A does not reach the accented capitals,
// which exist in G only, so the italic draws A-acute from the roman table slanted.
var SKELETONS = function (G, GI, S, D, ring) {
  GI.A[2] = S("M 180 300 L 520 300");
};
if (typeof module !== "undefined") module.exports = SKELETONS;
