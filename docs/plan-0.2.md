# Plan: font-design 0.2 — optical corrections, x-height and slab serifs, junctions, a genre vocabulary, a per-round visual diff

Status: a plan, written 2026-11-16 on branch `v0.2-font-research` (base: `0fc4314`, the 0.1.0 commit),
revised the same day after the cross-provider Impasse review (section 12: fourteen findings, every one
checked against the code or measured before the plan changed). Nothing in it is built. Markers:
**(read)** = checked against the named file at the lines given; **(measured)** = run here, with the
command or script named; **(inferred)** = not verified, the implementer checks it first. The five
changes come from the research report of 2026-11-16 (`font-gaps.md`, items 2, 3, 4, 9 and 10 of its
summary table); the report is a lead, and section 0 says where it is wrong about the code as it stands.

**The one decision the review changed:** the pointed apex (`apex`) is **designed, not built** in 0.2.
The arithmetic in section 4.4 shows why: one depth rule cannot serve `A` and `M` at once (the Bold `M`'s
crotch would reach the baseline), and the construction the first draft gave produced a 208-unit flat
top, not a point. `joints` and `crotch` ship; `apex` is refused by `params()` until 0.3 so it cannot be
a dead knob.

Contents

0. What the report got wrong, and what was verified
1. The hard constraints and how the plan meets them (compatibility, masters, testing, docs, honesty)
2. Item 3 — optical corrections in the pen model (`hzThin`, `roundGain`, `diagThin`)
3. Item 4 — an x-height parameter (`xh`) and an unbracketed serif (`serifBracket`)
4. Item 9 — junctions: `joints`, `crotch` built; `apex` designed, not built
5. Item 2 — the genre vocabulary (`references/genres.md`, `templates/concepts.genres.js`)
6. Item 10 — the per-round visual diff (`scripts/diff.py`)
7. Ordering, the work split, file ownership, how the CHANGELOG is merged
8. Acceptance runs
9. Risks, and what is out of scope
10. Questions for the operator
11. Work items
12. Plan review reconciliation (Impasse, 2026-11-16)

---

## 0. What the report got wrong, and what was verified

The repository changed after the report was written: items 1, 5, 6, 7 and 8 of its table are in 0.1.0
(the specimen's control strings and legibility row, the FontBakery gate, the table defaults, the
fallback-metrics tool and `text-wrap` guard) **(read: `scripts/specimen.py` header, `scripts/fontbakery-gate.py`,
`references/testing.md` section 2)**, so its "skill coverage: none" lines for those are stale. For the
five items this plan covers, checked against `scripts/gen.js` at `0fc4314`:

