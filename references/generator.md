# The generator: scripts/gen.js, parameter by parameter

WHAT IT'S FOR: the reference for writing and tuning a concept. Every outline in a face built with
this skill comes from `scripts/gen.js`: a letter is a centre-line skeleton, and `strokePolys()`
strokes it with a broad-nib width model, adds the terminals and the serifs, and records which
branch each stroke took. A concept is one parameter set; a weight is the same concept with `W`
multiplied. Read this file when you write `concepts.js`, when a review round asks for a change
and you need to know which knob moves what, when the exporter refuses two masters as
incompatible, or when a character the site needs has no skeleton. Every statement here was
checked against `scripts/gen.js`; where the precedent records and the code differ, the code wins.

Contents

1. Vocabulary
2. The skeleton grammar
3. The pen model
4. Every parameter: range, effect, interactions
5. End modes
6. What interpolates linearly and what does not
7. The vertical fit
8. Spacing and kerning
9. The italic
10. Adding a skeleton or a composite rule for a missing character
11. The concepts.js format and what params() refuses
12. The branch record, and why the exporter refuses masters
13. Designed, not built: `apex`

## 1. Vocabulary

The generator is a pen drawn along a skeleton with masters interpolated between weights, the family of
Metafont and of multiple-master fonts. Two standard criticisms of that family, skeleton-first letters that read
as mechanical and a parameter set large enough to tune instead of draw, are the risk the review loop exists to
catch; `references/genres.md` states which genres it reaches.

- **Skeleton** — a glyph's list of centre-line strokes in a 1000-unit em (baseline 0, x-line 500,
  cap height 700, ascender 740, descender −230; the concept's `xh` moves the x-line of the lowercase, section 7). Its role: the one drawing per letter that every
  concept and weight shares.
- **Concept** — one parameter set (`id`, pen, ends, transforms). Its role: a whole cut. The
  project keeps its concepts in `concepts.js`.
- **Master** — a concept drawn at one `mult` (so `W = concept.W × mult`) at one axis location. Its
  role: a corner `varLib` interpolates between. `export.js` draws every master of a group.
- **Group** — the masters that go into one variable font file (`roman` or `italic`). Roman and
  italic skeletons differ in structure, so they are separate groups and separate files.
- **Branch record** (`g.sig`) — the outcome of every geometry-dependent decision a stroke took,
  as a string per stroke. Its role: the exporter refuses masters whose records differ, because
  equal point counts alone do not prove the points are the same feature.
- **Pinned sampling** — the number of sample points per skeleton segment is computed once from
  the unfitted skeleton (`sampleCounts`) and reused for every master. Its role: identical point
  counts across masters, which `varLib` needs.

## 2. The skeleton grammar

```js
S(d, a, b)      // one open stroke: d is an SVG-like path "M x y L x y C x1 y1 x2 y2 x y ..." (absolute,
                // only M, L and C), a and b are the end types of its start and end
D(x, y)         // a dot (the i and j dots, punctuation, diaereses)
ring(cx, cy, rx, ry)   // a closed oval of four cubic curves; the o, O, 0, the bowls of 6 8 9 %, ©
```

End types are single letters chosen by the skeleton author:

| Letter | Meaning | Typical mode in `ends` |
|---|---|---|
| `s` | a stem end that takes a serif | `serif` |
| `t` | a free terminal | `flare`, `cut`, `taper`, `curl`, `butt` |
| `u` | a quieter free terminal (used where a full drop reads as a dot) | `flareS` |
| `x` | an italic exit stroke, or a stem too short for a serif (the top of the roman `t`) | `exit` |
| `j` | a plain square end, usually hidden inside another stroke | left unmapped |
| `""` | a hidden join: the stroke continues into another stroke | `disk` |
| `i` | a T-join: the stroke ends **on another stroke's centre line**, at an interior point of it, and is cut parallel to that stroke there, so the whole end is buried inside it; no terminal, whatever the `ends` table says. The `R`'s leg (since 0.5.0). `glyph()` throws if the end meets another stroke's END (that is a joint, type it `""`), lies on no stroke's interior within 2 units, runs within 14.5° of the stroke it meets, would need a cut longer than `cutSide`'s clamp (unreachable: the angle refusal bounds the reach at 1.87 widths), or whose cut crosses an edge of the stroke it meets as drawn or has its midpoint outside it (the burial check, exact: it refuses an end so near that stroke's end that the cut cannot fit, a partner so tightly bent between the corners that the cut's middle leaves it, and a dip of the partner's edge however narrow); the stroke met must come earlier in the skeleton, so its polygons exist to check against. A mistyped end fails every master instead of drawing a square end quietly | never mapped |

A concept's `ends` table maps each letter to a **mode** (section 5). An unmapped letter draws a
plain square end: the stroke body stops at its last sample with no terminal polygon and no width
change. No shipped table maps `j`, which is how `j` means "square". `i` is handled before the table
is read.

Three ways a stroke end can meet another stroke, and the construction each gets: two ENDS within 2
units make a **joint or corner** (next paragraph: a level or plumb cut, or a run-out to the partner's
far edge); an end on another stroke's INTERIOR typed `i` is a **T-join** (cut parallel to that stroke
on its centre line, buried); an end typed `""` inside a thicker stroke is a **hidden join** (its
`disk` cap hides inside the stroke it meets). The hidden join is wrong where the stroke met is
thinner than the cap: the `R`'s leg on the bowl's thin bar drew its disk into the counter, 15 to 36
units on Bract's masters, until 0.5.0 (`references/traps.md` row 36; the plan and its measurements are
`docs/plan-r-leg.md`).

Roman skeletons live in `G` (131 keys as of this writing, counted with `Object.keys(m.G).length`):
A–Z, a–z, 0–9, the punctuation real titles use (`. , ' : ; ! ? - – — … [ ] / ( ) % $ # + * &`),
the ligatures `fi fl ff`, accented lowercase vowels, `ñ ç š ā`, the capitals Á À Â Ä É È Ê Ë Í Ï Ó Ô
Ö Ú Ü Ñ Ç, and `© ™ •`. Italic overrides live in `GI` (47 keys); anything not in `GI` is the roman
skeleton slanted. The straight tick, double quotes and opening quotes are **not** skeletons: the
builder derives them from the apostrophe (`'`, which is drawn curly).

Two shared points make a **joint**: when a stroke's end lies within 2 units of another stroke's
end, `glyph()` records the partner (stroke index plus end, e.g. `0b`) and the direction the
partner leaves in. `strokePolys` then cuts the joint level or plumb instead of drawing a terminal
(the points of V, W, A; the corners of E, F, L, Z, the spur of G). The joint logic applies to
concepts whose `s` end is `serif` and to concepts that set `joints: true` (section 4); any other concept
keeps its own round or cut ends at joints (for a sans concept the V's apex is then two stroke ends,
each capped by its `ends[""]` terminal, `disk` in every shipped sans concept).
The glyphs whose records carry a joint end are `1 4 5 v w A M N V W`, the circumflex and caron marks
and `™`; `y` and `k` have none (their strokes cross or start mid-stroke).

At a **corner** (two ends within 2 units, one steep and one shallow) the steep stroke runs out to the partner's far
edge and is cut level. Since 0.10.0 the shallow stroke runs out to the partner's far edge and is cut **along the
partner's drawn end direction**, where 0.9.0 cut it plumb whatever the partner did. The cut is exact for a straight
partner. For a curved partner (the `2`, where the bar meets the bowl's end; the `e`, where the bar meets the bowl's
start) it follows the partner's tangent at its end, and the partner's edge curves away from it: the `2` falls from
12.5 to 51.2 units of tooth to 1.6 or less on every example concept, while the `e` of the unshipped round-1 concept
`blind` rises from 4.9 to 6.2 at mult 1.5 and from 5.5 to 7.7 at 1.65. With a plumb partner the direction is exactly
`[0, 1]` and the 0.9.0 cut runs, so a plumb corner (`E F L [ ] fl`) is the same bytes. The 1.6 units that remain on a
swelled stroke are the swell (`references/traps.md` row 36).

## 3. The pen model

For a sample point whose tangent direction is θ:

```
f = thin + (1 − thin) · |sin(θ − nib)|^pow        the nib: full width perpendicular to the nib angle
w = W · f · o · m                                    o: the optical factor below (1 with no knob set); m: the modifiers
```

**The width law is one function, `penWidth(θ, P, cw)`.** The stroke samples, the corner a stem runs
out to (the corner pass of `strokePolys`) and the vertical fit (`hwFlat`, section 7)
all call it, so they cannot disagree about how thick a stroke is. With no optical knob set it returns
`f` unchanged: the code path is the 0.1 expression, and the three example fonts rebuild to the same
bytes (`tests/test_backward_compat.py`).

**Optical corrections** (`hzThin`, `roundGain`, `diagThin`; all default 1, which is off). A
mechanical pen model draws a level bar, a curve and a diagonal at exactly the width the law gives,
and the eye reads a level bar as heavier than a plumb stem, a curve as lighter than a straight
stroke, and a diagonal as heavier at a crossing. With any of the three set, `f` is multiplied by

```
o = (1 − (1 − hzThin)  · cos²θ)        level strokes: cos²θ is 1 level and 0 plumb
  · (1 − (1 − diagThin) · sin²2θ)      diagonals: sin²2θ is 1 at 45° and 0 level or plumb
  · (1 + (roundGain − 1) · cw)         curves: cw is the curvature weight, 0 to 1
```

so a plumb stem is untouched by the first two factors and a straight stroke by the third. The
factors are independent: at 51° (an `x` stroke) both thins apply, `hzThin` at cos²θ ≈ 0.39. They do
not grow with the weight (`thinGrow` does not touch them).

