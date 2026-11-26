# Plan: `wonkAmount`, a concept setting for how far the `wonk` letters lean (0.12.0), as built

WHAT IT'S FOR: `scripts/gen.js` leans every letter a concept names in `wonk` by a fixed
`x -= 0.045 * y` (about 2.6 degrees). A face that wants a lean range on a variable-font axis needs that
number per master. This plan adds a numeric concept setting, `wonkAmount`, default exactly 0.045, refused
outside 0 to 0.2, and documents it. All paths are relative to the repository root.

## The stop condition the request set has fired

The request says: check, on a shipped fixture concept, that two masters differing only in `wonkAmount`
at the top of the documented range stay interpolation-compatible in `export.js`, and "if it does flip
one, report which glyphs and stop rather than widening the range".

**It flips one.** Research ran that check before planning, on a copy of `scripts/gen.js` outside the
repository whose only change is that line 501 reads the amount from the concept (default 0.045). The
repository's files were not modified. Measured 2026-11-25, node 26.13.1, through the real
`scripts/export.js` beside that copy, roman, both masters at mult 1, `wonk` naming every key of `G`, one
master at `wonkAmount: 0` and the other at `wonkAmount: 0.2`:

- **Every concept the three fixtures build is refused** (neutral `text` and `display`, Bract `text` and
  `display`, Driftwood `driftwood`). `export.js` exits 1 with "57 glyph(s) differ in structure or
  branch outcome between masters of group roman", the same 57 for all of them:
  `1 4 a b d f g h i j k l m n p q r u B D F H I J K L M N P R T U W Y ! fi fl ff ā á ú í à ù ì â û î ä ü ï ñ Í Ï Ú Ü Ñ`.
- With the Tiki trial's letters only (`wonk: "aeiokrAEIO"`) on the neutral `text` concept, 0 against
  0.2 and 0 against 0.158 are both refused on 5 glyphs: `a i k r I`.
- **The cause is one decision.** `serifKindOf` (gen.js line 671) calls a serif end `diag` when the
  end's tangent on the reference skeleton has `abs(TU[0]) > 0.1`, else `head` or `foot`. The lean is
  applied in `xf()` before that decision, to the reference skeleton as well as the drawn one. A plumb
  stem leaned by `wonkAmount` has a slope of `wonkAmount * xs`, so its serifs turn from `head`/`foot`
  to `diag` when `wonkAmount * xs` passes 0.1005. The lowercase head has 15 points and the diagonal
  serif 26, so the masters no longer match point for point (`l`: polygons `[496,15,26]` become
  `[496,26,26]`). Stems that already lean the other way flip in the opposite direction (`M` first,
  `W` last).
- **Where the flips start**, each concept against its own drawing at `wonkAmount: 0`, every key
  leaning, amounts stepped by 0.001:

  | concept | xs | first flip | most stems flip | last flip |
  |---|---|---|---|---|
  | neutral `text`, `display` (roman) | 0.92 | 0.081 (`M`) | 0.110 (56 glyphs) | 0.177 (`W`, 57) |
  | Bract `text`, `display` (roman) | 0.90 | 0.084 (`M`) | 0.112 (56) | 0.175 (57) |
  | Driftwood `driftwood` (roman) | 0.86 | 0.089 (`M`) | 0.117 (56) | 0.169 (57) |
  | neutral `text` (italic, 10 degrees) | 0.92 | 0.060 (`W`) | 0.087 (47) | not measured past 0.2 |

- **Three concepts with no end mapped to `serif` do not flip; one does.** Bract `bine`, Driftwood `tideline` and
  `dune`, every key leaning, 0 against 0.2: `export.js` exits 0, the structure of all 131 glyphs is
  equal, 125 of them differ in coordinates (the six that do not are `. - – — … •`), and no edge folds
  in either master. Driftwood `windswept` (cut ends, `shear` and `bend`) flips `curved` on 1 glyph at
  0.1 and 2 at 0.2 (`x` and `z` were the two read).
- **The Tiki trial's own concept does not flip.** The untracked `cane` concept with the trial's
  `skeletons.js` (read from the main checkout, not part of this change), `wonk: "aeiokrAEIO"`, mult 1
  and 1.5, amounts 0.045, 0.1, 0.158 and 0.2 against no lean: 0 glyphs differ in structure. With every
  key leaning, 1 glyph differs from 0.1 up: `>`, a key the trial's skeletons file adds.

**What this plan does about it.** It does not widen or narrow the range, and it does not change the
serif decision. It keeps the requested range, 0 to 0.2, states the limit exactly in the documentation,
and pins both outcomes with tests: the non-serif shipped concepts export and build across the whole
range, and a serif concept is refused loudly by the exporter, naming the glyphs. Whether to ship that
is the operator's ruling, the work item `lean-range-ruling`, which is a pre-build ruling only (the
Tiki trial is a separate, post-build item, `tiki-lean-trial`). **The build must not start until the
operator has accepted `lean-range-ruling`.** An agent that reaches the build stage without a recorded
acceptance stops and reports this section; it does not build.

## Decisions the operator can overrule

1. **The range stays 0 to 0.2 and is a design range, not a compatibility bound** (the stop condition
   above). The alternatives: (a) narrow the range to under the first flip on a serif concept (about
   0.08 roman, 0.06 italic), which cannot hold the 0.158 the Tiki face needs; (b) decide the serif
   kind on the skeleton before the lean, which changes what a leaning serif stem draws and is a
   design change this plan does not attempt; (c) stop the change. Recommended: ship the range with
   the limit documented, because the face that needs it has no serif ends and measures no flip.
2. **`wonkAmount` on a concept whose `wonk` is empty or absent is not refused.** It does nothing
   there. `params()` treats `headSink` without a serif the same way. An upright master may want to
   keep the key and drop the letters.
