// concepts.example.js: a round-1 spectrum of eight concepts for a fictional "Example" family, plus the
// display cut that a round-3 pick would add. Copy it next to your font.json as concepts.js and
// replace the values; every concept here passes scripts/gen.js params(), and "quill" also passes it
// with the italic flag, so the file can be exported as it stands.
//
// WHAT IT'S FOR: the shape of the file the skill asks for at phase 3 (round 1, the spectrum). Each
// entry is one parameter set for scripts/gen.js; one entry draws a whole cut, and a weight is the
// same entry with W multiplied by the master's `mult` in font.json. The order is the rule the skill
// uses for a spectrum: the concept closest to the face the site uses today comes first, the most
// organic last, so the operator sees the range before the recommendation. Each entry's comment names
// its GENRE from references/genres.md (a Didone, a Clarendon, a slab, a grotesque): name the genre
// beside the brand name, and cover at least three genres in a spectrum. templates/concepts.genres.js
// has a candidate recipe per genre.
//
// The file is JavaScript, not JSON, because angles are written in degrees times DEG. In Node it is a
// CommonJS module exporting the array; spliced into a concept page it leaves the global CONCEPTS.
// The full table of knobs, ranges and interactions is references/generator.md. Two rules params()
// enforces: a concept with `tear: true` must not set `flareAmt` (the flare swell never applies to
// teardrop terminals; size them with `dropAmt`), and a concept without `tear: true` must not set
// `dropAmt`.
var DEG = Math.PI / 180;

// The end-type table maps the letters a skeleton uses (s = stem end, t = free terminal, u = a quieter
// free terminal, "" = a hidden join, x = an italic exit stroke) to a drawing mode: serif, flare,
// flareS, beak, exit, disk, cut, taper, curl, butt. The skeleton letter "j" (a plain square end) is
// left unmapped on purpose; an unmapped letter draws a square end. Every table below maps x, so
// any of these concepts can be exported as an italic group.
var SERIF_ENDS = { s: "serif", t: "flare", u: "flareS", "": "disk", x: "exit" };