- **Curvature weight `cw`.** A ring (a closed stroke) has `cw` 1 by definition. For an open stroke,
  `cw = min(1, κ · 2.5 · W0)` at each sample, where `κ` is the turning angle at the sample divided by
  the mean length of its two chords; the end samples take their neighbour's. A curve of radius
  `2.5 · W0` (250 units for `W0` 100) or tighter takes the whole gain, a radius-500 curve half, a
  straight stroke none. This is why the gain is weighted per sample and not applied per stroke: the
  `n`'s arch and its right stem are one stroke (section 2), and a per-stroke flag would thicken the
  stem. **The 2.5 (`ROUND_GAIN_RADIUS` in `gen.js`) is a design constant with no source behind it**;
  the sources say only that round strokes look lighter than straight ones. Judge it on a render and
  change it there if a project needs another reach. Measured on the neutral example (monoline, nib 0,
  `overshoot` 10): the fit pulls a thick `c` so far inward that its tightest radius is about 420
  units, so the largest weight reached is about 0.6; without the fit (`overshoot` 0) the same `c`
  reaches 1. A heavy monoline concept therefore gets less of the gain than its `roundGain` suggests.
- **The branch record does not change.** Every decision that enters it (`curved`, the teardrop side,
  the serif kind, the joint and corner tests) reads tangents and partner directions, not widths, so
  a master with one value and a master with another stay compatible and the knob interpolates.
  The fold pin may pin different points; point counts and edge runs do not change.
- **The hairline is no longer `W × thin`.** The thinnest stroke is the minimum of
  `W · f · o` over every direction in the glyph, which has no closed form worth printing (`thin 1`
  with `diagThin 0.5` is `0.5·W` at 45°; `nib 0` with `thin 0.5` and `hzThin 0.9` is `0.45·W` level).
  Take it from the first export's `minStrokeWidth`, which `export.js` measures per master and
  `build.py` recomputes from the polygons; the build refuses a master below its pinned
  `hairline_floors`. A concept that adds any of the three knobs re-reads the export and re-pins its
  floors. A concept whose thin direction is level loses hairline margin under `hzThin`; the floor
  refusing that build is the floor doing its job.

The modifiers `m` (open strokes only unless stated):

- **End modifiers** (`endMod`) for the two ends' modes: `exit` thins to 50 % at the tip over
  0.9·W0; `flare` (only with `tear: false`) swells by `flareAmt · u²` over `flareLen`; `taper` thins
  by 62 % over `taperLen` with exponent 1.3; `curl` thins by 45 % over the curl's own length.
- **Join taper** (`tap`): a curved stroke whose end is a `disk` with no partner, or a T-join (`i`),
  thins by 30 % over 0.9·W0, so a join runs into its stem without a nub (the italic `R`'s curved leg
  keeps the taper it had as a hidden join; the roman leg is straight and never had one).
- **Swell**: `1 + swell · (0.5 − sin(π·s/total))`: the middle of each open stroke is thinner by
  `swell/2`, the ends thicker by `swell/2`. With `swell 0.03` the measured minima sit 1.5 % under
  `W × thin`, which is why the shipped floors are a unit under the nominal hairline.
- **Wobble** (`wob`): a deterministic ripple seeded by the character code and sample count. Both
  shipped faces use 0.
- **Teardrop** (`tear: true`): over the last 1.1·W0 of a free curved end, the outer edge swells by
  `0.55 · dk · wk · dropK · e` and the inner edge thins by `0.28 · dk · dropK · e`, with
  `e = u²(3 − 2u)` a smoothstep, `dk = dropAmt / 0.55`, `wk = (W0/W)^1.5` so a heavier master's
  drop swells less, and `dropK` 0.5 for `flareS`. A symmetric end (`S`) swells both edges by
  `0.3 · dk · e`. `dropAmt` therefore scales all three constants together (review finding F005).

Then the left and right edges are the centre line offset by `wl/2` and `wr/2`, the **fold pin**
runs (any edge point that would step against the centre line's direction is pinned to the point
before it, so a bend tighter than half the stroke width cannot fold into a loop; point count
unchanged), and the stroke body becomes one polygon of `2n` points with two **edge runs**
(`[0, n−1]` and `[n, 2n−1]`). Terminal and serif polygons are appended, each its own edge run.

When the concept sets `headSink` (0.9.0), the **head sink** runs next, on the same two edges: at each end that takes a lowercase head serif, the
run of points that lies above `y − headSink × h` is pinned down to that line (section 4). The point count does not change. The spacing profile is
measured on the body as it was before the sink (section 8).

**Pinned sampling.** A line gets `max(2, ceil(length/3))` points and a curve
`max(4, ceil(controlPolygonLength/3))`, computed from the unfitted skeleton, so the count is the
same for every master of a glyph. A ring's repeated closing point is dropped at the source,
identically in every master. Expect about 156,000 points per master before decimation for the
full roman set (measured on the Bract and Example configurations with `scripts/export.js`).

**Minimum interior stroke width** (`g.minw`): the smallest of `wl`, `wr` over samples further
than `max(1.1·W0, 0.9·W0)` from either end of an open stroke (all samples of a ring), so a
terminal's deliberate thinning is not reported as a hairline. The exporter records the minimum per
glyph and per master; the builder compares it with the group's `hairline_floors`.

## 4. Every parameter: range, effect, interactions

Required: `id`, `W`, `ends`. Everything else is optional; an unset numeric knob behaves as 0 or
"off" except where a default is named.

