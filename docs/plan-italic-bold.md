# Plan: an italic group takes a Bold master, and the italic opening quotes hold their ink

WHAT IT'S FOR: the implementation plan for two small defects a user's italic met when it needed a Bold master,
written by Claude (Fable 5.1) on 2026-11-19 on branch `fix/italic-bold-master` from `origin/main` at `5d0b29f`
(0.5.0), before any code, for independent review (Impasse) and then implementation. The motivating face is the
Driftwood example (`examples/driftwood/`, already public); its shipped italic group runs ×1 to ×1.3 and the user
wanted ×1.65.

Status: **reviewed by Impasse before code (section 9), built 2026-11-19; not yet committed.** Sections 0 to 8 are the plan
as reviewed, kept as the record of what was decided and why; section 9 and the "As built" paragraph below say where the
build departed from them, and those win.

**As built (2026-11-19).** Fix B (section 1.2) and the opening-quote rule (section 1.3) as planned, the eight generator
lines and the one builder helper. Departures: (1) the tests live in `tests/test_weight_decisions.py` with the node half in
`tests/weight_flips.js`; test (c) in the font suite compares structure (polygon and point counts, runs) as well as the
record, and its curls variant goes red at 0.5.0 on the `a` at mult 2 (a curl end dropped to a disk), not only on the `w`;
(2) test (d) rounds the instanced bounds as a saved static stores them and allows a two-unit bearing difference at an
intermediate (three roundings on an integer result; the plan's one unit was a measurement of rounded values and failed on
the correct code at the neutral `Medium Italic`, 12.00 / 10.60 before rounding), one unit at a master; (3) the F002 T-join
pin asserts both `L` and `R` appear across the weights, not that the set equals {L, R}: the leg stands perpendicular at one
weight and records `=`; (4) the F003 check runs the 0.5.0 generator from git beside the current one and tests the overlap
wherever their serif kinds disagree (27 cases over the five files), with a floor of 20 so agreement everywhere fails the
count; (5) the F006 fixture needs two glyphs, because one threshold cannot sit on both sides of the correct half width (30)
against the two wrong ones (21.2 under `thin: P.thin`, 42.4 under the fit at `P`); M3b is green against the concept files, as
section 4 allowed, and red on the fixture and on the font suite's curls variant (`K`); (6) test (f) had two defects of its
own found by running it: fontTools' `Panose` compares by identity and `GlyphOrder` is not a table, both fixed before the
mutations that exposed them were re-run; (7) the before/after picture of the `w` named in section 9 is kept outside the
repository (it publishes no images); (8) two catalogue mutations in `mutate.py` broke under the change and were re-formed
(`quotes-#23` no longer matched its line; `xh-curl-mapped` crashed node instead of failing, because the reference copy of a
stroke now exists at every multiplier but 1), both RED again, recorded in `references/testing.md` section 8. The compatibility baseline follows section 5 with the placeholder `COMMIT_A`, the
`darwin/26` entry taken from the fixed tree's `--print` output (the `--record` guard needs the commit to exist), and the
four other platform entries dropped until the `record-baseline` workflow records them from commit A, as 0.5.0's commit A
did. Measured again from the committed tests: 44 cases at 0.5.0 (bract 15, driftwood 3, neutral 2, the example template
13, genres 11), 220,080 comparisons, 0 flips after the fix; every opening-quote advance of section 1.3 equal to the
test's expectation from the 0.5.0 export's apostrophe.

Every number below was produced, before the build, by running `node` and the skill's
venv Python against the unmodified tree at `5d0b29f` and against modified copies of it in a scratch folder
outside the repository (a copy with the `w` skeleton change the operator proposed, two copies with the
decision-rule change of section 1.2, one of them also carrying the quote rule of section 1.3). The scratch
scripts are not evidence anyone else can re-run; the tests of section 4 commit each measurement, and every
figure here is to be re-stated from their output before the version is bumped (the rule 0.5.0 set,
`docs/plan-r-leg.md` F008).

**Markers.** **(read)** = checked against the named file. **(measured)** = run or counted here.
**(inferred)** = not verified; the implementer must check before relying on it.

## 0. The defects, exactly

### 0.1 An italic group cannot carry a master much heavier than the Regular

`node scripts/export.js` on the Driftwood example's `font.json` with the italic group's masters at ×1 and ×1.65
(axis 400–700) exits 1 (measured): "1 glyph(s) differ in structure or branch outcome between masters of group
italic: w", the Regular's first stroke recording `serifA=head` and the Bold's `serifA=diag`.

The cause is not the pen width. `strokePolys` picks a serif's kind from the end's unit direction `TU`
(read: `scripts/gen.js` line 790, `|TU[1]| > 0.5 && |TU[0]| > 0.1 → diag`, else `head`), and with the x-height
map off `TU` is the DRAWN tangent (line 718: `TU = pu === pts ? T : …`). The drawn x of every skeleton point is
`x · xs · (1 + 0.16·(W/W0 − 1)) · 0.95 + tan(10°)·y` (read: `xf`, line 350), so the direction of the italic
`w`'s first stroke `S("M 10 500 L 170 0", "s", "")` (line 197) is `dx = 160 · 0.95 · xs · (1 + 0.16·(mult − 1)) − 88.2`
over `dy = 500`; the shear nearly cancels the stroke's own slope, and what is left sits on the threshold
(`|TU[0]| = 0.1` is `|dx| ≈ 50.3`). The term that moves with weight is the `1 + 0.16·(mult − 1)` widening.
Measured on the five concept files (every serif concept, italic, mult 0.8 to 2.0 in steps of 0.05, the value
read from a debug copy of `gen.js` that appends `TU` to the record), and the formula reproduces every value to
four places:

