// Test fixture for tests/test_skeleton_overrides.py (a per-face skeleton override; references/generator.md, "Per-face skeletons").
// A malformed export block: something follows module.exports, so build-page.js's stripExports refuses the file.
var SKELETONS = function (G, GI, S, D, ring) {};
if (typeof module !== "undefined") module.exports = SKELETONS;
var after = 1;
