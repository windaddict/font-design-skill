// concepts.js: Tiki Terminal, round 1b. Six parameter sets for scripts/gen.js that run from an old
// console font to a carved tiki-bar sign.
//
// WHAT IT'S FOR: the spectrum the operator picks a shortlist from (SKILL.md phase 3). Tiki Terminal is
// the skill's own open example face, drawn for the repository's README and marketing images. Order:
// the concept closest to a console font first, the most organic tiki concept last. Each entry's
// comment names its genre from references/genres.md. The generator spaces every glyph
// proportionally (it has no fixed-width mode), so the "terminal" concepts borrow a console face's
// monoline stroke, slab serifs, tall x-height and open fit, not its fixed advance.
//
// Round 2 (2026-11-24, after the operator's notes on a, c and e): every curved free end is square (`butt`).
// An angled `cut` moves each end point along the stroke by up to its width, which drew wedges longer than the
// stroke on c, e, a, s and C at the Bold. The hooked flag genres.md section 7 records for butt-ended curves
// did not show at 2x on the redrawn a, c, e in skeletons.js. The cane concepts keep `cut` on their stems.
// Round 1b follows the round-1 review (2026-11-24): no free end draws a ball (a ball t foot reads as a
// full stop, the Sampler defect) and no curved free end is cut at 0 degrees (the hooked flag of
// genres.md section 7). Bamboo and Mainframe were replaced by Cane and Carved Slab, Tiki Torch by Totem.
var DEG = Math.PI / 180;

var CONCEPTS = [
  // 1. Genre: humanist sans (the round-1 reviewer's reading: two-storey a, wide rounds). A monoline
  //    stroke, narrow, tall in the lowercase, set loose: the console control. Free ends cut at 30 degrees.
  { id: "phosphor", name: "Phosphor", from: "A green prompt on a CRT after closing time",
    W: 96, nib: 0, thin: 1, pow: 1, xs: 0.92, swell: 0, track: 8,
    ends: { s: "butt", t: "cut", u: "cut", "": "disk", x: "exit" }, cut: 30 * DEG, dot: 0.55, overshoot: 10,
    hzThin: 0.92, roundGain: 1.04, diagThin: 0.95, xh: 560, joints: true, crotch: 0.3 },

  // 2. Genre: Egyptian / slab, at typewriter weight. A light near-monoline stroke with slab serifs and
  //    free ends cut at 30 degrees, the shape of a teletype printer face without its ball terminals.
  { id: "teletype", name: "Teletype", from: "The bar tab printed on a teletype roll",
    W: 88, nib: 0, thin: 0.82, pow: 1, xs: 0.96, swell: 0, track: 8,
    ends: { s: "serif", t: "butt", u: "butt", "": "disk", x: "exit" },
    serifLen: 0.6, serifH: 0.8, serifBracket: 0, serifGrow: 0.35, dot: 0.6, overshoot: 10,
    hzThin: 0.94, roundGain: 1.03, diagThin: 0.96, xh: 540 },

  // 3. Genre: none of the table's (a stick-built monoline). Heavy near-monoline strokes with every end,
  //    stems included, cut at 32 degrees, and a swell toward the ends: canes lashed into letters on a
  //    console skeleton. The round-1 reviewer's set A, with swell raised from 0.14 to 0.35 on the operator's
//    request (2026-11-24): above the 0-0.14 range generator.md documents, which params() does not enforce.
  { id: "cane", name: "Cane", from: "Bamboo canes lashed into a bar sign",
    W: 114, nib: 0, thin: 0.85, pow: 1, xs: 1.0, swell: 0.35, wob: 0.015, track: 6,
    ends: { s: "cut", t: "butt", u: "butt", "": "disk", x: "exit" }, cut: 32 * DEG,
    dot: 0.6, overshoot: 10, xh: 550, joints: true, crotch: 0.3 },

  // 4. Genre: Egyptian / slab with a chisel tilt. Mainframe's heavy slabs with a tilted pen and free ends
  //    that taper, so the sign-like Bold keeps its weight without notched terminals. The round-1
  //    reviewer's set B.
  { id: "carvedslab", name: "Carved Slab", from: "The bar's name routed into a plank",
    W: 114, nib: 18 * DEG, thin: 0.62, pow: 1, xs: 1.06, swell: 0.1, wob: 0.02, track: 4,
    ends: { s: "serif", t: "butt", u: "butt", "": "disk", x: "exit" },
    serifLen: 0.5, serifH: 0.7, serifBracket: 0, serifGrow: 0.35, dot: 0.6, overshoot: 10, xh: 540 },

  // 5. Genre: none of the table's (a flared glyphic roman). A tilted broad nib, a rippled stroke, every
  //    free end cut at one angle and small wedge serifs. Round 1b lowers the cut from 30 to 22 degrees
  //    and the swell from 0.08 to 0.04, against thin spikes the reviewer saw at the cut ends at 2x.
  { id: "carved", name: "Carved Post", from: "Letters chiselled into a tiki post",
    W: 110, nib: 30 * DEG, thin: 0.4, pow: 1, xs: 1.02, swell: 0.04, wob: 0.02, track: 2,
    ends: { s: "serif", t: "cut", u: "cut", "": "disk", x: "exit" }, cut: 22 * DEG,
    serifLen: 0.35, serifH: 0.55, dot: 0.6, overshoot: 10, xh: 520 },

  // 6. Genre: none of the table's (a stick-built monoline with a bouncing rhythm). Cane at full width,
  //    with the vowels and a few lowercase letters leaning back (`wonk`), so a word bounces the way
  //    hand-cut sign letters do. Driftwood found a back-lean read as an error on a quiet face; this
  //    concept tests whether it reads as play on a loud one.
  { id: "totem", name: "Totem", from: "A row of carved tiki heads, each at its own angle",
    W: 114, nib: 0, thin: 0.85, pow: 1, xs: 1.06, swell: 0.35, wob: 0.02, track: 4,
    ends: { s: "cut", t: "butt", u: "butt", "": "disk", x: "exit" }, cut: 32 * DEG,
    wonk: "aeiokrAEIO",
    dot: 0.62, overshoot: 10, xh: 560, joints: true, crotch: 0.3 }
];
// 7. Round 3 (2026-11-26): the operator chose Cane and Totem as finalists, and then one face with a
//    lean axis rather than two faces. Cane Lean is the far end of that axis: Cane exactly (its width,
//    x-height, tracking, wobble and dot, not Totem's adjusted ones) with Totem's leaning letters at
//    wonkAmount 0.158, about 9 degrees (0.12.0). Cane is the axis's upright end. A master pair that
//    differs only in wonkAmount exported interpolation-compatible at 0.045, 0.1 and 0.158.
CONCEPTS.push(Object.assign({}, CONCEPTS.filter(function (c) { return c.id === "cane"; })[0], {
  id: "canelean", name: "Cane Lean", from: "Cane with the tiki-head letters leaning back", wonk: "aeiokrAEIO", wonkAmount: 0.158 }));
if (typeof module !== "undefined") module.exports = CONCEPTS;
