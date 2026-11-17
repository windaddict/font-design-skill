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

A concept's `ends` table maps each letter to a **mode** (section 5). An unmapped letter draws a
plain square end: the stroke body stops at its last sample with no terminal polygon and no width
change. No shipped table maps `j`, which is how `j` means "square".

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
- **Join taper** (`tap`): a curved stroke whose end is a `disk` with no partner thins by 30 % over
  0.9·W0, so a join runs into its stem without a nub.
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
| `xs` | 0.86–1.12 | horizontal scale of every skeleton point, multiplied by `1 + 0.16·(W/W0 − 1)` so heavier masters widen slightly (×1.08 at mult 1.5), and by 0.95 for the italic | **a branch flipper**: the serif-kind test `|T[0]| > 0.1` reads the sheared tangent, and on the Example template the italic `w`'s first stroke read `head` at mult 1 and `diag` at mult 1.5 for `xs` 0.86–0.90 at 10°, so the exporter refused the group; 0.92 and above passed (measured here). Change `xs` and re-export every group |
| `hzThin` | 0.85–1.0 (`params()` refuses outside 0.5–1.5, bounds excluded); default 1 | level strokes are thinned by `1 − hzThin`, weighted by cos²θ (a level bar loses the whole amount, a plumb stem none) | optical correction, section 3. The vertical fit and the corner reach follow it, so a flat bar's outer edge still sits on its line. Values above 1 thicken level strokes (a reverse-contrast concept). Lowers the hairline of a concept whose thin direction is level: re-read `minStrokeWidth` and re-pin the floors |
| `roundGain` | 1.0–1.08 (refused outside 0.8–1.25, bounds excluded); default 1 | curves are thickened by `roundGain − 1`, weighted per sample by the local curvature (a ring fully, an open curve by `min(1, κ · 2.5 · W0)`, a straight stroke not at all) | optical correction, section 3. `2.5` is a design constant with no source. The fit gives a round extreme the half width of a fully weighted curve (weight 1), so a ring (the `o`) lands exactly at the line plus `overshoot` whatever `roundGain` is (measured: 510 at `overshoot` 10). **An open curve is not exact:** its weight at the extreme is below 1 (about 0.6 on the fitted `c`), so its top sits off the target by up to `hw × |roundGain − 1| × (1 − weight)`, never more than `(W/2) × f(0) × hzThin × |roundGain − 1|` (`f(0)` the pen width at a level tangent, 1 for a monoline concept; `hzThin` multiplies the gain term at a level extreme, so it enters the bound; the sign of `roundGain − 1` does not): measured on the monoline fixture the `c`, `e` and `s` tops moved by up to 2.28 units at `roundGain` 1.05 and `mult` 1.5 (bound 3.75), 5.91 at `roundGain` 0.85 and `mult` 1.5 (bound 11.25), and 4.49 at `roundGain` 1.05 with `hzThin` 1.4 (bound 5.25, where the bound without `hzThin` would be 3.75), and on the neutral example's `text` concept reduced to `nib` 0, `pow` 1, `thin` 0.6 and butt ends by at most 0.36 at `mult` 1 and 1.27 at `mult` 1.5. Fitting each sample with its own weight would be circular (the weight depends on the fitted curve) and was not built |
| `diagThin` | 0.85–1.0 (refused outside 0.5–1.5, bounds excluded); default 1 | diagonal strokes are thinned by `1 − diagThin`, weighted by sin²2θ (full at 45°, none level or plumb) | optical correction, section 3. Independent of `hzThin`: at 51° both apply. `params()` throws on a value outside the range, naming the knob |
| `xh` | 400–600 (`params()` refuses outside, bounds allowed); default 500 | the x-height of the lowercase, in skeleton units: every lowercase key (every key that is not `UPPERISH`, except the apostrophe) is drawn through a piecewise-linear y map, section 7. Capitals, figures, ascenders and descenders do not move | the range is a design range (0.8–1.2 of the body), not a compatibility bound: every branch decision is taken on the unmapped skeleton (section 12), so a legal `xh` cannot make the exporter refuse a group. The lowercase accents are compressed into the band as `xh` rises (an acute of 110 units draws about 92 at `xh` 560 and 64 at 600). The spacing band follows (section 8). Not echoed into the manifest |
| `serifBracket` | 0–1 (refused outside, bounds allowed); default 1 | blends every serif between today's bracketed form (1) and a slab (0) with **the same number of points**, so a bracket can interpolate between masters: the foot and symmetric head (26 points), the lowercase head (15) and the diagonal serif (26) | at 1 the code is the 0.1 code, unchanged. At 0 the foot is a rectangle `h` thick (`h = SW × serifH`), where the bracket climbed `1.7·h` (`1.9·h` for the lowercase head) and curved in by `0.45·h`; the controls of the slab lie on their chords. A slab wants a thin `serifH` (0.13–0.15 is a flat Scotch slab) |
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
| `serif` | none | `serifPoly` (foot, symmetric head for `UPPERISH` glyphs, or the lowercase one-sided wedge) or `diagSerifPoly` for a slanted stem; a round stroke end gets a ball | the branch record names the kind (`serifA=foot|head|diag|ball`) |
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
| `corner` (an outcome) | none | none | the same pass where a steep stroke meets a shallow one (E, F, L, Z, the spur of G): the steep stroke runs out to the partner's far edge, cut plumb or level |
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

