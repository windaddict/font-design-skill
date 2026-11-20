// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a stroke whose path holds a Q (a quadratic the generator does not draw; sampleCounts would skip it in silence).
var SKELETONS = function (G, GI, S, D, ring) {
  G.n[1] = S("M 90 380 Q 290 510 460 330 L 460 0", "", "s");
};
if (typeof module !== "undefined") module.exports = SKELETONS;
