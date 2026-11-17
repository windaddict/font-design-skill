// concepts.js for the "Sampler" example: the neutral fixture the skill's smoke run builds.
// A concept is one parameter set for scripts/gen.js; see references/generator.md for every knob.
// This file is JavaScript, not JSON, so angles can be written as degrees * DEG. In Node it is a
// CommonJS module; spliced into a concept page it leaves the global CONCEPTS.
var DEG = Math.PI / 180;
var CONCEPTS = [
  // An upright, low-contrast, bracketed serif unlike either shipped face: it exercises the FLARE
  // terminal path (tear: false, so flareAmt applies) that neither Bract nor Driftwood used.
  { id: "text", name: "Sampler", from: "A neutral text cut for the smoke run",
    W: 100, nib: 0, thin: 0.6, thinGrow: 0.6, pow: 1.2, xs: 0.92, swell: 0.02, track: 0,
    ends: { s: "serif", t: "flare", u: "flare", "": "disk", x: "exit" }, flareLen: 90, flareAmt: 0.2,
    serifLen: 0.5, serifH: 0.6, dot: 0.5, overshoot: 10, beak: true, tear: false, serifGrow: 0.4 },
  { id: "display", name: "Sampler Display", from: "The same cut for large titles: thinner hairlines, longer serifs, tighter",
    W: 108, nib: 0, thin: 0.5, thinGrow: 0.6, pow: 1.3, xs: 0.92, swell: 0.02, track: -8,
    ends: { s: "serif", t: "flare", u: "flare", "": "disk", x: "exit" }, flareLen: 100, flareAmt: 0.25,
    serifLen: 0.65, serifH: 0.5, dot: 0.5, overshoot: 10, beak: true, tear: false, serifGrow: 0.4 }
];
if (typeof module !== "undefined") module.exports = CONCEPTS;
