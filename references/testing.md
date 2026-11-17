# Testing a generated font: the suite template, its mutations, and the survivors

WHAT IT'S FOR: the reference for phase 7's "watch every guard fail". The skill copies the whole
`scripts/` folder into the site repo (`tools/<face>/scripts/`), `test_font.py`, `conftest.py` and
`mutate.py` included, because the suite needs `gen.js`, `export.js` and `build.py` beside it (the
conftest header says how a site that keeps the tests elsewhere points `--scripts` at them), and
fills `scripts/tests/test_site_wiring.py.tmpl` into the site's own tests. This file explains each test, the
exact property it pins, the mutation that must turn it red, how to choose a mutation that proves
the property rather than the fix, the three survivor shapes from Bract's first mutation run, and
the harness rules. Read it before running `mutate.py` and whenever a mutation stays green.

The first column of the table in section 2 gives each test's short name from the plan. The function
names in `scripts/tests/test_font.py`, in file order, are: `test_the_cmap_is_exactly_the_required_set`,
`test_every_required_character_is_mapped`, `test_nbsp_is_the_space_glyph`,
`test_ascii_apostrophe_draws_the_right_mark`, `test_the_axes_and_instances_are_what_the_css_relies_on`,
`test_every_glyph_with_contours_varies`, `test_each_master_location_reproduces_its_exported_outlines`,
`test_quote_glyphs_follow_the_apostrophe_in_every_master`, `test_avar_maps_the_reviewed_intermediate_weights`,
`test_kerning_and_advances_at_every_master`, `test_kerning_and_advances_at_the_interpolated_location`,
`test_hairlines_clear_the_floor`, `test_no_stroke_edge_folds_back`,
`test_the_fold_detector_sees_first_segment_decimated_and_unequal_folds`, `test_the_font_is_under_budget`,
`test_no_glyph_exceeds_the_win_metrics`, `test_the_line_height_is_the_reviewed_one_on_every_platform`,
`test_fs_type_is_the_operators_embedding_decision`, `test_stat_names_every_named_instance`,
`test_the_smart_dropout_program_pairs_with_gasp`, `test_the_code_page_and_name_platforms_are_the_reviewed_ones`,
`test_glyphs_declare_their_overlaps`,
`test_the_shipped_fonts_match_their_manifest`, `test_the_font_names_the_project`,
`test_style_metadata_matches_the_group`, `test_the_italic_straight_tick_is_slanted`,
`test_the_build_is_reproducible`, `test_dropamt_scales_the_outer_inner_and_symmetric_teardrop`,
`test_dropamt_changes_the_teardrops_and_flareamt_with_tear_throws`,
`test_export_refuses_a_required_character_without_a_skeleton`,
`test_build_refuses_a_required_character_without_a_skeleton` (C6: the build itself, on the export
path and the `--masters` path), `test_build_refuses_a_masters_json_that_overstates_its_stroke_width`
(C7), `test_build_refuses_a_masters_json_whose_parameters_differ_from_the_generator` (re-review
code-a F002), `test_build_refuses_a_masters_json_with_a_polygon_record_missing` (re-review code-a
F003) and `test_static_instances_exist_and_match_the_variable_font`. Cite those names in a record.

Contents

1. Why a green test proves nothing until it has failed
2. The font suite, test by test
3. Choosing the weakest mutation
4. The three survivor shapes, verbatim from Bract
5. Running scripts/tests/mutate.py
6. The site-wiring template
7. Harness rules
8. The repository's own guards for the added tools, and the survivors they showed

## 1. Why a green test proves nothing until it has failed

Every failure these two faces actually had passed a "the field exists" check: a 301 to a 404, a
sitemap with no dates, a quote glyph with the wrong advance, a fold guard that returned 0. The
operator's standing rule: after adding or changing a guard, break the code it guards and confirm
the suite goes red; if it stays green the test is decorative. Bract's first run: 28 mutations, 26
red, 2 green, both fixed before commit. The two greens are in section 4; they are the reason this
file exists.

## 2. The font suite, test by test

`conftest.py` takes `--font font.json` and `--requirements requirements.json`, and provides `font`
(a `TTFont` of the built woff2), `export` (a fresh node export, run once per session), `manifest`
and `cfg` (`font.json`, used only for paths: the woff2, the manifest, the concepts file). No expected
value comes from `font.json` (plan finding F002), so the mutation set includes editing `font.json`
(dropping an axis, a character, lowering a floor) and the suite must go red.

The expectations come from two sources, and the record should say which a given test rests on:

