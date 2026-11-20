// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// An override that declares a top-level const DEG, a name gen.js and concepts.js also declare. Spliced into a concept page
// inside its wrapper function it clashes with nothing; spliced bare it would throw a redeclaration in the browser.
const DEG = Math.PI / 180;
var SKELETONS = function (G, GI, S, D, ring) {
  G.n[1] = S("M 90 480 C 170 510 225 510 290 510 C 410 510 460 440 460 330 L 460 0", "", "s");
};
if (typeof module !== "undefined") module.exports = SKELETONS;
