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
`test_optical_corrections_change_only_the_strokes_they_name`, `test_the_optical_knobs_refuse_values_outside_their_ranges`,
`test_xh_moves_the_lowercase_lines_and_leaves_the_capitals`, `test_xh_does_not_change_any_branch_record`, `test_xh_sets_the_spacing_band`,
`test_xh_outside_its_range_is_refused`, `test_an_unbracketed_serif_is_a_slab_with_the_bracketed_point_count`, `test_serifbracket_outside_zero_to_one_is_refused`, `test_joints_opt_in_cuts_a_sans_joint_level`,
`test_crotch_thins_only_the_inner_edge_of_an_acute_joint`, `test_apex_is_refused_until_built`,
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
| optical corrections change only the strokes they name (`test_optical_corrections_change_only_the_strokes_they_name`) | monoline, nib 0, butt ends (so every width is `W` times the optical factor), one knob per variant then all three, at mult 1 and 1.5: a plumb `l` stays `W` in every variant; the level `-` is `0.9 W` under `hzThin 0.9` and `W` otherwise; the `o` ring is `1.05 W` thick at its right extreme under `roundGain 1.05`; EVERY sample of the `c` is `W (1 + 0.05 cw)` with `cw` recomputed in the test from the output centre line (turning angle over mean chord × 2.5 `W0`, capped at 1), once fitted and once with `overshoot` 0 where the cap is reached; the `x` stroke is `W (1 − 0.06 sin²2θ)` under `diagThin`, and under all three the full product, with θ read from the output; the `o` spans -10 to 510 whatever the knobs do; the `z` bar's top edge is 500 and the `E` stem ends flush with its bar under `hzThin` and under all three; explicit 1s draw every glyph exactly as no keys | `optical-hz-all`, `optical-round-straight`, `optical-round-open-off`, `optical-round-uncapped`, `optical-diag-flat`, `optical-fit`, `optical-corner`, `optical-corner-round`, `optical-fit-round`, `optical-radius`, `optical-ring-off`, `optical-flag-omits-round`, `optical-overshoot-round` (13) | one variant per knob, because the first draft of the plan expected a diagonal from `diagThin` alone while `hzThin` also applied at that angle (review F007). The plan placed the `c` check at its leftmost sample "radius ≈ 210 < 250"; measured here the fitted `c` never curves tighter than radius ~420 (weight ~0.6), so the test compares every sample with the weight the formula gives and keeps an unfitted variant to observe the cap |
| the optical knobs refuse values outside their ranges (`test_the_optical_knobs_refuse_values_outside_their_ranges`) | `params()` throws, naming the knob, for each of `hzThin`, `diagThin`, `roundGain` given null, a string, NaN, a boolean, a value just below, just above, far outside or either bound (the intervals are open), and accepts a value just inside each bound, the middle and 1; the case list is written in the test, not read from the fixture | `optical-range-removed`, `optical-null-accepted` | the first version built its bad cases from its own fixture and never sent `diagThin: null` or `roundGain: null` (Impasse review, G6) |
| open curve extremes stay within the documented bound (`test_open_curve_extremes_stay_within_the_documented_bound_of_the_overshoot`) | the `c`, `e` and `s` tops shift from the same drawing without `roundGain` by at most `(W/2) hzThin |roundGain − 1|` at `roundGain` 1.05, 0.85 and 1.05 with `hzThin` 1.4 (the last exceeds the bound without `hzThin`), and not all by zero | `optical-fit-overcorrect` | the ring is exact and the open curve is not (G3); the bound is documented in generator.md section 4 |
| no decision reads a mapped coordinate (`test_no_decision_reads_a_mapped_coordinate`) | 500 synthetic glyphs with a fixed seed, placed on the decisions' thresholds (level to 0.2 degrees, 30 degrees, 5.7 degrees off plumb, curved, a second stroke 1-3 units from the first's end), in five concepts (serif, beak with flare, curl, teardrop, sans with `joints`), roman and slanted: every record at `xh` 400 and 600 equals the one at 500 (10,000 comparisons), and each decision was reached a minimum number of times | `xh-beak-mapped`, `xh-partner-mapped` | the project's own glyphs sit far from every threshold: both mutations were GREEN against `test_xh_does_not_change_any_branch_record` (G1, G2) |
| `xh` moves the lowercase lines and leaves the capitals (`test_xh_moves_the_lowercase_lines_and_leaves_the_capitals`) | at `xh` 600 and 400, mult 1 and 1.5, every end a butt: the `o` spans -10 to `xh` + 10 (within 1.6, and its top moves by exactly `xh` - 500 from the xh 500 drawing); a butt `n` stem ends at `xh`; the `z` bar's top edge is at `xh`; the `-` is centred at 260 `xh` / 500; the `d` stem ends at 740 and its bowl tops out at `xh` + 10; `H`, `O`, `0`, `l` and the apostrophe do not move; the colon's dots are centred at `r` - 4 and `xh` - `r` + 4; the `i` dot is at the restated map of 680; no glyph gains a polygon or a point | `xh-round-literal`, `xh-flat-literal`, `xh-caps-too`, `xh-apostrophe-mapped`, `xh-band-unmapped`, `xh-dot-mapped` | the plan's absolute tolerance of 0.6 on the `o` fails on unmodified code (the Bold's `o` top reads 511.15 at `xh` 500: the offset of a stroke whose width varies with direction), so the absolute bound is 1.6 and the exact check is the shift from the `xh` 500 drawing |
| `xh` does not change any branch record (`test_xh_does_not_change_any_branch_record`) | every key of every master of the project's groups (italic as exported), and a variant of each master with every end but the serif a curl, at `xh` 500, 400 and 600: each glyph's branch record is the `xh` 500 record (more than 1,000 comparisons required) | `xh-branch-mapped`, `xh-curl-mapped` | no shipped face uses a curl end, so without the second variant a mutation of the curl decision survived (found when the mutation was tried by hand) |
| `xh` sets the spacing band (`test_xh_sets_the_spacing_band`) | the `o`'s left sidebearing at `xh` 500 and 600 equals the documented formula recomputed from the output polygons (band `[0, xh)`, 20-unit bins from -260, depth capped at 0.2 `xh`); the band of 500 and of 600 differ by more than 1 unit (5.2 measured); the `a|v` kern at `xh` 600 equals the restated kern rule (sparse cap, clearance, clamps) and differs by more than 1 from the same rule over a band of 500 (-49.05 against -63.12) | `xh-band-500`, `xh-kern-band-500` | the plan's `o|o` kern is 0 in both bands (its gap is the reference gap), so the kern half uses `a|v`; 305 of the 676 lowercase pairs shift by more than 1 |
| `xh` outside 400-600 is refused (`test_xh_outside_its_range_is_refused`) | `params()` names `xh` for 399, 601, a string and null; 400 and 600 pass | `xh-range-removed` | — |
| an unbracketed serif is a slab with the bracketed point count (`test_an_unbracketed_serif_is_a_slab_with_the_bracketed_point_count`) | `I` foot and head (26 points), `n` lowercase head (15) and feet, `v` diagonal serif (26), mult 1 and 1.5, `serifBracket` 0, 0.5, 1 and unset: at 0 every point lies between the line and one serif height (`h` = `W0` (`W` / `W0`)^`serifGrow` x `serifH`, restated) and both are reached; at 1 the extreme is 1.7 `h` (1.9 for the lowercase head); at 0.5 strictly between; the count is unchanged; 1 is the unset polygon exactly | `bracket-ignored`, `bracket-count`, `bracket-diag` | the plan said every slab point is on one of two lines; the slab's vertical sides are straight segments sampled by `quad()`, so their points lie between the lines |
| `serifBracket` outside 0-1 is refused (`test_serifbracket_outside_zero_to_one_is_refused`) | `params()` names `serifBracket` for -0.01, 1.01, a string and null; 0 and 1 pass | `bracket-range-removed` | — |
| `joints` opt-in cuts a sans joint level (`test_joints_opt_in_cuts_a_sans_joint_level`) | the project's first concept, every end a butt, and again with the shipped mapping of the empty end to a disk (no 64-point disk is drawn at a joint: V W M N v w have none, the A keeps the two on its crossbar), with and without `joints: true`, mult 1 and 1.5: with it both edge points of the `V`'s joint end lie on the baseline and the record reads `/joint`, and the `L`'s stem reaches its base's outer edge; without it the two edge points differ in y by the width times the tangent's x component (restated from the output) and the stem stops short | `joints-ignored`, `joints-keep-disk` | the jointed `V` reads y of 17.25 and -17.25 under the mutation |
| `crotch` thins only the inner edge of an acute joint (`test_crotch_thins_only_the_inner_edge_of_an_acute_joint`) | at the first unpinned sample at least eight steps in on the `V`'s and the `A`'s arms (the partner side found from the partner's OUTPUT): that edge moved inward by 0.3 e w/2 with e restated from the arc distance read off the output (within 2 %); the other edge did not move (under 1e-6); `l`, `n`, `E F L T H` and the right-angled joints of `š ê Ô` are identical at crotch 0 and 0.3; `V` and `A` keep their hairline minimum; crotch 0 draws every glyph as no key; the glyphs whose record names an acute joint are exactly `1 4 5 v w A M N V W ™ Á À Â Ä Ñ` | `crotch-both-edges`, `crotch-everywhere`, `crotch-corners`, `crotch-corner-as-joint`, `crotch-obtuse`, `crotch-floor` | the Bold pins the first samples before a tight joint, so the sample is chosen by scanning (the plan's "eight steps" fails there) |
| `apex` is refused until built (`test_apex_is_refused_until_built`) | `params()` throws naming `apex` and `generator.md`; `joints` must be a boolean; `crotch` a number from 0 to 0.6 (bounds allowed) | `apex-accepted` | — |
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

