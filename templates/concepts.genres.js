// concepts.genres.js: one recipe per genre the generator was tried against (references/genres.md).
//
// WHAT IT'S FOR: a parameter set per named genre, so a project can start a round-1 spectrum from a
// genre ("a Didone, a grotesque, a slab") instead of from numbers. Every recipe loads in params() at two
// weights, has only finite coordinates and exports as two compatible masters (tests/test_genres.py).
// Whether a recipe READS as its genre was decided by rendering the page and reading it on 2026-11-16;
// each `desc` opens with that verdict (reaches, partly or no) and the date, and genres.md holds the
// same verdict. A change to a recipe or to gen.js makes the verdict stale until the page is read again.
//
// Each entry carries `name` (the genre), `from` (one sentence on what defines it) and `desc` (the dated
// verdict and limit, as genres.md states it). The round-1 page does NOT read the recipe's `desc`: it shows
// text only from content.concepts.<id> in scripts/concepts/content.genres.json (its `desc` is `from`, its
// `risk` the table cell), and tests/test_genres.py keeps the three in step.
//
// Build the page:
//   node scripts/concepts/build-page.js --template round1 --concepts templates/concepts.genres.js \
//     --content scripts/concepts/content.genres.json out/smoke/pages/genres.html
//
// None of these sets `apex` (the pointed apex is designed, not built; params() refuses it). The
// grotesque and the geometric recipes set `joints: true` (a sans concept gets the serif concepts' joint
// and corner pass: level cuts where strokes meet) and a `crotch`, which thins the inner edge at acute joints.
var DEG = Math.PI / 180;

// s = stem end, t = free terminal, u = a quieter free terminal, "" = a hidden join, x = an italic exit.
var SERIF_ENDS = { s: "serif", t: "flare", u: "flareS", "": "disk", x: "exit" };
// sans: stems and free ends stop square, or are cut across (`cut`); no serif is drawn
var SANS_ENDS = { s: "butt", t: "cut", u: "cut", "": "disk", x: "exit" };