| Key | Type / range seen | Effect | Interactions and cautions |
|---|---|---|---|
| `id` | string, unique in the file | names the concept; masters in font.json refer to it | `params()` throws without it; `loadConcepts()` throws on a duplicate |
| `name`, `from`, `desc` | strings | labels for the concept pages | ignored by the generator |
| `W` | 88–114 units | pen width of the Regular (`W0`); a master's `W` is `W0 × mult` | must be > 0; `W0` is kept on `P` and drives every "follows the Regular" rule below |
| `nib` | 0–40° (write `12 * DEG`) | the angle of the pen edge: a stroke along the nib direction is thinnest; perpendicular to it, full width. `nib 0` = vertical stress (horizontals thin); larger values tilt the stress | `hwFlat` (the vertical fit) uses `sin(nib)`, so a change of `nib` moves every flat stroke's fitted position |
| `thin` | 0.27–0.82 | the thinnest stroke as a share of `W` (1 = monoline) | the hairline in units is `W × thin`, less `swell/2`, until an optical knob is set (then it is the smallest `minStrokeWidth` the export reports; section 3); see `thinGrow` |
| `thinGrow` | 0.5–0.6, or unset | with it, `P.thin = thin × mult^(thinGrow − 1)`, so hairlines grow as `mult^thinGrow` instead of in proportion to stems | unset means hairlines thicken as much as stems: Bract round 2 found the Bold's contrast collapsed and it read as another family (0.5 fixed it). The Bold's floor must be recomputed when this changes |
| `pow` | 1–2.4 | exponent on `|sin|`: higher makes the width fall off the thick direction faster, so more of each curve is near `thin` | raises apparent contrast without changing `thin` |
| `xs` | 0.86–1.12 | horizontal scale of every skeleton point, multiplied by `1 + 0.16·(W/W0 − 1)` so heavier masters widen slightly (×1.08 at mult 1.5), and by 0.95 for the italic | **a branch flipper between concepts, not between weights since 0.6.0**: the serif-kind test `|T[0]| > 0.1` reads the sheared tangent of the italic `w`'s first stroke, which `xs` 0.86–0.90 at 10° puts on `head` and 0.92 and above on `diag` at mult 1 (section 12 has the margins). Until 0.6.0 the test read the DRAWN tangent, so the weight widening alone moved it (the Example template's `w` read `head` at mult 1 and `diag` at mult 1.5 at `xs` 0.86–0.90, and the exporter refused the group; traps row 32); the widening still draws but no longer decides. Change `xs` and re-export every group |
| `hzThin` | 0.85–1.0 (`params()` refuses outside 0.5–1.5, bounds excluded); default 1 | level strokes are thinned by `1 − hzThin`, weighted by cos²θ (a level bar loses the whole amount, a plumb stem none) | optical correction, section 3. The vertical fit and the corner reach follow it, so a flat bar's outer edge still sits on its line. Values above 1 thicken level strokes (a reverse-contrast concept). Lowers the hairline of a concept whose thin direction is level: re-read `minStrokeWidth` and re-pin the floors |
| `roundGain` | 1.0–1.08 (refused outside 0.8–1.25, bounds excluded); default 1 | curves are thickened by `roundGain − 1`, weighted per sample by the local curvature (a ring fully, an open curve by `min(1, κ · 2.5 · W0)`, a straight stroke not at all) | optical correction, section 3. `2.5` is a design constant with no source. The fit gives a round extreme the half width of a fully weighted curve (weight 1), so a ring (the `o`) lands exactly at the line plus `overshoot` whatever `roundGain` is (measured: 510 at `overshoot` 10). **An open curve is not exact:** its weight at the extreme is below 1 (about 0.6 on the fitted `c`), so its top sits off the target by up to `hw × |roundGain − 1| × (1 − weight)`, never more than `(W/2) × f(0) × hzThin × |roundGain − 1|` (`f(0)` the pen width at a level tangent, 1 for a monoline concept; `hzThin` multiplies the gain term at a level extreme, so it enters the bound; the sign of `roundGain − 1` does not): measured on the monoline fixture the `c`, `e` and `s` tops moved by up to 2.28 units at `roundGain` 1.05 and `mult` 1.5 (bound 3.75), 5.91 at `roundGain` 0.85 and `mult` 1.5 (bound 11.25), and 4.49 at `roundGain` 1.05 with `hzThin` 1.4 (bound 5.25, where the bound without `hzThin` would be 3.75), and on the neutral example's `text` concept reduced to `nib` 0, `pow` 1, `thin` 0.6 and butt ends by at most 0.36 at `mult` 1 and 1.27 at `mult` 1.5. Fitting each sample with its own weight would be circular (the weight depends on the fitted curve) and was not built |
| `diagThin` | 0.85–1.0 (refused outside 0.5–1.5, bounds excluded); default 1 | diagonal strokes are thinned by `1 − diagThin`, weighted by sin²2θ (full at 45°, none level or plumb) | optical correction, section 3. Independent of `hzThin`: at 51° both apply. `params()` throws on a value outside the range, naming the knob |
| `xh` | 400–600 (`params()` refuses outside, bounds allowed); default 500 | the x-height of the lowercase, in skeleton units: every lowercase key (every key that is not `UPPERISH`, except the apostrophe) is drawn through a piecewise-linear y map, section 7. Capitals, figures, ascenders and descenders do not move | the range is a design range (0.8–1.2 of the body), not a compatibility bound: every branch decision is taken on the unmapped skeleton (section 12), so a legal `xh` cannot make the exporter refuse a group. The lowercase accents are compressed into the band as `xh` rises (an acute of 110 units draws about 92 at `xh` 560 and 64 at 600). The spacing band follows (section 8). Not echoed into the manifest |
| `serifBracket` | 0–1 (refused outside, bounds allowed); default 1 | blends every serif between today's bracketed form (1) and a slab (0) with **the same number of points**, so a bracket can interpolate between masters: the foot and symmetric head (26 points), the lowercase head (15) and the diagonal serif (26) | at 1 the code is the 0.1 code, unchanged. At 0 the foot is a rectangle `h` thick (`h = SW × serifH`), where the bracket climbed `1.7·h` (`1.9·h` for the lowercase head) and curved in by `0.45·h`; the controls of the slab lie on their chords. A slab wants a thin `serifH` (0.13–0.15 is a flat Scotch slab) |
| `headSink` | 0–0.7 (refused outside, bounds allowed; a string, `null`, a boolean and `NaN` are refused); default 0, off | sinks a stem end under a lowercase head serif by `headSink × h`, with `h = SW × serifH` (so `serifGrow` is included): at that end of each edge, the run of points above `y − headSink × h` is pinned to that line, and the point count is unchanged | **What it repairs.** The lowercase head's top edge slopes down to the left while the stem under it ends flat, so the stem's top-left corner shows above the wedge. Measured on the Driftwood example's `driftwood` concept (roman, 28 stem ends in 23 glyphs): the corner stands 2.81 units above the wedge at mult 1 and 4.11 at mult 1.65. The poke is `h × (0.38·t − 0.18)` with `t = w / (w + SW·serifLen − 0.5·h)` while the stem's left edge meets the straight part of the top edge, so it grows with `serifH` (the plan, `docs/plan-head-sink.md`, measured 16.8 units on `serifH` 0.85 and 22.0 on `clarendon` at mult 1.65). **How much.** 0.2 buries the poke when `serifLen >= 0.5 × serifH` (it does on the Driftwood example, measured 2026-11-21: the corner then lies 4.23 and 2.93 units under the wedge); 0.6 buries it in every concept this repository ships. **Why 0.7 is the limit.** The deepest poke the wedge can have is `0.65·h`, so 0.7 buries every case; above it the stem end can leave the serif, because the wedge's lower edge over the stem is at `y − h × (1 + 0.8 × serifBracket)`, and at `serifBracket: 0` a depth above 1 leaves a visible gap with no error. Applies to the bracketed head and to the blended one (`serifBracket` other than 1), which has the same slope scaled by the bracket; at `serifBracket: 0` the top is level and there is nothing to bury. Capitals, feet, diagonal serifs and ends that became a joint or a corner are untouched. It has no effect when no end maps to `serif`, and `params()` does not refuse it there (the same is true of `serifLen` and `serifH`). Advances, spacing profiles and kerns are those of the concept without it (section 8). Not echoed into the manifest |
| `joints` | `true` or `false` (anything else is refused); default false | gives a concept whose `s` end is not `serif` the joint and corner pass: a level or plumb cut where two stroke ends meet (`V W A M N 1 4 v w`), squared corners (`E F L Z z 2 5 7`, the spur of `G`), and no `ends[""]` terminal at those ends | read only when `ends.s !== "serif"`; a serif concept always has it. Two concepts in one group that differ in `joints` end the same strokes differently and are refused by the exporter. Judge the cut on `A V W` in the render: a level edge beside curved neighbours can read as a clipped corner |
| `crotch` | 0–0.5 (refused outside 0–0.6, bounds allowed); default 0 | at each stroke end that resolves as a **joint** between two arms meeting at an acute angle (`dot(−T_end, partner) > 0.3`: V, A, W, M, N, v, w, 1, 4, 5), the edge on the partner's side thins by `crotch × e` over the last `1.1·W0`, with `e = u²(3 − 2u)`, `u = 1 − d/(1.1·W0)` (the teardrop's smoothstep and reach). The outer edge keeps its line, so the apex stays where it was and the counter opens | the reach equals the teardrop's, so `g.minw`'s interior exclusion leaves it out and the hairline floor does not see it. A corner (`E F L`) is not a joint and does not thin. With `crotch` set, the outcome (acute or not) is recorded in the branch record of every open stroke (section 12), so two masters that disagree about an angle are refused; unset, nothing is recorded; the value itself interpolates. With `joints` off a sans concept has no joints and `crotch` does nothing; a serif concept has them always |
| `apex` | **refused**: `params()` throws | designed, not built in 0.2: a pointed apex that passes the line (section 13) | a knob that does nothing is the dead-knob shape of Driftwood issue #24, so the generator refuses it until a later version builds it |
| `swell` | 0–0.14 | thins each open stroke's middle by `swell/2` and thickens its ends by `swell/2` | lowers the measured minimum by `swell/2 × W × thin`; `track` and floors follow |
| `wob` | 0–0.02 | deterministic ripple along each stroke | 0 in both shipped faces |
| `track` | −10 to +10 units | added to every sidebearing term `T` and twice to the word space | lives in advances, not in kerning (review finding F005), so a display cut with `track −10` is tighter at every pair, including pairs no kern covers |
| `ends` | object | end-type letter → mode (section 5) | required; an italic group needs `x` mapped (normally `exit`) or exit strokes end square |
| `flareLen` | 90–100 units | reach of the flare swell | only with `tear: false` |
| `flareAmt` | 0.2–0.25 | swell at a flare tip (`1 + flareAmt` at the very end) | **dead with `tear: true`**, and `params()` throws if both are set (Driftwood issue #24). Bract's shipped 0.28 did nothing |
| `dropAmt` | default 0.55 | size of the teardrop; scales the 0.55 / 0.28 / 0.30 constants together | only with `tear: true`; `params()` throws otherwise |
| `taperLen` | 120–170 units | reach of a `taper` end | with `cut` for the tip's angle |
| `cut` | 22–40° | the angle of `cut` and `taper` ends, and the rotation of `leaf` dots | unset = 0 rad, a horizontal cut |
| `serifLen` | 0.3–1.0 | serif reach: `L = w/2 + SW × serifLen` (upright), `SW × serifLen` (diagonal, split 1.15 : 0.6 towards the open side) | ×0.6 in the italic for diagonal and symmetric-head serifs |
| `serifH` | 0.13–0.85 | serif thickness `h = SW × serifH`; the bracket climbs the stem to `1.7·h` | a flat Scotch slab is `serifH` ≈ 0.13–0.15 |
| `serifGrow` | 0.35 (0.6 was wrong), or unset | `SW = W0 × (W/W0)^serifGrow`: how much serifs grow with weight | **unset means serifs stay at Regular size in every weight** (`SW = W0`). 0.6 made Bract's Bold read as a Clarendon; 0.35 fixed it. Not linear in weight, so the interpolated Medium's serifs are not what a generated Medium would draw |
| `dot` | 0.47–0.74 | dot radius `r = W × dot` | dots scale in proportion to weight; the fit sits baseline dots at `r − 4` and x-height dots at `xh − r + 4` (`500 − r + 4` at the default); the rule reads the dot's unmapped position, section 7 |
| `leaf` | boolean | dots become ellipses `1.3r × 0.72r` rotated by `cut` | read as accents at every size on a precedent ("Guídes"); show it, do not default to it |
| `overshoot` | 10 units, or 0 | enables the vertical fit (section 7) and sets how far round extremes pass the lines | **0 or unset disables the fit entirely**: flat strokes then hang half their width below the baseline (Driftwood v1) |
| `beak` | boolean | a `flare` end on a level horizontal stroke becomes a beak serif instead | beak size follows `W0`, not `W`; the beak points up near the baseline (`y < 150`) and down near the top (`y > 450`), none on middle bars |
| `tear` | boolean | free curved ends get a teardrop built from the stroke's own two edges plus a half-round cap, instead of a ball | turns `flareAmt` off; needs `n > 30` samples on the stroke, else the swell is skipped (the cap still draws) |
| `pebble` | boolean | with `tear: false`, a flattened ellipse instead of a ball | Driftwood tried it twice; both read as lumps |
| `shear` | tan of 0–8° | `x += shear × y`: a uniform slant that is not an italic (no `GI` skeletons, no narrowing) | used by the Windswept concept; an italic uses `params(..., italic)` instead |
| `bend` | ~0.0002 | `x += bend × (y − 350)²` above `y = 350`: the lean grows toward the tops of tall letters | Windswept only |
| `wonk` | string of characters | those glyphs lean back: `x −= 0.045 × y` | Driftwood's back-lean on n/h/m "read as an error"; shipped as `""` |

`P.W0`, `P.italic`, `P.italicAngle`, `P.key` are set by `params()`, not by the concept.

## 5. End modes

| Mode | Width along the stroke | Terminal polygon | Notes |
|---|---|---|---|
| `serif` | none | `serifPoly` (foot, symmetric head for `UPPERISH` glyphs, or the lowercase one-sided wedge, whose stem end `headSink` can sink) or `diagSerifPoly` for a slanted stem; a round stroke end gets a ball. Since 0.10.0 the brackets of `serifPoly` end on the stroke's own edge (the straight line through the end's corner along the end's direction, so a stem that leans by 0.1 or less keeps its bracket on its edge), and a leaning head or foot end is cut level, as a `diag` end is | the branch record names the kind (`serifA=foot|head|diag|ball`) |
| `flare` with `tear: false` | `1 + flareAmt·u²` over `flareLen` | a ball of radius `w/2 × (1 − 0.4·(W/W0 − 1))`, so the Bold's balls grow more slowly than its stems; with `pebble`, an ellipse | the only mode where `flareAmt` matters |
| `flare` with `tear: true` | the teardrop (section 3) | a half-round cap across the end's own edges, bulging `0.5·r` along the stroke | side `L`/`R`/`S` from the curvature of the last quarter of the stroke; `|cross| < 0.03` is `S` |
| `flareS` | as `flare`, with `dropK = 0.5` | as `flare` | **one `dropK` per stroke**: if either end is `flareS`, both ends' drops halve |
| `beak` | none | `beakPoly`: height `0.95·W0`, back `0.5·W0` | reached automatically from `flare` on level strokes when `beak: true`; mapping it directly is allowed |
| `exit` | thins to 50 % over `0.9·W0`, exponent 1.2 | none | italic exit stems; the roman `t` top in Bract (a head serif there read as a flag) |
| `disk` | the join taper when the stroke is curved and has no partner | a circle of radius `0.42·w` | hidden joins (`""`); keep the cap inside the stroke it meets or it shows as a nub |
| `cut` | none | the end points move along the tangent to the line at angle `cut` (clamped to ±w) | Field, Windswept, Brush |
| `taper` | `1 − 0.62·(1 − d/taperLen)^1.3` | a 4-point tip cut at angle `cut` | Cone, Thorn |
| `curl` | `1 − 0.45·(1 − d/curlLen)` over the curl | 30 extra centre-line points continuing the stroke's turn as a spiral (radius `0.55·W + 22`, sweep 1.3π, shrinking 42 %), then a disc of `0.36·W`; needs ≥ 12 samples and curvature `|cross| ≥ 0.06`, else falls back to `disk` | the fallback is recorded (`A=disk`), so masters that disagree are refused |
| `joint` (an outcome, not a mapping) | none | none | what an end becomes when its partner's end meets it and both strokes are steep (`|T[1]| > 0.5`): cut level or plumb, no terminal. Every serif concept and every concept with `joints: true` has it; the record shows `ends=…/joint` |
| `corner` (an outcome) | none | none | the same pass where a steep stroke meets a shallow one (E, F, L, Z, the spur of G): the steep stroke runs out to the partner's far edge, cut level; the shallow stroke runs out to it too and is cut along the partner's drawn direction since 0.10.0 (plumb before) |
| `tee` (the outcome of `i`) | the join taper when the stroke is curved | none | the end is cut parallel to the stroke it runs into, through the end point on that stroke's centre line, so the cut is buried by the partner's half-thickness on both sides whatever the pen or the swell; the leg of `R`. Decided on drawn geometry per master (`cutSide` reads drawn tangents): under 14.5° to the partner, past the clamp, or with the cut crossing the partner's drawn edge or its midpoint outside the partner, the draw throws. The record reads `A=tee`, `ends=tee/…` and carries `tee=<stroke>@<segment><side>` (section 12) |
| `butt`, or any unmapped letter | none | none | a square end |

## 6. What interpolates linearly and what does not

`varLib` interpolates point coordinates linearly between masters. The generator is not linear in
`mult`, so an interpolated instance is **not** what the generator would draw at that `mult`:

- **Serifs** scale as `(W/W0)^serifGrow` (0.35 in Bract), stems as `W/W0`.
- **The teardrop** scales as `(W0/W)^1.5` (`wk`) and the ball radius as `1 − 0.4·(W/W0 − 1)`.
- **Hairlines** scale as `mult^thinGrow`.
- **The fit** moves flat strokes by half the horizontal stroke width, which depends on `W`,
  `thin`, `nib` and `pow`.
- **Spacing**: `T = 30 + 0.36·W0 − 0.25·(W − W0) + track − 6(italic)` is linear in `W`, but
  sidebearings clamp at 8 and the kern formula clamps at −170 and +80, so kerns do not
  interpolate linearly either.

Consequences: review the **Medium at the smallest size** in round 1 of the concept pipeline, and
pin it with `avar` so `font-weight: 500` renders the reviewed mix (Bract: user 500 → design 580,
normalized 0.333 → 0.6, which is `W × 1.3`). An intermediate `opsz` location is a blend of two
cuts whose `xs`, `track`, `serifLen` and `thin` differ; the review loop samples it (wght 550,
opsz 60) because nobody drew it.

## 7. The vertical fit

Skeletons are centre lines, so a stroke drawn on the baseline would hang half its width below it.
With `overshoot` set, `fitSkeleton()`:

- moves **flat** strokes whose y is in `FLAT = { 0: up, 500: down, 700: down, 740: down }` inward
  by `hwFlat = W × (thin + (1 − thin)·|sin(nib)|^pow) / 2`, half the horizontal stroke width. With
  an optical knob set, `hwFlat = W × penWidth(0, P, 0) / 2`, which includes the `hzThin` factor
  (a level stroke has cos²θ = 1) and neither the diagonal factor nor the round gain, so a bar thinned
  to `0.9 W` moves inward by `0.45 W` and its outer edge still lands on the line; a round extreme takes `W × penWidth(0, P, 1) / 2`, which adds the full
  `roundGain`, so a ring's top overshoots by exactly `overshoot` and an open curve's by `overshoot` within `(W/2) f(0) hzThin |roundGain − 1|` (section 4);
- moves **round** extremes whose control-point y is in
  `ROUND = { 510 → 500 up, −10 → 0 down, 710 → 700 up, 720 → 700 up, −230 → −230 down }` so the
  outer edge overshoots the line by `overshoot`;
- moves any point that shared a moved flat point with it, **except a serifed stem end**, whose
  serif covers the joint;
- recentres rings between their fitted top and bottom.

**The x-height map (`xh`).** Skeletons are drawn with the x-line at 500 and the round overshoot at
510 / −10. With `xh` set, every key that is not `UPPERISH`, except the apostrophe, goes through
`ymap` inside `fitSkeleton()` before the flat and round fits (a project without the fit, `overshoot` 0,
still gets its x-height):

```
y ≤ 0:          y                                    descenders unchanged
0 < y ≤ 500:    y · xh / 500                          the body scales, 0.8 to 1.2
500 < y < 740:  xh + (y − 500) · (740 − xh) / 240     the band to the ascender, 1.42 at xh 400 to 0.58 at 600
y ≥ 740:        y                                    ascenders unchanged
```

The mapped set is the lowercase, its accented forms, the ligatures and `. , : ; - – — … •`. The
apostrophe stays where it is drawn, because an apostrophe sits near the cap height in any face and
the builder derives the six quote glyphs from it. The `FLAT` and `ROUND` tables keep their literal
keys (a point AT 500 is "on the x-line"; a `C` control point at 510 is "the round overshoot above
it") and their TARGETS go through the map: a flat x-line stroke moves inward by `hwFlat` from `xh`,
a round top lands at `xh + overshoot`. Rings map their top and bottom and are recentred as before.
Curves whose control points straddle 500 (the `n`'s arch, the `a`'s top) are the Bézier of the
mapped control points, not the image of the curve. `t`'s and `f`'s crossbars (490) scale with the
body.

**A control or an end drawn nearer a round extreme than the fit's travel folds the centre line back.** The fit lifts a round
extreme and its control by `hwRound - overshoot` (14.3 units at the Driftwood Regular, 21.5 at the Medium, 30 at the Bold) and
leaves a neighbouring control or end where it is. When that neighbour is nearer the extreme than the travel, the centre line
runs flat or turns back after the lift, and the stroke's edges kink or fold there. Two skeletons did this until 0.10.0. The
roman `G`'s bowl ran from the extreme `(370, -10)` through a control `(560, 20)` 30 units above it: at the Medium the centre
line fell 0.01 units after its lowest point, 0.83 at the Driftwood Bold, 0.51 at the neutral Bold. The italic `r`'s arm
ended at `(380, 480)` with a control at `(360, 500)`, 10 to 30 units under the extreme the fit lowered by 24.3, 31.5 and 40
units, so the centre line humped over the control and turned 70 degrees in its last 50 units. 0.10.0 draws the `G`'s bowl through the controls
`(500, -10)` and `(610, 60)`, the second 70 units above the extreme, and runs it into the stem plumb, and ends the `r`'s arm at `(382, 450)`,
30 units lower with the same end direction. **The rule for a new skeleton, or a per-face override
(`references/generator.md`, "Per-face skeletons"):** keep every control and every end at least `hwRound - overshoot` of the
heaviest master's width (30 units at Bold on the examples) away from a round extreme the fit moves, measured along y, or
check the three-sample turn of the drawn edges on every master (`tests/joint_probe.js edges`).

The **dot rule** reads the dot's UNMAPPED position (review finding F006): a dot below 100 is a
baseline dot (`r − 4`); a dot between 380 and 460 is an x-height dot (`xh − r + 4`; the colon's upper
dot, drawn at 420); any other dot of a mapped glyph is carried by the map (the `i` and `j` dots at
680, the diaeresis at 650, the bullet at 300). With the mapped position the colon's upper dot at
`xh` 600 would read 504 and miss the rule. The **beak** side (`y < 150` up, `y > 450` down) is
decided on the unmapped end position too (section 12).

Draw new skeletons on exactly these y values or the fit will not see them. Because `hwFlat`
depends on the pen, the fitted skeleton differs per master; the sample counts do not, because
they come from the unfitted skeleton.

## 8. Spacing and kerning

**Sidebearings.** Each glyph's left and right profiles are measured in 54 bins of 20 units from
y = −260. Over the bins between the baseline and the top (`xh`, 500 unless the concept sets it, or 700 for `UPPERISH` glyphs: capitals,
figures and the punctuation that stands cap-high), the mean edge depth `mL`, `mR` is taken with
each bin's depth capped at `0.2 × top`. Then

```
T   = 30 + 0.36·W0 − 0.25·(W − W0) + track − (italic ? 6 : 0)
sbL = max(8, T − 0.5·mL)      sbR = max(8, T − 0.5·mR)
adv = (maxX − minX) + sbL + sbR
```

so heavier weights get less extra space than their stems grow, or the Bold looks letterspaced.
The word space is `210 + 0.3·W + 2·track` (the exporter emits it per master).

**With `headSink` set** (section 4), the profile of each stem body is measured on the body as it was before the sink, so advances, sidebearings and
automatic kerns equal the concept's without the key (checked in `tests/test_head_sink.py` on the Driftwood example's `driftwood` concept, roman and italic,
and on a built face; in the font suite on a synthetic concept. The sweep over every shipped serif concept checks the outline only). That is the exact
guarantee. It is not a claim that the profile follows the sunk outline: the profile reads polygon points and the wedge has none along its long right edge, so
the sunk body would read as a notch there although no ink moved.

**Spacing is read from `prof`, the polygon as 0.9.0 cut it (0.10.0).** `glyph()` measures a polygon's profile from its `prof` when it has
one, else from its points. Since 0.10.0 three constructions carry a `prof`: the head sink (the body before the sink, as in 0.9.0, or
the body as 0.9.0 cut its ends when one is cut differently now), a stroke body with a corner cut along a slanted partner or a
leaning serif end cut level (the body cut as 0.9.0 cut it), and a head or foot bracket on a leaning end (the same bracket
drawn on a plumb stem, `serifPoly(p, [0, +-1], ...)`). Without it the italic group's band (the 20-unit bins between the
baseline and the x-height or cap line) would read a moved corner as a different edge: measured without `prof`, the italic `Z`
lost 47 units of advance at mult 1.3 and the italic `z` 57 at mult 1.5. **The exact guarantee:** for every glyph except `G`
and the italic `r`, whose skeletons were redrawn, the advance and the two 54-bin profiles are the values 0.9.0 computes. Every
automatic kern of a pair that has neither `G` nor (in an italic group) `r` in it is too. A pair with `G` on the right in a roman
group is the exception that `tests/test_joint_spacing.py` found: its unrounded kern moves by up to 0.036 units (639 pairs over
the three examples, 1 of them rounding to another integer), because the pair reads the `G`'s left profile, which the redrawn
bowl's new sample points shift. After rounding, the exported kerns that change are those that
`tests/test_serif_joints.py::test_only_the_named_glyphs_changed_since_0_9_0` admits. It is not a claim that the profile follows the
ink: at those ends the ink differs from the profile by the corner triangle or the bracket sliver that moved, up to 24.3 units (the
roman `Z`'s tooth).

**Automatic kerning** (`kern(a, b)`): the pair's mean gap over the shared band is compared with
the reference pair's (`H|H` for two uppers, else `n|n`), over the same band: 700 when either glyph is `UPPERISH`, else `xh`; when it exceeds the reference by more
than 8, `k = −0.75 × (excess − 8)`, clamped at **−170**; a **sparse** pair, where either glyph has
ink in under 35 % of the band's bins (a hyphen, a dash, a period, a quote), is capped at
`kerning.sparse_cap` (default **−50**; `null` switches the cap off), because its mean gap is measured
at one height only and runs away (the hyphen before `S` in "Eighty-Seventh" hit −170 and crowded the
S in a cold dry run of this skill; trap 34). Bract sets `null`: its kerning was reviewed before the
cap existed (`.|Y` −102 at Regular and −149 at Bold), and taking the cap would change its reviewed
spacing, which is a design change and not a build fix; then
`k ≥ minClear − minRaw` with `minClear = 14 + 0.05·W` so no pair closes under the clearance; then
clamped at **+80**. Pairs of two figures are skipped (figures keep their own spacing). The automatic
pass never sees the word space, so a letter whose ink sits far left of its advance at the baseline
(`f`, whose arm sets the advance) leaves a wide gap before the next word; that is a `kerning.space`
pair (`["f", " ", -25]` in the neutral example; trap 35), not a generator change.

**What the exporter emits.** `kerning.set` in font.json is a regex over single-character keys
(ligatures always join). A pair enters the list when `|auto| ≥ kerning.threshold` (12 in Bract,
8 in Driftwood) in **any** master; then **every master carries its own value, zero included**,
so the GPOS structure interpolates. `kerning.hand` replaces the automatic value (`"f|f": 0`
suppresses a pair); `kerning.space` adds word-space pairs the automatic pass never sees; an italic
group adds `italic_hand` and `italic_space`. The exporter throws if a hand pair or a title names a
glyph the generator lacks. Bract emitted 4,100 pairs; the Example template 4,186.

**Ligatures** `fi fl ff` are substituted by `keysFor()` when `liga` is on, and by the builder's
`liga` feature in the font.

## 9. The italic

`params(concept, mult, italic)`: `italic` is `false`, `true` (10°) or the slant in degrees.
`P.italic = tan(angle)`, `P.italicAngle = angle`. With it:

- `glyph()` prefers `GI[key]` over `G[key]`. `GI` holds the lowercase that differs in structure
  (single-storey `a`, `f` with a descender, stems that leave the baseline in an exit stroke:
  a d h i l m n r u, v w y k e, the ligatures) and the capitals with diagonals or a free foot
  (A T W M R K V U N Y J). Everything else is the roman skeleton slanted.
- `xf()` multiplies x by 0.95 (a narrower set) and adds `P.italic × y` (the shear).
- Serif length is ×0.6 in `diagSerifPoly` and for symmetric heads in `serifPoly`. An italic stem serif comes
  through `diagSerifPoly` when the stroke's reference lean `|T[0]|` is over 0.1 (`serifKind` gives `diag`). **A stroke that leans
  by 0.1 or less takes `serifPoly`** (kind `head` or `foot`), and since 0.10.0 its brackets follow its edge. Measured over
  every key of `G` and `GI` and every serif concept of the three examples, roman and italic at 10 degrees: the italic `w`
  (first stroke, start; lean 0.085 to 0.126, so 8 of the 12 serif example concepts: the `w` of `blind`, `cone` and the
  neutral `text` and `display` is `diag`), the italic `W` (0.034 to 0.115, all 12) and the roman `M` (0.025 to 0.034, all 12).
  Nothing else. An italic slanted by less than 5.7 degrees would put every stem in this list. Driftwood once shortened serifs in
  `serifPoly` only and saw no change on a `diag` stem.
- Sidebearings are measured over the band between the baseline and the x-height or cap height
  only (`cMin`/`cMax`), so `f` hooks and tails overhang their neighbours instead of being spaced.
  `J`'s descender hook may hang only 90 units into the previous letter's space. The apostrophe is
  spaced by the same band, and its tail ends at y 505 with a flare whose ink dips below the x-line, so
  the band sees only the tail's foot and the sheared body above it runs 30 to 53 units past the advance
  on the examples' italic masters (measured 2026-11-19). For the apostrophe and the closing quotes
  that overhang is the italic's normal behaviour (a space or punctuation follows). An opening quote is
  followed by a letter, so since 0.6.0 the builder gives an italic group's `quoteleft` and
  `quotedblleft` the advance `max(the apostrophe-derived advance, round(xMax + max(xMin, 0)))` of their own
  ink: the right side bearing is never negative, and equals the left wherever that value sets the advance (`build.py` `quote_glyphs()`; `variable-font-build.md`
  section 9). The roman quotes lie inside their advances in every example master and are untouched.
- `T` loses 6 units.
- A concept used for an italic must map `x` in `ends` (normally `exit`).
- The italic `w` of a narrow concept (its first stroke takes the `head` kind, section 12) is the one italic end that draws the lowercase wedge, and so the one
  that `headSink` sinks. Measured on the Driftwood example: with `headSink` set, `w` is the only italic glyph that changes.

Roman and italic are separate groups and separate font files; there is no `ital` axis, because
the skeletons differ in structure and could never be point-compatible. Status: the italic path is
pipeline-tested (compatibility, folds, hairlines, build) in the skill's smoke run on the neutral
example; **no shipped font has been design-reviewed through it**. Driftwood's shipped italic came
from the earlier static CFF pipeline.

## 10. Adding a skeleton or a composite rule for a missing character

`export.js --requirements requirements.json` fails before drawing anything when a character in
`required_characters` has no skeleton, naming each code point (review finding F011). Space, NBSP
(when `nbsp_to_space` is on), `’`, `'`, `‘`, `"`, `“` and `”` are not reported, because the builder
maps or derives them from the apostrophe.

To add a character:

1. **A new skeleton.** Add `G["@"] = [S(...), ...]` with coordinates on the standard lines
   (section 7) and end types from section 2: in a project, in the face's `skeletons` file (section
   "Per-face skeletons", below); in the skill's own repository, in `G` itself. Decide joints by placing stroke ends within 2 units
   of each other. If the italic needs its own form, add `GI["@"]`; otherwise the roman is slanted.