- **Pinned in `requirements.json`**, reviewed with the operator and changed only with them: the
  cmap set and the required characters; the axes, their ends and the named instances; the `avar`
  map; the hairline floor per master; the hand kern pairs; the titles the kerning test lays; the
  name-table strings; the size budget; the fold units; the `gasp` table; the word space per
  master (`word_space`, review finding C9); and, since 2026-11-16, the font-table decisions: `names.fs_type`,
  each group's `vertical_metrics`, the STAT values (derived from the axes and instances), `tables.prep_hex`,
  `tables.code_page_range1` and `tables.mac_names`. A test over these fails when the font disagrees with
  the reviewed expectation, whatever the generator did.
- **Consistency checks against a fresh export** (`export.js` run by the `export` fixture from the
  same `gen.js` and `concepts.js`): the per-glyph outlines at each master's location (F013), the
  value of every emitted kern pair, the whole-title widths, and the manifest-equals-export
  equalities (hairline minima, advances, point counts). These prove that the built font is what the
  exporter drew. They do not prove that what the exporter drew is right.

**The shared-defect limit.** A defect in `gen.js` that both the export and the font inherit — a
skeleton drawn wrong, a kern the same code computes wrongly on both sides, a hairline measured on
the wrong sample — agrees with itself, so every consistency check passes. What catches it is the
first group: the requirements-pinned values (a floor, a hand pair, a word space, the cmap), the
independent fixtures (the fold detector fed hand-built edges, the quote glyphs re-derived in the
test, the teardrop fixture) and, outside the suite, the design-review screenshots. When a test in
the table below reads "equals the exporter's", that is the limit it carries.