3. **Version 0.12.0, and the `Font output:` line follows the 0.9.0 entry** (`headSink`, the last
   opt-in key): `Font output: changes: a face that sets wonkAmount builds differently under 0.12.0
   than under 0.11.0, which ignored the key.` followed by the statement that no shipped concept sets
   it and every example rebuilds to the recorded digests. `Font output: unchanged` would be true of
   every existing concept and false of a concept that carries the key, so two installs at one
   `VERSION` would differ; CLAUDE.md "Version discipline" forbids that.
4. **No test in the font suite (`scripts/tests/test_font.py`) and no entry in
   `scripts/tests/mutate.py` for `wonkAmount`.** `wonk`, `shear` and `bend` have none either. The
   guards are repository tests. The font suite changes in one line only (the fixture pin below).
5. **The default is not exported from `gen.js`.** Tests restate 0.045, so a change to the constant
   fails a test instead of following it.
6. **A negative amount (a forward lean of single letters) is refused.** `shear` leans every glyph
   forward; nothing leans named letters forward.

## Findings outside this change

- **The font suite's headSink fixture inherits the project's `wonkAmount`.** It is built from the
  project's first concept with `wonk: "l"`. With the feature in place, a face whose first concept sets
  `wonkAmount: 0.2` fails two of the suite's three headSink tests (measured on a copy of the neutral
  example: 2 failed, 1 passed; at 0.1 and 0 all three pass), because the fixture's `l` gets diagonal
  serifs and has no lowercase head. This plan fixes it (item `font-suite-fixture-pin`), because the
  feature creates it.
- **A group whose only axis is the lean does not build.** `build.py` fails its self-check "glyphs
  without gvar variations" on `period hyphen endash emdash ellipsis bullet`: the lean moves those
  glyphs rigidly and the sidebearings cancel the move, so both masters are identical. A weight axis
  beside the lean varies every glyph. Documented, not changed.
- **A four-master weight and lean face from Driftwood `tideline` is 108,656 bytes** as woff2, over the
  102,400 budget the Driftwood example's `font.json` sets. The test below raises its own budget.
- **Advances follow the lean.** In that built face the advance of `l` is 226 at LEAN 0 and 305 at
  LEAN 100 (wght 400): the spacing profile reads the leaned outline. Documented, not changed.
- **The italic `w` already flips at the default lean.** Bract `text` italic flips `w` at an amount of
  0.004 and Driftwood at 0.019, so an italic group that mixes a `wonk` master with a plain one can be
  refused today. `references/generator.md` section 12 records that margin (0.0028). Not changed.
- **Not examined:** the whole font suite on a face whose concepts lean. The one run stopped at "no
  built font" for reasons unrelated to the lean.

## Code to be changed

### `scripts/gen.js` (item `gen-wonk-amount`)

1. **A named default.** Directly after line 443 (`var DROP_AMT_DEFAULT = 0.55; ...`) add
   `var WONK_AMOUNT_DEFAULT = 0.045; // the back-lean of the letters a concept names in wonk: x -= 0.045 * y, about 2.6 degrees, what every version up to 0.11.0 drew`.
2. **`xf()`, line 501.** `if (P.wonk && P.wonk.indexOf(ch) >= 0) x -= 0.045 * y;` becomes
   `if (P.wonk && P.wonk.indexOf(ch) >= 0) x -= P.wonkAmount * y;`. No fallback in `xf()`: every
   caller of `glyph()` builds its `P` with `params()` (`scripts/export.js`, `scripts/bounds.js`,
   `scripts/concepts/*.html`, `layWord` and `kern` in `gen.js`; checked with grep on 2026-11-25), and
   `PU` inside `glyph()` is copied from `P`. One default site, so one place a mutation can hide.
3. **`params()`, validation.** After the `crotch` check (lines 1139 to 1141) add:
   ```js
   if (concept.wonkAmount !== undefined && !(finiteNumber(concept.wonkAmount) && concept.wonkAmount >= 0 && concept.wonkAmount <= 0.2)) {
     var shownWonk = typeof concept.wonkAmount === "number" ? String(concept.wonkAmount) : JSON.stringify(concept.wonkAmount);
     throw new Error("params: concept " + concept.id + " sets wonkAmount to " + shownWonk + "; it must be a number from 0 to 0.2 (references/generator.md, section 4)");
   }
   ```
   `String()` for a number, because `JSON.stringify(NaN)` and `JSON.stringify(Infinity)` both print
   `null` and the message would name the wrong value.
4. **`params()`, default.** After `P.serifBracket = ...` (line 1144) add
   `P.wonkAmount = concept.wonkAmount === undefined ? WONK_AMOUNT_DEFAULT : concept.wonkAmount;`.
   `cacheKey()` serialises the concept, not `P`, so a concept without the key keeps its cache key and
   one with it gets its own.
5. **Comments.** Line 439: "the transforms (shear, bend, wonk)" becomes "the transforms (shear,
   bend, wonk with wonkAmount)". The header's ORIGIN list gains item 12 after item 11 (line 48):
   "The lean amount (0.12.0). A concept's wonkAmount sets how far the letters named in wonk lean back
   (x -= wonkAmount * y); unset it is 0.045, what every earlier version drew, so a concept without the
   key draws as before. The lean is applied before every branch decision, so a branch decision can differ
   between two masters that differ in wonkAmount, and export.js refuses a master pair whose structure or
   branch outcome differs, naming the glyphs. Two measured causes: the serif kind on a concept with
   serif ends (head or foot becomes diag), and the curved decision on a cut-end concept (Driftwood
   windswept). Compatibility is what export.js checks per pair; the amount does not guarantee it."

`scripts/export.js` and `scripts/build.py` do not change. The trial build below passed every
`build.py` self-check with a `LEAN` axis.

