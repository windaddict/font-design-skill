// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: one stroke that is both a dot and a path (glyph() would draw only the dot; diff review F005).
var SKELETONS = function (G, GI, S, D, ring) {
  G.i[1] = { dot: [110, 680], d: "M 90 500 L 90 0", a: "s", b: "s" };
};
if (typeof module !== "undefined") module.exports = SKELETONS;