| Test (plan name) | Asserts | Named mutation | Notes |
|---|---|---|---|
| covers every display character | `HTMLParser` over the built pages for the display selectors (or `titles.txt`) → every character in the cmap, naming the first page that uses it | put `ž` in a built H1 | the site-side coverage test; Bract's named the page |
| cmap is exactly the declared set | set equality with `requirements.json` `cmap` | drop U+2018 from the cmap table and rebuild | the F007 test: a build that maps something new or drops something fails here |
| NBSP is space; ASCII apostrophe is curly and ≠ tick | `cmap[0xA0] == cmap[0x20]`; `cmap[0x27] == cmap[0x2019]`; the apostrophe's outline differs from `quotesingle`'s, which is unmapped | map U+0027 to `quotesingle` **and** disable the two self-checks (three edits) | survivor shape 2, section 4 |
| axes and instances | `fvar` axes and named instances equal `requirements.json` | opsz max 72 | — |
| every contoured glyph varies | a `gvar` entry per contoured glyph | delete `o`'s `gvar` entry with the self-check off | two edits |
| each master location reproduces its exported outlines (F013) | instancing at each master's location returns that master's polygons within 2 units, advances exact, every glyph including the builder-made quotes (diff review F004) | build one master from another's outlines (Bract: DisplayBold from TextBold's; failed at 15.2 units) | the one that proves both axes move every glyph |
| quote glyphs follow the apostrophe at every master | re-derives all six quote glyphs from the exported apostrophe in the test and checks outlines and advances exactly | restore Driftwood's `quotedblleft` advance (issue #23) | the test does its own derivation; it does not read the builder's |
| Medium is the reviewed weight | `avar` maps normalized 0.333 → 0.6 (±0.01) | drop the map | Bract's mutation raised `KeyError: 'avar'` |
| kerning and advances at every reviewed location (F005, F010, C9; re-review code-a F004, F005) | hand pairs from `requirements.json`; every emitted pair and the whole-title widths at every master equal the exporter's, and the font carries no GPOS pair the exporter did not emit; at least one pair that is neither a hand pair (by `font.json`'s own lists: a classification, not an expected value) nor a word-space pair exists with a non-zero value, so a `kern()` that returned 0 everywhere cannot agree with itself; the word space at every master equals the value **pinned** in `requirements.json` `word_space`, and the exporter's own figure must equal it too (so the exporter is never its own expectation); the `interpolated_check` location within a unit of the mix | zero the display masters' kerns; drop `2 × track` from the word space in `export.js` (red against the pinned value); edit the pinned value by one unit; add `pos zero one -40` in `build.py` (`kern-extra`); make `export.js` compute 0 for every automatic pair (`kern-auto-zero`) | five mutations, one test; the automatic VALUES stay unpinned (section 2, the shared-defect limit) |
| hairlines clear the floor (F009, C7) | manifest ≥ floor, exporter ≥ floor, manifest equals exporter, and the builder's own figure recomputed from the polygons (`min_stroke_width_recomputed`) ≥ floor and within 0.15 of the exporter's, per master; `gasp` is `{65535: 15}` | lower the manifest's figure to 40; lower the recomputed figure to 40; drop the `gasp` table; raise a floor above the stroke (the build must refuse, with the floor in its message) | the floors are fixed in `requirements.json` |
| the `--masters` path refuses doctored parameters (re-review code-a F002) | `build.py --masters` with a JSON whose `W` is tripled exits 1 naming the master, `W` and the value `gen.js params()` gives (the recomputation's interior reach follows `W`, so an overstated `W` could hide a thin end region; the parameters are read back from `gen.js` through node and the JSON must equal them) | the parameter comparison replaced by `check(True, ...)` (`C7-params`) | needs node on the `--masters` path too |
| the `--masters` path refuses a polygon record missing (re-review code-a F003) | a JSON whose `keptIdx` list is one record short in every master (so the cross-master comparison agrees) exits 1 naming the glyph and the four lengths; every zip over the per-polygon lists is strict | the length check replaced by `check(True, ...)` AND the three `strict=True` dropped (`zip-lengths`; with the check alone removed a strict zip raises and the test fails on its message, survivor shape 1) | — |
| no edge folds back | the exporter's `foldedEdges` is 0 and both excursion maxima are under the thresholds, per master | — (see the fixture test) | this test trusts the exporter's verdict (re-review F004), which is why the next exists |
| the fold detector sees first-segment and decimated folds | hand-built edges fed to `backwardExcursion`: clean reads 0/0; a fold in the first segment reads > 4 raw; a fold present only in the decimated edge reads 0 raw and > 10 decimated | the fixture **is** the mutation: the first guard skipped the first segment and measured raw only | independent of the generator |
| under budget | woff2 ≤ `size_budget_bytes` | build with `--eps 0` with the budget lifted (Bract: 185,580 bytes) | — |
| no glyph exceeds the win metrics (F012) | every glyph of every master inside win ascent/descent (the assertion that hhea equals win is gone: hhea now equals typo) | return the precedent's constants (940/300): `À` at 947 failed | — |
| the line height is the reviewed one | hhea and OS/2 typo ascender, descender and line gap each equal `groups.*.vertical_metrics` in `requirements.json`, the static instances too | `vm-hhea-gap`: hhea gap 200; `vm-typo`: typo descender one unit short; `vm-override`: a `typo_metrics` override in `font.json` the requirements do not hold | each needs the build's two metric self-checks cut, or they refuse the build first (shape 1); USE_TYPO_METRICS is held by the style test, mutation `use-typo` |
| `fsType` is the operator's decision | `OS/2.fsType` equals `names.fs_type` in the requirements; statics too | `fstype-code`: build.py forces another value; `fstype-config`: `font.json` says another | the config mutation is the F002 shape: the build agrees with its config, the requirements do not |
| STAT names every named instance | per axis, format-1 values for every instance coordinate plus the default, standard weight names, the default (and only it) elidable, the elided fallback the style; no STAT in a static | `stat-none`, `stat-missing` (the last value of each axis left out), `stat-name` (700 named Heavy), `stat-elide`, `stat-fallback` (always Regular; italic only), `static-stat` | the expected set is derived from the requirements' axes and instances, with the weight names restated in the test |
| smart dropout `prep` beside `gasp` | `prep`'s bytes equal `tables.prep_hex`; `maxp.maxStackElements` ≥ 1 | `prep-missing`; `prep-bytes` (SCANTYPE operand 4 → 5, which the build's own check accepts because it compares with its own constant); `prep-maxp` | that a renderer honours it is not testable from a Mac |
| code page and name platforms | `ulCodePageRange1` equals `tables.code_page_range1`; Macintosh records present only if `tables.mac_names` | `codepage` (bit 0 → bit 1), `mac-names` (`mac=False` dropped), `static-mac` | `gasp` is held by the hairline test, whose mutation also cuts the build's new gasp check |
| glyphs declare overlaps | `OVERLAP_SIMPLE` on every contoured glyph | clear the flag, disable the flag check **and** lift the raster budgets | survivor shape 1, section 4 |
| manifest matches the shipped bytes and sources | sha256 of the woff2 and of `gen.js`, `export.js`, `build.py` equal the manifest | edit a comment in `gen.js` | the commit-together guard |
| name table | family, copyright, manufacturer, vendor id and URL, licence from `requirements.json` | rename the family | — |
| build is reproducible | `build.py --check` exits 0 under a foreign `SOURCE_DATE_EPOCH` in the environment, with `sys.executable` | `Math.random()` added to an advance in `export.js` | the foreign epoch is re-review F005 |
| `dropAmt` changes outlines; `flareAmt` + `tear` throws | export twice with two `dropAmt` values: polygons differ in the teardrop glyphs; `params()` throws on the bad concept | revert the throw | new in this skill |
| `dropAmt` scales the outer, inner and symmetric teardrop (`test_dropamt_scales_the_outer_inner_and_symmetric_teardrop`) | finds a stroke with an L, an R and an S teardrop from the branch records; at a sample inside the zone (re-aligned for the sidebearing shift, clear of the fold pin) the outer edge swells and the inner thins in the ratio 55/28, the S case moves both edges equally, and every displacement doubles from 0.55 to 1.1 | `dropamt-inner` (dk dropped from the inner thinning only) and `dropamt-s` (dk dropped from the symmetric case only). Both survived the "changes outlines" test above during the review of this repo, which is why this test exists: a knob that moves *something* is not a knob that works |
| italic group (when wired) | the same compatibility, floors, F013 and instancing checks over the second file; `post.italicAngle`, the `fsSelection` italic bit, `macStyle`; a slanted tick | build the italic from the roman JSON | pipeline-tested only; no shipped font has gone through it |

