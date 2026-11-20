// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Refused: a ring whose d is not what ring() draws.
var SKELETONS = function (G, GI, S, D, ring) {
  var r = ring(290, 250, 210, 260); r.d = r.d.replace("M 290", "M 291"); G.o[0] = r;
};
if (typeof module !== "undefined") module.exports = SKELETONS;