| `xs` (concepts) | `|TU[0]|` at ×1 | at ×1.5 | at ×1.65 | kind flips from `head` to `diag` at |
|---|---|---|---|---|
| 0.86 (Driftwood, `field`, `brush`) | 0.0848 head | 0.1054 | 0.1116 | ×1.4 |
| 0.90 (Bract `text` `display` `foil` `burin` `burin2` `burinD`, `scotch`) | 0.0968 head | 0.1183 | 0.1247 | ×1.1 |
| 0.92 (neutral `text` `display`, `cone`, `opsz-display`) | 0.1028 diag | 0.1247 | 0.1313 | head only at ×0.8–0.9 |
| 0.94 (`ledger` `quill` `thorn` `quill-display` `didone`) | 0.1088 diag | 0.1312 | 0.1378 | head only at ×0.8 |
| 0.98, 1.0, 1.04, 1.08 (`fatface`, `reverse`, `opsz-text`, `slab`, `clarendon`, `blind`, `anvil`) | ≥ 0.1207 diag | | | never (diag throughout) |

So at `5d0b29f` the shipped groups pass because their masters happen to fall on one side (Driftwood ×1 and ×1.3
both head; the neutral example ×1 and ×1.5 both diag, 0.0028 from the threshold, which `generator.md` section 12
already records as "a pre-existing fragility"), and `references/traps.md` row 32 records the same refusal seen on
the Example template at `xs` 0.86–0.90 (read).

**The `w` is not alone.** Comparing every glyph's structure and record (what `export.js` compares: polygon
count, points per polygon, edge runs, `sig`) at mult 1 against mults 0.8–2.0 for every concept of the five
files, roman and italic, 220,080 comparisons (measured), 44 (glyph, concept, slant) cases flip with weight:
the italic `w` in 19 concepts; the italic `W` in 8 (`blind`, `anvil` from ×1.35; `slab`, `clarendon` from
×1.6; `reverse`, `opsz-text` from ×1.85; `fatface` at ×2); the roman `Q`, `j`, `y` and italic `T`, `f`, `j`
of the curl concepts `bine` and `vine` and the roman `Q` of `tideline` (13 cases, from ×1.15 to ×1.7); the
roman `x` of `windswept` (×1.55); `™` of `geometric` (×1.7); `z` of `opsz-text`, roman and italic (×1.85). Every one is a decision read from drawn, weight-dependent
geometry: the `xf` widening above, or the vertical fit, which moves a flat stroke's endpoints inward by half
the stroke width (`hwFlat(P)`, read: lines 809–812 and 841), so a short stroke's drawn tangent follows `W`.

### 0.2 The italic opening quotes overhang their advance