2. **A composite rule.** Accented letters are the base skeleton plus a mark:
   `G["ő"] = G.o.concat(acute(290))` for lowercase marks (`acute`, `grave`, `circ`, `diaer`,
   `tilde`, each centred on the base's x from `BASES`), and
   `G["Ő"] = G.O.concat(raise(acute(CAPS.O), 170))` for capitals (the lowercase mark raised 170).
   `DOTLESS_I` is the `i` stem without its dot, for `í ì î ï`.
3. Add the character to `font.json` `charset.required` and to `requirements.json`
   `required_characters` **and** `cmap`, so the cmap test pins it.
4. Re-export every group: a new skeleton must take the same branches in every master. Check
   `UPPERISH` if the glyph should space and serif as a capital (symmetric head serifs, cap-height
   band).
5. Add it to a title in `font.json` `titles` if real content uses it, so the kerning test lays it.

A character the site needs but the design cannot carry (a literal `**Update**` rendering an
asterisk) is an operator decision: fix the content or carry the glyph. Bract fixed the content
and carried `*` anyway.

## 11. The concepts.js format and what params() refuses

`concepts.js` is a CommonJS module exporting a non-empty array of concept objects; in a concept
page the same file is spliced in as a script that leaves a global `CONCEPTS`, which is why it is
JavaScript and not JSON (angles are `12 * DEG`). `loadConcepts(file)` throws on an empty array and
on a duplicate `id`; `conceptById(list, id)` throws naming the ids it has.

`params(concept, mult, italic)` throws, so a dead knob is a loud error rather than a silent no-op,
on:

- a concept with no `id`;
- a concept with no `ends` table;
- `W` not > 0, or `mult` not > 0;
- `flareAmt` set together with `tear: true` ("flareAmt has no effect with teardrop terminals, set
  dropAmt instead");
- `dropAmt` set without `tear: true` ("dropAmt only sizes teardrop terminals");
- `apex`, set to anything ("apex is designed but not built in 0.2"; section 13);
- `joints` that is not a boolean, or `crotch` that is not a number from 0 to 0.6 (the error names the knob and the range);
- `xh` that is not a number from 400 to 600, or `serifBracket` that is not a number from 0 to 1 (the
  error names the knob and the range);
- `headSink` that is not a number from 0 to 0.7 (the error names the knob and the range; a string, `null`, a boolean and `NaN` are refused too);
- `hzThin` or `diagThin` that is not a number strictly between 0.5 and 1.5, or `roundGain` not
  strictly between 0.8 and 1.25 (the error names the knob and the range; a string and `null` are
  refused too).

It does **not** throw on an `ends` table missing a letter a skeleton uses; that end draws square.

**Compatibility promise, exactly.** A project on 0.1 to 0.4 that copies 0.5's `scripts/` over its own and rebuilds, without touching `concepts.js` or
`font.json`, gets the same outlines and tables (decoded TTF, export JSON and manifest figures) as before **except the glyph `R`**, whose leg root is
redrawn in 0.5.0 (the hidden-join disk gone, the end cut level on the bar's centre line; every other point of `R`, its advance, its spacing profile and
its kerns unchanged: `tests/test_r_leg_join.py::test_only_the_r_changed_since_0_4_0` holds that against the 0.4.0 generator read from git). From 0.5.0
the three examples' digests are held to the 0.5.0 record (`tests/fixtures/baseline.json`, whose `supersedes` entry names the 0.1.0 record and that one
departure), and a later change that moves them is a regression unless its changelog says otherwise. The promise is **per platform and node major
version**: the generator's floating-point output depends on both, so the digests are keyed `darwin/26`, `linux/22` and so on, and a platform that is
not recorded has no promise until it is recorded from the baseline commit. The raw woff2 bytes are a separate claim, also per brotli version. The branch
record is not part of it; it gains tokens (section 12), and only a curl end (`curlsg`), a set `crotch` or a T-join end (`tee`) writes one.

0.6.0 adds the optional `skeletons` key (section "Per-face skeletons"); a project without it builds to the 0.5.0 digests, held by the same
unchanged fixture. A project with it differs from one without in the override's record (two export fields, one manifest key, the sixth
source hash and `font.json`'s own hash) and in whatever the override draws.

**0.7.0, exactly.** A project on 0.1 to 0.6 that copies 0.7's `scripts/` and rebuilds without touching `concepts.js` or `font.json` gets the
same outlines and tables as before, **except the advances of `quoteleft` and `quotedblleft` in an italic group**, which grow to hold the slanted
ink, the right bearing never negative (section 9; no outline, no other advance and no kern moves: `tests/test_weight_decisions.py::test_only_the_italic_opening_quotes_changed_since_0_5_0`
holds every glyph's compiled outline, GPOS and every other advance of every example group to the 0.5.0 build, and the export JSON of every
group is byte-identical), **and with one condition on the generator's decisions**: since 0.7.0 every branch decision reads the geometry at
mult 1 and xh 500 of the master's OWN concept (section 12), so a master's record is that concept's mult-1 record. A group whose every master
keeps its decisions under that reset gets identical output; every shipped group does, because each has a mult-1 master per concept whose
heavier siblings the exporter had already required to agree with it. A group whose masters all sit at a multiplier other than 1, or that
mixes concepts so that one concept has no mult-1 master in the group, may see a decision move to the mult-1 one; none of the examples is such
a group (the bract example's `text` at mult 1 beside its `display` at mult 1.5 is exported before and after in
`test_a_mixed_concept_group_without_a_mult_1_master_per_concept_exports_as_0_5_0_did` and does not move). The promise covers the decisions the
rule moved (section 12 lists them); a T-join's pinned edge still reads the drawn geometry and can still differ between weights (section 12). From
0.7.0 the three examples' digests are held to the 0.7.0 record (`tests/fixtures/baseline.json`, `supersedes` naming the 0.5.0 record `788760d`
and this departure).