### Version carriers (item `version-bump`)

`VERSION` (`0.12.0`), `package.json` (`"version": "0.12.0"`), `SKILL.md` (frontmatter
`version: 0.12.0` and the line `**Version 0.12.0**`), `README.md` (the badge, `version-0.12.0-blue`),
`CHANGELOG.md` (the entry under Documentation to be updated).

## Code to be written

No new production file. The new files are tests: `tests/wonk_amount_probe.js`,
`tests/test_wonk_amount.py`, `tests/test_wonk_default.py`.

## New automated tests

Every measure reads what the generator, the exporter or the builder produced, never the generator's
source. `FONT_DESIGN_WONK_SCRIPTS` names another copy of the whole `scripts/` folder, with a copy of
`VERSION` beside it, for the watches in Verification; unset, the real folder. Both test files load
`tests/conftest.py` by path, as `tests/test_head_sink.py` does.

### `tests/wonk_amount_probe.js` (written by `tests-wonk-amount`, used by both test files)

`node tests/wonk_amount_probe.js GEN.js MODE SPEC_JSON`. It reports and asserts nothing. It loads the
generator afresh for each concept and style (the glyph cache is never freed; research ran out of a
4 GB heap without the reload). A glyph or a `params()` call that throws outside the `refusals` mode
ends the probe with a non-zero exit. Modes:

- `keys`: prints every key of `G`.
- `concepts`, spec `{files}`: per concept `{file, id, xs, ends, serif, shear, bend}`, `serif` true
  when a value of `ends` is `"serif"`, `shear` and `bend` true when the concept sets a non-zero one.
- `draw`, spec `{file, id, set, wonk, amounts, styles, mults, keys}`: `set` is merged over the
  concept; `wonk` is a string, or `"ALL"` for every key of `G` joined, or absent to leave the concept's
  own; each entry of `amounts` is a number or `"undef"` (the key deleted), and with `amounts` absent
  the concept keeps its own `wonkAmount` (test 6 needs that). Per glyph draw it prints
  `{concept, style, mult, amount, key, adv, counts, runs, sig, pHash, L, R, centre}`: `pHash` a sha256
  per polygon, `centre` two points of the centre line of the first polygon with two edge runs (the
  midpoints of the two edges at a quarter and at three quarters of the run, indexed as
  `tests/head_sink_probe.js` `bodiesOf` does), or `null`.
- `refusals`, spec `{file, id, cases}`: each case is `{label, value}` or `{label, token}` with token
  one of `NaN`, `Infinity`, `-Infinity`, `undefined`, `absent`, because JSON cannot carry those. Per
  case it prints `{label, delivered, message}`: `delivered` is `typeof v + ":" + String(v)` of the
  value the probe handed to `params()` (`absent` for a deleted key), `message` the error text or
  `null`.
- `old`, spec `{file, styles, mults, old}`: for every concept of the file, with `wonk` set to every
  key and `wonkAmount` absent, draws every key with the generator under test and with the generator
  at the path `old`, and per glyph draw prints `{concept, style, mult, key, same, leaning, first}`:
  `same` is exact equality of `polys`, `adv`, `L`, `R`, `sig` and `runs`; `leaning` is whether the old
  generator's drawing differs from its own drawing of the concept with `wonk: ""`; `first` names the
  first field that differs. Italic only for a concept that maps the `x` end, at 10 degrees.

### `tests/test_wonk_amount.py` (item `tests-wonk-amount`, proof: red-green)

Each marker below is the first assertion about the new behaviour, appears in no other assertion of its
test, and every assertion before it passes on 0.11.0 (research ran each red state on the unmodified
generator). It is the `expected_failure` of its test.

1. **`test_wonkamount_sets_how_far_a_named_glyph_leans`**. Level: across functions (`params()`,
   `xf()`, `glyph()`). Bract `bine` (no serif end, no swell, `xs` 0.98) with `wonk: "lIH"`, amounts
   `undef`, 0, 0.045, 0.1, 0.158, 0.2, mult 1 and 1.5, keys `l I H o n`. The lean of a stem is
   `(x1 - x0) / (y1 - y0)` of its two `centre` points; the expected lean is
   `-amount * xs * (1 + 0.16 * (mult - 1))`, restated from `references/generator.md` section 4.
   - Setup, passes on 0.11.0: the probe exits 0; `l`, `I` and `H` report a `centre`; the probe echoes
     `xs` 0.98; `WONK-MEASURE-CONTROL:` with the key absent, `l` leans `-0.045 * 0.98 * (1 + 0.16 * (mult - 1))`
     within 1e-9 at both multipliers (prototype: -0.0441 and -0.047628, error under 1e-16).
   - **Expected failure: `WONK-AMOUNT-LEAN:`**. For each amount in the order 0.158, 0, 0.1, 0.2,
     0.045, each of `l I H`, each multiplier: the lean equals the expected lean within 1e-9. On
     0.11.0 `l` at 0.158 leans -0.0441 where -0.15484 is expected.
   - Then `WONK-SCOPE:` the keys `o` and `n`, which `wonk` does not name, have at every amount the
     `pHash`, `adv`, `L` and `R` of the same concept drawn with `wonk: ""`.