`scripts/build.py` `quote_glyphs()` (read: line 343) derives the six quote glyphs from the apostrophe and gives
`quotedblleft` the advance `round(ap_adv + dbl_gap)` and `quoteleft` the apostrophe's own advance, in every
group. In an italic group the apostrophe itself overhangs: the generator spaces an italic glyph over the band
between the baseline and the x-height only (read: `glyph()`, lines 1106–1112: "f hooks and tails overhang their
neighbours instead of being spaced"), and the apostrophe's tail ends at y 505 with a flare terminal whose ink
dips below 500 (measured: the Driftwood italic Regular's apostrophe spans y 471.9–696.4, the neutral italic
Regular's 453.0–705.0), so the band sees only the tail's foot (x 9.5–71.9 on Driftwood) and the sheared body
above runs to x 123.6 against an advance of 81. Every curly quote inherits that (measured, from the export JSON
through `build.quote_glyphs`; `lsb`/`rsb` = left/right side bearing in units):

| Group, master | apostrophe adv, lsb, rsb | `quoteleft` | `quotedblleft` adv, xMax, rsb | `quotedblright` rsb |
|---|---|---|---|---|
| Driftwood italic Regular | 81, 9.5, −42.6 | 81, rsb −42.6 | 246, 289.0, **−43.0** | −43.0 |
| Driftwood italic Medium (×1.3) | 91, 8.0, −47.1 | 91, −47.1 | 280, 326.7, **−46.7** | −46.7 |
| Driftwood italic Bold (×1.65, the user's master, with section 1.2 applied) | 106, 8.0, −53.2 | 106, −53.2 | 325, 378.4, **−53.4** | −53.4 |
| neutral italic Regular | 143, 15.3, −29.6 | 143, −29.6 | 371, 400.7, **−29.7** | −29.7 |
| neutral italic Bold (×1.5) | 161, 8.0, −35.6 | 161, −35.6 | 434, 470.1, **−36.1** | −36.1 |
| neutral italic at wght 500 (the named instance `Medium Italic`, from the woff2) | 154, 11, −32 | 154, −33 | 409, 442, **−33** | −32 |
| Driftwood roman Regular / Bold | 127, 15.6, 14.6 / 158, 8, 8.2 | same | 267, 252.8, 14.2 / 364, 355.4, 8.6 | 14.2 / 8.6 |
| neutral roman, four masters | rsb 7.7 to 19.7 | same | rsb 7.8 to 19.8 | same |

A closing quote or an apostrophe is followed by a space or punctuation and its overhang is the italic's normal
behaviour. An opening quote is followed directly by a letter, so its second mark (43 units past the advance on
the Driftwood Regular, 53 on the Bold) lands on that letter's top left; the user's own build saw the mark touch
a following capital `W`. The single `quoteleft` overhangs by the same amount and is followed by a letter too.
The roman quotes lie inside their advances in every master.

## 1. The change

### 1.1 The operator's proposal R1, measured and not recommended

R1 moves the first stroke's start: `"M 10 500 L 170 0"` → `"M 20 500 L 170 0"`. On the Driftwood concept it reads
`head` from ×0.8 to ×1.8 (measured), which covers the user's ×1.65, and `w`'s advance at ×1 goes 710 → 704. But
the threshold moves with it, not away from it. Measured on every serif concept, italic, R1 flips `head` → `diag`
at: `xs` 0.90 at **×1.5** (the seven Bract-type concepts and `scotch`); `xs` 0.92 at **×1.35** (the neutral
example's `text` and `display`, `cone`, `opsz-display`); `xs` 0.94 at ×1.25; `xs` 0.98 at ×0.95; `xs` 1.0 at
×0.85; `xs` 0.86 at ×1.85. Consequences, measured: `node scripts/export.js` on **the neutral example's italic
group** (×1 and ×1.5) is refused with R1 ("w … serifA=head / serifA=diag"), where `5d0b29f` accepts it; and
`tests/test_genres.py::test_every_genre_recipe_passes_params_and_exports_two_compatible_masters` goes red on
`didone` and `opsz-display` ("italic structure differences are ['w'], expected []"). R1 also changes the serif
kind of nine concepts' italic `w` at ×1 (from `diag` to `head`), a design change on the neutral example and the
digests of both italic groups.

No start x holds the head serif for every concept across weights (inferred from the measured relation
`dx = (170 − x0) · 0.95 · xs · (1 + 0.16·(mult − 1)) − 88.2`): for `xs` up to 1.08 at ×2.0 the start must be
past x 54, and below x 59 the Regular at `xs` 0.86 would lean backwards; in that five-unit window the margin to
the threshold at `xs` 1.08 is 0.018 at ×1.65 and 0.005 at ×2.0, and the stroke draws plumb. A clearly `diag` stroke needs a start at or left
of x −20 (`"M 0 500"` reads 0.0922 at `xs` 0.86 ×0.8 and 0.1009 at ×1, measured: `head` to ×0.95 and `diag`
by 0.001 at ×1), which changes the serif on every face and was rejected by the operator. The skeleton cannot be moved off a threshold that weight drags
across it.

### 1.2 Fix B: decisions read the geometry at mult 1 and xh 500

0.2 set the rule "unmapped coordinates decide, mapped coordinates draw" for the x-height map (read:
`generator.md` section 12): `glyph()` fits every mapped skeleton again at `xh` 500 (`src500`), samples it with the
same counts, and hands `strokePolys` the pair (`pts` drawn, `U.pts` deciding). The weight widening and the
weight-dependent fit are maps of the same kind. The change extends the rule to them, so the branch record of
any master is the record of that concept at mult 1 and xh 500:

```js
// scripts/gen.js params():            P.W = concept.W * mult; P.W0 = concept.W; P.thin0 = concept.thin;
// scripts/gen.js glyph(), after `src`/`mapOn`:
var PU = Object.assign({}, P, { xh: 500, W: P.W0, thin: P.thin0 === undefined ? P.thin : P.thin0 });
var decideOn = mapOn || P.W !== P.W0;
var src500 = decideOn ? fitSkeleton(raw, PU, key) : src;
function unmapped(si) { return samplePath(src500[si].d, counts[si]).map(function (p) { return xf(key, PU, p); }); }
// and `mapOn ? unmapped(si) : …` becomes `decideOn ? unmapped(si) : …` at both call sites (qU and ptsU)
```

Eight changed or added lines; the diff of the scratch copy is exactly this (measured). `thin0` is needed because `thinGrow`
rewrites `P.thin` per weight (line 940) and `hwFlat` reads it. `strokePolys`, `partner()`, `tee()` and
`buriedIn()` are untouched: they already take the deciding points from `U` and the drawn points from `pts`.
With `decideOn` false (mult 1, xh 500) the 0.1 code path runs as today.

Measured with this change: the Driftwood example's italic group at ×1 and ×1.65 exports (`w` records
`serifA=head` in both masters; advances 710 and 792; `minStrokeWidth` 30.44 and 50.2 against floors of 30
and 50 set in that scratch `font.json`); the neutral italic exports as before; **0 of the 220,080 comparisons flip**
(the 44 cases of section 0.1 are gone, by construction: every master's decisions are the mult-1 decisions);
**every digest of every example group is unchanged** (export, decoded-TTF and manifest digests and the woff2
bytes of the five groups, `tests/baseline_digest.py --print` on the unmodified tree against the changed copy,
`darwin/26`); `tests/test_r_leg_join.py::test_only_the_r_changed_since_0_4_0` stays green against it; the
whole font suite on the neutral example built by the changed tree passes except the quote test of section 1.3
(102 passed, 2 failed, both the quote test on the italic masters). The digests cannot move for a group that has a
mult-1 master and exports today: its heavier masters' decisions already equal the Regular's (or the exporter
would have refused them), and the Regular's are the mult-1 decisions.

A variant that undoes only the `xf` widening and keeps the fit at the drawn weight was measured too: it leaves
10 of the 44 flips (the curl concepts' `j`, `y`, `f` and `opsz-text`'s `z`, all fit-driven), and its digests are
also unchanged. Section 8 asks; the recommendation is the full rule.

Exact guarantee: a group's masters cannot be refused by the exporter for a decision that weight moved, because no
decision reads weight any more. It does **not** make a concept's decisions robust to `xs`: the neutral example's
italic `w` still reads 0.1028 against 0.1 at every weight, and a change of `xs` from 0.92 to 0.90 still flips it
(section 0.1 table); that is a concept author's choice and is documented as such. A group whose every master is
at mult ≠ 1 may see a decision move to the mult-1 one: no shipped group is such a group (read: the three
`font.json`s and `examples/bract/`), and the comparison test of section 4 (f) proves nothing shipped moved.

### 1.3 The opening quotes grow to hold their ink, in an italic group only

In `quote_glyphs()` (`scripts/build.py`), for `quoteleft` and `quotedblleft` when `italic_angle` is set:
`adv = max(adv, round(max(xs) + min(xs)))` over the glyph's own polygon x's, so the advance holds the ink with a
right side bearing equal to the left (the rule the user's own build applied to `quotedblleft`; here extended to
`quoteleft`, which overhangs by the same amount, section 0.2). The roman is untouched by the gate, which matters:
applied to the roman too, the rule would move the Driftwood roman Regular's `quotedblleft` by one unit (15.6 +
252.8 rounds to 268 against 267), a change for nothing. The closing quotes, the apostrophe and the straight
quotes are not changed.

Measured, after the rule: Driftwood italic Regular `quoteleft` 81 → 133 (lsb 9.5, rsb 9.4), `quotedblleft`
246 → 299 (rsb 10.0); Medium 91 → 146 (rsb 7.9), 280 → 335 (rsb 8.3); the ×1.65 Bold 106 → 167 (rsb 7.8),
325 → 386 (rsb 7.6); neutral italic Regular 143 → 188 (15.3 / 15.4), 371 → 416 (15.3 / 15.3); Bold 161 → 205
(8.0 / 8.4), 434 → 478 (8.0 / 7.9). At the neutral `Medium Italic` instance (wght 500, read from the built woff2
through the instancer): `quoteleft` adv 198, lsb 12, rsb 11; `quotedblleft` 453, 12, 11. The bearings are equal
within a unit at every master and at the intermediate. `max()` never binds on the shipped examples (the rule's
value exceeds the old advance in the four shipped italic masters and the ×1.65 one), so a synthetic case must exercise it (section 4 e).

## 2. What moves in the shipped output

Measured, the unmodified tree against the copy with both changes, `tests/baseline_digest.py --print` and a
table-by-table comparison of the decoded fonts:

| Group | export digest | TTF digest | manifest digest | woff2 bytes | tables that differ |
|---|---|---|---|---|---|
| `neutral/italic` | same | **moves** | same | **moves** | `hmtx` (`quoteleft` 143 → 188, `quotedblleft` 371 → 416, nothing else), `HVAR`, `gvar` (the two glyphs' phantom points carry the advance: inferred), `OS/2` (`xAvgCharWidth` 527 → 528), `head` (the checksum adjustment: inferred) |
| `driftwood/italic` | same | **moves** | same | **moves** | the same five: `hmtx` (`quoteleft` 81 → 133, `quotedblleft` 246 → 299), `HVAR`, `gvar`, `OS/2` (480 → 481), `head` |
| `neutral/roman`, `driftwood/roman`, `bract/roman` | same | same | same | same | none |

The export JSON of every group is byte-identical (the generator's output does not move: section 1.2 changes no
shipped decision, and the quotes are the builder's). The manifest digest holds because the manifest records
per-master figures from the export (`minStrokeWidth`, titles; read: `build.py` lines 1244–1254) and drops the
woff2 hash and size. `glyf` is identical in every group: no outline moves anywhere, only two advances per italic
group. Nothing in GPOS moves: the curly quotes are outside every `kerning.set` (read: the three `font.json`s).

## 3. Blast radius

- **Generator:** eight lines in `glyph()` and `params()`; the record grammar is unchanged (no new token); no
  skeleton changes. Point counts are unchanged (they come from the unfitted skeleton). A project whose group has
  a mult-1 master gets identical output; a project whose masters all sit at mult ≠ 1 may see a branch move to
  the mult-1 decision (section 1.2). Cost: `unmapped()` now runs for every stroke at mult ≠ 1 where before it ran
  only under the x-height map; the digest builds took the same time to within noise (measured, not timed).
- **Builder:** one helper in `quote_glyphs()`; two advances per italic group.
- **Fixtures that pin output:** `tests/fixtures/baseline.json` + `tests/test_backward_compat.py` go red on the
  two italic groups' TTF digests on every recorded platform (section 5). `docs/reviews/genres-2026-11-19.md`'s
  digests do **not** move: `current_digests()` draws the roman `G` only (read: `tests/test_genres.py` line 428),
  and the roman output is unchanged; no genre re-review. `tests/test_genres.py::KNOWN_ITALIC_REFUSALS`
  (`{"scotch": ["w"]}`) goes red ("italic structure differences are [], expected ['w']", measured) and shrinks
  to `{}`, as its comment says it must; the `scotch` note in `references/genres.md` section 4, the table cell's
  last sentence ("The italic is refused (section 4)"), the recipe's `desc` in `templates/concepts.genres.js`
  and the `risk` in `scripts/concepts/content.genres.json` are one text held equal by three tests (read: lines
  143–178, 215–227, 357–368) and change together; the dated record's row keeps its text (the tests compare its
  verdict and date only, read: line 464). `scripts/tests/test_font.py::test_quote_glyphs_follow_the_apostrophe_in_every_master`
  goes red on the italic masters ("italic Regular quoteleft: advance 188, expected 143", measured) because its
  `expected_quote_glyphs` is a copy of the builder's rule (read: line 197); the copy gains the same gated rule
  (measured green with it: 6 passed). Every other test of the font suite and of `tests/` that runs the generator
  stays green (measured: the suite on the neutral build, `test_r_leg_join.py`, `test_genres.py` except the
  refusal list).
- **Sites:** a site that takes 0.6's `scripts/` and rebuilds gets the same roman; an italic group gets two wider
  opening quotes and nothing else, and may now add a heavier master. The manifest's `sources_sha256` changes, so
  a site's `build.py --check` fails until the rebuild, as it should.

## 4. Tests

Each test runs the real generator or builder; none asserts on source text. Mutations are applied to a scratch
copy named by an environment variable (as `FONT_DESIGN_R_GEN` and `FONT_DESIGN_GENRES_GEN` do) or, for the
builder, by `mutate.py`'s edit-and-restore; each is recorded in `references/testing.md` section 8 with its
outcome. The baseline revision for the comparison tests is `5d0b29f` (0.5.0), written as a literal as
`test_r_leg_join.py` writes `598044b`.

| | Test | Asserts | Mutations that must turn it red |
|---|---|---|---|
| a | `tests/test_weight_decisions.py::test_no_branch_or_structure_changes_with_weight[file]` (the five concept files; every concept, roman and italic; mults 0.8–2.0 step 0.05 against mult 1; one node process per concept and slant, because one process holding every drawing ran out of heap at 4 GB, measured) | for every glyph, `[polys.map(len), runs, sig]` at every mult equals its value at mult 1; the comparison count is at least 200,000 (measured 220,080), so an empty loop fails. **Red at `5d0b29f`**: the 44 cases of section 0.1, each named | **M1** `decideOn = mapOn` (the 0.5.0 condition): red, all 44. **M2** `xf(key, P, p)` in `unmapped()` (the widening back in the deciding points): red on the `w` and `W` cases. **M3** `src500` fitted with `P` instead of `PU` (the fit at the drawn weight): red on the 10 fit-driven cases (`bine`/`vine` `j` `y` `f`, `opsz-text` `z`; measured on the xf-only variant) |
| b | `tests/test_weight_decisions.py::test_an_italic_group_exports_with_a_bold_master` | a `font.json` written to tmp with the Driftwood example's `concepts.js` and an italic group at ×1 and ×1.65 goes through the real `export.js`: exit 0, the `w`'s record identical in both masters and reading `serifA=head`, and a second group at ×1 and ×2.0 exports too. **Red at `5d0b29f`** (exit 1 naming `w`) | M1; the threshold `0.1` changed to `0.12` in the serif-kind test (the record moves to `head` in both masters, so this test stays green and (a) stays green: recorded as the mutation this pair cannot see, which is correct, since the kind is a design choice; the digests of section 5 see it) |
| c | `scripts/tests/test_font.py::test_weight_does_not_change_any_branch_record(cfg)` (the site suite, beside `test_xh_does_not_change_any_branch_record`, reusing its fixture's two variants "as drawn" and "curls") | every master's concept of the project's groups, at that master's slant, drawn at mults 0.8, 1, 1.25, 1.5, 1.65 and 2: every record equals the mult-1 record; at least 1,000 records compared. **Red on the neutral fixture at `5d0b29f`** (the italic `w` at 0.8 and 0.9) | M1, M2 (red). M3: the neutral concepts carry no fit-driven flip (section 0.1), so M3 is caught here only if the "curls" variant reproduces one (inferred); if it does not, record it as caught by (a) and not by the site suite |
| d | `scripts/tests/test_font.py::test_opening_quotes_lie_inside_their_advance[group-instance]` (per named instance of every group, from the instanced woff2: `glyf` bounds and `hmtx`) | in an italic group, `quoteleft` and `quotedblleft` have a right side bearing ≥ 0 and `|rsb − lsb| ≤ 1`; `quoteright` and `quotedblright` keep the apostrophe-derived advances (the closing quotes unchanged); in a roman group, rsb ≥ 0 for all four (a control, green before and after). **Red at `5d0b29f`** at every italic master and at the neutral `Medium Italic` instance (rsb −30 to −47). The intermediate matters: the advance and the ink interpolate separately and are rounded separately, so the one-unit tolerance is asserted where it is weakest (measured 12 / 11 at wght 500) | **Q1** the `if italic_angle` gate removed from the rule (the roman gets the rule: red on nothing here, since the roman rsb stays ≥ 0 — caught by (f)). **Q1'** the rule removed (0.5.0 restored): red, every italic instance. **Q2** `round(max(xs))` instead of `max(xs) + min(xs)` (ink flush with the advance): red on `|rsb − lsb|` (0 against 9.5). **Q3** the rule applied to `quotedblright` too: red on the closing-quote assertion |
| e | `tests/test_weight_decisions.py::test_quote_glyphs_opening_rule` (unit test of `build.quote_glyphs`, imported through `importlib`) | three synthetic apostrophes: one overhanging in an italic group (the advance becomes `xMax + xMin`, both opening quotes, the closing ones unchanged); one already inside its advance with a larger right bearing (the advance is kept: `max()` binds); the first one in a roman group (nothing changes). Point-for-point the outlines equal the 0.5.0 derivation | Q1 (red on the roman case), Q1', Q2, Q3, **Q4** `max()` dropped (red on the second case: the only place that branch is observable, since on the shipped examples the rule's value always exceeds the old advance) |
| f | `tests/test_weight_decisions.py::test_only_the_italic_opening_quotes_changed_since_0_5_0` | builds the three examples from a `git archive 5d0b29f` tree (scripts and examples, built with that tree's `build.py`, the way `baseline_digest.py --repo` builds a checkout) and from the working tree, and asserts per group: the export JSON is identical (`export_digest`); in a roman group the decoded TTF digest is identical; in an italic group every glyph's compiled `glyf` record is identical, `hmtx` differs on exactly `{quoteleft, quotedblleft}` with the new advance equal to `round(xMax + xMin)` of the old glyph, GPOS is identical, and the tables that differ are a subset of `{hmtx, HVAR, gvar, OS/2, head}` with `OS/2` differing in `xAvgCharWidth` only. **Red at `5d0b29f`** by design ("hmtx changed on [], expected ['quoteleft', 'quotedblleft']"), as test e of the R plan was. Cost: six builds, about a minute (inferred from the 20-second compat build) | Q3 (three glyphs); a kern value nudged in `export.js` (GPOS); any outline change in `gen.js` (`glyf`); the quote rule applied to the roman (the roman TTF digest) |

Two existing tests change: `test_quote_glyphs_follow_the_apostrophe_in_every_master`'s rule copy (section 3) and
`tests/test_genres.py::KNOWN_ITALIC_REFUSALS` → `{}`. `scripts/tests/mutate.py`'s catalogue (read: lines 643–650,
`add(name, tests, edit, expect)`) gains `weight-branch-drawn` (M1 against (c)) and `quote-opening-unslanted` (Q1'
against (d)), so `scripts/smoke.sh` step 5 runs them on every CI run. Clear `__pycache__` between mutation runs
(`testing.md` section 7).

## 5. The compatibility baseline

`tests/test_backward_compat.py` holds the five groups to `788760d`'s digests per platform and node major
(`darwin/20`, `darwin/22`, `darwin/26`, `linux/20`, `linux/22`; read: the fixture). This change moves exactly the
`ttf_sha256` and woff2 sha256 of `neutral/italic` and `driftwood/italic` (section 2) on every platform (inferred
for the platforms not measured here: the advance change is integer arithmetic, not floating point). The export
and manifest digests of all five groups and every digest of the three roman groups must come out equal to the
0.5.0 record, and the recording step checks that before merging (below). Excluding `hmtx` from the TTF digest is
not an option (a digest that skipped tables would stop proving what it proves). So the baseline moves to the fix
commit, the way 0.5.0 moved it:

1. `tests/fixtures/baseline.json`: `baseline_rev` = the sha of the commit carrying both changes,
   `baseline_version` `"0.6.0"`, and `supersedes` naming `788760d`, `0.5.0` and the reason ("0.6.0 widened the
   italic opening quotes: the TTF digests of the two italic groups moved; every export and manifest digest and
   every roman digest did not; `tests/test_weight_decisions.py::test_only_the_italic_opening_quotes_changed_since_0_5_0`
   holds every glyph outline, every other advance and every kern to the 0.5.0 build"). `supersedes` stays one
   entry (the test checks only that it exists, read: line 57); the 0.1.0 → 0.5.0 step is in git history and the
   0.5.0 changelog.
2. `tests/test_backward_compat.py`: `BASELINE_REV`, the module docstring's departure sentence.
   `tests/baseline_digest.py`: the header's revision sentence. `.github/workflows/record-baseline.yml`: the
   worktree and `--rev` shas (two lines, read); `tests/test_ci_workflow.py` imports `BASELINE_REV` from the compat
   test, so it follows (read: line 67).
3. Order, as 0.5.0 did it (`docs/plan-r-leg.md` section 6.1 step 5): **commit A** (code, tests, docs, version,
   the fixture with the placeholder `COMMIT_A`, the workflow and the test literal reading it), not pushed; then
   `A=$(git rev-parse --short HEAD)`, the placeholder replaced in the three files,
   `.venv/bin/python3 tests/baseline_digest.py --record --rev $A` (re-records `darwin/26` under the
   script-identity guard), and a check in the same step that the new entry differs from the 0.5.0 entry in exactly
   the two italic `ttf_sha256` and woff2 values (a six-line comparison, run by hand and quoted in the commit
   message); **commit B**; push. CI runs `record-baseline` on B (ubuntu and macos × node 20 and 22); the compat test
   is red on every leg until **commit C** merges the four `entry-baseline.json` artifacts
   (`--merge`). The genre legs need nothing: their digests are unchanged. The PR merges only after C.

The promise, exactly, for `generator.md` section 11 and the docstring: a project on 0.1 to 0.5 that copies 0.6's
`scripts/` and rebuilds without touching `concepts.js` or `font.json` gets the same outlines and tables as
before, **except the advances of `quoteleft` and `quotedblleft` in an italic group**, which grow to hold the
slanted ink with equal bearings (no outline, no other advance, no kern moves); and a group whose masters all sit
at a multiplier other than 1 may see a branch decision move to the mult-1 decision (none of the examples does).
The three examples' digests are held to the 0.6.0 record per platform and node major.

## 6. Docs, CHANGELOG, version

- `references/generator.md`: section 4's `xs` row ("multiplied by `1 + 0.16·(W/W0 − 1)` … a branch flipper"): the
  widening still draws but no longer decides; `xs` itself still flips between concepts. Section 9 (the italic):
  one paragraph on the apostrophe's band spacing and the opening quotes' advance rule. Section 11: the 0.6.0
  compatibility paragraph (section 5 above) beside the 0.5.0 one. Section 12: the decision rule restated as
  "the geometry at mult 1 and xh 500 decides, the drawn geometry draws", the audit list (`fitSkeleton` at `PU`;
  the widening), the "When it refuses" paragraph (weight removed from the list of movers), and the measured-margins
  paragraph (the italic `w`'s 0.0028 is an `xs` margin at every weight; the sentence "the Bold's widening lifts it
  to 0.123" goes).
- `references/traps.md`: row 32 rewritten as fixed in 0.6.0, with the general cause (a branch read from drawn,
  weight-dependent geometry: 44 cases over the five concept files at `5d0b29f`, the `w`'s serif kind being 19 of
  them) and the guard (tests a–c). This is the trap the caller asked about, and it is row 32, not a new row: the
  0.5.0 text named the mechanism and the workaround (`xs` 0.92 and above) without the general cause. A new row 37:
  the italic opening quotes overhang (cause: the band spacing of an apostrophe whose flare dips below the x-height;
  guard: the builder's rule and tests d–f; where: the Driftwood example's italic, 43 units, and the neutral
  italic, 30, both measured here; a user's italic build, where the mark touched a following capital).
- `references/genres.md` section 4 (`scotch`): the refusal note becomes "exported since 0.6.0"; the table cell,
  the recipe `desc` and `content.genres.json` `risk` lose "The italic is refused (section 4)" together (section 3).
- `references/variable-font-build.md`: the quote-derivation sentence gains the opening quotes' italic advance.
- `references/testing.md` section 8: rows for tests a–f and the two existing tests that changed, the mutation
  outcomes, and the two survivors stated as such (the `0.12` threshold against a–b; M3 against c if it survives).
- `scripts/gen.js`: the comment at `strokePolys`' head ("U carries the same stroke on the UNMAPPED skeleton (the
  x-height map undone)") names the weight too; `scripts/build.py` `quote_glyphs()` docstring; the
  `expected_quote_glyphs` docstring in the font suite.
- `CHANGELOG.md`: `## [0.6.0] — <date>`: Fixed (the italic Bold master, with the 44-case count and "no shipped
  output moved"; the opening quotes, with the before/after advances), Changed (the decision rule; the baseline
  re-recorded and the promise restated; the `scotch` note), Added (tests a–f), and the pointer to this plan.
- `VERSION`, `SKILL.md` (frontmatter `metadata.version` and the "**Version 0.6.0**" line), `README.md` badge,
  `package.json` `version`: `tests/test_versions_and_skill.py::test_version_is_the_same_everywhere` holds the five
  equal (read).
- This plan: the status paragraph updated at build, as `plan-r-leg.md` was; the file must carry no machine path
  or session string (`tests/test_hygiene.py` walks `docs/`, read).

**Version: 0.6.0.** The output of every italic group changes (two advances), the baseline is re-recorded, and a
decision rule changes with a documented migration note: the same kind of change 0.5.0 was. 0.5.1 is defensible as
"the same fonts, two advances corrected"; section 8 asks.

## 7. Order of work

1. Tests a, b, c, d, f written first against the unmodified tree: a, b, c, d red (the defects), e red (the
   builder lacks the rule), f red by design (the changed set is empty). Then the generator (1.2) and the builder
   (1.3); the rule copy in the font suite; `KNOWN_ITALIC_REFUSALS`. All six green; the mutation runs through the
   scratch copy, logged.
2. The repository suite: everything green except `test_backward_compat` (expected red until step 4).
   `scripts/smoke.sh --full` steps 1–7.
3. Docs and version (section 6).
4. Commit A, commit B with the `darwin/26` record and the two-digest check, push; CI; commit C with the four
   runner entries (section 5).
5. Impasse review of the whole diff, with the export comparison and the digest table as evidence; reconcile;
   re-review once. Merge.

Serial; the two fixes are independent but too small to split.

## 8. Risks and questions for the operator

Risks:
- Fix B changes where every decision reads its geometry. For the shipped groups the digests prove nothing
  moved; for a project whose masters are all at mult ≠ 1 the promise is weaker (section 1.2), and no such
  project exists in this repository to measure.
- The fit at the Regular's width (`PU`) is part of the rule. The xf-only variant also leaves the digests
  unchanged but keeps 10 weight flips; if the full rule is taken, mutation M3 must be watched red in (a).
- The compat baseline moves for the second time; the recording path is the 0.5.0 one, exercised once.
- The italic has never been design-reviewed (read: `generator.md` section 9); the quote advances are judged by
  arithmetic (equal bearings), not on a page.

Questions, each with the recommendation:
1. **Fix B (decisions at mult 1) in place of R1, no skeleton change?** R1 refuses the neutral example's italic
   and two genre recipes and changes nine concepts' `w` at ×1 (section 1.1); B keeps the head serif on the
   Driftwood example at ×1.65 and moves nothing shipped. Recommendation: B.
2. **The full rule (fit at mult 1 too) or the xf widening alone?** Recommendation: the full rule; the xf-only
   variant leaves 10 flips (section 1.2).
3. **`quoteleft` included?** It overhangs by the same 43 units and is followed by a letter. Recommendation: yes.
4. **The closing quotes and the apostrophe stay as they are?** Their overhang (30 to 53 units) is the italic
   band rule working as designed, and the apostrophe's advance is the generator's and kerned. Recommendation:
   leave them, and record the figures in traps row 37 for the italic's first design review.
5. **0.6.0 or 0.5.1?** Recommendation: 0.6.0 (section 6).
6. **No genre re-review** (the roman digests are unchanged, measured) and the `scotch` note reworded without a
   new date. Recommendation: yes.
7. **The neutral example's italic `w` stays 0.0028 from the `xs` threshold at every weight.** Moving it means a
   skeleton or threshold change and a digest move. Recommendation: leave it, documented.

## 9. Independent review and what it changed

Impasse 0.5.0, backend `codex` (OpenAI, cross-provider), 2026-11-19, review `italic-bold-plan-review-001`, on this plan
with `scripts/gen.js`, `scripts/build.py`, `scripts/tests/test_font.py`, `tests/test_backward_compat.py`,
`references/generator.md` and the measured Fix B diff. Six findings, all accepted after checking against the code;
none rejected, no deadlock (reconciliation `skill-italic-bold-plan-recon-2026-11-19`). These amend sections 1, 4 and 6
and win over them where they differ:

| Finding | Claim | Change to the plan |
|---|---|---|
| F001 high | a group whose masters use different concepts resets each to its own mult-1 geometry, so the "cannot move" promise is too wide | the promise in `generator.md` section 11 covers groups whose masters keep their decisions under the reset; a mixed-concept fixture (the bract example's two concepts) is exported before and after and must not move |
| F002 high | the T-join's pinned side and refusals still read drawn geometry | the guarantee names only the decisions moved to reference geometry; a near-perpendicular T-join test across weights is added |
| F003 medium | no test shows a serif chosen from the reference stays sound on a differently angled drawn stroke | inspected (a before/after picture of the Driftwood example's italic `w` at ×1, 1.3, 1.65, 2, kept outside the repository, which publishes no images; Fix B's head serif joins the stem cleanly at ×1.65 and ×2); added: every serif polygon overlaps its stroke body at each tested mult where the reference and drawn kinds disagree |
| F004 high | `max()` can keep a larger old advance, so equal bearings would fail valid output | the quote test asserts a right bearing ≥ 0 always and equal bearings (±1) only where the ink sets the advance; the synthetic `max()` case stays |
| F005 medium | the expected advance must come from the exported polygons, not compiled `glyf` bounds | test f computes it from the export JSON |
| F006 medium | mutation M3 changes `W` and `thin` together | an added mutation restores `thin` alone (`PU.thin = P.thin`), with a `thinGrow` fixture near the threshold that goes red under it |

The operator's choice (2026-11-19) was "keep the head serif" on the italic `w`; Fix B keeps it (both masters `head`),
so the choice stands with a different mechanism than the first-proposed skeleton edit (R1), which section 0 shows
refuses the neutral example's own italic group.