## 12. The branch record, and why the exporter refuses masters

Each stroke's record reads like
`open n=176 A=serif B=disk curved=false tap=00 tear=null/null joins=-/1a ends=serif/joint serifA=head`:
open or ring, sample count, both end modes after `flareS`/`beak`/`curl` resolution, whether the
stroke is curved (any sample more than 3 units off the chord), the join tapers, the teardrop sides,
the partner identity of each end, the end outcome after joint and corner handling, and then the
beak count, teardrop cap or serif kind per end. Dots record `dot`.

`export.js` compares, per glyph, the polygon count, every polygon's point count, the edge runs
and the record across all masters of a group, and exits 1 naming the glyphs and printing the first
three records. Exact guarantee: compatible means the same contour count, the same point count per
contour and the same branch record; it is **not** a proof that corresponding points are the same
feature (review finding F001 is what added the record, which narrows but does not close that gap).

When it refuses, the fix is in the concept or the skeleton, never in the exporter: change the
parameter that moved a decision across its threshold (`xs` and the `0.1` serif-kind test,
section 4; the `0.03` teardrop-side test; the `0.06` curl test; the 3-unit `curved` test), or
redraw the stroke so the decision is not marginal in any master. Since 0.6.0 weight is not among the
movers: two masters of one concept at different multipliers cannot be refused for a decision in the
list below, because every such decision reads the mult-1 geometry (the rule at the end of this
section). What a heavier master can still be refused for is a T-join whose pinned edge differs (the
`tee` token, next paragraph but one), and what still differs between CONCEPTS (`xs`, the skeleton) is
unchanged.