2. **`test_wonkamount_outside_its_range_is_refused`**. Level: unit (`params()`). The cases are
   written in the test, not read from the generator. Bad: -0.01, 0.2000001, 0.21, 1, `"0.1"`, `null`,
   `true`, `false`, `[0.1]`, `{}`, and the tokens `NaN`, `Infinity`, `-Infinity`. Good: 0, 0.045, 0.1,
   0.2, and the tokens `undefined` and `absent`.
   - Setup, passes on 0.11.0: `WONK-DELIVERED:` every case's `delivered` is what the case means
     (`number:NaN`, `number:Infinity`, `object:null`, `string:0.1`, `undefined:undefined`, `absent`
     and so on), so the harness is shown to deliver each bad value.
   - **Expected failure: `WONK-AMOUNT-REFUSED:`**. For each bad case, `message` is not `null`. On
     0.11.0 `params()` accepts -0.01.
   - Then `WONK-REFUSAL-MESSAGE:` each message holds `wonkAmount`, the concept's id,
     `it must be a number from 0 to 0.2` and `references/generator.md, section 4`, and the messages
     for `NaN` and `Infinity` hold `NaN` and `Infinity`. Then `WONK-AMOUNT-ALLOWED:` each good case's
     `message` is `null`.
3. **`test_two_masters_that_differ_only_in_wonkamount_export_together_without_a_serif_end`**. Level:
   integration across modules (a concepts file, `gen.js`, the `export.js` command, the JSON read
   back). For each of Bract `bine`, Driftwood `tideline`, Driftwood `dune`: a face in `tmp_path` made
   of the example's `font.json` with `groups` replaced by one group `roman` (one axis, tag `LEAN`,
   0 to 100; masters `Upright` and `Leaning`, both mult 1), and a `concepts.js` that requires the
   example's file and exports two copies of the concept, ids `lo` and `hi`, both with `wonk` every
   key, `wonkAmount` 0 and 0.2. Run `node <scripts>/export.js --font <face>/font.json <face>/export.json`.
   - Setup, passes on 0.11.0: `WONK-NO-SERIF-SET:` the probe's `concepts` listing of the three
     example concept files says those three ids are exactly the concepts with `serif` false and with
     neither `shear` nor `bend` set (so a new shipped concept of that kind fails here until it is
     added; `windswept` is left out by the second condition). `WONK-EXPORT-EXIT:` the exporter exits
     0, stderr quoted in the message.
   - **Expected failure: `WONK-EXPORT-LEAN:`**. The `polys` of `l` differ between the two masters.
     On 0.11.0 both masters draw the 0.045 lean and are identical.
   - Then: in the `Leaning` master the mean x of the points of `l`'s first polygon above y 700 minus
     the mean x of those below y 40 is `-0.2 * xs * 740` within 0.5 units (prototype: -145.05, -145.00
     and -165.75), and within 0.5 of 0 in `Upright`; at least 120 of the 131 glyphs differ between the
     masters (prototype: 125); every glyph's polygon point counts, `runs` and `sig` are equal between
     the masters.
4. **`test_a_serif_concept_is_refused_when_its_masters_stand_either_side_of_the_serif_threshold`**.
   Level: integration across modules, the same face builder on the neutral `text` concept. It pins the
   limit this plan documents: the exporter refuses, and says which glyphs.
   - **Expected failure: `WONK-SERIF-REFUSED:`**. The exporter exits 1. On 0.11.0 it exits 0, because
     the key is ignored and the masters are identical.
   - Then: stderr holds `differ in structure or branch outcome between masters of group roman`; the
     glyph list after that text holds `l`, `H`, `n`, `i` and `I` and at least 50 glyphs (prototype:
     57); an `Upright` record line holds `serifB=foot` and a `Leaning` record line holds
     `serifB=diag`.
5. **`test_a_face_with_a_weight_and_a_lean_axis_builds`**. Level: the software as a whole (concepts
   file to woff2, through `build.py` and every self-check). The face builder with Driftwood
   `tideline`, axes `wght` 400 to 700 and `LEAN` 0 to 100, four masters (`Regular` lo mult 1,
   `Bold` lo mult 1.5, `LeanRegular` hi mult 1, `LeanBold` hi mult 1.5), instances at the three
   corners used, `hairline_floors` 20 for each master, `size_budget_bytes` 204800. Run
   `<python> <scripts>/build.py --font <face>/font.json --no-requirements --keep-masters <face>/keep/export.json`.
   - Setup, passes on 0.11.0: `WONK-BUILD-EXIT:` the build exits 0 (prototype: 39 self-checks ok,
     6 s); the font's `fvar` axes are `wght` (400, 400, 700) and `LEAN` (0, 0, 100).
   - **Expected failure: `WONK-BUILD-LEAN:`**. In the instance at `wght` 400, `LEAN` 100
     (`fontTools.varLib.instancer`), the mean x of `l`'s points above y 700 minus the mean x of those
     below y 40 is `-0.2 * 0.98 * 740` within 1.5 units (prototype: -145.5). On 0.11.0 it is -32.0.
   - Then: within 1.5 of 0 at `LEAN` 0, and within 1.5 of half the figure at `LEAN` 50 (prototype:
     -72.75).
6. **`test_the_font_suites_headsink_fixture_keeps_its_own_lean`**. Level: across tools (a face, the
   generator, the font suite run by path). A copy of `examples/neutral` in `tmp_path` whose first
   concept gains ` wonkAmount: 0.2` (the anchor `beak: true, tear: false, serifGrow: 0.4 },` occurs
   once, in the first concept, because the last concept has no trailing comma; assert the count
   before replacing it with `beak: true, tear: false, serifGrow: 0.4, wonkAmount: 0.2 },`).
   - **Expected failure: `WONK-SUITE-FACE:`**. Precondition that the face can show the defect at all:
     the copy's first concept, drawn by the probe with the fixture's own overrides (`wonk: "l"`,
     `shear: 0`, `bend: 0`) and `amounts` absent, leans its `l` by `-0.2 * 0.92` within 1e-9
     (prototype: -0.184, error under 1e-16). On 0.11.0 it leans `-0.045 * 0.92`, -0.0414.
   - Then `WONK-SUITE-FIXTURE:` running `<scripts>/tests/test_font.py` by path with `-k headsink`,
     `--font`, `--requirements`, `--static-dir none`, `--scripts=<scripts>` on the copy exits 0 with
     `3 passed`. The red gate proves only the precondition; watch W7 proves this assertion.

