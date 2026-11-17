// Driftwood MA (movingavg.com, 2026-11-14): the concept that shipped and the three it was chosen over.
// Parameters only; no outlines or font files ship here. Driftwood shipped with flareAmt 0.28 beside
// tear: true, a dead knob (issue #24); it is dropped here and the teardrop keeps its default dropAmt.
var DEG = Math.PI / 180;
var CONCEPTS = [
  { id: "driftwood", name: "Driftwood", from: "From the tree",
    desc: "Soft wedge serifs, flared stroke ends and strokes that thicken and thin a little along their length, like wood worn smooth by the sea.",
    W: 88, nib: 25 * DEG, thin: 0.36, pow: 1.4, xs: 0.86, wob: 0, swell: 0.08, track: 0,
    ends: { s: "serif", t: "flare", u: "flareS", "": "disk", x: "exit" }, flareLen: 90,
    serifLen: 0.64, serifH: 0.4, wonk: "", dot: 0.47, overshoot: 10, beak: true, pebble: false, tear: true },
  { id: "tideline", name: "Tideline", from: "From the sea",
    desc: "Low contrast, with the free ends of a, c, f, r, s, j and y curling over like a breaking wave. Stems end flat, so the curls are the only movement in a line.",
    W: 90, nib: 10 * DEG, thin: 0.66, pow: 1, xs: 0.98, track: 6,
    ends: { s: "butt", t: "curl", "": "disk" }, dot: 0.6 },
  { id: "dune", name: "Dune", from: "From the sand",
    desc: "Wide, low-contrast letters with every end worn round, like stone shaped by blowing sand.",
    W: 104, nib: 0, thin: 0.82, pow: 1, xs: 1.12, track: 10,
    ends: { s: "disk", t: "disk", "": "disk" }, dot: 0.74 },
  { id: "windswept", name: "Windswept", from: "From the tree on the cliff",
    desc: "The stress tilts with the wind, the lean grows toward the tops of tall letters, and every stroke end is cut at the same angle. The dots are leaf-shaped.",
    W: 90, nib: 40 * DEG, thin: 0.48, pow: 1.3, xs: 0.92, track: 0,
    shear: Math.tan(8 * DEG), bend: 0.00022,
    ends: { s: "cut", t: "taper", "": "disk" }, cut: 22 * DEG, taperLen: 120, dot: 0.6, leaf: true }
];
if (typeof module !== "undefined") module.exports = CONCEPTS;