**Automatic kerning** (`kern(a, b)`): the pair's mean gap over the shared band is compared with
the reference pair's (`H|H` for two uppers, else `n|n`), over the same band: 700 when either glyph is `UPPERISH`, else `xh`; when it exceeds the reference by more
than 8, `k = −0.75 × (excess − 8)`, clamped at **−170**; a **sparse** pair, where either glyph has
ink in under 35 % of the band's bins (a hyphen, a dash, a period, a quote), is capped at **−50**,
because its mean gap is measured at one height only and runs away (the hyphen before `S` in
"Eighty-Seventh" hit −170 and crowded the S in a cold dry run of this skill; trap 34); then
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
- Serif length is ×0.6 in `diagSerifPoly` and for symmetric heads in `serifPoly`. **Every italic
  stem is slanted, so every italic stem serif comes through `diagSerifPoly`**; Driftwood once
  shortened serifs in `serifPoly` only and saw no change.
- Sidebearings are measured over the band between the baseline and the x-height or cap height
  only (`cMin`/`cMax`), so `f` hooks and tails overhang their neighbours instead of being spaced.
  `J`'s descender hook may hang only 90 units into the previous letter's space.
- `T` loses 6 units.
- A concept used for an italic must map `x` in `ends` (normally `exit`).

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
   (section 7) and end types from section 2. Decide joints by placing stroke ends within 2 units
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
- `hzThin` or `diagThin` that is not a number strictly between 0.5 and 1.5, or `roundGain` not
  strictly between 0.8 and 1.25 (the error names the knob and the range; a string and `null` are
  refused too).

It does **not** throw on an `ends` table missing a letter a skeleton uses; that end draws square.

**Compatibility promise, exactly.** A 0.1 project that copies 0.2's `scripts/` over its own and rebuilds, without touching `concepts.js` or `font.json`, gets
the same outlines and tables (decoded TTF, export JSON and manifest figures) as 0.1.0 gave. The promise is **per platform and node major version**: the
generator's floating-point output depends on both, so the digests the repo records (`tests/fixtures/baseline-0.1.0.json`) are keyed `darwin/26`, `linux/22`
and so on, and a platform that is not recorded has no promise until it is recorded from the 0.1.0 code. The raw woff2 bytes are a separate claim, also
per brotli version. The branch record is not part of it; it gains tokens (section 12), and only a curl end (`curlsg`) or a set `crotch` writes one.

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
redraw the stroke so the decision is not marginal in any master.