| Report claim | What the code says | Status |
|---|---|---|
| The serif bracket is "hard-coded (`gen.js:393–409`, `1.7·h`)" | `serifPoly` is lines 393–418: the foot and the symmetric head climb `1.7·h` (397, 404), the lowercase one-sided wedge (410–416) uses its own `1.8·h` and `1.9·h`, and `diagSerifPoly` (424–440) climbs `1.7·h` through `onEdge`. Three constructions, not one, and the unbracketed option has to cover all three | (read) partly wrong |
| Joints "are cut level/plumb (`gen.js:553–571`) with no thinning" | Right for serif concepts. **The joint logic runs only when `P.ends.s === "serif"`** (line 554): a `butt`/`cut`/`taper` concept gets no level cut at all; the V's apex is two stroke ends drawn in whatever `ends[""]` maps (`disk` in every shipped sans concept), each capped with a circle of radius `0.42·w`. The report's grotesque and geometric rows assume level joints a sans concept does not have today | (read) incomplete, and it changes item 2 |
| "Bold `V W A M N w v y k` fill at 17.6 px" at crotches | `y` and `k` have no end-to-end joint: their strokes cross or start mid-stroke (`y`'s first stroke ends at (260, 0) on the second's body; `k`'s arm ends on the stem and its leg starts with a `j` square end). The glyphs whose branch record carries a `joint` end are `1 4 5 v w A M N V W`, plus the circumflex and caron marks and `™` | (measured: `node` over `gen.js`, every key, serif concept, `ends=…joint` in `g.sig`) wrong on `y k`, missing `1 4 5` |
| Pointed apexes "are flat-cut at the line" and read short beside the `O` at 710 | `A`'s two arm polygons reach y = 700.0 exactly; the `O` ring's outer top is 710.5 | (measured, same script) right |
| "Accents are placed above the x-height by literal numbers, `gen.js:234–238`"; the x-height is therefore effort L because "every lowercase skeleton has literal 500s and 510s" | The marks are 234–258 and 272–279 (lowercase composites), capitals through `raise(…, 170)` at 259–271. None of them needs editing if the x-height is a y-transform inside `fitSkeleton()` (section 3), which already parses and rewrites every coordinate. The literals that DO need the transform's attention are the `FLAT`/`ROUND` tables (626–627), the dot rule (751–752) and `beakPoly`'s `y < 150` / `y > 450` (450). Effort M, not L | (read) effort over-estimated, lines partly wrong |
| `thin ≥ 0.27` limits the fat face's hairline-to-stem ratio | 0.27 is the smallest value a shipped concept used (`generator.md` section 4 says "range seen"); `params()` sets no bound. `thin: 1` (monoline) exports two compatible masters today, and so does `nib: 90°` | (measured: `params()` + `glyph()` at mult 1 and 1.5 over every key, 0 incompatible glyphs for both) wrong; the real limit is the hairline floor |
| `overshoot` is "the same … for both optical cuts" | Each cut is its own concept and carries its own `overshoot`; the examples happen to write 10 in both (`examples/bract/concepts.js`) | (read) wrong in principle, right about the examples |
| Round-stroke gain "to `ring` strokes and to open strokes whose `curved` flag is set" | `curved` is one flag per stroke (line 477), and `n`'s arch plus its right stem is ONE stroke (line 73), so a per-stroke gain would thicken the `n`'s stem and not the `i`'s. The gain has to be weighted per sample by local curvature (section 2) | (read) the mechanism would draw the wrong letters |
| Grotesque: "`thin` 1 with `cut`/`butt` ends" | Also needs `thinGrow` unset: `params()` sets `P.thin = thin × mult^(thinGrow − 1)` (line 712), so a monoline concept with `thinGrow 0.5` is not monoline in the Bold | (read) incomplete |
| x-height "risks branch flips" | Right, and the first draft of this plan under-counted them. A y-map can move the serif-kind test (`|T[0]| > 0.1`, line 609: the italic `w`'s first stroke reads 0.127 at `xh` 500 and 0.061 at 640 with `xs` 1; section 3.2), the `vert` test (`|T[1]| > 0.5`, lines 555 and 568: the caron and circumflex arms read 0.63 today and 0.32 under the band scale of `xh` 640), the chord test behind `curved` (3 units, line 477–479: the apostrophe tail flattens under the band compression), the beak thresholds (line 450) and the dot rule (751–752). Section 3 takes every branch decision on the unmapped coordinates, so none of them can move | (measured, section 3.2) right, and larger than the first draft said |
| "Add the Bold `v w y k A M N W` at the smallest site size as a specimen row" | The row is `1 4 A M N V W v w` (the joint glyphs above) | corrected |
| "`build.py --check` proves byte identity; nothing shows a change" | Right. `--check` compares the rebuilt woff2 and the manifest with the shipped ones (`build.py` 1364–1381) and prints DIFFERS with the differing manifest keys; `shoot.py` writes `head`/`body` crops (`DEFAULT_BANDS`, line 144) but nothing diffs two builds | (read) right |

Also verified, because the plan rests on them:

- The three examples' `out/` folders on this machine were built from the current sources: every
  `sources_sha256` in the three manifests equals `shasum -a 256` of `scripts/gen.js`, `export.js`,
  `build.py` today **(measured)**. Those folders are therefore the 0.1.0 baseline for `--check`, and
  they are **not tracked** (`.gitignore`: `out/`, `*.woff2`), so section 1.1 records their digests
  before any 0.2 code runs.
- **The manifest records the source hashes** (`build.py:1273`, `"sources_sha256": sources`) and the
  tool versions (`"tools": tool_versions()`), so after any edit of `gen.js` a `--check` prints
  `manifest DIFFERS` with `manifest.sources_sha256` listed, whatever the font bytes do **(read)**.
  Section 1.1 states the acceptance accordingly.
- Pillow in the skill venv has raqm (`PIL.features.check("raqm")` → True) and FreeType 2.14.3
  **(measured)**, so `diff.py` can lay out with GPOS kerning (section 6).
- **FreeType autohints the shipped fonts as they are.** The neutral roman (`prep` present, no `fpgm`,
  `maxp.maxSizeOfInstructions` 0) renders identically with its `prep` deleted (0 grey levels of
  difference) and differently by 212–255 levels once a one-instruction `fpgm` is added, at 16 and 40 px
  for `B` and a title **(measured, Pillow 13 / FreeType 2.14.3)**. The first draft of this plan inferred
  the opposite from memory of the FreeType source; the measurement wins, and section 6 renders through
  the `fpgm` trick `build.py` already uses (`raster_font_file`, lines 582–584).
- `templates/export.schema.json` has `additionalProperties: false` on the master and glyph records
  **(read)**: the export JSON gains no new fields in 0.2; only the branch-record strings grow.
- `SKILL.md` is 475 lines against the 500-line test **(measured: `wc -l`)**; 0.2 adds at most six.

---

## 1. The hard constraints and how the plan meets them

### 1.1 Backward compatibility: byte-identical fonts

**The rule.** Every new parameter has a default under which `gen.js` runs the ORIGINAL expression,
not a new expression that happens to equal it. Two shapes are allowed: a factor that is exactly `1`
and an addend that is exactly `0` (IEEE: `x × 1 = x`, `x + 0 = x`, `1 − 0 × c = 1` for finite `c`), or
a branch on the default that falls through to the unchanged code. A rewritten constant such as
`1 + 0.7 × b` in place of `1.7`, or `y × 500 / 500` in place of `y`, is not allowed even where the
doubles agree, because the next edit will not check. `params()` sets a single `P.optical` flag when
any of the item-3 knobs is set, and `fitSkeleton`/`glyph()` branch on `P.xh === 500`, so the default
paths are the 0.1 lines verbatim.

**What "byte-identical" means here.** The woff2 bytes of every group are identical. The manifest is
identical **except `sources_sha256`** (the hashes of `gen.js`, `export.js`, `build.py` change because
the files change; `build.py:1273`) and `tools` (node, Python and Pillow versions, which differ between
machines). Nothing else in the manifest moves: no key is added, and every per-master figure (`W`,
`thin`, `track`, `space`, `points_raw`, `points`, `min_stroke_width`, the title widths) is the same,
because the geometry is.

**The proof, three layers:**

1. **A tracked baseline, recorded before any 0.2 code (work item W0).** `tests/fixtures/baseline-0.1.0.json`
   holds, per example and group, three digests computed by `tests/baseline_digest.py`: `export_sha256`,
   over the export JSON with every `sig` removed (canonical JSON of each master's `adv`, `polys`, `raw`,
   `runs`, `keptIdx`, `minw`, `kerns`, `space`, `titles`, `minStrokeWidth`), which is pure node arithmetic;
   `ttf_sha256`, over the woff2 decompressed by fontTools and re-serialised (`flavor = None`,
   `save()`), which does not depend on the brotli build; and `manifest_sha256`, over the manifest with
   `sources_sha256`, `tools` and each group's `woff2_sha256`/`woff2_bytes` removed (the last two follow
   brotli). The woff2 sha256 of each file as built here is recorded too, informational. The record is
   keyed by node major version: if a CI node produces a different `export_sha256` on the UNCHANGED
   0.1.0 tree, that is a V8 arithmetic difference, not a regression, and the operator adds that node's
   digest after confirming with `build.py --check` on a 0.1.0 checkout under that node; the test then
   accepts the recorded set and nothing else.
   `tests/test_backward_compat.py::test_the_0_1_examples_export_and_build_to_the_recorded_digests`
   exports every group of the three examples and builds them into `tmp_path` (`--out-dir`,
   `--no-requirements` for bract and driftwood, as `smoke.sh` step 2 does) and compares all three
   digests. **Watched red on 0.1.0 itself** before 0.2 starts, under the weakest mutation:
   `Math.round(g.adv)` → `Math.round(g.adv) + 1` in `export.js` (every digest changes). The baseline
   file must exist; a missing or malformed file FAILS, never skips.
2. **`build.py --check` on the three examples against the 0.1.0 outputs** (acceptance, section 8).
   `smoke.sh` step 2 rebuilds `examples/*/out/`, so W0 first copies the three `out/` folders to a scratch
   directory outside the repo, `BASELINE_OUT` below (`cp -R`); the acceptance run copies them back and
   runs `--check`, which must print `font identical` for every group and list `manifest.sources_sha256`
   (and, on another machine, `manifest.tools`) as the ONLY differing manifest keys.
3. **The manifest is unchanged in shape**, so a 0.1 site reads a 0.2 manifest with no schema change.
   The new knobs are NOT echoed into it (section 9 lists that as a limit).

A site that copies 0.2's `scripts/` over its 0.1 copy and rebuilds without touching `concepts.js` or
`font.json` therefore gets the same woff2 bytes and a manifest whose only change is the three source
hashes; `test_the_shipped_fonts_match_their_manifest` (`scripts/tests/test_font.py:512`, which compares
the manifest's `sources_sha256` with the files, lines 530–531) goes red until that rebuild, which is
the documented signal (`generator.md`, "Adding glyphs").

### 1.2 Master compatibility

`export.js` refuses a group whose masters differ in polygon count, point count per polygon, edge runs
or branch record (`export.js` 164–175 **(read)**). Each change below says which of the four it can
touch. The rule for 0.2: **no new parameter changes a point count or a run**; a parameter that gates a
geometry-dependent decision records the OUTCOME in `g.sig`, never the value, so two masters with
different values of the same knob stay compatible (the knob interpolates) and two masters whose
geometry falls on different sides of a threshold are refused, as `xs` is today. **Every branch
decision is taken on coordinates the x-height map has not touched** (section 3.2), so `xh` cannot move
one. `params()` refuses values outside the ranges in each section with a message naming the range, so
an illegal value is a loud error, not a silent clamp.

### 1.3 Testing discipline

Every guard below names its test and the **weakest mutation** that must turn it red, chosen by the
rule in `references/testing.md` section 3. Geometry tests execute `gen.js` through node (the
`TEARDROP_FIXTURE` pattern in `scripts/tests/test_font.py` lines 616–672 **(read)**) and measure the
built polygons: a width is the distance between the two edge points of one sample, read through the
polygon's two edge runs; a line is the extreme y of a polygon. Expected values are the configured
ratio or the documented formula restated in the test with the test's own trigonometry, never a figure
the generator prints. Font-suite guards (`scripts/tests/test_font.py`) get an entry in
`scripts/tests/mutate.py`, with `expect=` naming the assertion text; repo guards (`tests/`) record
their mutation in the docstring and in `references/testing.md` section 8, as 0.1 did. Tests that
build a variant of the project's concept delete the keys that `params()` would refuse beside the
forced ones (`flareAmt` with `tear`, `dropAmt` without it), as the dropAmt fixtures do.

### 1.4 Docs in the same change

Per item: `references/generator.md` (section 3 formula, section 4 table rows, section 7 fit, section
8 band, section 12 record tokens and the decision rule), `references/concept-pipeline.md`,
`references/review-loop.md`, the two reviewer briefs, `templates/concepts.example.js`,
`templates/font.schema.json` (one description), `references/testing.md` (the header's function list,
section 2 rows, section 8), `CHANGELOG.md` (`## [0.2.0]`), `VERSION`, the `SKILL.md` frontmatter and
README badge, `SKILL.md`'s tool table (one row for `diff.py`) and reference index (one line for
`genres.md`), `scripts/smoke.sh` (three steps). `tests/test_docs_commands.py` checks every documented
flag against the script, and `tests/test_versions_and_skill.py` checks the version, the 500-line limit
and that every file `SKILL.md` names exists, so the docs are tested, not only written.

### 1.5 Honesty about the design

The genre table (section 5) has a column "reaches it today?" with four values: **yes, rendered and
reviewed on <date>**, **partly** (with the exact limit, and the same render review), **no** (with what
would be needed), and **candidate** (a recipe written but not yet rendered and read). A recipe moves
from candidate to yes or partly only after the genres page has been built, shot, and read by a fresh
strong-model reviewer (work item C3). Where the generator cannot reach a genre the table says so and
does not invent a parameter set.

---

## 2. Item 3 — optical corrections in the pen model

### 2.1 Design

Today (`gen.js` 499, 560, 628 **(read)**), the width law is computed in three places:

```
f = thin + (1 − thin) · |sin(θ − nib)|^pow      the sample width (499), the corner partner's width (560)
hwFlat = W · (thin + (1 − thin) · |sin(nib)|^pow) / 2        the vertical fit's half horizontal width (628)
```

0.2 moves it into one function and adds an optical factor, computed only when a knob is set:

```js
function penWidth(th, P, cw) {              // cw: curvature weight 0..1 (0 for a straight sample)
  var f = P.thin + (1 - P.thin) * Math.pow(Math.abs(Math.sin(th - P.nib)), P.pow);
  if (!P.optical) return f;                 // the 0.1 path, verbatim
  var c = Math.cos(th), s2 = Math.sin(2 * th);
  return f * (1 - (1 - P.hzThin) * c * c)     // level strokes thinner: cos²θ is 1 level, 0 plumb
           * (1 - (1 - P.diagThin) * s2 * s2) // diagonals thinner: sin²2θ is 1 at 45°, 0 level and plumb
           * (1 + (P.roundGain - 1) * cw);    // curves heavier, by how much the sample curves
}
```

| Key | Range the docs give | `params()` refuses | Default | Effect |
|---|---|---|---|---|
| `hzThin` | 0.85–1.0 (sources: 1–9 % bar/stem difference) | outside (0.5, 1.5) | 1 | level strokes × `hzThin`, weighted by cos²θ |
| `roundGain` | 1.0–1.08 | outside (0.8, 1.25) | 1 | curved samples × `roundGain`, weighted by curvature |
| `diagThin` | 0.85–1.0 | outside (0.5, 1.5) | 1 | diagonal samples × `diagThin`, weighted by sin²2θ |

`params()` sets `P.hzThin`, `P.diagThin`, `P.roundGain` to the concept's values or 1, and
`P.optical = !(hzThin === 1 && diagThin === 1 && roundGain === 1)`. Values above 1 for the thins (and
below 1 for the gain) are allowed within the refusal range, for reverse-contrast concepts.

**Curvature weight.** For an open stroke, `cw_i = min(1, κ_i · ROUND_GAIN_RADIUS · W0)` with
`κ_i = |Δθ| / Δs` over the samples `i−1 .. i+1` (the tangent `tang()` already exists, line 488) and
`ROUND_GAIN_RADIUS = 2.5`: a curve of radius `2.5·W0` or tighter (250 units for `W0` 100; the `o`'s
ring is 210 × 260) gets the full gain, a radius-500 curve half, a straight stem none. Closed strokes
(rings) get `cw = 1` by definition. The constant is a design choice to be judged on the genre renders,
named in `generator.md` so a project can be told what it saw. **(inferred)**: whether 2.5 is right;
the sources give no radius, only "round strokes look lighter than straight ones".

**Where the factor must follow.** All three places take `penWidth`: the sample width (`cw` from the
local curvature), the corner partner's width (`cw` 0, the partner is straight by construction), and
`hwFlat` (θ = 0, `cw` 0). A fit that ignored `hzThin` would move a level bar inward by half the
UN-thinned width and leave its outer edge `W·(1 − hzThin)/2` inside the line; a corner that ignored it
would run the stem that many units past the bar's far edge. Both are measured by the test.

**The thinnest direction is no longer the nib direction.** With the three factors the minimum of
`W · f(θ) · optical(θ)` over θ has no closed form worth printing: `thin 1` with `diagThin 0.5` gives
`0.5·W` at 45°, and `nib 0` with `thin 0.5` and `hzThin 0.9` gives `0.45·W` level. The hairline
`generator.md` section 3 describes as `W × thin` becomes "the smallest value the first export's
`minStrokeWidth` reports", which is what the floor logic already uses: `export.js` measures the
interior minimum per master and `build.py` recomputes it from the polygons (`min_interior_stroke_width`,
line 876) and refuses below the pinned `hairline_floors`. No formula is relied on; a project adding any
of the three knobs re-reads the export and re-pins its floors, or the build refuses. `thinGrow` does
not apply to the optical factors (they are weight-independent in 0.2; a `hzThinGrow` is out of scope).
`guidelines.md` section 3 gains one sentence: set the three knobs whenever a concept's `thin` is above
about 0.7, because the contrast no longer supplies the correction by accident.

### 2.2 Compatibility

Branch-free: `curved`, the teardrop side, the curl test, the beak test, the serif kind and the joint
and corner decisions read tangents and partner directions, not widths (lines 477–492, 554–571, 609
**(read)**), so no outcome moves. The fold pin may pin different points (it reads edge steps), which
changes coordinates only. Point counts and runs: unchanged. Masters with different knob values are
compatible and interpolate.

### 2.3 Tests

`scripts/tests/test_font.py::test_optical_corrections_change_only_the_strokes_they_name` (node
fixture `OPTICAL_FIXTURE`). Base: the project's first concept with `thin 1, nib 0, pow 1, swell 0, wob 0,
thinGrow deleted, tear false, flareAmt/dropAmt deleted, overshoot 10`, every end type mapped to `butt`, so
`f = 1` everywhere and the only width variation is the optical factor. **Four variants, one knob each
and then all three together**, at mult 1 and 1.5, so no expectation mixes two factors by accident
(review finding F007: the first draft's diagonal expectation forgot the `hzThin` factor that applies at
the same angle). Measured on the raw polygons (before export decimation):

| Assertion | Variant | Measured how | Expected |
|---|---|---|---|
| a | every variant | `l` body width at the middle sample | `W` (± 0.05) |
| b | `hzThin 0.9` alone | `-` body width at the middle sample | `0.9·W` (± 0.05) |
| c | `roundGain 1.05` alone | `o` horizontal thickness at the right extreme: `max x(outer) − max x(inner)` | `1.05·W` (± 0.1) |
| d | `roundGain 1.05` alone | `c` body width at its leftmost sample (vertical tangent, radius ≈ 210 < 250) | `1.05·W` (± 0.1) |
| e | `diagThin 0.94` alone | `x` first stroke width at the middle sample, θ read from the edge direction in the test | `W · (1 − 0.06 · sin²2θ)` (± 0.05) |
| e2 | all three | the same `x` sample | `W · (1 − 0.1·cos²θ) · (1 − 0.06·sin²2θ) · (1 + 0.05·cw)` with `cw` 0 (a straight stroke): the product, restated |
| f | `hzThin 0.9` alone | `z` top bar's top edge (a FLAT 500 stroke) | y = 500.0 (± 0.1): the fit followed the thinning |
| g | `hzThin 0.9` alone | `E` stem body's max y vs the top bar body's max y | equal (± 0.1): the corner reach followed it |
| h | all three at 1 | every measurement above | the 0.1 widths (`W`, and `z`/`E` as today) |

| Mutation (mutate.py name) | Edit | Goes red on |
|---|---|---|
| `optical-hz-all` | `hzThin` applied without the `cos²` weight (`(1 − (1 − P.hzThin))`) | a: the stem is `0.9 W` |
| `optical-round-straight` | `cw` forced to 1 for open strokes | a: the stem is `1.05 W` |
| `optical-round-open-off` | `cw` forced to 0 for open strokes (rings only) | d: the `c` is `W` |
| `optical-diag-flat` | `sin²2θ` weight replaced by 0 | e: the `x` stroke is `W` |
| `optical-fit` | `hwFlat` uses the pen law without the optical factor | f: the `z` bar's top edge at 495 |
| `optical-corner` | the corner's `pw` uses the pen law without the optical factor | g: the stem overshoots the bar by 5 |

Plus the compatibility guard: `tests/test_backward_compat.py` red under `hzThin` default `0.999`
(mutation `compat-default`, applied by hand and recorded).

### 2.4 Docs

`generator.md` section 3 (the law, `penWidth`, the curvature weight and its constant; the hairline
sentence rewritten as above), section 4 (three rows), section 7 (`hwFlat` follows `hzThin`);
`guidelines.md` section 3 (when to set them); the genre table uses them (section 5). CHANGELOG.

### 2.5 Risks and out of scope

Risk: a concept whose thin direction is level loses hairline margin under `hzThin` and the build
refuses on the floor; this is the floor doing its job, and `generator.md` says so. Out of scope:
weight-dependent optical factors; an expansion (pointed-pen) contrast model (section 5 says what it
would add).

---

## 3. Item 4 — x-height (`xh`) and the unbracketed serif (`serifBracket`)

### 3.1 x-height: design

Skeletons are drawn with the x-line at 500 and the lowercase round overshoot at 510/−10 (`FLAT`,
`ROUND`, lines 626–627 **(read)**). `xh` (default 500; `params()` refuses outside **[400, 600]**, a
narrower range than the first draft's [380, 640]: see 3.2) is a **piecewise-linear y map applied
inside `fitSkeleton()`** to every glyph in the mapped set, before the flat and round fits:

```
y ≤ 0:            y                                   (descenders unchanged)
0 < y ≤ 500:      y · xh / 500                         (the lowercase body scales, 0.8–1.2)
500 < y < 740:    xh + (y − 500) · (740 − xh) / 240    (the band to the ascender: scale 1.42 at xh 400, 0.58 at 600)
y ≥ 740:          y                                   (ascenders unchanged)
```

**The mapped set** is every key that is not `UPPERISH` (line 280) **except the apostrophe `'`**:
lowercase letters, their accented forms, the ligatures, and `. , : ; - – — … •`. The apostrophe stays
where it is drawn (655), because an apostrophe sits near the cap height in any face, and the builder
derives the six quote glyphs from it (`build.py` `quote_glyphs`), so they stay too. Capitals, figures
and cap-high punctuation are not mapped.

The `FLAT` and `ROUND` lookups keep their literal keys (a point AT 500 is "on the x-line", a `C`
control point at 510 is "the round overshoot above it") and the TARGET line becomes `ymap(500) = xh`:
a flat x-line stroke moves inward by `hwFlat` from `xh`, a round top lands at `xh + overshoot`. Rings
map their top and bottom (`cy ± ry`) and are recentred as today. The `moved` map keys stay the literal
coordinates, so joints and shared points move together as today. `fitSkeleton` currently returns early
when `overshoot` is 0 (line 630); the map applies before that return, so a project without the fit
still gets its x-height. `fitSkeleton(src, P)` gains the glyph key as a third argument (`glyph()` has
it, line 730). `fitSkeleton` passes dot records through unchanged (`if (!pp) return st`), so dots are
mapped where their y is decided, in `glyph()` (lines 749–756): **the dot rule reads the unmapped
literal `dy`**: `dy < 100` → `r − 4` (a baseline dot); `380 < dy < 460` → `xh − r + 4` (an x-height
dot: the colon's upper dot at 420, the `i`'s is not one); any other dot of a mapped glyph → `ymap(dy)`
(the `i` and `j` dots at 680, the diaeresis at 650, the bullet at 300). Review finding F006: with the
mapped `dy` the colon's upper dot at `xh` 600 would read 504 and miss the rule.

**Spacing follows the line.** The sidebearing band (`top = UPPERISH ? 700 : 500`, line 790), its depth
cap `0.2·top`, and `kern()`'s band and reference pair (`top`, `pairGap(ref, ref, 500)`, `coverage`,
lines 842–853) read `P.xh` for lowercase. Default identical (`P.xh === 500` branches to the literal).