## 3. Choosing the weakest mutation

The obvious mutation is the inverse of the fix you just made, and it is caught by construction:
it proves the fix is present, not that the property holds. Ask instead: **what is the weakest
change that would make this assertion false, and is that change the defect the test is named
for?** Two Bract examples of the difference:

- The kerning test could have asserted "named pairs negative and ≥ −200 at opsz 80". A font with
  static Regular kerning and no GPOS deltas passes that (plan F010). The weakest defeating change
  is "the display masters' kerns are zero", so the test compares every emitted pair and whole-title
  widths with the exporter's per master.
- The `gvar` test could have asserted "an entry exists". A glyph that varies on one axis only
  passes that (plan F013). The weakest defeating change is "one master built from another's
  outlines", so the test instances each master's location and compares outlines.

A test that builds its expected value from the code under test cannot fail when the code drops a
field. The suite therefore recomputes: the quote glyphs are re-derived in the test, the fold
fixture bypasses the generator, and the floors live in `requirements.json`.

## 4. The three survivor shapes, verbatim from Bract

From the mutation log of 2026-11-15 (28 mutations, 2 problems on the first run):

**Shape 1 — the mutation is blocked by an earlier self-check.**
`overlap: flag not set, self-check off` stayed GREEN: the build exited 1 with
`self-check failed: TextRegular@16px: overlap rendering of B differs from its union by 120 levels`.
The raster check refused the mutated font before the flag test could see it, so the shipped font
was still the pristine one. The fix was a third edit: lift `RASTER_BUDGET` to 255 for the run.
Then the test went red: `glyphs without OVERLAP_SIMPLE: ['.notdef', 'zero', ...]`. Lesson: when a
mutation needs a rebuild, check the build actually wrote the mutated font.

**Shape 2 — another mapping masks the mutation.**
`i: U+0027 mapped to the straight tick` stayed GREEN after one edit. Mapping 0x27 to `quotesingle`
was overridden by the builder's own cmap check (`cmap[0x27] == cmap[0x2019] == "quoteright"`),
which refused the build; disabling that check still left the "quotesingle unmapped" self-check.
Three edits were needed (the mapping, the two self-checks) before the test could observe the
defect. Lesson: a self-check and a test guarding the same property mean either can be deleted
unnoticed, because the other refuses first; mutate until the test itself is what fails.

**Shape 3 — the property is one no input exercises.**
The branch record's partner identity (diff review F005) could not be mutated through geometry:
no stroke end in the glyph set has two partners within 2 units, so "switch to another nearby
partner" had nothing to switch to. The mutation was applied to the **recording** instead (the
identity the record carries), so the exporter could be shown to stop telling apart two masters
that pair a point differently. Lesson: when the input space cannot reach the defect, mutate the
mechanism that would record it, and say so in the log.

Record survivors as findings, in the commit message or the record, not as chores: a fix that
survives its own mutation is evidence about how the change was made.

## 5. Running scripts/tests/mutate.py