**The `crotch` token.** When `crotch` is set (> 0), every open stroke's record carries `… ends=A/B crotch=a/b`, `a` and `b` being 1 where that end is a joint
between arms at an acute angle (decided on the unmapped skeleton, like every decision here) and 0 otherwise, so masters whose geometry puts a joint on different
sides of the 0.3 test are refused. With `crotch` unset the token is not written and the record is the 0.1 record, so a 0.1 project is not newly refused
(`test_an_unset_crotch_leaves_the_0_1_branch_record`). **The `curlsg` token:** a stroke with a curl end also records `curlsg=a/b`, the handedness (1 or −1,
0 for no curl) of each spiral, decided on the unmapped cross product like the curl itself; it is the one token 0.2 adds to a 0.1 record, and only a curl
concept writes it (two masters of a 0.1 curl project that spiral opposite ways would now be refused, as their shapes are not compatible). The shipped glyphs sit far from the test (the `V`'s arms read
a dot product of 0.72, the circumflex's 0); the margin has not been measured for a concept with `xs` far from 1.

**The audit of mapped coordinates inside decisions** (Impasse review of 0.2, G1 and G2). Every geometry-dependent branch of `glyph()`,
`strokePolys()` and `fitSkeleton()`, and what it reads: `fitSkeleton`'s flat and round tests (literal skeleton coordinates, unmapped by
construction); the dot rule (the unmapped `dy`); the partner pairing (`partner()`, the unmapped endpoints `qU` and `ptsU`, fixed in 0.2: it
read the drawn ones, so two ends 1.8 apart at `xh` 500 were 2.16 apart at 600); the partner directions (unmapped; the drawn ones feed
only the reach of a corner); the beak gate, level strokes only (`pu`, fixed in 0.2: it read the drawn points, so a stroke 0.45 units off
level at `xh` 500 was 0.54 at 600); `curved`, the teardrop side and its `n > 30` test, the curl test, `vert`, the serif kind, the corner and joint
tests, the beak side and the crotch test (`pu`, `TU`, `pdU`). What still reads drawn coordinates and is NOT in the record: the fold pin, `cutSide`'s
0.25 parallel test, `clipPast`, the sidebearing and kerning bands (they are meant to follow the drawn glyph) and `minw`'s interior test. Each of
those changes coordinates only, never a point count or a record, so a master at another `xh` stays compatible. `test_no_decision_reads_a_mapped_coordinate`
holds the list: 500 synthetic glyphs placed on the thresholds, in five concepts, compared at three `xh`.

**The decision rule for `xh`: unmapped coordinates decide, mapped coordinates draw.** The x-height
map changes a stroke's tangents (the band between the x-line and the ascender scales by 0.58 to 1.42),
and the thresholds above are tangents. So `glyph()` also fits every mapped skeleton at `xh` 500
(`src500`, sampled with the same counts, point for point) and `strokePolys()` takes the `curved` chord
test, the teardrop side, the curl test, `vert` (`|T[1]| > 0.5`), the serif kind (`|T[0]| > 0.1`),
the corner and joint tests (with the partner's unmapped direction) and the beak side on those points;
widths, cuts, serifs, terminals and the fold pin read the drawn ones. The branch record at any legal
`xh` is therefore the `xh` 500 record. `test_xh_does_not_change_any_branch_record` draws every key of every master of the
project's groups, and a variant of each master with every end a curl, at `xh` 500, 400 and 600 and
compares the records.

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
and 600, and no record changed in the 16,768 glyph comparisons. **The italic `w`'s serif-kind margin is a
pre-existing fragility, not caused by `xh`:** the neutral example's `xs` 0.92 reads 0.1028 in the
Regular against the 0.1 threshold, so a change to `xs`, the italic narrowing or the `w` skeleton can
flip it and the exporter will refuse the italic group (the Bold's widening lifts it to 0.123).


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

## Adding glyphs in a site without forking the generator

A site's copy of the generator lives at `tools/<face>/scripts/gen.js`, and a glyph the site needs
(a character the skeleton table lacks) is added there. Editing that file forks it from the skill's
`scripts/gen.js`, and the next skill update then has to be merged by hand. Convention (a convention
the skill asks for, not a mechanism `gen.js` has today): keep the site's additions in
`tools/<face>/scripts/extra-glyphs.js`, a module that exports a function taking `(G, GI, S, D, ring)`
and adding entries, and make the site's `gen.js` load it with a three-line patch at the end of the
skeleton section:

```js
// site additions, kept out of the skill's file so it can be replaced wholesale
var EXTRA = require("path").join(__dirname, "extra-glyphs.js");
if (require("fs").existsSync(EXTRA)) require(EXTRA)(G, GI, S, D, ring);
```

Record the patch in the font record. To take a skill update: copy the new `scripts/gen.js` over the
site's, re-apply the three lines, rebuild, and run the suite; `test_the_shipped_fonts_match_their_manifest`
goes red until the rebuild, which is the point. Additions that belong to everyone (a missing
punctuation mark, a currency sign) are a separate change to the skill's own repository, never an edit of the
installed copy during a project: draw the glyph in the site's `extra-glyphs.js` for this project, then, only
on the operator's word, add it as a skeleton in `G` in a checkout of the skill repository with its own tests
and review. The project picks it up with the next skill update (the paragraph above), after which its
`extra-glyphs.js` entry is deleted.