**The `crotch` token.** When `crotch` is set (> 0), every open stroke's record carries `… ends=A/B crotch=a/b`, `a` and `b` being 1 where that end is a joint
between arms at an acute angle (decided on the unmapped skeleton, like every decision here) and 0 otherwise, so masters whose geometry puts a joint on different
sides of the 0.3 test are refused. With `crotch` unset the token is not written and the record is the 0.1 record, so a 0.1 project is not newly refused
(`test_an_unset_crotch_leaves_the_0_1_branch_record`). **The `curlsg` token:** a stroke with a curl end also records `curlsg=a/b`, the handedness (1 or −1,
0 for no curl) of each spiral, decided on the unmapped cross product like the curl itself; it is the one token 0.2 adds to a 0.1 record, and only a curl
concept writes it (two masters of a 0.1 curl project that spiral opposite ways would now be refused, as their shapes are not compatible). The shipped glyphs sit far from the test (the `V`'s arms read
a dot product of 0.72, the circumflex's 0); the margin has not been measured for a concept with `xs` far from 1. **The `tee` token** (0.5.0): a stroke
with a T-join end (`i`, section 2) records `tee=<stroke>@<segment><side>/…` per end: the partner stroke's index, the index of the sampled
SEGMENT of its centre line nearest the end (measured to the segment, not to the sample points, so an end midway between two samples is on one
segment in every master; the earlier nearest-sample rule flipped there with floating-point rounding between weights), and the edges `clipPast`
actually pinned past the cut (`L`, `R`, `LR`, or `=` for neither), recorded as the decision was made and not as the angle that predicts it,
because two masters within a dead band of that angle can pin opposite edges. Masters that pick different strokes or segments, or whose
stroke crosses perpendicular to the partner between them so that different edges are pinned, are refused. A T-join within a few degrees of
perpendicular is therefore fragile across weights (the `slope` case of `tests/test_r_leg_join.py`, at 91°, pins `R` at mult 1 and `L` at
`xs` 1.12 × mult 1.5); draw it clearly off perpendicular, as the `R` is at 54°, or expect the refusal. How many samples the pin reaches is a width, not a decision (the
acute corner sits `w / (2 tan φ)` along the edge: 11 samples on Bract TextRegular, 17 on TextBold), so it differs between weights by construction
and is not recorded, like the fold pin's reach (section 3). For the `R` the token is `1@314L` in every roman master and `1@317L` in every italic
one (measured 2026-11-19 over the five concept files, `tests/test_r_leg_join.py`), and the leg meets the bar at 54° against the 14.5° refusal, so
no shipped `xs`, weight or slant is near a threshold. Only a stroke with an `i` end writes the token.

**The audit of drawn coordinates inside decisions** (Impasse review of 0.2, G1 and G2; extended to weight in 0.6.0). Every geometry-dependent branch of `glyph()`,
`strokePolys()` and `fitSkeleton()`, and what it reads: `fitSkeleton`'s flat and round tests (literal skeleton coordinates, unmapped by
construction; the fit that feeds the decisions runs at `PU`, the Regular's width and hairline, and the fit that draws at `P`); the dot rule (the unmapped `dy`); the partner pairing (`partner()`, the unmapped endpoints `qU` and `ptsU`, fixed in 0.2: it
read the drawn ones, so two ends 1.8 apart at `xh` 500 were 2.16 apart at 600); the partner directions (unmapped; the drawn ones feed
only the reach of a corner); the beak gate, level strokes only (`pu`, fixed in 0.2: it read the drawn points, so a stroke 0.45 units off
level at `xh` 500 was 0.54 at 600); `curved`, the teardrop side and its `n > 30` test, the curl test, `vert`, the serif kind, the corner and joint
tests, the beak side and the crotch test (`pu`, `TU`, `pdU`). What still reads drawn coordinates and is NOT in the record: the fold pin, the head sink (it reads the end's mode, the reference tangent `TU` and the glyph key, which are the same in every master; how many points it pins differs between weights, like the fold pin's reach, and point counts and edge runs do not change), `cutSide`'s
0.25 parallel test, `clipPast`, the sidebearing and kerning bands (they are meant to follow the drawn glyph) and `minw`'s interior test. Each of
those changes coordinates only, never a point count or a record, so a master at another `xh` stays compatible. `test_no_decision_reads_a_mapped_coordinate`
holds the list: 500 synthetic glyphs placed on the thresholds, in five concepts, compared at three `xh`.