```
.venv/bin/python3 scripts/tests/mutate.py --font font.json --requirements requirements.json --static-dir none   # every mutation; no statics ship
.venv/bin/python3 scripts/tests/mutate.py --font font.json --requirements requirements.json --static-dir out/static   # when statics were built
.venv/bin/python3 scripts/tests/mutate.py --font font.json --requirements requirements.json --static-dir none --list   # name each mutation and its target tests, run nothing
.venv/bin/python3 scripts/tests/mutate.py --font font.json --requirements requirements.json --static-dir none --only overlap --only apostrophe
```

`.venv/bin/python3` is the skill venv's interpreter, run from the skill folder (`SKILL.md`, "Finding the skill folder"). The flags are exactly these three
beside `--font` and `--requirements`: `--only NAME` runs the mutations whose name contains NAME and
repeats; `--list`; `--static-dir DIR`, or `--static-dir none` when no statics ship, the same word
`conftest.py` takes, which SKIPS the static mutations (eight of them: overlap, weight, missing, and since 2026-11-16 mac, metrics, fstype, stat and designer) with the reason printed. Without the
flag the default is `<out_dir>/static`, and a missing folder refuses the run naming both ways out;
the first harness read `none` as a path, built statics into the served font folder during the
static-overlap mutation and died in a `FileNotFoundError` (second dry run, finding 1). There is no
`--all`: running everything is the default.

**Every expected text is derived from the project's own files** (second dry run, finding 2): the
`required-F002` mutation expects `lacks [<the digits the project's required_characters hold>]`, the
floor mutations expect the project's first-master floor less one, the names mutation the project's
family. A mutation the project cannot exercise is `SKIPPED` with its reason, counted apart from the
problems and never silently GREEN: no digit in `required_characters`, no `opsz` axis, no `avar`
map or no intermediate point in it, no hand kern pair, `ascii_apostrophe_curly` false, NBSP or
U+2018 absent from the reviewed cmap, no statics. Two mutations stay design-dependent and say so in
their comments: `floor-F002b` cuts every concept's `thin` to 0.8 of itself, which takes the
hairline under the reviewed floor only when the design has less than a fifth of margin above it, and
`budget` relies on an undecimated build exceeding the budget.

Each mutation is a named entry: the test ids it should turn red, an `apply()` of exact-string
replacements, whether a rebuild is needed and with what extra arguments, and the proof text:
`expect=` (one or more strings that must appear in the failing assertions' output) or
`build_refused=` (the text a refusing build must print). The harness copies every file it will
touch to a pristine directory first, applies the mutation, rebuilds if asked, runs the named
tests, restores every file by `copyfile`, confirms every digest is back, and reruns the tests green.

**What RED means** (review finding C8; the first harness called any non-zero pytest exit RED, ran
the tests even when the rebuild had failed, and never looked at which assertion fired). A mutation
is RED only when all of these hold: every replacement applied exactly as many times as declared;
a rebuild exited 0 and left at least one artefact (a woff2, the manifest, a static) different from
its pristine copy, or, for a `build_refused` mutation, failed with the declared text and changed
nothing; pytest reported every named test FAILED (not ERROR, not a collection error), no test
ERRORed, and every `expect` text appears in the `E` lines of the failure section OF THE TEST IT
BELONGS TO (`expect` is one text or a list, held against every named test, or a dict naming each
test's own text; the first stricter harness searched one combined string, so two tests could
satisfy each other's text: re-review code-a F008, with `tests/test_mutate_harness.py` on the pure
judgement). A project with no roman group takes its first group as the primary one, and one with a
single named instance gets `static-missing` on that instance (re-review code-a F006). Anything else is
**UNPROVEN**, with the reason (the rebuild failed, so the tests would have seen the pristine
files; the tests failed on another assertion; a test ERRORed), and a mutation whose tests pass is
**GREEN**. Both are findings about the test or the mutation, and both make the run exit non-zero.
The log line per mutation is
`VERDICT | name | detail | build note | restored=... green again=... | seconds` (a skipped one is
`SKIPPED | name | reason | nothing applied, nothing run`), and the run ends with
`N mutations, M RED, S skipped, K problem(s)` naming each skip and each problem and why.

Re-run under the stricter harness, the neutral example's set gave 44 RED of 44, 0 problems
(`scripts/smoke.sh --full` step 5, 2026-11-16, this machine). Two mutations that the first harness had counted RED were UNPROVEN under it and were
rewritten: the NBSP mutation (blocked by `export.js`'s required-character check once `build.py`
passed it `--requirements`, survivor shape 1 of section 4) and the inner-teardrop mutation, whose
first `expect` named the linearity assertion when the one that fires is "must thin". After the
independent re-review of 2026-11-16 the set is 48 (`kern-extra`, `kern-auto-zero`, `C7-params`,
`zip-lengths` added) and the `F013` mutation shifts the last master's outlines by 3 units instead
of building it from the first master's: on a two-master group the first form made every glyph
identical, the builder's own gvar self-check refused the build, and the harness reported UNPROVEN
(re-review code-a F007; reproduced on a two-master copy of the neutral roman, RED after the change).
The full set re-run after these changes gave 48 RED of 48, 0 problems, 0 skipped (`scripts/smoke.sh --full`
step 5, 2026-11-16, this machine).
The font-table work of the research reviews (`fsType`, line metrics, STAT, `prep`, code page, Macintosh names) added 20
mutations and reworked the `gasp` one (68 RED of 68); the fix rounds added `designer-code` and `designer-config` and made
`static-weight` force a class no static has: 70 RED of 70 (the last round added `static-designer` and the three `stat-*-refused` mutations that prove the STAT name self-check refuses: 74 RED of 74), 0 problems, 0 skipped (`scripts/smoke.sh --full` step 5,
2026-11-16, this machine). With `--static-dir none` the eight static mutations are SKIPPED.

## 6. The site-wiring template

`scripts/tests/test_site_wiring.py.tmpl` carries the tests that live in the **site** repo, with
`{{ }}` slots for the stylesheet path, the templates glob, the preload tag, the font URLs (an italic
URL left empty when no italic group is built), the display, text-cut and Medium selectors, the opsz maximum,
the old face's name and files (both left empty when the old face stays in use elsewhere or shipped
no files, which skips c and d with the reason printed), the static-serving config (left empty when
the host serves every file type, which skips f; the stylesheet is refused by name, because its
`url()` says woff2 whatever the host serves) and `font_synthesis` (`adopted` runs r, `declined`
skips it with the reason; anything else fails r naming the two words), `fallback_family` (guard t; empty skips) and `balance_selectors` (guard u; `[]` skips). Guard e skips, saying so,
outside a git work tree (second dry run, finding 9).