### `tests/test_wonk_default.py` (item `tests-wonk-default`, proof: mutation)

- **`test_an_unset_wonkamount_draws_what_0_11_0_drew`**. Level: the whole generator against the
  previous release. `GEN_0_11_0 = "4efcca7"`, the last commit that changed `scripts/gen.js` before
  0.12.0 (`git log -1 --format=%h -- scripts/gen.js` printed it on 2026-11-25; its file has the
  sha256 of the working tree's, `27ec39dd...e4c0`). The test writes `git show 4efcca7:scripts/gen.js`
  to `tmp_path` (failing, not skipping, when git cannot show it, as `tests/test_cut_reach.py` does)
  and runs the probe's `old` mode, one node process per concept file, on
  `examples/neutral/concepts.js`, `examples/bract/concepts.js` and `examples/driftwood/concepts.js`,
  roman and italic, mult 1 and 1.65.
  - Floors, so the test cannot pass on nothing: at least 7,000 glyph draws compared (prototype:
    7,598) and at least 6,800 of them `leaning` (prototype: 7,565), so the comparison is of letters
    that lean.
  - `WONK-DEFAULT:` no draw has `same` false; the message gives the count and the first ten
    (concept, style, mult, key).
  - It passes when written: the generator under test is the 0.11.0 generator. It is proved by the
    mutation in Verification (prototype under it: 7,552 of 7,598 draws differ), and it must still
    pass after `gen-wonk-amount` (prototype with the changed line: 0 differ).

## Automated tests to be changed

- **`scripts/tests/test_font.py`, the `HEADSINK_FIXTURE` (item `font-suite-fixture-pin`).** Line 1642:
  `shear: 0, bend: 0, wonk: "l" });` becomes `shear: 0, bend: 0, wonk: "l", wonkAmount: 0.045 });`.
  The comment at line 1638 gains: "the amount is pinned (wonkAmount, 0.12.0), so a project whose first
  concept sets a steeper lean cannot turn the `l`'s head serif into a diagonal one". Inert on 0.11.0,
  which ignores the key (measured: the pinned suite passes its three headSink tests on the unmodified
  generator), so it lands before `gen-wonk-amount`.
- No other existing test changes. These must stay green unchanged, and they are the proof that every
  existing concept, fixture and genre recipe draws what it drew: `tests/test_backward_compat.py`
  (the three examples against `tests/fixtures/baseline.json`), `tests/test_genres.py` (the recipe
  digests), `tests/test_cut_reach.py` (every shipped concept file against `d9974f3`),
  `tests/test_head_sink.py`, `tests/test_serif_joints.py`, `tests/test_joint_spacing.py`,
  `tests/test_r_leg_join.py`, `tests/test_weight_decisions.py`, `tests/test_schemas_and_concepts.py`,
  `tests/test_mutate_harness.py`. `tests/fixtures/baseline.json` is not re-recorded.

## Documentation to be updated

Every figure below marked "prototype" or taken from the first section was measured on a copy with a
one-line change. The documentation states figures re-measured with `tests/wonk_amount_probe.js` and
the real `scripts/export.js` on the final generator, with the date and the node version. A figure
that is not re-measured is left out.

- **`references/generator.md`** (item `docs-generator-testing`):
  - Section 4, the `wonk` row (line 252): the effect reads "those glyphs lean back:
    `x -= wonkAmount * y` (0.045 unless the concept sets `wonkAmount`)".
  - Section 4, a new row `wonkAmount` after it. Range: 0 to 0.2 (`params()` refuses outside, bounds
    allowed; a string, `null`, a boolean, `NaN` and an infinity are refused); default 0.045. Effect:
    how far the glyphs named in `wonk` lean back, applied before `xs`, so the drawn slope is
    `wonkAmount * xs * (1 + 0.16 * (W/W0 - 1))`, times 0.95 and less the slant in an italic; 0.045 is
    about 2.6 degrees and 0.158 about 9 degrees at `xs` 1. Notes: read only for a glyph `wonk` names,
    and not refused when `wonk` is empty; unset draws what 0.11.0 drew
    (`tests/test_wonk_default.py`); **the range is a design range, not a compatibility bound**; a
    branch decision can flip between masters (the serif kind on a concept with serif ends, `curved` on
    a Driftwood `windswept` cut-end concept), and `export.js` refuses such a pair, pointing to
    section 12; advances and
    kerns follow the leaned outline; not echoed into the manifest.
  - Section 6, a bullet: a lean axis interpolates the lean of each centre line linearly (the built
    trial reads half the lean at the middle of the axis); the stroke edges are offsets along the
    normal, so an instance between the masters is not what the generator would draw at that amount.
    State a measured deviation or say it was not measured.
  - Section 11, a bullet in the list of what `params()` refuses: `wonkAmount` that is not a number
    from 0 to 0.2 (the error names the knob and the range; a string, `null`, a boolean, `NaN` and an
    infinity are refused too).
  - Section 12, a paragraph "A lean (0.12.0)", stating the exact guarantee and no more. Compatibility
    is what `export.js` checks per master pair (same structure and branch outcome for every glyph); the
    amount does not guarantee it. Two measured failure modes: (1) the serif-kind test reads the leaned
    reference tangent, and a plumb stem turns `diag` when `wonkAmount * xs` passes 0.1005, with the
    table of first flips from the first section, re-measured, and 0 against 0.2 refused on every
    concept the three fixtures build; (2) Driftwood `windswept` (cut ends, no serif end) flips
    `curved` on 1 glyph at 0.1 and 2 at 0.2, re-measured. Measured clean, 0 against 0.2: `bine`,
    `tideline` and `dune`, and no other concept is claimed. The paragraph does not say that serif ends
    are the only cause or that a concept without them is compatible; the exporter exits 1 naming the
    glyphs.
- **`references/variable-font-build.md`** (same item): beside the paragraph on a group's `axes` (line
  203), a paragraph "A lean axis": a custom four-letter tag such as `LEAN` builds; masters at the
  corners differ in `wonkAmount`; pair it with a weight axis, because a group whose only axis is the
  lean fails "glyphs without gvar variations" on the glyphs the lean does not move; the size grows
  (the measured figure); the compatibility limit (serif kind, `windswept` `curved`), pointing to `generator.md` section 12. One claim comes from
  memory and was not checked in research: that OpenType reserves lowercase tags for registered axes
  and asks for capitals in a private one. Check it against the `fvar` specification before writing
  it, or leave the sentence out. Any command shown must pass `tests/test_docs_commands.py`.