**The decision rule: the geometry at mult 1 and `xh` 500 decides, the drawn geometry draws.** The x-height
map changes a stroke's tangents (the band between the x-line and the ascender scales by 0.58 to 1.42),
and so does weight: `xf` widens every x by `1 + 0.16·(W/W0 − 1)` in a heavier master, and the vertical
fit moves a flat stroke's ends inward by half the stroke width (`hwFlat`, which follows `W` and `thin`),
so a short stroke's drawn tangent follows the weight. The thresholds above are tangents. So `glyph()` also
fits every skeleton at the reference parameters `PU` (`xh` 500, `W` = `W0`, `thin` = the concept's `thin`
before `thinGrow`; `src500`, sampled with the same counts, point for point) whenever the master is mapped
or at a multiplier other than 1, transforms those points with `xf` at `PU` (so the widening is undone), and
`strokePolys()` takes the `curved` chord test, the teardrop side, the curl test and the spiral's
handedness, `vert` (`|T[1]| > 0.5`), the serif kind (`|T[0]| > 0.1`), the corner and joint tests (with
the partner's reference direction), the beak gate and side, the partner pairing and the crotch test on
those points; widths, cuts, serifs, terminals, the fold pin and the T-join (its cut, its burial check and
the edges `clipPast` pins) read the drawn ones. The branch record at any legal `xh` and any multiplier is
therefore the `xh` 500, mult-1 record of the master's concept (0.2 set the rule for `xh`; 0.6.0 extended it
to weight after an italic group refused a Bold master, `docs/plan-italic-bold.md`: 44 (glyph, concept,
slant) cases over the five concept files changed structure or record between mult 1 and some multiplier
from 0.8 to 2.0, 27 of them the serif kind of the italic `w` or `W`, the rest the curl test (12), the beak gate (2), the
`crotch` test (1) and the `curved` test (1) on fit-moved strokes). A serif chosen from the reference geometry is drawn on the master's own
stroke: at the Driftwood example's x1.65 the `w`'s head serif joins a stem whose drawn tangent would have
said `diag` (inspected 2026-11-19 on a before/after picture kept outside the repository, which publishes no images;
`test_every_serif_chosen_from_the_reference_sits_on_its_drawn_stroke` holds every such terminal on its
body). `test_xh_does_not_change_any_branch_record` and `test_weight_does_not_change_any_branch_record`
draw every key of every master of the project's groups, and a variant of each master with every end a
curl, at `xh` 500, 400 and 600 and at mult 0.8, 1, 1.25, 1.5, 1.65 and 2, and compare the records;
`tests/test_weight_decisions.py` does the same for every concept of the five concept files at 24
multipliers (220,080 comparisons on 2026-11-19, 0 flips).

The first version recovered the unmapped points by applying the inverse map to the drawn ones. It is
exact for a curve whose control points lie in one band and approximate for one that straddles the
x-line, and on a concept whose every end is a curl it flipped 103 glyph records at `xh` 400 and 600
(the largest drift of the curl test's cross product was 0.25 against a threshold of 0.06). Fitting
the skeleton at `xh` 500 removes the approximation.

**Measured margins at `xh` 500** (every lowercase stroke of the three examples' concepts, roman and
italic, `mult` 1 and 1.5; the value is how far the decision's quantity sits from its threshold):
the italic `w`'s first stroke, serif kind `|T[0]| > 0.1`: **0.0028** (value 0.1028, neutral `text`, `mult` 1);
the 3-unit `curved` test: 0.0060 (windswept `x`, `mult` 1.5); the curl test `|cross| < 0.06`: 0.0010
(bract `bine`); `vert`: 0.047 (the `š` caron arm, bract `blind`); the teardrop side `|cross| < 0.03`: 0.030;
the beak side: 11.7 units from 450. Every one of those decisions reads the same value at `xh` 400
and 600, and no record changed in the 16,768 glyph comparisons. **The italic `w`'s serif-kind margin is an
`xs` margin, the same at every weight since 0.6.0:** the neutral example's `xs` 0.92 reads 0.1028 against
the 0.1 threshold in every master (the value is `(160 · 0.95 · xs − 88.2) / 500` with the shear nearly
cancelling the stroke's own slope; `xs` 0.90 reads 0.0968, `head`), so a change to `xs`, the italic
narrowing or the `w` skeleton can flip it and the exporter will refuse the italic group. Weight cannot:
until 0.6.0 the Bold's widening lifted the drawn value to 0.123 at mult 1.5 and took the Driftwood
example's `xs` 0.86 from `head` to `diag` at mult 1.4.


## 13. Designed, not built: `apex`

**Status: designed, not built. `params()` refuses a concept that sets `apex`** ("apex is designed but not built in 0.2"), so a concept cannot carry a
knob that does nothing. This section is the design, so a later version starts from it and not from the first draft, which was wrong.

**What it is for.** A book face's `A`, `V`, `N` and `M` come to a point that passes the line by a little (the way a round passes it by
`overshoot`), so the point does not read short beside the `O`. Today the `A`'s arms end level at 700.0 exactly while the `O`'s outer top is
710.5 (the planning measurement of 2026-11-16 on `gen.js` 0.1.0).

**The first draft's construction made a flat top, not a point.** It moved the arms' shared centre point down and cut both edges of each arm
level at `line + apex`. For the `A` at `W` 96 with symmetric arms (half-angle 22.5°) the outer edges then meet at the line, but each arm's inner edge
reaches the line `δ_y·tan 22.5° + (w/2)/cos 22.5° = 103.9` units from the apex x on each side: a flat top 208 units wide.

**The construction that makes a point.** For a joint of two steep strokes at a flat line, whose shared point `P0 = (x0, y_line)` has no
flat neighbour and whose angle is acute:

1. `Q`, the point, is the intersection of the two OUTER edges, placed at `y_line ± apex`. `C`, the crotch, is the intersection of the two INNER
   edges. Both come from the arms' directions `d₁, d₂` (unit, into and out of the joint), their pen widths `w_i = W·penWidth(θ_i, P, 0)` and their
   normals `n_i`: the outer offset `δ` solves `n₁·δ = w₁/2`, `n₂·δ = w₂/2`, with the signs chosen so that each `n_i` points away from the partner
   (`n_i·pd < 0`; blindly taking left normals gets the `4` and the `V` wrong), and the inner offset `δ_C` solves the same system with `−w_i/2`.
2. In `fitSkeleton`, the shared point moves **in y only**: `P' = (x0, y_line ± apex − δ_y)`, so that `Q = P' + δ` lands on `y_line ± apex`. `Q_x = x0 + δ_x`
   absorbs the asymmetry; `P'` keeps `x0`, so a plumb stem (the `N`'s) stays plumb and no x token is rewritten. `fitSkeleton` must find the joint
   itself, on the unfitted endpoints (two stroke ends within 2 units, the `partner()` rule of `glyph()`, which today runs AFTER the fit on the fitted
   samples), and annotate the strokes it returns (`apexA`, `apexB`) so `strokePolys` knows which ends are apexes.
3. In `strokePolys`, the apex end's OUTER edge point is set to `Q` (an extension along the edge line; `cutSide`'s clamp widened to
   `Ws[k] + |δ| + apex`) and its INNER edge point to `C`; every inner-edge sample between `C` and the end is pinned to `C` (`clipPast` with the cut line
   through `C`, perpendicular to the stroke; its `steps < 80` limit must grow to cover `|P'C|/3` samples, 116 for the Bold `M`). Each arm's body
   polygon then ends with the segment `Q–C`, shared by the two arms, and their union is the pointed apex. The record gains `apex=A/B`.

**The arithmetic** (Bract text concept: `nib` 12°, `thin` 0.44, `pow` 1.5, the Bold's `thin` 0.359 by `thinGrow`; `apex` 10; measured by intersecting
the edge lines in a script that is not kept):

| Glyph, joint | Weight | arm widths `w₁ w₂` | angle φ | drop of the centre point | `Q` (the point) | `C` (the crotch) | `|P'C|` (samples at 3 units) |
|---|---|---|---|---|---|---|---|
| `A` (330, 700) | Regular 96 | 82.5 94.7 | 45.0° | 105.7 → P' at 594 | (333.3, 710) | (326.7, 478.6) | 116 (39) |
| `A` | Bold 144 | 120.8 141.7 | 45.0° | 161.4 → 539 | (335.7, 710) | (324.3, 367.1) | 172 (57) |
| `V` (320, 0) | Regular | 94.7 82.5 | 45.0° | 125.7 → −126 | (323.3, −10) | symmetric to `A` | 116 |
| `N` top-left (100, 700) | Regular | 94.2 90.0 | 34.4° | 138.3 → 562 | (52.9, 710) | (147.1, 413.4) | 156 (52) |
| `N` | Bold | 141.0 133.7 | 34.4° | 211.0 → 489 | (29.5, 710) | (170.5, 267.9) | 232 (77) |
| `M` outer (110, 700) | Regular | 93.7 94.8 | 23.4° | 218.6 → 481 | (69.6, 710) | (150.4, 252.9) | 232 (77) |
| `M` outer | Bold | 140.1 142.0 | 23.4° | 332.0 → 368 | (49.7, 710) | (170.3, **26.1**) | 347 (116) |

These figures come from the planning measurement of 2026-11-16 and were not re-measured when `joints` and `crotch` were built.

**Why it waits.** The `A` works at both weights (the Bold crotch at 367 leaves a 127-unit counter above the bar at 240). The `M` and `N` do not: at
23.4° the Bold `M`'s crotch falls to y = 26 (the table's last row), the letter closes, and the Regular `M`'s crotch at 253 is already lower than a
book face draws it. Pointed-apex faces solve this with thinner diagonals (an expansion contrast model, which this generator does not have) or by
drawing the `M` with vertical outer stems and a shallower V (a skeleton change). One `apex` number cannot serve `A` and `M`; shipping it would
need a per-glyph exception list or a construction a design review would send back.

**Three open points** for whoever builds it: the `M` and `N` depth (above); the `clipPast` step limit (it must grow with the crotch depth); and the
normal signs of the `4`'s joints. The table is the measurement to reproduce first. Until then the nearest things that exist are `crotch`
(section 4), which opens the counter without moving the point, and `joints`, a level cut at the line.

## Per-face skeletons: the `skeletons` file

WHAT IT'S FOR: a face sometimes needs its own form of a letter the shared tables draw for everyone (Bract's
`n`, `m`, `h` and `r`, whose shoulder showed a nick where the head serif meets the arch), or a glyph the
tables lack. Since 0.6.0 that goes in one project file named by `font.json`, not in an edited copy of
`gen.js`, so a skill update can replace `scripts/` wholesale and the edit is hashed into the manifest like
any other source. The design record is `docs/plan-skeleton-overrides.md`.