var CONCEPTS = [
  // 1. Genre: Didone-leaning (modern). Closest to the face in use: vertical stress (nib 0), high
  //    contrast, flat serifs, round balls. tear is off, so the terminals are balls and flareAmt is live.
  { id: "ledger", name: "Ledger", from: "The ruled columns of an account book",
    W: 100, nib: 0, thin: 0.30, pow: 2.2, xs: 0.94, swell: 0, track: 0,
    ends: SERIF_ENDS, flareLen: 90, flareAmt: 0.25,
    serifLen: 0.70, serifH: 0.15, dot: 0.5, overshoot: 10, beak: true, tear: false },

  // 2. Genre: transitional (a Scotch roman's gentler cousin). A slightly oblique nib, bracketed serifs, teardrops built from the stroke's
  //    own edges. thinGrow and serifGrow keep the Bold in the same family as the Regular (both
  //    shipped faces needed them; see references/traps.md item 17).
  { id: "quill", name: "Quill", from: "A copperplate caption cut with a fine point",
    W: 96, nib: 12 * DEG, thin: 0.44, thinGrow: 0.5, pow: 1.5, xs: 0.94, swell: 0.03, track: 0,
    ends: SERIF_ENDS, flareLen: 90,
    serifLen: 0.75, serifH: 0.50, serifGrow: 0.35, dot: 0.5, overshoot: 10, beak: true, tear: true },

  // 3. Genre: Clarendon-leaning (bracketed slab serifs). Low contrast, slightly wide, square free ends ("butt" is not a drawn mode:
  //    the stroke simply stops, the same as an unmapped end type).
  { id: "anvil", name: "Anvil", from: "Letters struck into a plate",
    W: 114, nib: 0, thin: 0.74, pow: 1, xs: 1.08, swell: 0, track: 6,
    ends: { s: "serif", t: "butt", u: "butt", "": "disk", x: "exit" },
    serifLen: 0.50, serifH: 0.85, dot: 0.6, overshoot: 10 },

  // 4. Genre: Egyptian / slab. The anvil's proportions with the bracket removed: serifBracket 0 draws
  //    every serif as a slab with the same point count as the bracketed one. Its thin is above 0.7, so the
  //    three optical knobs are set (references/guidelines.md section 3): level strokes a little
  //    lighter, curves a little heavier, diagonals a little lighter.
  { id: "slab", name: "Slab", from: "A rail-yard stencil board",
    W: 108, nib: 0, thin: 0.74, pow: 1, xs: 1.04, swell: 0, track: 4,
    ends: { s: "serif", t: "butt", u: "butt", "": "disk", x: "exit" },
    serifLen: 0.50, serifH: 0.85, serifBracket: 0, serifGrow: 0.6, dot: 0.6, overshoot: 10,
    hzThin: 0.94, roundGain: 1.03, diagThin: 0.96 },

  // 5. Genre: grotesque (no serifs). A near-uniform stroke (thin 1), a taller x-height (xh 540), terminals
  //    cut across the stroke, and the three optical knobs, which are most of what makes a monoline pen read
  //    as even. Limit: the skeleton's rounds are humanist ovals and the G has a bar, not a spur
  //    (references/genres.md).
  { id: "grot", name: "Grot", from: "The lettering on a freight timetable",
    W: 100, nib: 0, thin: 1, pow: 1, xs: 1.0, swell: 0, track: 2,
    ends: { s: "butt", t: "cut", u: "cut", "": "disk", x: "exit" }, dot: 0.55, overshoot: 10,
    hzThin: 0.92, roundGain: 1.04, diagThin: 0.95, xh: 540 },

  // 6. Genre: none of the table's (a broad-nib humanist hand). A broad-nib hand: a steep nib angle, a visible swell along each stroke, every free end cut at
  //    one angle (`cut`), small wedge serifs.
  { id: "brush", name: "Brush", from: "A reed pen on rough paper",
    W: 92, nib: 38 * DEG, thin: 0.30, pow: 1, xs: 0.86, swell: 0.14, track: 0,
    ends: { s: "serif", t: "cut", u: "cut", "": "disk", x: "exit" }, cut: 30 * DEG,
    serifLen: 0.32, serifH: 0.45, dot: 0.55, overshoot: 10 },

  // 7. Genre: none of the table's (a tapered display hand). Free ends taper to a point over `taperLen` units and take the `cut` angle at the tip; dots are
  //    leaf-shaped ellipses rotated to `cut`. Leaf dots read as accents at small sizes on a precedent
  //    (references/guidelines.md), so this is a concept to show, not a safe default.
  { id: "thorn", name: "Thorn", from: "The pointed tips of a seed head",
    W: 96, nib: 24 * DEG, thin: 0.36, pow: 1.3, xs: 0.94, swell: 0.06, track: 0,
    ends: { s: "serif", t: "taper", u: "taper", "": "disk", x: "exit" }, taperLen: 170, cut: 40 * DEG,
    serifLen: 0.30, serifH: 0.75, dot: 0.6, leaf: true, overshoot: 10 },

  // 8. Genre: none of the table's (a curling display hand). The most organic end of the spectrum: flat stems, free ends that curl over as a shrinking
  //    spiral. A curl needs a curved end with at least 12 samples; a straight end falls back to a
  //    disk, and the branch record says which happened, so masters cannot disagree silently.
  { id: "vine", name: "Vine", from: "A climbing stem",
    W: 92, nib: 8 * DEG, thin: 0.62, pow: 1, xs: 0.98, swell: 0, track: 6,
    ends: { s: "butt", t: "curl", u: "curl", "": "disk", x: "exit" }, dot: 0.6, overshoot: 10 },

  // Added after round 3 for the fictional pick: the display cut of "quill", for titles at the large
  // end of the optical-size axis. Stems 8% heavier, hairlines thinner, serifs longer, a tighter set.
  // The two cuts must take the same branches in every stroke (same end types, same teardrop sides)
  // or scripts/export.js refuses them; keep ends, beak and tear identical between cuts.
  { id: "quill-display", name: "Quill Display", from: "Quill for the largest titles",
    W: 104, nib: 12 * DEG, thin: 0.32, thinGrow: 0.5, pow: 1.8, xs: 0.94, swell: 0.03, track: -10,
    ends: SERIF_ENDS, flareLen: 90,
    serifLen: 1.0, serifH: 0.40, serifGrow: 0.35, dot: 0.5, overshoot: 10, beak: true, tear: true }
];
if (typeof module !== "undefined") module.exports = CONCEPTS;
