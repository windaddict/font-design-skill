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

## 1. Vocabulary

- **Skeleton** — a glyph's list of centre-line strokes in a 1000-unit em (baseline 0, x-height 500,
  cap height 700, ascender 740, descender −230). Its role: the one drawing per letter that every
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
(the points of V, W, A; the corners of E, F, L, Z, the spur of G). The joint logic only applies to
concepts whose `s` end is `serif`; other concepts keep their own round or cut ends at joints.

## 3. The pen model

For a sample point whose tangent direction is θ:

```
f = thin + (1 − thin) · |sin(θ − nib)|^pow        the nib: full width perpendicular to the nib angle
w = W · f · m                                        m is the product of the modifiers below
```

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
| `thin` | 0.27–0.82 | the thinnest stroke as a share of `W` (1 = monoline) | the hairline in units is `W × thin`, less `swell/2`; see `thinGrow` |
| `thinGrow` | 0.5–0.6, or unset | with it, `P.thin = thin × mult^(thinGrow − 1)`, so hairlines grow as `mult^thinGrow` instead of in proportion to stems | unset means hairlines thicken as much as stems: Bract round 2 found the Bold's contrast collapsed and it read as another family (0.5 fixed it). The Bold's floor must be recomputed when this changes |
| `pow` | 1–2.4 | exponent on `|sin|`: higher makes the width fall off the thick direction faster, so more of each curve is near `thin` | raises apparent contrast without changing `thin` |
| `xs` | 0.86–1.12 | horizontal scale of every skeleton point, multiplied by `1 + 0.16·(W/W0 − 1)` so heavier masters widen slightly (×1.08 at mult 1.5), and by 0.95 for the italic | **a branch flipper**: the serif-kind test `|T[0]| > 0.1` reads the sheared tangent, and on the Example template the italic `w`'s first stroke read `head` at mult 1 and `diag` at mult 1.5 for `xs` 0.86–0.90 at 10°, so the exporter refused the group; 0.92 and above passed (measured here). Change `xs` and re-export every group |
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
| `dot` | 0.47–0.74 | dot radius `r = W × dot` | dots scale in proportion to weight; the fit sits baseline dots at `r − 4` and x-height dots at `500 − r + 4` |
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
  by `hwFlat = W × (thin + (1 − thin)·|sin(nib)|^pow) / 2`, half the horizontal stroke width;
- moves **round** extremes whose control-point y is in
  `ROUND = { 510 → 500 up, −10 → 0 down, 710 → 700 up, 720 → 700 up, −230 → −230 down }` so the
  outer edge overshoots the line by `overshoot`;
- moves any point that shared a moved flat point with it, **except a serifed stem end**, whose
  serif covers the joint;
- recentres rings between their fitted top and bottom.

Draw new skeletons on exactly these y values or the fit will not see them. Because `hwFlat`
depends on the pen, the fitted skeleton differs per master; the sample counts do not, because
they come from the unfitted skeleton.

## 8. Spacing and kerning

**Sidebearings.** Each glyph's left and right profiles are measured in 54 bins of 20 units from
y = −260. Over the bins between the baseline and the top (500, or 700 for `UPPERISH` glyphs: capitals,
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
the reference pair's (`H|H` for two uppers, else `n|n`); when it exceeds the reference by more
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
- `dropAmt` set without `tear: true` ("dropAmt only sizes teardrop terminals").

It does **not** throw on an `ends` table missing a letter a skeleton uses; that end draws square.

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