What the map does to a letter, to document and to review in round 1: the `n`'s arch control points at
470 and 510 straddle the x-line and are mapped piecewise (the curve is the Bézier of the mapped
control points, not the image of the curve); the i-dot (680) and the lowercase marks (610–720) are
compressed into the band when `xh` rises (an acute of 110 units is 92 at `xh` 560 and 64 at 600),
which is what a large-x-height face does to its accents; the `t`'s crossbar (490) and the `f`'s (490)
scale with the body. Caps do not move; a `capH` is out of scope (section 9).

### 3.2 x-height: compatibility — every branch decision on unmapped coordinates

Point counts come from the unfitted skeleton (line 729) and are unchanged. The branch record is the
risk, and the review (F004, F005) showed it is larger than the first draft said. Measured and computed
for the shipped skeletons **(measured: a node probe that mapped the skeleton strings as above and drew
three concepts at `xh` 380/440/560/640; its sample counts and ring handling differ from the real
design, so only the flips that arithmetic confirms are cited)**:

- **Serif kind, `|T[0]| > 0.1` (line 609), on the italic `w`'s first stroke** (`GI.w`, line 195,
  `M 10 500 L 170 0`). With the italic shear and the 0.95 narrowing, `|T[0]| = |0.95·xs·160 − tan 10°·xh| / hypot(…)`:
  0.127 at `xh` 500 and 0.061 at 640 for `xs` 1 (the reviewer's figures, reproduced); the crossing is at
  `xh` 549 for `xs` 1 and **532 for the neutral example's `xs` 0.92, whose Regular reads 0.103 today,
  0.003 above the threshold** (the Bold's widening lifts it to 0.123). A pre-existing fragility, recorded
  in section 9.
- **`vert`, `|T[1]| > 0.5` (lines 555, 568), on the caron and circumflex arms** (`M 150 700 L 260 610`):
  (110, 90) reads 0.63 today; under the band scale 0.417 of `xh` 640 the arms read (110, 37.5) → 0.32,
  and the joint at the mark's apex stops being a joint.
- **`curved`, the 3-unit chord test (477–479)**: the first draft's "smallest chord distance 16.0 units"
  covered the body band only (scale ≥ 0.8). In the ascender band the scale is 0.58 at `xh` 600 and
  0.417 at 640, and the apostrophe's tail (`M 112 650 C 112 585 95 540 60 505`, 145 units tall) flattens
  enough to flip in the probe at 640. The apostrophe is now exempt from the map; the tilde and the
  other in-band curves are what A2m measures.
- **The curl test** (`addCurl`, `|cross| < 0.06`, line 369) and **the teardrop side** (`|cross| < 0.03`,
  line 491) read tangents and move with any y-scale; unmeasured for the real design.
- **`beakPoly`'s `y < 150 ? 1 : y > 450 ? −1 : 0`** (line 450) reads the drawn y: at `xh` 440 the `z`'s
  top bar (440) would fall in the middle zone and lose its beak (the probe showed `beakA 1 → 0`).

**The fix is a rule, not a range:** every geometry-dependent decision that enters the branch record is
taken on the **unmapped** coordinates, and every drawn coordinate is the mapped one. `glyph()` keeps,
beside the sampled fitted points `pts`, the same points with the inverse y-map applied per point
(`ptsU`; when `P.xh === 500`, `ptsU` IS `pts`, the same array, so the default path is untouched).
`strokePolys` receives both: `curved`, the teardrop-side tangents, the curl test, the `vert` tests, the
serif-kind test and the beak thresholds (compared with the unmapped end y) read `ptsU`; the partner
directions for the joint and corner tests are computed from `ptsU` too; widths, cuts, serifs,
terminals and the fold pin read `pts`. For a stroke whose control points lie within one band the
mapped curve is the affine image of the unmapped one, so the decisions are exactly the `xh` 500
decisions; for a curve whose control points straddle 500 (the `n`'s arch, the `a`'s top) the inverse
map recovers them up to the Bézier's reparametrisation, and **work item A2m measures the margin of
every decision for every lowercase stroke of the three examples' concepts at `xh` 400 and 600, roman
and italic, mult 1 and 1.5, and records the smallest in `generator.md` section 12**. With the rule in
place the range [400, 600] is a design range (0.8–1.2 of the body), not a compatibility bound.

### 3.3 Unbracketed serif: design

`serifBracket` (default 1; `params()` refuses outside [0, 1]) blends each serif construction between
today's bracketed form (1) and a slab (0) **with the same number of points**, so masters stay
compatible and a bracket can interpolate. The three constructions (section 0), their point counts
**(read: two `push` + four `quad()` of six; three `push` + two `quad()`; one `push` + four `quad()` +
one `push`)** and their slab forms:

- **Foot and symmetric head** (`serifPoly`, 2 + 4 × 6 = 26 points): anchors `b·today + (1 − b)·slab`,
  controls likewise, where the slab is the rectangle `(x ∓ w/2, y ± h) → (x ∓ L, y ± h) → (x ∓ L, y) →
  (x ± L, y) → …`: the climb top `h·1.7` becomes `h`, the corner inset `0.45h` becomes 0, each `quad()`
  control sits on its chord so the six points lie on a straight segment.
- **Lowercase head** (3 + 2 × 6 = 15 points): the wedge becomes a flat slab to the left,
  `(x + w/2, y − h) → (x + w/2, y) → (x − L, y) → (x − L, y − h) → (x − w/2, y − h)`.
- **Diagonal** (`diagSerifPoly`, 1 + 4 × 6 + 1 = **26** points; the first draft said 25, review
  finding F013): `onEdge(a, h·1.7)` becomes `onEdge(a, h)`, the insets 0, controls on the chords.

Branch on the default: `if (b === 1)` runs the 0.1 code unchanged (section 1.1 rule).

### 3.4 Tests

`test_xh_moves_the_lowercase_lines_and_leaves_the_capitals` (node fixture, project's first concept with
every end `butt`, `xh` 600 and 400, mult 1 and 1.5):

| Assertion | Expected |
|---|---|
| a | `o` outer polygon max y = `xh + overshoot` (± 0.6); min y = `−overshoot` (± 0.6) |
| b | `n` stem body max y = `xh` (± 0.05): a butt end at the x-line (no flat neighbour, so the fit does not move it) |
| c | `z` top bar's top edge = `xh` (± 0.1): a FLAT 500 stroke moved inward from the new line |
| d | `-` body centre y = `260 · xh / 500` (± 0.1) |
| e | `d` stem max y = 740 (± 0.05); `d` bowl top = `xh + overshoot` |
| f | `H` max y = 700, `O` outer top = 710, `0` top = 710, `l` max y = 740, the apostrophe's extremes: unchanged |
| g | the colon's two dot centres at `r − 4` and `xh − r + 4`; the `i` dot centre at `ymap(680)` (restated) |
| h | every polygon count and point count equals the `xh 500` glyph's |

| Mutation | Edit | Red on |
|---|---|---|
| `xh-round-literal` | `ROUND` targets stay literal 500 (`R[0]` not mapped) | a, e: the `o` top at 510 |
| `xh-flat-literal` | `FLAT` 500 moves from 500, not from `xh` | c: the `z` bar at 500 |
| `xh-caps-too` | the map applied to `UPPERISH` keys and the apostrophe | f: `O` at 710 → 830 |
| `xh-band-unmapped` | `500 < y < 740` left unmapped | a: the `o` top at 510 while the stem is at 600 |
| `xh-dot-mapped` | the dot rule reads the mapped `dy` | g: the colon's upper dot at `ymap(420)`, not `xh − r + 4` |

`test_xh_does_not_change_any_branch_record` (node fixture): for the project's concepts (every master's
concept and `mult`, roman and the italic flag when the project has an italic group), draw every key at
`xh` 500, 400 and 600 and compare each glyph's `sig` with its sample counts stripped (`n=…` does not
change either, but the comparison is on decisions): identical for every glyph. Mutation
`xh-branch-mapped` (the decisions read `pts` instead of `ptsU`): on a project with an italic group the
`w` flips at `xh` 600 (section 3.2: `xs` 0.92 reads 0.057); on any project the caron's `š` arms read
`|T[1]|` 0.43 at the band scale 0.58 and the mark's joint vanishes → red naming the glyph. This test is
also the executable form of A2m's margin measurement.