var CONCEPTS = [
  // Didone / modern: vertical stress, hairline unbracketed serifs and horizontals, ball terminals.
  { id: "didone", name: "Didone", from: "Vertical stress, hairline unbracketed serifs and horizontals, ball terminals",
    desc: "Partly (2026-11-22): Moderate contrast because of the hairline floor, and equal-weight diagonals on A V W M N v w x y, so it reads as a light modern, not a Didone. The diagonals need an expansion model, which is out of scope",
    W: 104, nib: 0, thin: 0.28, pow: 2.2, xs: 0.94, swell: 0, track: 0,
    ends: SERIF_ENDS, flareLen: 90, flareAmt: 0.2,
    serifLen: 0.7, serifH: 0.13, serifBracket: 0, dot: 0.5, overshoot: 10, beak: true, tear: false },

  // Fat face: a Didone at poster weight. The Regular is heavy already; the Bold (mult 1.5) is the fat face.
  { id: "fatface", name: "Fat face", from: "A Didone at poster weight, the counters reduced to slits",
    desc: "No (2026-11-22): Stems are about 1/6 of the cap height even at the Bold; W past its range cannot reach 1/3-cap stems without collapsing the counters. It needs new shapes",
    W: 130, nib: 0, thin: 0.22, pow: 2.2, xs: 0.98, swell: 0, track: -4,
    ends: SERIF_ENDS, flareLen: 90, flareAmt: 0.2,
    serifLen: 0.7, serifH: 0.13, serifBracket: 0, dot: 0.5, overshoot: 10, beak: true, tear: false },

  // Scotch roman / transitional: Bract's "foil", unchanged apart from the id and the labels.
  { id: "scotch", name: "Scotch roman", from: "Vertical stress, bracketed serifs, high contrast, brass-foil sharp",
    desc: "Reaches (2026-11-22): A near-twin of the Didone at these sizes; the bracket and the a terminal are what differ. Also shipped and reviewed as Bract's foil on hopsafari.com (2026-11-15).. Its italic exported since 0.7.0 (section 4)",
    W: 110, nib: 0, thin: 0.27, pow: 2.4, xs: 0.9, swell: 0, track: 0,
    ends: SERIF_ENDS, flareLen: 90, serifLen: 0.72, serifH: 0.13, dot: 0.5, overshoot: 10, beak: true, tear: true },

  // Clarendon: bracketed slab serifs, moderate contrast, drawn as a bold companion. thin is above 0.7, so
  // the three optical knobs are set (references/guidelines.md section 3).
  { id: "clarendon", name: "Clarendon", from: "Bracketed slab serifs, moderate contrast, a bold companion",
    desc: "No (2026-11-22): The serifs are short pointed wedges, not square bracketed slabs, so it reads as a wedge serif. A longer serifLen with serifGrow 0 might fix it; untested. Rendering defects: section 7",
    W: 108, nib: 0, thin: 0.74, pow: 1, xs: 1.04, swell: 0, track: 4,
    ends: { s: "serif", t: "butt", u: "butt", "": "disk", x: "exit" },
    serifLen: 0.5, serifH: 0.85, serifBracket: 1, serifGrow: 0.6, dot: 0.6, overshoot: 10,
    hzThin: 0.94, roundGain: 1.03, diagThin: 0.96 },

  // Egyptian / slab: the Clarendon recipe with the bracket removed (serifBracket 0).
  { id: "slab", name: "Egyptian slab", from: "Unbracketed slab serifs, low to moderate contrast",
    desc: "Reaches (2026-11-22): Square unbracketed slabs at stem weight, low contrast, in Rockwell or Memphis proportion. Rendering defects: section 7",
    W: 108, nib: 0, thin: 0.74, pow: 1, xs: 1.04, swell: 0, track: 4,
    ends: { s: "serif", t: "butt", u: "butt", "": "disk", x: "exit" },
    serifLen: 0.5, serifH: 0.85, serifBracket: 0, serifGrow: 0.6, dot: 0.6, overshoot: 10,
    hzThin: 0.94, roundGain: 1.03, diagThin: 0.96 },

  // Grotesque: near-uniform stroke, flat apexes, horizontal terminals, level-cut joints.
  { id: "grot", name: "Grotesque", from: "A near-uniform stroke, flat apexes, terminals cut across the stroke",
    desc: "Partly (2026-11-25): A monoline neo-grotesque with level-cut joints and a straight-leg R; the double-storey g with its sharp ear and the hooked a read humanist, which needs skeleton work. Seen after the cut default was fixed (section 7). The cut terminals were re-read on 2026-11-25 after the 0.11.0 clip: no spike, and a small step where a curved terminal meets its cut corner on t, f and J (section 7)",
    W: 100, nib: 0, thin: 1, pow: 1, xs: 1.0, swell: 0, track: 2,
    ends: SANS_ENDS, dot: 0.55, overshoot: 10,
    hzThin: 0.92, roundGain: 1.04, diagThin: 0.95, xh: 540, joints: true, crotch: 0.3 },

  // Geometric: the grotesque with the textbook x-height, wider rounds and a lighter pen.
  { id: "geometric", name: "Geometric", from: "Circles and squares, a monoline stroke, an even colour",
    desc: "No (2026-11-25): A wide humanist sans, not Futura-like: it needs a circular O, a single-storey a and pointed apexes, all unbuilt. The cut terminals were re-read on 2026-11-25 after the 0.11.0 clip: no spike, and a small step where a curved terminal meets its cut corner on t and f (section 7)",
    W: 92, nib: 0, thin: 1, pow: 1, xs: 1.08, swell: 0, track: 4,
    ends: SANS_ENDS, dot: 0.55, overshoot: 10,
    hzThin: 0.92, roundGain: 1.04, diagThin: 0.95, xh: 500, joints: true, crotch: 0.2 },

  // Reverse contrast (French Clarendon): thin verticals, thick horizontals, heavy unbracketed slabs.
  { id: "reverse", name: "Reverse contrast", from: "Thin verticals, thick horizontals, heavy slabs",
    desc: "Partly (2026-11-22): Reverse contrast, but light, at typewriter weight; a larger W and a lower thin might reach a French Clarendon (untested). Rendering defects, and a lump where the bowls of P, B and R meet the thin stem: section 7",
    W: 100, nib: 90 * DEG, thin: 0.4, pow: 1, xs: 1.0, swell: 0, track: 4,
    ends: { s: "serif", t: "butt", u: "butt", "": "disk", x: "exit" },
    serifLen: 0.6, serifH: 0.85, serifBracket: 0, dot: 0.55, overshoot: 10 },

  // Optical sizes (the metal lesson): two cuts of one design. The text cut is wider, taller, lower in
  // contrast and looser; the display cut is the reverse. xh differs per cut (item 4).
  { id: "opsz-text", name: "Optical size, text cut", from: "The small-size cut: wider, taller x-height, less contrast, looser",
    desc: "Reaches (2026-11-22): As a pair: a wider, looser text cut with a taller x-height beside a narrower, higher-contrast display cut. The display cut is close to the Didone",
    W: 100, nib: 0, thin: 0.55, pow: 1.3, xs: 1.0, swell: 0.02, track: 6,
    ends: SERIF_ENDS, flareLen: 90, flareAmt: 0.2,
    serifLen: 0.7, serifH: 0.4, serifBracket: 1, dot: 0.5, overshoot: 10, beak: true, tear: false, xh: 540 },
  { id: "opsz-display", name: "Optical size, display cut", from: "The large-size cut: narrower, lower x-height, more contrast, tighter",
    desc: "Reaches (2026-11-22): As a pair: a wider, looser text cut with a taller x-height beside a narrower, higher-contrast display cut. The display cut is close to the Didone",
    W: 104, nib: 0, thin: 0.3, pow: 1.9, xs: 0.92, swell: 0.02, track: -8,
    ends: SERIF_ENDS, flareLen: 90, flareAmt: 0.2,
    serifLen: 0.9, serifH: 0.2, serifBracket: 1, dot: 0.5, overshoot: 10, beak: true, tear: false, xh: 480 }
];
if (typeof module !== "undefined") module.exports = CONCEPTS;