**The contract.** `font.json` gains `"skeletons": "skeletons.js"`: a **bare file name** beside `font.json`
(no directory part, ending `.js`; `export.js`, `build.py` and `templates/font.schema.json` all refuse
anything else, and `build.py` refuses the five names the manifest already hashes). The file has the shape
of `concepts.js`, a CommonJS module in node and a script leaving one global when spliced into a page. The
file must set `SKELETONS` unconditionally and export that: node reads `module.exports`, a concept page reads
`SKELETONS`. `build-page.js --skeletons` runs the file as a page would (with `gen.js`'s names and no `module`)
and refuses it unless `SKELETONS` is then a function, so an anonymous `module.exports = function ...`, or a
`SKELETONS` set only inside `if (typeof module !== "undefined")`, fails the build instead of leaving the page
without the override:

```js
// tools/<face>/skeletons.js
var SKELETONS = function (G, GI, S, D, ring) {
  G.n[1] = S("M 90 480 C 170 510 225 510 290 510 C 410 510 460 440 460 330 L 460 0", "", "s");
};
if (typeof module !== "undefined") module.exports = SKELETONS;
```

The function edits the two live tables in place: it replaces an entry, edits a stroke inside one
(`G.t[0].a = "s"`), or adds a key. Its return value is ignored. It receives the three constructors of
section 2 and nothing else: the mark helpers (`acute`, `grave`, `circ`, `diaer`, `tilde`, `raise`,
`exitStem`) are private, so an override that needs a mark writes its strokes itself. One file serves every
group and every master of the face; there are no per-master or per-concept skeletons (masters of one group
must share a skeleton to interpolate).

**When it runs.** `export.js` calls `applySkeletons(fn, name)` once, after loading the concepts and before
listing or drawing any glyph, and prints one stderr line, for example
`skeletons skeletons.js: overrides G h, G m, G n, G r; re-derives G ñ` (with `adds ...` for new keys, or
`changes nothing`). It writes `skeletons` (the name) and `skeletonsSha256` (the file's sha256) into the
export JSON, only when the key is set. `build.py` hashes the file into `sources_sha256` under its name and
records `skeletons` in the manifest, again only when set, so `--check` and the site suite's manifest test see an
edit to it as they see an edit to `gen.js`, and `update-check.py`'s drift check reports one as drift. `build-page.js --skeletons PATH` does
the same for a concept page (`references/concept-pipeline.md` section 8). A second `applySkeletons` call in
one process throws.

`applySkeletons` does, in order: copies every entry in place (so no two keys share a stroke object, and an
edit of `G.n[1]` reaches `G.n` only) and keeps the JSON of each; calls the function; applies the refusals
below; rebuilds the derived glyphs it did not touch; empties the glyph and kern cache; and returns
`{ overridden, added, rederived }`.

**Derived glyphs follow their base.** Every glyph built from a base at load is registered with
`derive(table, key, build)` (the list is `DERIVED` in the exports), and the rebuild assigns it again from
the overridden tables, in place, so the glyph order does not move:

| Table | Base | Derived keys |
|---|---|---|
| `G` | `a` `e` `o` `u` | `á à â ä ā`, `é è ê ë`, `ó ò ô ö`, `ú ù û ü` |
| `G` | `n` `c` `s` | `ñ`, `ç`, `š` |
| `G` | `A E I O U N C` | `Á À Â Ä`, `É È Ê Ë`, `Í Ï`, `Ó Ô Ö`, `Ú Ü`, `Ñ`, `Ç` |
| `GI` | `a` `e` `u` `n` | `ā á à â ä`, `é è ê ë`, `ú ù û ü`, `ñ` |

The rule is **touched or followed**, decided by content, not by reference: a derived key the override
changed itself (assigned whole, or edited inside) is the override's and is not rebuilt; one it left alone
follows its base. Not derived, so never rebuilt: `í ì î ï` in both tables (built on a literal dotless stem,
so an override of `i` does not reach them), `©`, `™` and `•` (authored glyphs that sit among the composites),
the ligatures `fi fl ff` (authored; an override of `f` or `i` does not reach them), and `GI`'s capitals (merged
at load, before any override).

**The italic falls back to the roman entry.** `glyph()` reads `GI[key]` and then `G[key]` from the live
tables at draw time, so a `G` override reaches the italic for every key `GI` lacks (`t`, and every roman key
outside `GI`). Adding `GI.t` gives the italic its own form. A `G` override leaves an existing `GI` entry
alone. **One limit:** the accented capitals exist in `G` only, so an italic group draws them from the roman
table slanted, and an override of `GI.A` does not reach italic `Á`. An override that wants an italic `Á`
assigns `GI["Á"]` itself.

**Refused, each naming the file, the table, the key and the stroke:**

1. the module does not export a function;
2. a key present before the call is missing after it (an override may not delete);
3. an entry that is not an array of at least one stroke, or a stroke that is not one of the three shapes:
   `{d, a, b}` (those three fields and no other) whose path is `M` and two numbers, then one or more `L` (two numbers) or `C` (six numbers)
   and nothing else, with `a` and `b` each one of `""`, `s`, `t`, `u`, `x`, `j`, `i`; `{dot: [x, y]}` with two
   finite numbers and no other field (`glyph()` draws a stroke carrying `dot` as a dot and ignores a path beside
   it); or a ring, `{d, closed: true, r: [cx, cy, rx, ry]}` and no other field, with positive `rx` and `ry` and `d`
   exactly what `ring()` draws. This is its own validator: `sampleCounts()` and `samplePath()` skip a token
   they do not know (a `Q`, a stray number), so they cannot be the check;
4. a new key the cmap cannot map: anything longer than one UTF-16 unit that is not in `LIGS`, or a lone
   surrogate (a code unit, not a character). A character outside the Basic Multilingual Plane is refused too, because `export.js`'s title layout and `keysFor` read
   text unit by unit and would look it up as two halves;
5. a new `GI` key with no `G` counterpart (the export draws the keys of `G`, so it would be left out); a glyph
   added for both groups goes into both tables;
6. a second call in one process.

Not refused: an override that would change a glyph's stroke count between masters cannot exist (every
master of a group draws one table), and the exporter's compatibility check still refuses a pen that makes
branches differ.

**What an override cannot change:** the end-type letters and their meaning (section 2), `LIGS`, `UPPERISH`
(a new capital-like key spaces and fits as lowercase), the mark helpers, and the kerning reference.
**Overriding `n` or `H` re-kerns.** Every lowercase pair is kerned against the `n|n` gap and every capital
pair against `H|H` (section 8), so redrawing `n`'s arch moves the reference by hundredths of a unit and
re-rounds the pairs that sat nearest a half unit: for Bract's shoulder override on `examples/bract`, 14, 7, 29
and 21 of 4,100 pairs on the four masters, each by exactly 1 unit, with no advance moved (plan section 4.2,
re-run through `export.js` for 0.6.0). The plan's alternative, raising `n`'s serif with a taller stem, moved
`n`'s sidebearing and advance and re-kerned 1,324 to 1,777 pairs per master (plan section 4.1; not re-run).

**`--masters` refuses a stale export.** That path never runs `export.js`, so `build.py` compares the export's
`skeletons` with `font.json`'s key and its `skeletonsSha256` with the file as it is now, and refuses either
disagreement naming both values. An export kept with `--keep-masters` is therefore unusable after any edit of
the override; export again.

**A glyph every face needs** (a missing punctuation mark, a currency sign) goes into `G` in the skill's own
repository, with its own tests and review, never into the installed copy during a project. Draw it in the
project's `skeletons.js` meanwhile; after the skill update that carries it, delete the project's entry.

**Retired: the copy-and-patch convention.** Before 0.6.0 a site kept its additions in
`tools/<face>/scripts/extra-glyphs.js` and patched three lines into its copy of `gen.js` to load it, and built
concept pages with `--gen` pointing at that copy. A site on that convention moves the file's function into
`tools/<face>/skeletons.js` (the same `(G, GI, S, D, ring)` signature), names it in `font.json`, deletes the
patch, and rebuilds; `build-page.js --gen` still works for anyone who has not moved.