**Which selectors go in `display_selectors`** (second dry run, finding 16): every selector set in
the display cut, at or above the `opsz` start, whose advances carry the display concept's `track`;
guard p forbids `letter-spacing` on those because it doubles the track (F005). A selector set in
the face below the `opsz` start, in the text cut, is not a display selector: the text concept's
`track` is 0 in every example here (`concepts.js`), so a tracked caps wordmark at 22 px keeps its
`letter-spacing` and goes in `text_cut_selectors` instead. Guard s (re-review code-b F008) requires
every selector whose stylesheet rule sets the family to be in one of the two lists and the display
list to be non-empty, so a display rule added later cannot stay outside p and r unnoticed; guard g
covers it all the same, because g reads every rule that sets the family from the stylesheet, not
the slot.

How it reads the stylesheet (dry-run finding W12): comments stripped, every `selector-list {
declarations }` block collected, blocks nested in `@media` or `@supports` included; a rule written
for a selector list (`h3, .plate-title { … }`) counts for each selector; the family name is read
with single quotes, double quotes or none; a size is a `clamp()` (its third argument), a `rem`, a
`px` or an `em` value. Limits, stated in the file: declarations are read as `property: value`
pairs, so the `font` shorthand is not expanded; an `em` size is taken at the 16 px root; a `vw`-only
size is refused by name; display selectors are tags, classes, `tag.class` compounds and descendant
chains of those (`>` read as a descendant), anything else raises rather than guesses.

