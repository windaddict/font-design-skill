// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// Bract's candidate B7 (docs/plan-skeleton-overrides.md section 4.2): the arch of n, h, m and r starts at the head
// serif's corner on the stem, its first controls on the 510 line, so the shoulder has no nick.
var SKELETONS = function (G, GI, S, D, ring) {
  var arch = "M 90 480 C 170 510 225 510 290 510 C 410 510 460 440 460 330 L 460 0";
  G.n[1] = S(arch, "", "s");
  G.h[1] = S(arch, "", "s");
  G.m[1] = S("M 90 484 C 160 510 205 510 260 510 C 360 510 405 450 405 350 L 405 0", "", "s");
  G.m[2] = S("M 405 484 C 475 510 520 510 575 510 C 675 510 720 450 720 350 L 720 0", "", "s");
  G.r[1] = S("M 90 480 C 170 510 225 510 290 510 C 345 510 385 495 405 455", "", "t");
};
if (typeof module !== "undefined") module.exports = SKELETONS;