Added 2026-11-16 with the optical corrections (0.2 item 3); the findings are about the tests and the plan:

- **The byte-identity guard is `tests/test_backward_compat.py`**, not a font-suite test, because it needs
  the 0.1.0 digests in `tests/fixtures/baseline-0.1.0.json`. Watched red twice: `export.js`'s
  `adv: Math.round(g.adv)` made `+ 1` (the export and TTF digests move on all five groups), and
  `gen.js`'s default `P.hzThin` made 0.999 (`compat-default`, applied by hand: the test failed, naming
  the groups, all three digests on every group). The manifest digest moved under the 0.999 default and
  did not move under the advance mutation, so the advance mutation alone does not prove it.
- **First version of the manifest digest was not reproducible**: a build with `--out-dir` records the
  group's absolute output path in `file`, so two runs differed. `manifest_digest()` now cuts `file` to
  its name. Found because the test failed on unmodified 0.1.0 code, the first run it was given.
- **A plan figure was wrong and the mutation list could not see it.** The plan put the `roundGain`
  check at the `c`'s leftmost sample ("radius ≈ 210 < 250, weight 1"). Measured: that sample has radius
  322 unfitted and about 420 after the fit, so its weight is 0.6 at most. A test written to the plan
  would have failed on unmodified correct code. The test compares every sample of the `c` with the
  restated formula instead, and a second variant without the fit is there to reach the cap.