| Plan letter | Asserts | Mutation |
|---|---|---|
| a | one `@font-face` per style (normal; italic when the slot is set) with the weight RANGE the fvar axis spans, `font-display: swap`, the slot's src | `400 700` → `400`; the italic face not expected while the stylesheet declares one |
| a2 | the file behind each declared face carries that style's tables: the italic src has `post.italicAngle`, the fsSelection ITALIC bit and `macStyle` italic set, the roman's has them clear (re-review code-b F009: a roman file named as the italic src passed a and b) | the italic src pointed at the roman woff2 (red); the three `== italic` comparisons replaced by `or True` (green: the defect) |
| b | every font `url()` in the stylesheet has a file under the web root | rename the woff2 |
| c | nothing names the old face: stylesheet, templates, built pages (skipped when the slot is empty) | add it to one stack; an empty slot compiled as a match-all regex instead of a skip |
| d | the old face's files are gone (skipped when the slot is empty) | copy one back |
| e | woff2 on disk equals `git ls-files`; skipped with the reason outside a git work tree | an untracked woff2 beside the font; the work-tree check removed (an error outside a repository) |
| f | the static config serves the extension; skipped with the reason when the slot is empty; the stylesheet refused as the config | drop `woff2` from the allowlist; the empty-slot skip removed (an error, not a skip); the stylesheet comparison removed (a vacuous pass) |
| g | every character the built pages set in the display face (the rules read from the stylesheet, not the slot) is in the cmap, naming the first page | `h2` set in the face on the fixture site, whose H2s carry `Å` and `Ž` (red, naming both); reading the slot instead of the stylesheet (green: the defect) |
| s | every selector whose stylesheet rule sets the family is in `display_selectors` or `text_cut_selectors`, the display list is not empty, no selector is in both, and nothing listed is unset (re-review code-b F008) | `h2` set in the face and listed nowhere (red, naming h2); `unlisted` built from the slot instead of the stylesheet (green: the defect) |
| n | the largest size any display selector can reach, across all its rules (a nested `@media` rule included), equals the opsz axis maximum and the slot | frontispiece max `6rem`; `clamp()` read only; the `@media` walk flattened |
| o | every `font-weight` declared for a Medium selector is 500 | remove one; a narrow-width override to 400 |
| p | no `letter-spacing` in any rule for a display selector | re-add `-.01em` |
| q | the preload link, with `crossorigin`, in every template and built page, before the stylesheet | change the href |
| t | optional (holds the declaration's vertical overrides and stack, NOT `size-adjust` against the real fallback widths): the fallback `@font-face` is one `local()` face with `size-adjust` and the three overrides, its overrides times its `size-adjust` equal the font's hhea ascent, descent and line gap within 0.5 points of the em, and every display stack starts with the family and then the fallback | a `url()` src; no `size-adjust`; one override off by 5 to 100 %; the `x size-adjust` factor dropped; the fallback after `serif` in the stack (the `in` mutation of the stack check survived until that case existed); the tolerance widened to 50 |
| u | optional (declarations on the listed selectors only; the cascade is not computed): every `text-wrap` value declared for each listed selector is `balance` | one selector without it; `text-wrap: wrap` in a media rule after it (`any` instead of `all` survives the first case only) |
| r | `font-synthesis: none` declared for every display selector, in its own rule or a shared one: a **recommendation**, not used by Bract; the `font_synthesis` slot says `adopted` or `declined` (declined skips with the reason) | reading a selector's first rule only (the shared rule is then missed); the declined skip removed |

Named instances: `test_the_stylesheet_declares_one_variable_face_per_style`,
`test_each_declared_face_file_carries_the_style_it_is_declared_for`,
`test_every_selector_set_in_the_face_is_listed_as_display_or_text_cut`,
`test_every_font_url_in_the_stylesheet_has_a_file`, `test_nothing_names_the_old_face_any_more`,
`test_the_old_font_files_are_gone`, `test_shipped_fonts_are_tracked`,
`test_the_static_config_serves_the_font_extension`,
`test_the_font_covers_every_character_the_display_face_sets`,
`test_fluid_sizes_stay_inside_the_opsz_axis`, `test_small_titles_and_numerals_are_medium`,
`test_display_rules_carry_no_letter_spacing`, `test_every_template_preloads_the_font`,
`test_display_rules_forbid_synthesised_styles`, `test_the_fallback_face_is_metric_matched_to_the_font`,
`test_display_headings_balance_their_lines`. The skill repo's
`tests/test_site_wiring_template.py` fills the template for `tests/fixtures/site-sample` in three
CSS styles (single quotes, one selector per rule, `clamp()`, an old face named, `font_synthesis`
declined; double quotes, a selector list, a plain `rem` size inside `@media`, `font-synthesis` in a
shared rule, adopted, no old face; the static config empty, synthesis declined and no git, each
skipping with its reason) and runs the filled suite there exactly as a site would (no marker to
register, unknown-mark warnings turned into errors), then points the static-config slot at the
stylesheet and requires guard f alone to fail naming it, and adds the H2 rule and requires guard g
to fail naming `Å` and `Ž`. The mutations in the table's last column were applied to the template
and watched turn that test red (2026-11-16, both dry runs).

## 7. Harness rules

- **Pristine copies by `copyfile`, never `rm`.** The operator's machine deny-lists `rm`; a restore
  overwrites. A file a mutation created in an output directory (a renamed static, a font under a
  renamed family) is deleted on restore, and a file it renamed away comes back from its pristine copy.
- **Exact-string replacements asserted to match once.** `rep(path, old, new)` asserts
  `s.count(old) == 1` before writing, so a mutation that no longer matches fails loudly instead
  of silently mutating nothing (the BSD `sed -i` no-op is how a hop-safari guard once looked
  verified when it had never run).
- **Clear `__pycache__` between runs.** A same-length identifier swap leaves the file size
  unchanged and Python reuses the cached bytecode, so a restore "does not take".
- **Log RED, GREEN or UNPROVEN per mutation, restore, and re-green before the next.** A survivor
  is a problem line at the end, not an exception mid-run.
- **No test writes outside the repo.** Anything that would (a backup log, a Keychain) is redirected
  to `tmp_path` by an autouse fixture.
- **A mutation that needs the exporter** rebuilds without `--masters`, so a fresh export runs.
- Keep the run's log; the record quotes the count and names the survivors.
- **Copy `scripts/` into a site only after `smoke.sh` has finished.** The mutation step edits
  `gen.js`, `export.js` and `build.py` in place and restores them by digest; a copy taken mid-run
  carries a mutated file, which the manifest's source hashes catch later and nothing catches at
  copy time. `diff -r <skill dir>/scripts tools/<face>/scripts` after the copy must print nothing
  (second dry run, finding 14), except for a project whose copy was made early to carry a glyph: the recorded
  `gen.js` patch and `extra-glyphs.js` only.

## 8. The repository's own guards for the added tools, and the survivors they showed

Added 2026-11-16 after two research reviews; each file names the mutation that turned each guard red.

| File | Guards | Executes |
|---|---|---|
| `tests/test_check_env.py` | `check-env.py` names each missing piece with its fix command and exits 1 (node missing, node 18, bash missing, a `$CHROME` naming no file, Python 3.9, each package missing); `build.py` refuses Python 3.9 and a missing fontTools naming the venv command; every script that needs 3.10 carries the guard | the real files, with a PATH holding fake `node` and `bash`, with `sys.version_info` set and `sys.modules[name] = None` by a wrapper (nothing edited); the last test reads the AST, and says why |
| `tests/test_fontbakery_gate.py` | `judge()` on crafted reports (FAIL, ERROR, FATAL block; WARN does not; whole-id match; stale entries; unfinished report); `load_accepted()` refusing a missing or malformed list; the script against a stub `fontbakery` (exit 1 naming the finding, exit 0 with the reason, `--profile`, exit 3 when not installed); the build path hands FontBakery a real variable TTF; the real FontBakery on the neutral roman, passing with its one accepted finding and failing with none accepted | the script, a stub command, and (skipped loudly when not installed) the real FontBakery |
| `tests/test_fallback_metrics.py` | `size-adjust` and the overrides against arithmetic done in the test from fontTools; `--location` moves them; a character the fallback lacks does not tilt the ratio | the script on the built neutral font and a fallback font made in the test |
| `tests/test_shoot.py`, `find_chrome` and specimen tests | the order `$CHROME`, the macOS app, Program Files, Program Files (x86), LocalAppData, PATH names; the specimen's spacing and legibility rows, built only from characters the font maps | `find_chrome()` on real files and a real PATH; `specimen.py` on the neutral font and on fonts made in the test |
| `tests/test_site_wiring_template.py`, style D | guards t and u pass on a correct declaration and fail, alone, on each defect | the filled template, run as a site would |

Survivors and blocked mutations these guards showed while they were written (the finding is about the
test or the mutation each time, as `mutate.py` reports):

- `mac-names` was GREEN: `removeNames(platformID=1)` in the builder was dead code, because
  `setupNameTable(mac=False)` and `buildStatTable(macNames=False)` already write no Macintosh records.
  The line was deleted; the mutation now drops `mac=False`, the real source.
- `gasp` became UNPROVEN when the new gasp self-check refused the build first (survivor shape 1): the
  mutation cuts that check too. `stat-none` and `stat-missing` were UNPROVEN on their first form, which
  deleted the first half of a line and left a syntax error; the harness has a `cut()` helper for "switch
  this self-check off" now.
- Guard t's stack check survived `in` instead of "the first two entries" until a test put the fallback
  after `serif`. The FontBakery gate's first WARN mutation (WARN added to the blocking set) was equivalent, because
  the WARN branch comes first; the mutation removes the branch instead.
- Stale bytecode, once more: a mutation that swaps two same-length strings in a module another test
  imports through `importlib` leaves a `.pyc` with the same size and a same-second mtime, and the
  restored file is not what runs. Clear `scripts/__pycache__` after every mutation of an imported file.
