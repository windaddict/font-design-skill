// Bract (hopsafari.com, 2026-11-15): the two cuts that shipped, plus the six round-1 concepts and the
// round-3 revisions the face was chosen from. Parameters only; no outlines or font files ship here.
// The shipped cuts carried flareAmt 0.28 beside tear: true, which the generator now refuses because
// the flare swell never applies with teardrop terminals (Driftwood issue #24); they are dropped here
// and the teardrop keeps its default dropAmt 0.55, so the outlines are unchanged.
var DEG = Math.PI / 180;
var BRACT_ENDS = { s: "serif", t: "flare", u: "flareS", "": "disk", x: "exit" };
var CONCEPTS = [
  // --- the two cuts that shipped as one variable font (wght 400-700, opsz 40-80) ---
  { id: "text", name: "Bract", from: "Engraved captions on natural-history plates",
    W: 96, nib: 12 * DEG, thin: 0.44, thinGrow: 0.5, pow: 1.5, xs: 0.9, swell: 0.03, track: 0,
    ends: BRACT_ENDS, flareLen: 90,
    serifLen: 0.75, serifH: 0.5, dot: 0.5, overshoot: 10, beak: true, tear: true, serifGrow: 0.35 },
  { id: "display", name: "Bract Display", from: "Bract's display cut, for the largest titles",
    W: 104, nib: 12 * DEG, thin: 0.32, thinGrow: 0.5, pow: 1.8, xs: 0.9, swell: 0.03, track: -10,
    ends: BRACT_ENDS, flareLen: 90,
    serifLen: 1.0, serifH: 0.40, dot: 0.5, overshoot: 10, beak: true, tear: true, serifGrow: 0.35 },
  // --- round 1: six concepts, closest to the face in use (Bodoni Moda) first ---
  { id: "foil", name: "Foil", from: "Brass foil stamped on the bookcloth",
    W: 110, nib: 0, thin: 0.27, pow: 2.4, xs: 0.9, swell: 0, track: 0,
    ends: BRACT_ENDS, flareLen: 90, serifLen: 0.72, serifH: 0.13, dot: 0.5, overshoot: 10, beak: true, tear: true },
  { id: "burin", name: "Burin", from: "Engraved captions on natural-history plates",
    W: 94, nib: 12 * DEG, thin: 0.4, pow: 1.5, xs: 0.9, swell: 0.03, track: 0,
    ends: BRACT_ENDS, flareLen: 90, serifLen: 0.6, serifH: 0.3, dot: 0.5, overshoot: 10, beak: true, tear: true },
  { id: "blind", name: "Blind", from: "The title pressed blind into the cover",
    W: 114, nib: 0, thin: 0.74, pow: 1, xs: 1.08, swell: 0, track: 6,
    ends: { s: "serif", t: "butt", u: "butt", "": "disk", x: "exit" },
    serifLen: 0.5, serifH: 0.85, dot: 0.6, overshoot: 10 },
  { id: "field", name: "Field", from: "Lettering in a field notebook",
    W: 92, nib: 38 * DEG, thin: 0.3, pow: 1, xs: 0.86, swell: 0.14, track: 0,
    ends: { s: "serif", t: "cut", u: "cut", "": "disk", x: "exit" }, cut: 30 * DEG,
    serifLen: 0.32, serifH: 0.45, dot: 0.55, overshoot: 10 },
  { id: "cone", name: "Cone", from: "The bracts of the hop cone in the mark",
    W: 96, nib: 24 * DEG, thin: 0.36, pow: 1.3, xs: 0.92, swell: 0.06, track: 0,
    ends: { s: "serif", t: "taper", u: "taper", "": "disk", x: "exit" }, taperLen: 170, cut: 40 * DEG,
    serifLen: 0.3, serifH: 0.75, dot: 0.6, leaf: true, overshoot: 10 },
  { id: "bine", name: "Bine", from: "The climbing hop vine",
    W: 92, nib: 8 * DEG, thin: 0.62, pow: 1, xs: 0.98, swell: 0, track: 6,
    ends: { s: "butt", t: "curl", u: "curl", "": "disk", x: "exit" }, dot: 0.6, overshoot: 10 },
  // --- round 3: Burin revised (the text cut above, before thinGrow and with serifGrow 0.6) and the
  //     first display sketch "D2"; these became "text" and "display" with serifGrow 0.35 and thinGrow 0.5
  { id: "burin2", name: "Burin, revised", from: "Round 3: bigger serifs, heavier hairlines, serifs that grow with weight",
    W: 96, nib: 12 * DEG, thin: 0.44, pow: 1.5, xs: 0.9, swell: 0.03, track: 0,
    ends: BRACT_ENDS, flareLen: 90, serifLen: 0.75, serifH: 0.5, dot: 0.5, overshoot: 10, beak: true, tear: true, serifGrow: 0.6 },
  { id: "burinD", name: "Burin display (D2)", from: "Round 3: stems 8% heavier, hairlines thinner, serifs longer, tighter",
    W: 104, nib: 12 * DEG, thin: 0.32, pow: 1.8, xs: 0.9, swell: 0.03, track: -10,
    ends: BRACT_ENDS, flareLen: 90, serifLen: 1.0, serifH: 0.40, dot: 0.5, overshoot: 10, beak: true, tear: true, serifGrow: 0.6 }
];
if (typeof module !== "undefined") module.exports = CONCEPTS;