- **`optical-corner-round` and `optical-fit-round` survived the plan's six assertions.** A corner or a fit
  that wrongly gives its straight bar the round gain moves the line by 2.25 units, and the plan's
  assertions f and g measured `hzThin` alone, where the gain is 1. They now also run under all three
  knobs. Two more mutations the plan did not name (`optical-radius`, `optical-ring-off`) and one for the
  dead-knob shape (`optical-flag-omits-round`) were written after the first run and are RED.
- **Round tops and `roundGain` (operator decision 2026-11-16).** The plan's `hwFlat` (weight 0) made a round
  top overshoot by `overshoot + hw·(roundGain − 1)`: the `o` top measured 512.5 for `overshoot` 10. The fit
  now gives round extremes the half width of a fully weighted curve, and the test asserts the `o` spans
  -10 to 510 in every variant. `optical-overshoot-round` (the old half width) was watched red on that
  assertion (-12.50 to 512.50).
- **Digests differ by node major and by platform.** (Section 8's Linux note below supersedes the node-only keying.) Recorded from a clone at 0fc4314 on macOS under node 20, 22 and 26: node 20 and
  22 give identical digests; node 26 differs in the export and TTF digests of 4 of 5 groups and in the
  manifest digest of all 5 (V8 arithmetic, not a regression). The test accepts only a recorded major.

Added with the diff tool and the specimen junction row (agent B, 2026-11-16):

- `tests/test_diff.py` has 7 tests (the 5 planned, one for a missing group file named in the error, one for the
  install command on the wrong interpreter). 13 by-hand mutations, all red: before font at px+1; after = before;
  layout BASIC (the kerning test); first instance only; `with_fpgm` removed (the autohinter test); the missing-file
  check off; `except ImportError` changed to `KeyError`; threshold 300; red and blue swapped; panels swapped; bbox
  None; PNG for every entry; italic reading the roman. A size loop cut to one size turned 3 red.
- `test_the_specimen_carries_the_junction_row`: 6 mutations, all red (empty list, weight 400, largest size, `y`
  added, template selector without `data-fd-junctions`, cmap filter off). The checklist test's junction item and
  `diff.md` brief slot: 2 mutations red.

Added with `xh` and `serifBracket` (0.2 item 4):

- **The plan's mechanism for the unmapped points was replaced.** It applied the inverse y-map to the drawn
  points. That is exact for a curve whose control points lie in one band and approximate for one that
  straddles the x-line, and the all-curl variant of the branch test flipped 103 glyph records at `xh` 400 and
  600 (the curl test's cross product drifted by up to 0.25 against a threshold of 0.06). `glyph()` now fits the
  skeleton at `xh` 500 as well and samples that, so the decisions are the `xh` 500 ones by construction.
- **A mutation survived by hand and the test was widened.** Reading the curl decision from the drawn tail
  stayed green on the three examples, because none of them uses a curl end. The branch test now also draws a
  variant of each master with every end a curl; `xh-curl-mapped` is RED there.
- **Mutations that crashed instead of failing.** The first form of `xh-curl-mapped` removed the unmapped array
  and made node throw (the test went red on a stack trace, not on an assertion; `mutate.py` reported
  UNPROVEN). The second form changes only the decision, and the arrays stay aligned.

Added with `joints`, `crotch` and the refused `apex` (0.2 item 9):

- **An equivalent mutation, recorded.** `crotch` ignoring the end's own flag (`!flags[side]`) changes no glyph on this skeleton set: no shipped
  skeleton has a flagged end at a shared point where the arms are also acute. It is not in `mutate.py`.
- **A survivor widened the test.** `crotch` counting a corner as a joint stayed green against the first test (the corners of `E F L` are right angles and give no acute dot product; the acute ones, `z 2 3 7 B Z`, were not on its list); the test now compares the exact set of glyphs whose record names an acute joint, and `z 2 3 7 B Z` appear under
  the mutation. The first identical-at-0-and-0.3 list (`l n E F L T H`) held no obtuse joint, so a mutation that made every joint count as acute could not have failed it (reasoned, not run on that list); the caron and circumflex joints (`š ê Ô`, right-angled) were added, and `crotch-obtuse` is RED on them.
- **The plan's "eight steps before the joint end"** is pinned by the fold guard on the Bold's `V` and `A`; the test takes the first
  unpinned sample at least eight steps in. The plan's check order also let a mutation fail on an unrelated assertion (every end thinning failed on
  "no partner arm found" before the `l` check); the glyph checks now run first.

**`tests/test_genres.py`** (item 2, 0.2). The recipes in `templates/concepts.genres.js` against the table in
`references/genres.md` and the page content in `scripts/concepts/content.genres.json`. Watched red: the fitted-path
sample count (`samplePath(st.d, sampleCounts(st.d))`) on all 10 recipes' master compatibility; `xs` 0.86 on a serif
recipe (it survives on `grot` by design: the serif-kind test sits inside serif mode); a renamed recipe, a changed
table id and a flipped verdict on the table-and-recipes test; a page built from `concepts.example.js` on the
page test (red through the id comparison once the content `concepts` block is empty); and six edits on the content
drift test (a renamed, removed or added key, an edited `risk`, an edited table cell, a recipe added without the
content file following).

Added after the Impasse review of the finished 0.2 diff (2026-11-16):

- **G1, G2: two decisions still read drawn coordinates, and no test could see it.** The beak gate and the pairing of two stroke ends read the mapped
  points; a stroke 0.45 units off level, or two ends 1.8 apart, flipped at `xh` 600. Both mutations were GREEN against
  `test_xh_does_not_change_any_branch_record`, because the project's own glyphs sit far from every threshold. Fixed, and
  `test_no_decision_reads_a_mapped_coordinate` draws glyphs placed on the thresholds; `xh-beak-mapped` and `xh-partner-mapped` are RED there.
- **G3: the round fit is exact for a ring and not for an open curve.** Documented with its bound and measured; the first version of the open-curve
  assertion could not fail on a fit that was too weak, so `optical-fit-overcorrect` (weight 2) is the mutation that proves it.
- **G4: `test_backward_compat` never proved woff2 bytes.** It proves outlines, the TTF fontTools writes from the woff2, and the manifest figures.
  `test_the_0_1_woff2_bytes_are_unchanged_for_the_recorded_brotli` adds the bytes, keyed by platform, node major AND brotli version (1.2.1 recorded, macOS), and
  skips naming both versions when this brotli differs. It is RED under the same `Math.round(g.adv) + 1` mutation.
- **G6, G7:** the refusal test now carries its own case list (every knob times null, string, NaN, boolean, below, above, bounds), and the joints
  test also runs the shipped `"": "disk"` mapping (`optical-null-accepted` and `joints-keep-disk` are RED).

Added after the Impasse re-review (2026-11-16):

- **R1: the curl's spiral direction read the drawn cross product** while the curl decision read the unmapped one, and the record did not encode it. The
  record now carries `curlsg`, the sign decides on the unmapped cross product, and the stress test has 150 glyphs whose curl tail straddles the x-line
  (`xh-curl-handedness` is RED there; without the token the flip changes no sample count and nothing could see it).
- **R2: the `crotch` token was written on every open stroke**, so a 0.1 project whose masters fell on opposite sides of the new test would have been
  refused for a knob it never set. It is written only when `crotch` > 0; `test_an_unset_crotch_leaves_the_0_1_branch_record` matches every record of
  the project's masters against the 0.1 grammar (`crotch-token-always` is RED). The crotch test now reads the acute ends from the crotch 0.3 build.
- **R3: the open-curve bound had the wrong sign and omitted `hzThin`.** At `hzThin` 1.4 the measured shift (4.49) exceeds the old bound (3.75).

Added after the first CI run (2026-11-17):

- **The byte-identity promise is per platform AND node major version.** The first Linux CI run matched the neutral digests and not the bract and
  driftwood ones recorded on macOS under the same node major version (export, TTF and manifest digests of `bract/roman` and `driftwood/roman`, the
  manifest digest of `driftwood/italic`): the generator's floating-point output depends on the operating system as well as on V8, and integer
  rounding in the TTF then flips. We did not know whether 0.1.0 itself differs on Linux or whether 0.2 introduced it. The fixture
  (`tests/fixtures/baseline-0.1.0.json`, schema `font-design/baseline-digests/v2`) is therefore keyed `darwin/26`, `linux/22` and so on, a platform that is
  not recorded FAILS with the recording instructions (it never skips), and the `record-baseline` workflow
  (`.github/workflows/record-baseline.yml`, manual) records the 0.1.0 code on Linux for node 20 and 22 and, beside it, the current branch's digests on the
  same machine, so the two can be compared: equal means 0.2 changed nothing on Linux; different means it did. Entries are merged with
  `.venv/bin/python3 tests/baseline_digest.py --merge entry-baseline.json`, and `--merge` refuses an entry without a baseline revision (the branch's own digests).
  Guards: `test_an_unrecorded_platform_fails_with_the_recording_instructions` (RED under a lookup that ignores the platform),
  `test_a_recorded_platform_whose_digest_differs_fails_naming_it` (RED under a comparison that skips the manifest digest),
  `test_merging_adds_one_platform_entry_and_refuses_a_head_entry` (RED under a merge that accepts a null revision, which needed a second case with no
  fixture yet: the first version of the test had two guards covering one fixture, and the revision check against the existing record refused the entry
  first), `tests/test_ci_workflow.py` for the workflow text. The genre record in `tests/test_genres.py` rounds to 0.01 and passed on Linux.
- **The macOS CI job lacked libfribidi, not libraqm.** `diff.py` refused because Pillow reported no raqm. On the author's Mac there is no libraqm
  anywhere (`find /opt/homebrew -name 'libraqm*'` is empty) and raqm works: the Pillow wheel carries the engine and loads libfribidi at run time
  (`strings` on its `_imagingft` module names `libfribidi.dylib`), and Homebrew's `fribidi` is installed. So `ci.yml` runs `brew install fribidi`
  before the pip install on macOS and asserts `features.check('raqm')` after it, and `check-env.py` reports raqm as a REQUIRED piece (the review loop
  runs `diff.py` from round 2, so a machine without it fails in the middle of phase 8) with the fix per OS. Guards: `tests/test_check_env.py`
  (RED under a `check_raqm` that always passes) and `tests/test_ci_workflow.py` (RED under each of: the brew step removed, moved after pip, its macOS
  condition removed, the assertion turned into a print, a workflow that is not valid YAML).

Added with the lint job (issue #3, 2026-11-17):

- **`npm run check` proved only that each `.js` file parses.** The `lint` job in `ci.yml` now runs `npm run lint:js`, ESLint's correctness rules
  (`eslint.config.js`: `no-undef`, `no-unused-vars`, `no-unreachable`, `valid-typeof` and the rest of eslint:recommended's error class; style is not
  linted) over `scripts/*.js` and `scripts/concepts/*.js`, and `npm run lint:sh`, shellcheck over `scripts/smoke.sh`. ESLint runs through
  `npx --yes eslint@10.14.0`, so the skill still has no npm dependencies; the version is exact because npx otherwise resolves the newest release on
  the day. `render.js` names gen.js's spliced functions (`glyph`, `kern`, `layWord`, `wrap`) as globals, so a misspelling of them still fails.
  Both passed the 0.2.0 tree with no findings. Planted mistakes watched red: an undefined name in `gen.js`, an unused variable in `render.js`, a
  misspelt `typeof` string in `build-page.js`. Guards: `test_the_lint_job_runs_eslint_pinned_and_shellcheck_on_smoke` (RED under each run line
  removed, `eslint@10` for the exact version, `lint:sh` pointed at another file) and `test_version_is_the_same_everywhere`, which now holds
  `package.json`'s version to `VERSION` (RED on the 0.2.0 tree, where `package.json` still said 0.1.0).

Added with the platform run (0.3). The guards and the weakest mutation each must turn red; each test's docstring
names its mutation and the date it was watched red:

| File | Guards | Weakest mutations |
|---|---|---|
| `tests/test_shoot.py` | fractional `--scales` and the `@{scale:g}x` names (`@2x` unchanged); `crop_bands()` rounding a fractional box (band `head:0:901` at 1.25, because 900 × 1.25 is a whole number and could not fail); the Windows teardown (a Python grandchild holding the inherited stdout is killed; `run_chrome()` returns after a kill even when a helper holds the pipe; a profile directory a helper left behind is a `NOTE:`, not a failed shot); `--meta` (platform, `ua`, `height`, the failed list, exit 1); `--rows` in viewport CSS px with the scroll offset, no rows file for a failed shot, a verified shot whose rows never arrive failed, rows from another shot's browser ignored; repeatable `--font-url`; one dead browser not stopping the run; `--browser firefox` without Playwright exiting 3; the specimen's unique `data-fd-row` keys and the duplicate-key refusal | `type=int` restored; `int(round())` removed; the grandchild kill dropped, or on Windows `taskkill` run after `p.kill()`; `ignore_cleanup_errors` removed; the rect reported in device px; `scrollY` added back into `y`; the rows file written before the proofs; the cookie check dropped on the rows handler; "any named path served 200"; the exit code made 0; the surface dropped from the readable key |
| `tests/test_shoot_playwright.py` | a Firefox shot passes the Probe page and fails the Georgia page on the same server proofs as Chrome (skipped loudly without Playwright or its Firefox, and with the recorded message on the macOS "Could not find profile folder" failure); `--launcher playwright` shoots Chrome through Playwright at exactly the shot's width and height at scales 1 and 1.25 (skipped loudly without Playwright) | the launcher skipping the beacon wait; every Chrome shot routed to the command line whatever the launcher |
| `tests/test_compare_shots.py` | one image per row at the zoom, legs in order; a bad leg refused and the others compared, `--min-legs`; a PNG without rows and a scrolled shot refused; rows paired by key AND text and computed style; rows missing from a leg or below the capture listed; ink measured against the crop's own background (equal on paper and on cloth, `ink n/a` on a non-uniform border); smallest size first and labels from the meta (`FontSmoothingType` 2 is ClearType); several `meta*.json` in one leg; one test feeds a real `shoot.py --rows --meta` leg in, so the two tools agree on the shipped files | the zoom ignored; the refusal raising; the field comparison dropped; the key intersection replaced by the first leg's keys; `L_bg` fixed at 255; the label read from `FontSmoothing`; only `meta.json` read |
| `tests/test_check_env.py` | Playwright reported as optional with the install command, exit code unchanged | the row made required; the install command dropped |
| `tests/test_ci_workflow.py` | the template: manual dispatch with its inputs, three OSes × two browsers, `fail-fast: false`, the compare job and both uploads `if: always()`, `--family`, `--rows`, `--meta` and `--browser` on both shoot lines, `--height 6000` and `--require-captured` on the specimen, the download `path` and `merge-multiple: false`, the `FD_BUILD` and `FD_FONT_JSON` conditions; every expansion quoted; every flag registered by the script that runs it (through `registered_flags()` from `tests/test_docs_commands.py`, the shipped checker); the pins equal to the requirements files; the skill's own workflow equal to the template with the neutral slots filled; the template parses as YAML; `smoke.sh` step 9 running `compare-shots.py` on the tall specimen | each clause removed in turn; `--family` dropped; `merge-multiple: true`; `--family $FD_FAMILY` unquoted; `--meta` misspelled; a pin changed in one file |

The workflow tests read text, and say so: the run itself is the check that the workflow works, and the skill's
own `platform-shots.yml` runs on every pull request that touches the tools.