`test_xh_sets_the_spacing_band` (node fixture): under `xh 600`, recompute `o`'s left sidebearing from its
polygon profile with the documented formula (bins of 20 from −260, the band `[0, xh)`, each bin's depth
capped at `0.2·xh`, `T = 30 + 0.36·W0 − 0.25·(W − W0) + track`, `sbL = max(8, T − 0.5·mL)`) and compare
with `glyph("o").adv − ink width − sbR` recomputed the same way; and recompute the `o|o` automatic kern
with `pairGap` restated over the same band. **Work item A2m measures first** that the recomputed `o`
sidebearing and `o|o` kern at `xh 600` differ by more than 1 unit between a band of 500 and of 600; if
the kern does not, the kern half of the test is dropped and the gap recorded in `testing.md` section 8
(a mutation that cannot fire is a finding, not a chore). Mutations: `xh-band-500` (`top` stays 500 for
lowercase in `glyph()`), `xh-kern-band-500` (`kern()` keeps 500).

`test_an_unbracketed_serif_is_a_slab_with_the_bracketed_point_count` (node fixture, serif concept,
`serifBracket` 0, 0.5, 1; glyphs `I` foot and head, `n` lowercase head, `v` diagonal foot): at 0 every
point of the serif polygon has y ∈ {`y_end`, `y_end ± h`} (± 0.05) with `h = SW·serifH`, `SW = W0·(W/W0)^serifGrow`
restated in the test; at 1 the polygon's extreme y is `y_end ± 1.7h` (foot, head, diag) and `1.9h` (lowercase);
at 0.5 strictly between; the point count is 26, 15 and 26 at 0, 0.5 and 1 alike; at 1 the polygons equal
the `serifBracket`-undefined polygons exactly. Mutations: `bracket-ignored` (`b` forced 1: the slab
still climbs 1.7h), `bracket-count` (the slab drawn as a six-point rectangle: counts differ),
`bracket-diag` (`diagSerifPoly` not given the blend: the `v` foot still climbs).

Repo: the three example groups still export (`tests/test_schemas_and_concepts.py`, existing) and the
compat test (section 1.1) stays green: `xh` default and `serifBracket` default change nothing.

### 3.5 Docs