- **`references/traps.md`** (same item): the next free row (44 is the last) under a line "One more,
  met in 0.12.0": symptom (the exporter refuses a group with a lean axis on about 57 glyphs, with
  `serifB=foot` in one master and `serifB=diag` in the other); cause (a branch decision differs between the masters: one measured cause is the lean
  passing the serif-kind threshold, another is the `curved` flip on Driftwood `windswept`; the
  exporter's refusal is the check); guard (`tests/test_wonk_amount.py`); where.
- **`references/testing.md`** (same item): contents line and section 13, "The lean-amount guards
  (0.12.0)", in the form of section 12: the table of tests with the first assertion each fails on
  0.11.0, the mutation proof of `tests/test_wonk_default.py`, and the watches W1 to W7 with the
  figure each fired on, the date, the node version and the `shasum -a 256` of the real
  `scripts/gen.js` before and after.
- **`CHANGELOG.md`** (item `version-bump`): a `## [0.12.0]` entry above 0.11.0. First line:
  `Font output: changes: a face that sets wonkAmount builds differently under 0.12.0 than under 0.11.0, which ignored the key. No concept this repository ships sets wonkAmount, and with the key absent every example rebuilds to the recorded digests (`tests/test_backward_compat.py`) and the letters a concept names in `wonk` are drawn as 0.11.0 drew them (`tests/test_wonk_default.py`).`
  Then `### Added` (the setting, its range and default, the refusal), `### Changed` (the font suite's
  headSink fixture pins its lean), `### Looked at and not changed` (the `windswept` `curved` flip and the serif-kind decision under a
  lean, with the 57 glyphs and the thresholds; a group whose only axis is the lean; the italic `w`).
  In `## Releases`: the row `| v0.12.0 | the merge commit of the release branch | tagged after the merge |`,
  and the v0.11.0 row becomes `| v0.11.0 | 14e03fc | merge of PR #28 |` (`git tag --list` shows
  v0.11.0 on 14e03fc; confirm with `git rev-list -n 1 v0.11.0` before writing it).
- **`SKILL.md`, `README.md`, `VERSION`, `package.json`** (item `version-bump`): the version only.
- **`CLAUDE.md`** (item `docs-generator-testing`): the layer 2 line's test count, file count and date,
  from `.venv/bin/python3 -m pytest --co -q` on the final tree (767 tests in 30 files today; seven
  new tests in two new files are planned); the duration of the full smoke run if it is timed.
- **`docs/plan-wonk-amount.md`** (same item): this plan as built, with an "As built" section that
  records what differed, the operator's rulings and the re-measured figures. No machine path.
- **`scripts/gen.js`** comments: under Code to be changed.
- **Not changed, checked:** `templates/concepts.example.js` and `templates/concepts.genres.js` name
  neither `wonk`, `shear` nor `bend` (grep, 2026-11-25), so there is no transform list to extend.
  `README.md` and `SKILL.md` do not name `wonk`. `templates/font.schema.json` already allows any
  four-letter axis tag.

## Work items

| id | title | kind | files | verifiable_by |
|---|---|---|---|---|
| `tests-wonk-amount` | Write the probe and the six tests that fail on 0.11.0 because wonkAmount has no effect and is not validated. | test-new | tests/wonk_amount_probe.js, tests/test_wonk_amount.py | agent |
| `tests-wonk-default` | Write the test that holds an unset wonkAmount to the drawing of the 0.11.0 generator. | test-new | tests/test_wonk_default.py | agent |
| `font-suite-fixture-pin` | Pin the lean of the font suite's headSink fixture to 0.045 so a project's wonkAmount cannot change it. | test-change | scripts/tests/test_font.py | agent |
| `gen-wonk-amount` | Read the lean of the wonk letters from the concept setting wonkAmount, default 0.045, refused outside 0 to 0.2. | code-change | scripts/gen.js | agent |
| `version-bump` | Bump the version to 0.12.0 and write the changelog entry with its font-output line. | code-change | VERSION, package.json, SKILL.md, README.md, CHANGELOG.md | agent |
| `docs-generator-testing` | Document wonkAmount and its serif limit in the generator and build references, the traps list and the testing log, keep the plan, then run the full smoke check last. | doc-change | references/generator.md, references/variable-font-build.md, references/traps.md, references/testing.md, docs/plan-wonk-amount.md, CLAUDE.md | agent |
| `lean-range-ruling` | The operator rules before the build on the stop condition the request set and on decisions 2 to 6, because a 0.2 lean flips the serif kind in 57 glyphs of every concept the fixtures build. | live-acceptance | | operator |
| `tiki-lean-trial` | The operator builds the Tiki lean trial with wonkAmount 0.158 after the build and judges the leaning letters at LEAN 100. | live-acceptance | | operator |
| `release-acceptance` | The operator runs CI by hand on the branch, merges, and tags v0.12.0. | live-acceptance | | operator |

Order: `lean-range-ruling` (the pre-build ruling) is accepted before anything is built. Then `tests-wonk-amount` (it writes
the probe), `tests-wonk-default`, `font-suite-fixture-pin` (inert on 0.11.0), `gen-wonk-amount`,
`version-bump`, `docs-generator-testing`, whose verification ends with the full smoke run on the final
bytes. `tiki-lean-trial` follows `gen-wonk-amount` and `release-acceptance` follows the full run.
`lean-range-ruling` accepts `tests-wonk-amount`, the first item built, which it gates;
`tiki-lean-trial` accepts `gen-wonk-amount`; `release-acceptance` accepts `version-bump`.

## Verification

Layers, per CLAUDE.md "Choosing how much to test": the change touches `scripts/gen.js` (layer 4), the
font suite (layer 3, then layer 4) and `VERSION` (layer 4 with `--full`, then layer 5). The agent runs
layers 1 to 4 here. Layer 5 is `release-acceptance`. The commit and the pull request say which layers
ran.

### Per work item

- **`tests-wonk-amount`, agent, proof: red-green.**
  `.venv/bin/python3 -m pytest tests/test_wonk_amount.py -q` on the unmodified generator: six failed,
  each on its own marker (`WONK-AMOUNT-LEAN:`, `WONK-AMOUNT-REFUSED:`, `WONK-EXPORT-LEAN:`,
  `WONK-SERIF-REFUSED:`, `WONK-BUILD-LEAN:`, `WONK-SUITE-FACE:`). A test that fails on a setup
  assertion, on a probe crash or on a count below its floor is not red for the expected reason: fix
  the test. `.venv/bin/python3 -m ruff check tests/` passes. Green after `font-suite-fixture-pin` and
  `gen-wonk-amount`.
- **`tests-wonk-default`, agent, proof: mutation.** The test passes when written, on the unmodified
  generator. Recipe, on the tree before `gen-wonk-amount`:
  - File: `scripts/gen.js`. `mutation_files`: `scripts/gen.js` only.
  - Find the one line whose text, after its two spaces of indentation, is
    `if (P.wonk && P.wonk.indexOf(ch) >= 0) x -= 0.045 * y;` (line 501; `0.045` occurs once in the
    file).
  - Replace it with `if (P.wonk && P.wonk.indexOf(ch) >= 0) x -= 0.05 * y;`.
  - No rebuild or restamp: the test runs node on the file.
  - Run `.venv/bin/python3 -m pytest tests/test_wonk_default.py -q`. The one test must fail on its
    assertion `WONK-DEFAULT:` (prototype: 7,552 of 7,598 glyph draws differ from `4efcca7`).
  - Restore `scripts/gen.js` by digest. The test passes again.
- **`font-suite-fixture-pin`, agent.** On the unmodified generator:
  `.venv/bin/python3 -m pytest scripts/tests/test_font.py -q -p no:cacheprovider --font examples/neutral/font.json --requirements examples/neutral/requirements.json --static-dir none -k headsink`
  prints `3 passed`, and the same on `examples/driftwood`. `tests/test_head_sink.py` green. After
  `gen-wonk-amount`: layer 3 on the neutral fixture (the command in `pytest.ini`, after building the
  example as `examples/neutral/README.md` says), then the mutations run inside layer 4.
- **`gen-wonk-amount`, agent.** Not started before `lean-range-ruling` is accepted.
  `tests/test_wonk_amount.py` and `tests/test_wonk_default.py` green (seven tests). The files named
  under "Automated tests to be changed" as unchanged are green. `npm run lint:js` passes. Watches,
  each one exact replacement that matches once, applied to a copy of `scripts/` outside the
  repository with a copy of `VERSION` beside it, the two test files run with
  `FONT_DESIGN_WONK_SCRIPTS` on the copy, the real `scripts/gen.js` checked by `shasum -a 256` before
  and after. Log each in `references/testing.md` section 13 with the figure it fired on. A watch that
  stays green is a finding about the test: say so in the log and the pull request, and strengthen the
  test.
  - W1, the setting ignored: `x -= P.wonkAmount * y;` back to `x -= 0.045 * y;`. Expected red: tests
    1, 3, 4, 5 and 6 of `tests/test_wonk_amount.py` on their markers; test 2 and
    `tests/test_wonk_default.py` green.
  - W2, the default moved: `var WONK_AMOUNT_DEFAULT = 0.045;` to `0.05`. Expected red: `WONK-DEFAULT:`
    and `WONK-MEASURE-CONTROL:`.
  - W3, the range check removed: the `if (concept.wonkAmount !== undefined && ...) { ... }` block
    deleted. Expected red: `WONK-AMOUNT-REFUSED:`.
  - W4, the bounds excluded: `>= 0 && concept.wonkAmount <= 0.2` to `> 0 && concept.wonkAmount < 0.2`.
    Expected red: `WONK-AMOUNT-ALLOWED:` on 0 and 0.2.
  - W5, the weakest check, a value coerced: `finiteNumber(concept.wonkAmount) && concept.wonkAmount >= 0 && concept.wonkAmount <= 0.2`
    to `+concept.wonkAmount >= 0 && +concept.wonkAmount <= 0.2`. Expected red: `WONK-AMOUNT-REFUSED:`
    on `"0.1"`, `null`, `false` or `[0.1]`.
  - W6, the letter test dropped: `if (P.wonk && P.wonk.indexOf(ch) >= 0)` to `if (P.wonk)`. Expected
    red: `WONK-SCOPE:`.
  - W7, the fixture pin removed, in the copy's `tests/test_font.py`: `wonk: "l", wonkAmount: 0.045 });`
    back to `wonk: "l" });`. Expected red: `WONK-SUITE-FIXTURE:` (prototype: 2 failed, 1 passed).
  - Not watched, and said so in the log: replacing `finiteNumber(v)` by `typeof v === "number"` is an
    equivalent mutation, because `NaN` and the infinities fail the two comparisons.
- **`version-bump`, agent.** `tests/test_versions_and_skill.py`, `tests/test_docs_commands.py`,
  `tests/test_hygiene.py` green. The `Font output:` line is the one quoted above, unless the operator
  ruled otherwise (decision 3).
- **`docs-generator-testing`, agent.** Re-measure every figure the documentation states, on the final
  generator. `tests/test_docs_commands.py`, `tests/test_hygiene.py`,
  `tests/test_versions_and_skill.py` green. Then, on the final bytes, `bash scripts/smoke.sh --full`
  (steps 1 to 11; at most 59 min 12 s on 2026-11-25): exit status 0, every mutation RED in step 5,
  layer 2 green in step 7 with the new test count. Log the result in `references/testing.md` section
  13 and put the count and the date in `CLAUDE.md`. A file edited after the full run reruns the
  layer that file needs.

### Operator items

- **`lean-range-ruling`, operator, pre-build, live-acceptance of `tests-wonk-amount`.** It gates the
  whole build and needs nothing built. It requires:
  1. The operator's ruling on the stop condition in the first section: ship the 0 to 0.2 range with
     the serif limit documented and pinned by tests 3 and 4 (recommended), narrow the range, change
     the serif decision, or stop the change. Accepting this item is the first of those. Any other
     ruling changes tests 3, 4 and 5, the range in `params()` and the documentation, so the plan is
     revised before the build.
  2. The operator's rulings on decisions 2 to 6 where they differ from the plan.
- **`tiki-lean-trial`, operator, post-build, live-acceptance of `gen-wonk-amount`.** It does not gate
  the build. It requires the motivating case, which needs files that are not in this change and human
  judgement: in the main checkout, the untracked Tiki Terminal concept and its lean trial
     (`examples/tiki-terminal/`, `out/tiki/leantrial/`). Set `wonkAmount: 0.158` on the LEAN 100
     masters' concept, export and build the four-master group, and look at the leaning letters at
     LEAN 100. Research measured no structure difference on that concept with `aeiokrAEIO`, on a
     copy; it did not build it, and the trial's stroke folds are a separate problem.
- **`release-acceptance`, operator, live-acceptance of `version-bump`.** It requires GitHub
  credentials: `gh workflow run ci.yml --ref feature/lean-amount` (layer 5; CI does not run on push),
  the four `test` jobs and the lint job green, the merge of the pull request, and the tag `v0.12.0`
  on the first `main` commit that carries the version, pushed after the merge. Then the `## Releases`
  row for v0.12.0 can name the commit.

## As built

Built as planned, with the departures below. Dates are 2026-11-25; node 26.13.1.

- **The ruling on the stop condition.** The plan's recommended option was built: the range 0 to 0.2 ships, the serif limit is
  documented and pinned by tests 3 and 4, and the serif decision is unchanged. The operator gave this ruling twice. The run first stopped before the plan review. The operator was then shown the 57 flipped glyphs, the cause (`serifKindOf` reading the leaned skeleton) and the four options (ship 0 to 0.2 with the limit documented, narrow the range, decide the serif kind before the lean, or stop). They were told that accepting also accepts decisions 2 to 6, which were listed one by one. They answered "Yes" to accepting `lean-range-ruling` and `release-acceptance`. The plan review then split the Tiki trial into `tiki-lean-trial` and rewrote the compatibility wording, which changed every consent key. The operator was shown both changes and that decisions 1 to 6 were unchanged, and they answered "yes" to all five keys. Decisions 2 to 6 were built as written.
- **Work items.** `tests-wonk-amount`, `tests-wonk-default`, `font-suite-fixture-pin` and `gen-wonk-amount` are as in "Code to be
  changed" and "New automated tests". `version-bump` and `docs-generator-testing` are as written under "Documentation to be updated".
- **Figures re-measured on the final generator**, in `references/generator.md` section 12 and `references/testing.md` section 13: the
  first-flip table equals the plan's prototype for every row; `windswept` first flips `x` at 0.069; the four-master weight and lean face
  is 108,508 bytes as woff2 with one named instance (the plan's 108,656 was a different configuration); the `l` top against foot is 0.0,
  -72.75 and -145.5 at LEAN 0, 50 and 100, and the advance of `l` is 226, 266 and 305; the italic `w` first differs at 0.0038 (Bract) and
  0.0189 (Driftwood), and not up to 0.2 on the neutral concept. The 0.158 figure for the Tiki trial (about 9 degrees) is arithmetic on
  `atan(0.158)`, not a measurement.
- **Not carried out in this change.** The OpenType claim about lowercase tags for registered axes and capitals for private ones was not
  checked against the `fvar` specification, so the documentation leaves the sentence out. How far an instance between lean masters
  stands from the generator's drawing at that amount was not measured; the documentation says so. The font suite on a face whose
  concepts lean was not run beyond the headSink tests (`WONK-SUITE-FIXTURE:`).
- **The watches** W1 to W7 all fired (`references/testing.md` section 13). W4 and W5 turn red on more tests than the plan named, because
  the amounts 0 and 0.2 are used by the other tests, and the two assertions that carry them stop at their first case.
- **The test count.** The plan expected 774 repository tests after seven new ones; `pytest --co -q` on the final tree counts 775 in 32
  files (`CLAUDE.md` now says so). The gap of one against the recorded 767 was not traced.
- **Items left to the operator.** `tiki-lean-trial` (build the Tiki lean trial at `wonkAmount` 0.158 and look at the leaning letters at
  LEAN 100) and `release-acceptance` (CI by hand, merge, tag `v0.12.0`, then the `## Releases` row names the commit).
