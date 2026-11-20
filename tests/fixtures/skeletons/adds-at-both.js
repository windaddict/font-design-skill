// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// A new glyph added to both tables: accepted, and each group exports it (the italic drawing the GI entry).
var SKELETONS = function (G, GI, S, D, ring) {
  G["@"] = [ring(330, 300, 220, 250), S("M 400 300 L 400 120", "j", "j")];
  GI["@"] = [ring(330, 300, 220, 250), S("M 420 320 L 400 120", "j", "j")];
};
if (typeof module !== "undefined") module.exports = SKELETONS;