`generator.md` section 1 (vocabulary: the x-line is `xh`), section 4 (two rows, the ranges), section 7
(the map, the mapped set, the literal keys, the dot rule, the beak thresholds), section 8 (the band
reads `xh`), section 12 (the decision rule: unmapped coordinates decide, mapped coordinates draw; the
margins from A2m; the italic `w`'s 0.003 margin at `xs` 0.92 today). `genres.md` uses both. CHANGELOG.

### 3.6 Out of scope

`capH`, a separate ascender/descender knob, an `xh` that varies with `mult`, per-glyph overrides, and
any skeleton redraw. A site that wants a single-storey roman `a` can set `G.a = GI.a` in its
`extra-glyphs.js` today (the hook receives `G` and `GI`; `generator.md` "Adding glyphs"), provided its
`ends` maps `x`; `genres.md` says so.

---

## 4. Item 9 — junctions: `joints` and `crotch` built; `apex` designed, not built

### 4.1 Design of what ships

**`joints`** (boolean, default false; read only when `ends.s !== "serif"`). Line 554 gates the whole
joint/corner pass on `P.ends.s === "serif"`. With `joints: true` a sans concept gets the same pass:
level or plumb cuts where two stroke ends meet (`V W A M N 1 4 v w`), squared corners (`E F L Z z 2 5 7`,
the spur of `G`), no `ends[""]` terminal at those ends. Without it nothing changes. This is one
condition: `var jointsOn = P.ends.s === "serif" || P.joints === true;`.

**`crotch`** (0–0.5, default 0; `params()` refuses outside [0, 0.6]). At each stroke end that the joint
pass resolves as a `joint` whose two strokes meet at an acute angle (`dot(−T_end, pd) > 0.3`, where
`T_end` is this stroke's tangent at the end and `pd` the direction the partner leaves the shared
point, both already computed, lines 488 and 762–763, read on the unmapped coordinates per section
3.2), the **crotch-side edge only** thins over the last `CROTCH_LEN = 1.1·W0` units:
`w_side *= 1 − crotch·e`, `e = u²(3 − 2u)`, `u = 1 − d/CROTCH_LEN` (the teardrop's smoothstep and
reach). The crotch side is the edge the partner lies on: `n·pd > 0 → left edge`, `n = (−t_y, t_x)`. The
outer edge is untouched, so the apex keeps its line and the counter opens. `CROTCH_LEN` equals the
teardrop reach `tearL`, so `g.minw`'s interior exclusion (line 523) already leaves it out: **the
hairline floor does not see the crotch**. The acuteness outcome is recorded:
`sig += " crotch=" + (acuteA ? 1 : 0) + "/" + (acuteB ? 1 : 0)` on every open stroke (text only; the
export JSON is not shipped and `--check` does not compare it).

**`apex`**: `params()` **refuses** a concept that sets it, with the message "apex is designed but not
built in 0.2 (references/generator.md, 'Designed, not built'); remove it", the same shape as the
`flareAmt`-with-`tear` refusal, so a concept cannot carry a knob that does nothing (Driftwood issue #24
is the precedent). Section 4.4 holds the design.

### 4.2 Compatibility

`joints`: the decision reads `P.ends.s` and `P.joints`, constants per concept; two concepts in one group
that differ in `joints` would differ in end outcomes and be refused, correctly. `crotch`: thinning
changes coordinates only; the acuteness outcome is in the record; its test reads unmapped tangents that
`xs`, `shear` and the italic shear can still move (the `xs` caution of `generator.md` section 4
applies). Point counts and runs: unchanged by both.

### 4.3 Tests

`test_joints_opt_in_cuts_a_sans_joint_level` (node fixture, project's first concept with every end
`butt`, with and without `joints: true`): with it, `V` stroke 0's two end edge points both lie at y = 0
(± 0.05) and its record reads `ends=…/joint`; `L`'s stem body min y equals its base body's min y (the
corner squared); without it the two end points differ in y by `w·|T_x|` and the record carries no
`joint`. Mutation `joints-ignored` (`jointsOn` reads `ends.s` only).

`test_crotch_thins_only_the_inner_edge_of_an_acute_joint` (serif concept, `crotch` 0.3 vs 0, mult 1
and 1.5; the `V` and `A` from the record's `crotch=…1`, re-aligned on a reference sample as the
teardrop fixture does):

| Assertion | Expected |
|---|---|
| a | at the sample eight steps before the joint end, the crotch-side edge moved inward by `0.3·e·(w/2)` (± 2 %), with `e` restated from the sample's distance |
| b | the outer edge of the same sample did not move (< 1e-6) |
| c | `l`, `n` (no partner) and `E` (corners) are identical at 0 and 0.3 |
| d | `g.minw` of `V` and `A` is identical at 0 and 0.3 |
| e | with `crotch` 0 every glyph equals the `crotch`-undefined glyph exactly |

| Mutation | Edit | Red on |
|---|---|---|
| `crotch-both-edges` | `wl` and `wr` both thinned | b |
| `crotch-everywhere` | the partner test dropped (every end thins) | c: `l` |
| `crotch-corners` | the acute test dropped | c: `E` |
| `crotch-floor` | `CROTCH_LEN = 2·W0` | d: `minw` drops |

`test_apex_is_refused_until_built`: `params()` on the project's first concept with `apex: 10` throws
naming `apex` and `generator.md`. Mutation `apex-accepted` (the throw removed).

Specimen (B): a junction row, `1 4 A M N V W v w` and the words `AVAWMNW vwvy`, in the Bold at the
smallest review size, marked `data-fd-junctions="true"`; `tests/test_tools_and_templates.py::test_the_specimen_carries_the_junction_row`
holds it (mutation: the row's text built from an empty list), and `smoke.sh` step 9 greps the marker
as it does the spacing rows.

### 4.4 `apex`: designed, not built — the construction, the arithmetic, and why it waits

**What the first draft got wrong (review F002).** It moved the arms' shared centre point down and cut
BOTH edges of each arm level at `line + apex`. For the `A` at `W` 96 with symmetric arms (half-angle
22.5°), the outer edges then meet at the line, but each arm's inner edge reaches the line
`δ_y·tan 22.5° + (w/2)/cos 22.5° = 103.9` units from the apex x, on each side: a flat top 208 units
wide **(measured: `apex.py` in the planning scratch directory)**, not a point. The test it specified
(x-extent under 3 units near the max y) could never have passed; the construction was wrong, not the
test.

**The construction that does make a point.** For a joint of two `vert` strokes at a FLAT line whose
shared point `P0 = (x0, y_line)` has no flat neighbour and whose angle is acute:

1. `Q`, the point, is the intersection of the two OUTER edges, placed at `y_line ± apex`. `C`, the
   crotch, is the intersection of the two INNER edges. Both are found from the arms' directions
   `d₁, d₂` (unit, into and out of the joint), their pen widths `w_i = W·penWidth(θ_i, P, 0)` and their
   normals `n_i`: the outer offset `δ` solves `n₁·δ = w₁/2`, `n₂·δ = w₂/2` (signs chosen so that each
   `n_i` points away from the partner, `n_i·pd < 0`; the first draft's probe got the `4` and `V` signs
   wrong by taking left normals blindly), and the inner offset `δ_C` solves the same system with `−w_i/2`.
2. In `fitSkeleton`, the shared point moves **in y only**: `P' = (x0, y_line ± apex − δ_y)`, so that
   `Q = P' + δ` lands on `y_line ± apex`. `Q_x = x0 + δ_x` absorbs the asymmetry; `P'` keeps `x0` so a
   plumb stem (the `N`'s) stays plumb. **No x token is rewritten** (review F003), and the `moved` map's
   y-only rewrite suffices. `fitSkeleton` must find the joint itself, on the unfitted endpoints (two
   stroke ends within 2 units, the `partner()` rule of `glyph()` line 745, which today runs AFTER
   `fitSkeleton` on the fitted samples), and annotate the stroke objects it returns (`apexA`, `apexB`)
   so `strokePolys` knows which ends are apexes; `glyph()` passes the flags through.
3. In `strokePolys`, the apex end's OUTER edge point is set to `Q` (an extension along the edge line;
   `cutSide`'s clamp widened to `Ws[k] + |δ| + apex`) and its INNER edge point to `C`; every inner-edge
   sample between `C` and the end is pinned to `C` (`clipPast` with the cut line through `C`
   perpendicular to the stroke; its `steps < 80` limit, line 444, must grow to cover `|P'C|/3`
   samples: 116 for the Bold `M`, below). Each arm's body polygon then ends with the segment `Q–C`,
   shared by the two arms, and their union is the pointed apex. The record gains `apex=A/B`.

**The arithmetic, Bract text concept (`nib` 12°, `thin` 0.44, `pow` 1.5; Bold `thin` 0.359 by
`thinGrow`), `apex` 10 (measured: `apex.py`, line intersections):**

| Glyph, joint | Weight | arm widths `w₁ w₂` | angle φ | drop of the centre point | `Q` (the point) | `C` (the crotch) | `|P'C|` (samples at 3 units) |
|---|---|---|---|---|---|---|---|
| `A` (330, 700) | Regular 96 | 82.5 94.7 | 45.0° | 105.7 → P' at 594 | (333.3, 710) | (326.7, 478.6) | 116 (39) |
| `A` | Bold 144 | 120.8 141.7 | 45.0° | 161.4 → 539 | (335.7, 710) | (324.3, 367.1) | 172 (57) |
| `V` (320, 0) | Regular | 94.7 82.5 | 45.0° | 125.7 → −126 | (323.3, −10) | symmetric to `A` | 116 |
| `N` top-left (100, 700) | Regular | 94.2 90.0 | 34.4° | 138.3 → 562 | (52.9, 710) | (147.1, 413.4) | 156 (52) |
| `N` | Bold | 141.0 133.7 | 34.4° | 211.0 → 489 | (29.5, 710) | (170.5, 267.9) | 232 (77) |
| `M` outer (110, 700) | Regular | 93.7 94.8 | 23.4° | 218.6 → 481 | (69.6, 710) | (150.4, 252.9) | 232 (77) |
| `M` outer | Bold | 140.1 142.0 | 23.4° | 332.0 → 368 | (49.7, 710) | (170.3, **26.1**) | 347 (116) |

**Why it waits.** The `A` works at both weights (the Bold crotch at 367 leaves a 127-unit counter above
the bar at 240). The `M` and `N` do not: at 23.4° the Bold `M`'s crotch falls to y = 26, the letter
closes, and the Regular `M`'s crotch at 253 is already lower than a book face draws it. Pointed-apex
faces solve this with thinner diagonals (an expansion contrast model, out of scope) or by drawing the
`M` with vertical outer stems and a shallower V, which is a skeleton change. One `apex` number cannot
serve `A` and `M`; shipping it would mean either a per-glyph exception list (out of scope) or a
construction the review loop would send back. The design above, the table, and the three open points
(the `M`/`N` depth; the `clipPast` limit; `4`'s normal signs) go into `generator.md` under a heading
"Designed, not built: `apex`", so 0.3 starts from them. Until then `params()` refuses the knob (4.1).

### 4.5 Docs

`generator.md` section 2 (joints apply to serif concepts and to `joints: true`), section 4 (two rows:
`joints`, `crotch`), section 5 (the `joint` end), section 12 (the `crotch` record token), and the new
"Designed, not built: `apex`" section with 4.4's construction and table; `review-loop.md` section 3
item 1 names the junction row; `reviewer-brief-design-round.md` names it in "what to read";
`genres.md` (grotesque uses `joints`; geometric says "flat apex; a pointed apex is designed, not built").
CHANGELOG: `joints` and `crotch` under Added; `apex` under a heading "Designed, not built", naming the
refusal and the `generator.md` section.

### 4.6 Risks and out of scope

Out of scope: `apex` (4.4), ink traps (notches), per-glyph apex exceptions, the pointed `W` inner apex
(not on a line), weight-dependent `crotch` (a project gives the Bold's concept its own value only
through a separate concept per master). Risk: `crotch` on a sans concept with `joints: true` thins the
inner edge of a level-cut end whose outer edge is square; the genres page shows the grotesque's `A V W`
and the reviewer judges it.

---

## 5. Item 2 — the genre vocabulary

### 5.1 Design

A new reference, `references/genres.md` (with a contents line; under 300 lines so no TOC test
applies), and a parameter file, `templates/concepts.genres.js`, one concept per recipe, exported as a
module like `concepts.example.js` and loadable by `build-page.js`. The table has the columns the
report proposed plus the honesty column of section 1.5. **Every recipe below is "candidate" until
C3's render review** (review F012: the first draft wrote "yes, candidate" on two rows, which is not a
value the column has). The rows and what the 0.1 code plus 0.2's knobs give **(read: `generator.md`
section 4 ranges)**:

| Genre | Defines it | Recipe | Reaches it today? |
|---|---|---|---|
| Didone / modern | vertical stress, hairline unbracketed serifs and horizontals, ball terminals | `nib 0, thin 0.28, pow 2.2, serifH 0.13, serifLen 0.7, serifBracket 0, tear false, flareAmt 0.2` (balls) | **candidate for partly**: rounds and stems yes; the translation model gives both diagonals of `A V W M N v w x y` the same width, where a Didone's are thick/thin; an expansion mode is out of scope |
| Fat face | a Didone at poster weight, counters reduced to slits | the Didone recipe at `W 130`, `mult` 1.5 for the Bold | **candidate for partly**, same limit; the hairline floor, not `thin`, bounds the ratio |
| Scotch roman / transitional | slightly oblique stress, bracketed serifs, moderate–high contrast | Bract's `foil` (`examples/bract/concepts.js`) | **yes**: shipped and reviewed as a round-1 concept on hopsafari.com (2026-11-15), the one row with a review behind it |
| Clarendon | bracketed slab serifs, moderate contrast, drawn as a bold companion | `thin 0.74, serifH 0.85, serifLen 0.5, serifBracket 1, serifGrow 0.6` | **candidate** (Bract's `blind` is close; never named a Clarendon in a review) |
| Egyptian / slab | unbracketed slab serifs | the Clarendon recipe with `serifBracket 0` | **candidate** (needs item 4) |
| Grotesque | near-uniform stroke, flat apexes, horizontal curve terminals | `thin 1, nib 0, pow 1`, no `thinGrow`, `ends` cut/butt, `joints true, hzThin 0.92, roundGain 1.04, diagThin 0.95, xh 540` | **candidate for partly**: the skeleton's rounds are humanist ovals, the `G` has a bar not a spur, the `c e s` terminals are the skeleton's curves cut; needs items 3, 4, 9 |
| Geometric | circles and squares, pointed `N A` apexes, single-storey `a`, monoline | the grotesque recipe with `xh 500` and **no `apex`** | **candidate for partly**: flat apexes (`apex` is designed, not built, section 4.4), no circular `O` (the ring is 600 × 720 and `xs` 1.12 leaves it oval), no roman single-storey `a` (a site can set `G.a = GI.a` in `extra-glyphs.js`) |
| Reverse contrast (French Clarendon) | thin verticals, thick horizontals, heavy slabs | `nib 90 · DEG, thin 0.4, serifH 0.85, serifBracket 0` | **candidate**: exports compatibly (section 0); never rendered |
| Tuscan (bifurcated serifs) | split, curled serif ends | — | **no**: a serif polygon with a notch is a new construction |
| Art Deco (Broadway, Bifur) | one-idea letters, two-tone strokes, high or low waists | — | **no**: no two-tone stroke, no bar-height knob; `shear`/`bend` are a wind, not Deco |
| Optical sizes (the metal lesson) | small sizes wider, taller x, less contrast, looser | `opsz` axis: `xs`, `thin`, `track`, `serifLen` per cut plus `xh` per cut (item 4) | **candidate**: the mechanism exists once item 4 lands; no two-cut recipe has been rendered with different `xh` |
| Parametric lineage (Metafont, MM) | pen on skeleton; masters interpolated | this generator | the two standard criticisms (skeleton-first letters, parameter overload) are stated in `generator.md` section 1 as the risk the review loop exists to catch |

Each recipe in `concepts.genres.js` carries `name` (the genre), `from` (one sentence on what defines
it) and `desc` (the limit, verbatim from the table), so the round-1 page shows the limit beside the
render. `concept-pipeline.md` section 1 says: name each round-1 concept's genre from `genres.md`
beside its brand name, and build the spectrum so that at least three genres appear; the reviewer brief
(`reviewer-brief-concepts.md`) asks the reviewer to name the genre it sees for each concept, and to say
where the render falls short of it. `templates/concepts.example.js` gains a comment per entry naming
its genre, and two entries (`slab`, an Egyptian; `grot`, a grotesque) so the example spectrum covers the
new knobs. `guidelines.md` section 3 points at `genres.md` for the vocabulary of the contrast axes.

### 5.2 Rendering before claiming

`smoke.sh` step 6b builds `out/smoke/pages/genres.html` with
`node scripts/concepts/build-page.js --template round1 --concepts templates/concepts.genres.js --content scripts/concepts/content.minimal.json`
(the round-1 template reads per-concept content optionally, `round1-template.html` line 259 **(read)**,
so the minimal content serves); `--full` step 8b shoots it at 500 and 1280 with `--dump-dom` and no
`--family` (the comparison face is Georgia, installed; `concept-pipeline.md` section 4 says how that
reading is weaker) and asserts `data-fd-rendered > 0`. Work item C3: a fresh strong-model reviewer
reads the shots with a brief derived from `reviewer-brief-concepts.md` and, per recipe, answers "does
this read as the genre named, and what is the first thing that says it does not?"; the host fills the
"reaches" column from that reading (yes / partly with the reviewer's limit sentence / stays candidate
with the reason), and records the date and the shot directory in `genres.md`.

### 5.3 Tests

`tests/test_genres.py`:

- `test_every_genre_recipe_passes_params_and_exports_two_compatible_masters`: for each concept in
  `concepts.genres.js`, `params()` at mult 1 and 1.5 (and the italic flag), then `glyph()` over every
  key, and the structure+record comparison the exporter makes (restated: polygon counts, point counts,
  runs, `sig`); zero incompatible glyphs. **Weakest mutation, one that must fail on every recipe**
  (review F009: `xs 0.86` moves a serif-kind branch, so it cannot fire on a sans recipe): in `glyph()`,
  `samplePath(st.d, counts[si])` → `samplePath(st.d, sampleCounts(st.d))`, which takes the sample counts
  from the FITTED path (the Driftwood defect that pinned sampling fixed): the flat and round fits move
  endpoints by `hwFlat`, which follows `W`, so the Bold's counts differ from the Regular's on every
  recipe → red naming glyphs. `xs 0.86` stays as a second, serif-only mutation, with the reason it cannot
  fire on the grotesque written beside it.
- `test_the_genre_table_and_the_recipes_name_the_same_concepts`: the first column of every table row
  in `genres.md` that carries a recipe names a concept id present in `concepts.genres.js`, and every
  recipe id appears in the table; a row marked **no** names no id. Mutation: a recipe renamed.
- `test_the_genres_page_builds_and_names_every_recipe`: `build-page.js` round 1 over the file; the page
  contains each recipe's id as a `?face=` target (read from the built HTML's embedded concepts).
  Mutation: the page built from `concepts.example.js` → red (ids differ).
- `tests/test_schemas_and_concepts.py::test_every_concept_passes_params` is parametrised over
  `concepts.genres.js` too (one line; C owns the file, review F011).

### 5.4 Docs

`references/genres.md` (new), `references/concept-pipeline.md` section 1, `templates/reviewer-brief-concepts.md`,
`templates/concepts.example.js`, `references/guidelines.md` section 3, `generator.md` section 1 (the
lineage, two sentences; A writes it from C's text), `SKILL.md` reference index (one line),
`scripts/smoke.sh` steps 6b and 8b.

### 5.5 Out of scope

Skeleton changes a genre needs: a circular `O`, a spurred `G`, a single-storey roman `a` in `G`, a
Tuscan serif, two-tone strokes, bar-height knobs, an expansion contrast model, the pointed apex. Each is
named in the table's last column so the next version can pick one.

---

## 6. Item 10 — the per-round visual diff

### 6.1 Design

`scripts/diff.py OUT --font font.json --before DIR [--after DIR] [--sizes PX ...] [--scale N]`:
renders every title of `font.json` `titles` (plus `review.wordmark` when set) at every size in
`review.sizes` (or `--sizes`), at every named instance of every group, from the fonts in `--before`
(a folder holding the previous build's group files by their configured names: the host copies `out/`
to `work/round-<N−1>/` before each build, `cp -R`, never `rm`) and in `--after` (default: the
`font.json`'s `out_dir`), and pixel-diffs each pair. Rendering: the woff2 is read by fontTools,
instanced at the instance's location with `varLib.instancer` (what `build.py --static` uses, so what
the reviewer sees is what a static would be), **given a one-instruction `fpgm` (`SVTCA[0]`)**, saved to
a temp TTF and drawn by Pillow with `layout_engine=ImageFont.Layout.RAQM` (GPOS kerning and `liga`
apply; `features.check("raqm")` is asserted and the run refuses without it, naming `requirements.txt`),
`anchor="ls"`, grey antialiasing, at `size × --scale` pixels (default 2) on canvases of identical size
(the wider advance plus a margin).

**Hinting (trap 2), measured.** FreeType via Pillow autohints the shipped fonts as they are: the neutral
roman renders identically with its `prep` removed and differs by 212–255 grey levels once a
one-instruction `fpgm` is added (section 0, measured 2026-11-16 at 16 and 40 px). The first draft of
this plan inferred from memory that the `prep` table would prevent autohinting; it does not, and
review finding F010 asked for the measurement that showed it. `diff.py` therefore renders every
instance through the same `fpgm` trick `build.py`'s raster self-checks use (`raster_font_file`, lines
582–584 **(read)**), records `"hinting": "autohint suppressed by a one-instruction fpgm (trap 2)"` in
`diff.json`, and the probe the first draft proposed is dropped: a "with and without `fpgm`" comparison
cannot tell "not autohinted" from "the `fpgm` did nothing". The guard is the test in 6.2 instead.

Output: `OUT/diff.json` (per group × instance × size × title: `changed_px`, `share`, `bbox`, the two
advance widths; the renderer and versions: Pillow, FreeType, fontTools; the hinting line; the layout
engine), `OUT/diff.md` (the changed entries sorted by `share` descending, then "N of M renders
unchanged", then the renderer line), and one PNG per CHANGED entry, `<group>-<instance>-<size>px-<slug>.png`:
before (black on white), after, and the diff (red where `after` has more ink, blue where less, grey
where both do), stacked. A changed pixel is `|a − b| > 8` of 255. Unchanged entries get no PNG. Exit 0
whether or not anything changed; exit 2 when `--before` lacks a group's file (named) or `--after` does.
**What it proves**: what FreeType drew on this machine from the two files at these sizes, unhinted; not
CoreText, not Chrome, not the page's CSS. The docs say so in one sentence beside every mention.

The reviewer brief gains a slot: "What changed since round N−1: `{{diff dir}}/diff.md` (N of M
renders changed) and the triptych PNGs; the parameter changes, as numbers". The host's two spot-checks
(`review-loop.md` section 6) are aimed at the two largest `share` entries.

### 6.2 Tests (`tests/test_diff.py`)

| Test | Asserts | Weakest mutation (applied by hand, recorded in the docstring and `testing.md` section 8) |
|---|---|---|
| `test_diff_reports_no_change_between_a_font_and_itself` | the neutral `out/` against a copy of itself: every entry `changed_px == 0`, `diff.md` says "0 of M renders changed", no PNG written, exit 0 | the `before` render at `size × scale + 1` pixels (a mismatch that reports everything changed) |
| `test_diff_sees_a_moved_glyph_in_the_titles_that_use_it_only` | a copy of the neutral roman with `o`'s default outline shifted +30 units in x (fontTools `glyf`, the deltas untouched, so every instance moves): every title containing `o` has `changed_px > 0` at every instance and size, `SIX WAYS OUT` has 0, the PNG for one changed entry exists and its diff panel holds red or blue pixels inside the reported `bbox` | `after` rendered from the `before` path (nothing changes) |
| `test_diff_lays_out_with_kerning_so_a_kern_change_shows` | a copy with one GPOS pair value changed by +80, the pair chosen by reading the font's PairPos for two glyphs adjacent in a `titles` entry: that title changes, a title without the pair does not; `diff.json` records `layout: raqm` | `layout_engine` forced to BASIC (GPOS ignored, nothing changes); skipped loudly, never silently, when raqm is absent |
| `test_diff_renders_every_instance_at_every_size` | entry count = Σ groups (instances × titles × sizes); the Bold entry of a glyph shifted in the Bold master only (a copy whose `gvar` delta for `o` at the `wght` max is enlarged) changes while the Regular entry does not | the instance loop reduced to the default location |
| `test_diff_renders_without_the_autohinter` | `diff.py`'s renderer, given the neutral Regular instance, draws `B` at 16 px (scale 1) differently from plain Pillow on the same instanced TTF without the `fpgm`: max grey difference > 100 (212 measured here); `diff.json` carries the hinting line | the `fpgm` insertion removed (the two renders are equal) |

Plus `test_docs_commands.py` (existing) over the documented `diff.py` lines, and
`tests/test_tools_and_templates.py::test_the_review_checklist_and_the_reviewer_brief_ask_for_the_proof_rows`
extended to require the brief's "what changed" slot to name `diff.md` (a data assertion on a template).

### 6.3 Docs

`review-loop.md` section 1 (the round gains "copy `out/` → `diff.py`"), section 2 (the tool, with
what it proves, the hinting fact), section 6 (spot-checks aimed by `share`); `templates/reviewer-brief-design-round.md`;
`templates/font-record.md` (one line: the diff directories per round); `SKILL.md` phase 8 (one
sentence) and tool table (one row); `references/fallbacks.md` "No Chrome" (the diff still runs: it is
FreeType evidence, not browser evidence); `templates/font.schema.json` (`review.sizes` description:
"specimen.py and diff.py render every one"); `references/traps.md` row 2 gains "the shipped fonts are
autohinted by FreeType as they are (`prep` does not prevent it, measured 2026-11-16); `diff.py` uses the
same `fpgm`" (host applies B's text); `scripts/smoke.sh` step 2b (the neutral `out/` diffed against a
copy of itself: "0 of M renders changed"). CHANGELOG. `process.md` phase 8 line (host).

### 6.4 Out of scope

A Chrome-shot diff (two `shoot.py` runs of the same page); a tree diff of the font tables (fontTools
`ttx` does it; one sentence in `review-loop.md` says how); word lists beyond the project's titles;
cross-machine comparison.

---

## 7. Ordering, the work split, file ownership, the CHANGELOG

### 7.1 Decision

Items 3, 4 and 9 all edit `strokePolys`, `fitSkeleton`, `serifPoly`/`diagSerifPoly` and `params()`,
and each must leave the three examples byte-identical before the next starts, so they are **serial, one
agent (A), in the order 3 → 4 → 9**, with a handback after each item so the host runs the compatibility
test and `--check` between them. Item 10 touches none of that and is **parallel (agent B)** from the
start. Item 2 needs the parameters of 3 and 4 for six of its recipes and `joints` for two, so **agent C
starts after A2 is accepted** and adds the grotesque/geometric `joints` lines after A3; C can write the
history columns and the "no" rows while A works, in its own files. The critical path is A (three items)
plus C3's render review; B finishes inside A's window. The split saves roughly the length of item 10
(the second-largest item) against the briefing cost of two extra agents, well over the one-fifth rule.

### 7.2 File ownership (no file has two writers)

| Owner | Files |
|---|---|
| **W0 (host, before anything)** | `tests/baseline_digest.py`, `tests/fixtures/baseline-0.1.0.json`, `tests/test_backward_compat.py`; a copy of the three `examples/*/out/` to `BASELINE_OUT`, a scratch directory outside the repo |
| **A** (items 3, 4, 9) | `scripts/gen.js`; `scripts/tests/test_font.py` (new tests), `scripts/tests/mutate.py` (new entries), `references/generator.md`, `references/testing.md` (header list, section 2 rows, section 8 for A's guards); the branch-margin measurement (A2m). **Nothing under `tests/`** (review F011): the repo runs A's tests through `tests/test_copy_into_site.py`, which copies `scripts/` into a sample site and runs the suite |
| **B** (item 10, junction row) | `scripts/diff.py` (new), `tests/test_diff.py` (new), `scripts/specimen.py`, `scripts/specimen.html.tmpl`, `tests/test_tools_and_templates.py`, `references/review-loop.md`, `templates/reviewer-brief-design-round.md`, `templates/font-record.md`, `templates/font.schema.json`, `references/fallbacks.md` |
| **C** (item 2) | `references/genres.md` (new), `templates/concepts.genres.js` (new), `tests/test_genres.py` (new), `tests/test_schemas_and_concepts.py` (the one-line parametrisation), `templates/concepts.example.js`, `templates/reviewer-brief-concepts.md`, `references/concept-pipeline.md`, `references/guidelines.md`, `scripts/concepts/README.md` |
| **Host** (integration) | `SKILL.md`, `README.md`, `CHANGELOG.md`, `VERSION`, `scripts/smoke.sh`, `references/process.md`, `references/traps.md`, `.github/workflows/ci.yml` if a step is added; the Fable genre review (C3); the acceptance runs; the Impasse reviews |

Where an agent needs a line in a host-owned or another agent's file (B's `testing.md` rows and
`traps.md` sentence, C's `process.md` phase-3 sentence and `generator.md` lineage sentences, the
`smoke.sh` steps of B and C), it writes the exact text into its handback report and the host or the
owner applies it. Agents run in one worktree; the Edit tool rewrites a whole file, so two writers on
one file would lose an update.

### 7.3 CHANGELOG

Agents do not edit `CHANGELOG.md`. Each handback ends with a section `### CHANGELOG` holding its entry
text in Keep-a-Changelog form (Added / Changed / Docs / Designed, not built), one bullet per parameter
or tool, each naming its test and its mutation count. The host writes `## [0.2.0] — <date>` once, in
item order (3, 4, 9, 2, 10, then the compatibility guard), and pastes `references/testing.md` section 8
survivors there as findings, the way 0.1's entry does. `VERSION`, the frontmatter and the README badge
move to `0.2.0` in the same host commit, and `tests/test_versions_and_skill.py` holds them equal.

### 7.4 Briefing the agents

Each agent gets: this plan (its sections only, plus sections 1, 7 and 12), the files it owns, the rule
that the compat test and the full font suite on the neutral example must be green at every handback,
the "watch it fail" rule with the named mutations, and the instruction to report any mutation that
stays GREEN or UNPROVEN as a finding, not to rewrite the mutation until it fails. A's brief names the
byte-identity rule of section 1.1 as the first thing to verify after every edit
(`.venv/bin/python3 -m pytest tests/test_backward_compat.py -q`) and the decision rule of section 3.2
as the second.

---

## 8. Acceptance runs

In this order, on this machine, after integration and before the Impasse diff review:

1. `cp -R "$BASELINE_OUT"/<ex>/. examples/<ex>/out/` for the three examples (`BASELINE_OUT` is the
   scratch directory W0 copied the 0.1.0 outputs to), then
   `.venv/bin/python3 scripts/build.py --font examples/neutral/font.json --check`,
   `.venv/bin/python3 scripts/build.py --font examples/bract/font.json --check --no-requirements`,
   `.venv/bin/python3 scripts/build.py --font examples/driftwood/font.json --check --no-requirements`:
   every group `font identical`, and the manifest lines list `manifest.sources_sha256` as the only
   differing key (review F001: the source hashes change by definition; `tools` too on another machine).
2. `.venv/bin/python3 -m pytest tests -q`: the repo suite, including `test_backward_compat.py`
   (all three digests), `test_diff.py`, `test_genres.py`.
3. `bash scripts/smoke.sh --full` (needs node and Chrome): steps 1–11 plus 2b (diff of the
   neutral `out/` against itself), 6b (the genres page builds), 8b (the genres page shot and executed),
   9 (the junction row present), and step 5's mutation run reporting every mutation RED, the new
   entries included, 0 problems.
4. `.venv/bin/python3 scripts/tests/mutate.py --font examples/neutral/font.json --requirements examples/neutral/requirements.json --static-dir examples/neutral/out/static --list`
   names every new mutation (6 optical, 9 x-height, 3 bracket, 1 joints, 4 crotch, 1 apex refusal); the
   run in step 3 is the proof.
5. The genre renders: `out/smoke/shots*/genres-500@1x.png`, `genres-1280@1x.png` read by a fresh Fable
   subagent (C3); the table's "reaches" column filled from its reading; two of its claims spot-checked
   by the host on the PNGs.
6. `.venv/bin/python3 scripts/fontbakery-gate.py --font examples/neutral/font.json --requirements examples/neutral/requirements.json` (unchanged, must stay green).
7. Impasse review of `git diff --cached` (code, tests, docs) with `templates/impasse-diff-instruction.txt`;
   reconcile; one re-review; then one commit.

---

## 9. Risks, and what is explicitly out of scope

**Risks**

- **A V8 arithmetic difference between node versions moves the export digest** (section 1.1): the
  fixture keys digests by node major; a CI difference is a recorded second digest after a `--check`
  confirms the 0.1.0 tree, never a loosened test.
- **The decision-rule margins for straddling curves** (section 3.2) are unmeasured for the real
  implementation; A2m measures them before A2's tests are written, and `test_xh_does_not_change_any_branch_record`
  holds them for the project's own concepts afterwards.
- **A pre-existing fragility, not caused by 0.2:** the neutral example's italic `w` first-stroke serif
  kind reads `|T[0]|` 0.103 against the 0.1 threshold in the Regular (`xs` 0.92) and 0.123 in the Bold.
  Any future change to `xs`, the italic narrowing or the `w` skeleton can flip it and the exporter will
  refuse the italic group. Recorded in `generator.md` section 12; not fixed here.
- **`ROUND_GAIN_RADIUS` and the optical ranges** are design constants from no source; the genre
  renders are where they are judged, and `generator.md` names them so a project can change them.
- **A reviewer may call a candidate recipe short of its genre**; the table then stays "candidate" with
  the reason, which is the honest outcome, not a failure of the plan.
- **`SKILL.md`'s 500-line limit**: 475 today; the additions are six lines at most. If the phase-8
  sentence does not fit, it goes to `review-loop.md` and `SKILL.md` keeps the tool-table row.
- **The manifest is unchanged**, so a reviewer reading `manifest.json` cannot see a project's `xh` or
  optical knobs; they are in `concepts.js`, which the manifest hashes. A manifest schema v2 that echoes
  them is a 0.3 item, because it breaks `--check` on every 0.1 site at upgrade.
- **`diff.py` renders unhinted FreeType grey**, which is what `build.py`'s self-checks compare too; it
  is not what any browser draws. The docs say so wherever the tool is named.

**Out of scope for 0.2** (each named where it arose): `apex` (designed, section 4.4); weight-dependent
optical factors; an expansion contrast model; `capH`, ascender/descender knobs, `xh` per `mult`; ink
traps, per-glyph apex exceptions, the `W` inner apex; skeleton redraws for any genre (circular `O`,
spurred `G`, roman single-storey `a`, Tuscan serifs, two-tone strokes, bar heights); a Chrome-based
diff; a table diff; the manifest echoing the new parameters; changing the default joint behaviour of
sans concepts (opt-in only).

---

## 10. Questions for the operator

1. **The pointed apex is deferred.** The first draft asked whether to build it behind a gate; the
   review's arithmetic (section 4.4) changed the recommendation: `joints` and `crotch` ship, `apex` is
   refused by `params()` and fully designed in `generator.md` for 0.3. Confirm the deferral, or ask for
   the `A`-only version (which would need a per-glyph exception list that is itself out of scope).
2. **`references/genres.md` as a new file** (one line in `SKILL.md`'s reference index) rather than a
   section of `concept-pipeline.md`. I recommend the new file: the table is the length of a reference
   and `concept-pipeline.md` is about the rounds, not the vocabulary.
3. **Skeleton work stays out.** The genre table will say "no" or "partly" for Tuscan, Art Deco, the
   geometric `O` and single-storey `a`, the spurred `G`, and the pointed apex. I recommend confirming
   that 0.2 draws no new skeleton, so the five items stay reviewable in one diff.

---

## 11. Work items

| id | title | kind | files | verifiable_by |
|---|---|---|---|---|
| W0 | Record the 0.1.0 baseline digests (export, TTF, manifest minus hashes/tools/woff2 figures) and copy the three example outputs to `BASELINE_OUT` outside the repo; the compat test watched red on 0.1.0 under `Math.round(g.adv) + 1` | test-new | tests/baseline_digest.py, tests/fixtures/baseline-0.1.0.json, tests/test_backward_compat.py | `.venv/bin/python3 -m pytest tests/test_backward_compat.py -q` green on `0fc4314`; red under the export.js mutation; `ls "$BASELINE_OUT"/{neutral,bract,driftwood}` |
| P1 | Impasse review of this plan; findings reconciled (section 12) | docs | docs/plan-0.2.md | section 12 names every finding with its verdict and the evidence read or run |
| A1 | Item 3: `penWidth()` with `hzThin`, `roundGain`, `diagThin`, `P.optical`; fit and corner follow; range refusals | code | scripts/gen.js | compat test green; `test_optical_corrections_change_only_the_strokes_they_name` green |
| A1t | Item 3 tests (single-knob variants plus the product variant) and the six mutations; testing.md rows | test-new | scripts/tests/test_font.py, scripts/tests/mutate.py, references/testing.md | `mutate.py --only optical` 6 RED, 0 problems |
| A1d | Item 3 docs: generator.md sections 3, 4, 7; the hairline sentence rewritten | docs | references/generator.md | `pytest tests/test_docs_commands.py -q` green; the three rows present with ranges and refusals |
| A2m | With the decision rule implemented, measure every branch decision's margin for every lowercase stroke of the three examples' concepts at `xh` 400 and 600 (roman, italic, mult 1 and 1.5); measure the `o` sidebearing and `o|o` kern shift at `xh` 600 between band 500 and 600 | code | references/generator.md | the figures recorded in generator.md section 12 and in the A2 handback; the smallest margin named |
| A2 | Item 4: the `xh` map in `fitSkeleton` (literal keys, mapped targets, the mapped set, rings, early return), `ptsU` and the decision rule in `glyph()`/`strokePolys` (curved, tear side, curl, vert, serif kind, beak thresholds, partner directions), the dot rule on the unmapped `dy`, the spacing band, `serifBracket` in three serif constructions | code | scripts/gen.js | compat test green; the three example groups export; `test_xh_does_not_change_any_branch_record` green on the neutral example (italic included) |
| A2t | Item 4 tests (`xh` lines, branch record, spacing band, slab serif) and twelve mutations | test-new | scripts/tests/test_font.py, scripts/tests/mutate.py, references/testing.md | `mutate.py --only xh --only bracket` all RED, or the kern-band mutation SKIPPED with the recorded reason |
| A2d | Item 4 docs: generator.md sections 1, 4, 7, 8, 12 (the decision rule, the margins, the italic `w` fragility) | docs | references/generator.md | docs tests green; the margins from A2m present |
| A3 | Item 9: `joints`, `crotch` with the record token, `CROTCH_LEN`; `params()` refuses `apex` | code | scripts/gen.js | compat test green; `test_joints_opt_in…`, `test_crotch_thins_only…`, `test_apex_is_refused_until_built` green |
| A3t | Item 9 tests and six mutations | test-new | scripts/tests/test_font.py, scripts/tests/mutate.py, references/testing.md | `mutate.py --only joints --only crotch --only apex` all RED |
| A3d | Item 9 docs: generator.md sections 2, 4, 5, 12 and the "Designed, not built: `apex`" section with 4.4's construction and table | docs | references/generator.md | docs tests green; the section carries the table of 4.4 |
| B1 | `scripts/diff.py`: instancing, the `fpgm` insertion, raqm layout, `diff.json`, `diff.md`, triptychs | code | scripts/diff.py | `diff.py out/diff --font examples/neutral/font.json --before examples/neutral/out` exits 0 and reports 0 of M changed |
| B1t | `tests/test_diff.py`: the five tests, each with its by-hand mutation recorded | test-new | tests/test_diff.py | `.venv/bin/python3 -m pytest tests/test_diff.py -q` green; each docstring names its mutation and the date it was watched red |
| B2 | The junction row in the specimen and its test | code | scripts/specimen.py, scripts/specimen.html.tmpl, tests/test_tools_and_templates.py | `test_the_specimen_carries_the_junction_row` green, red under an empty row |
| B3 | Item 10 docs: review-loop.md, the design-round brief, the record template, schema description, fallbacks; the traps row-2 sentence handed to the host | docs | references/review-loop.md, templates/reviewer-brief-design-round.md, templates/font-record.md, templates/font.schema.json, references/fallbacks.md | docs tests green; the brief's "what changed" slot names diff.md |
| C1 | `references/genres.md` with the table (every recipe "candidate"), `templates/concepts.genres.js` with one recipe per reachable row, none setting `apex` | docs | references/genres.md, templates/concepts.genres.js | `node -e` loads the file; every recipe passes `params()` |
| C1t | `tests/test_genres.py` (three tests) and the parametrisation of `test_every_concept_passes_params` | test-new | tests/test_genres.py, tests/test_schemas_and_concepts.py | green; red under the fitted-path sample-count mutation on every recipe and under a renamed recipe |
| C2 | Item 2 docs: concept-pipeline.md section 1, the concepts brief, concepts.example.js (genre comments, `slab`, `grot`), guidelines.md section 3, scripts/concepts/README.md | docs | references/concept-pipeline.md, templates/reviewer-brief-concepts.md, templates/concepts.example.js, references/guidelines.md, scripts/concepts/README.md | `test_every_concept_passes_params` green on the example file; docs tests green |
| C3 | Render the genres page (smoke 6b/8b), a fresh Fable reviewer reads the shots, the "reaches" column is filled with the date and the shot directory | live-acceptance |  | genres.md's table has no "candidate" row without a reviewer sentence; two reviewer claims spot-checked by the host |
| H1 | Integration: SKILL.md (tool row, index line, phase 8 sentence, version), README badge, VERSION, CHANGELOG.md from the handbacks (with the "Designed, not built" heading), smoke.sh steps 2b/6b/8b/9, process.md, traps.md row 2 | docs | SKILL.md, README.md, CHANGELOG.md, VERSION, scripts/smoke.sh, references/process.md, references/traps.md | `pytest tests/test_versions_and_skill.py tests/test_docs_commands.py tests/test_ci_workflow.py -q` green |
| H2 | Acceptance runs of section 8 | live-acceptance |  | the seven steps of section 8 with their outputs pasted into the commit message |
| H3 | Impasse review of the staged diff, reconcile, one re-review, commit | live-acceptance |  | the review record names every finding and its verdict; one commit on `v0.2-font-research` |

---

## 12. Plan review reconciliation (Impasse, cross-provider, 2026-11-16)

Fourteen findings on the first draft. Each was checked against the code or measured before this
plan changed; the coordinator verified F001, F004, F006 and F013 independently. Where this section
disagrees with the first draft, this plan's body already carries the change.

| # | Finding | Checked how | Verdict | What changed |
|---|---|---|---|---|
| F001 | `--check` cannot print "manifest identical" after a `gen.js` edit: the manifest holds `sources_sha256` | `build.py:1273` (read); `scripts/tests/test_font.py:530–531` compares them (read) | accepted | Section 1.1 restates byte-identity as woff2 bytes identical and the manifest identical except `sources_sha256` and `tools`; the baseline gains a `manifest_sha256` over the manifest minus those keys and the brotli-dependent `woff2_sha256`/`woff2_bytes`; acceptance step 1 names `manifest.sources_sha256` as the only differing key |
| F002 | The apex construction gives a 208-unit flat top, not a point | `apex.py` (measured): with both edges cut level after the drop, each inner endpoint lands 103.9 units from the apex x for the `A` at `W` 96 | accepted | Section 4.4: the construction redone as the outer-edge intersection `Q` and the inner-edge intersection `C`, with the arithmetic for `A`, `V`, `N`, `M` at Regular and Bold; and `apex` is deferred, because the same arithmetic puts the Bold `M`'s crotch at y = 26 |
| F003 | `δ` can have an x component; the `moved` map rewrites y only; partners are found after `fitSkeleton` | `gen.js` 648, 669, 675 (`p.ny`, `pp.t[p.ix + 1]`: y only) and 735–747 (partners on fitted samples) (read); `apex.py`: `Q_x` = 333.3 for the `A`, 52.9 for the `N`, so `δ_x` ≠ 0 | accepted in part | The construction keeps `P'` at `x0` and moves it in y only, so `Q` absorbs `δ_x` and no x token is rewritten (the `N`'s stem stays plumb; `apex.py` gives `Q` = (52.9, 710) for a stem at x 100 with its outer edge at 100 − 47); the ordering point is accepted: `fitSkeleton` must find the joint itself on the unfitted endpoints and annotate the strokes. Both are in the deferred design, section 4.4 |
| F004 | Legal `xh` flips the italic `w`'s serif kind (0.127 → 0.061) | arithmetic reproduced (`xhflip.js`, measured): 0.127 at 500, 0.100 at 549, 0.061 at 640 for `xs` 1; 0.103 / 0.078 / 0.042 for the neutral's `xs` 0.92 | accepted, and widened | Section 3.2: every branch decision is taken on unmapped coordinates (`ptsU`), so `xh` cannot move one; `test_xh_does_not_change_any_branch_record` with mutation `xh-branch-mapped`; the neutral italic `w`'s 0.003 margin today recorded as a pre-existing fragility (section 9) |
| F005 | The band scale is 0.417 at `xh` 640, not 0.76; the curl threshold is unchecked | the map's arithmetic; the probe showed the apostrophe tail's `curved`/tear flips and the caron arms' `vert` flip (0.63 → 0.32) at 640 (measured, with the probe's limits stated in 3.2) | accepted | Range narrowed to [400, 600]; the apostrophe exempt from the map; the curl test, the tear side, `vert`, `curved`, the serif kind and the beak thresholds all read unmapped coordinates; A2m measures the straddling-curve margins |
| F006 | At `xh` 600 the colon's upper dot maps to 504 and misses the dot rule; dots pass through `fitSkeleton` unchanged | `gen.js` 751–752 (`380 < dy < 460`), 662 (`if (!pp) return st`) (read) | accepted | Section 3.1: the dot rule reads the unmapped literal `dy`; other dots of mapped glyphs take `ymap(dy)`; assertion g and mutation `xh-dot-mapped` |
| F007 | The diagonal expectation ignores the `hzThin` factor applied at the same time | the first draft's variant applied all three knobs at once; `cos²θ` at the `x`'s 51° is 0.39, so the product differs from the single-knob expectation by 3.9 % | accepted | Section 2.3: one variant per knob (a–g) plus a product variant (e2) with the full product restated; the other assertions were checked (b, c, d, f, g isolate one factor by angle) |
| F008 | `W·thin·hzThin` is not the minimum for legal values | the formula: `thin 1, diagThin 0.5` gives `0.5·W` at 45° | accepted | Section 2.1: no closed form is claimed; the floor rests on the exporter's measured `minStrokeWidth` and `build.py`'s recomputation from the polygons (`min_interior_stroke_width`, line 876, read), which never used a formula |
| F009 | `xs 0.86` cannot fail on a sans recipe (the `w` flip is a serif-kind branch) | `gen.js` 609: the kind test is inside `mode === "serif"` (read) | accepted | Section 5.3: the mutation is now the fitted-path sample count (`sampleCounts(st.d)` on the fitted string in `glyph()`), which breaks every recipe; `xs 0.86` kept as a serif-only second mutation with the reason |
| F010 | Show which glyph and size makes the with/without-`fpgm` bitmaps differ, or replace the detector | measured: the neutral roman renders identically with `prep` removed (0 levels) and differs by 212 (`B`, 16 px), 246 (a title, 16 px), 255 (40 px) once a one-instruction `fpgm` is added | accepted, and it overturned the first draft's inference | Section 6.1: the shipped fonts ARE autohinted by FreeType via Pillow; `diff.py` renders through the `fpgm` trick `build.py` already uses; the probe is dropped (it could not tell the two cases apart) and replaced by `test_diff_renders_without_the_autohinter` (> 100 levels, 212 measured); `traps.md` row 2 gains the measurement |
| F011 | A and C1t both write `tests/test_schemas_and_concepts.py` | section 7.2 of the first draft (read) | accepted | A owns nothing under `tests/` (its tests reach the repo suite through `tests/test_copy_into_site.py`); C owns the parametrisation |
| F012 | "yes, candidate" is not a value the honesty column has | section 5.1 of the first draft | accepted | Every recipe is "candidate" (or "candidate for partly" where a limit is already known) until C3; the one "yes" is the Scotch roman, which shipped as a reviewed round-1 concept |
| F013 | The diagonal serif has 26 points, not 25 | `diagSerifPoly` 433–438: one `push`, four `quad()` of six, one `push` (read) | accepted | Section 3.3 and the slab test's count assertion (26, 15, 26) |
| F014 | The apex deferral had no integration path | sections 4.5, 5.1 and 11 of the first draft | accepted | The deferred branch is now the plan: `params()` refuses `apex` (test `test_apex_is_refused_until_built`, mutation `apex-accepted`), the geometric recipe sets no `apex` and its row says so, `generator.md` gains "Designed, not built: `apex`" with the construction and table, the CHANGELOG gains the heading, work items A3/A3t/A3d/C1 carry it; owners named |

No finding was rejected outright. F003 is accepted in part: the x rewrite is unnecessary under the
y-only move, which the arithmetic shows (`Q_x` ≠ `x0` is where the asymmetry goes, and the stem keeps
its x); the ordering point stands.
