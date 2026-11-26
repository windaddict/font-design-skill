# Plan: Tiki Terminal, a fourth example face in `examples/tiki-terminal/`, as built

WHAT IT'S FOR: the skill has three example faces, all serif, and none uses a per-face skeleton file, cut
stem ends or a custom axis. This plan adds Tiki Terminal, the operator-approved open display face, as a
buildable face folder, holds it to its approved design with tests, and puts it in the smoke run. It is
phases 6 and 7 of the skill's process for that face. `scripts/gen.js`, `scripts/export.js` and
`scripts/build.py` do not change, so `VERSION` stays 0.12.0. The existing font outputs are unchanged;
the Tiki Terminal build is new.

Operator amendments (2026-11-25, after the first plan review): the review's medium advisories F002, F003
and F005 are adopted into this plan (test 6 at 16 units with exact equality, a per-face bowl bound
instead of a shared one, and M4 run so the build succeeds); F006 is adopted as the wording above; F004
is stated as a limit in `spacing-review`, not fixed.

Operator rulings (2026-11-25, after the second plan review): the escalated question on test 6 is ruled
as a 1-unit tolerance band (every suppressed pair measures under 17 units unsuppressed; every pair under
15 units is suppressed), not exact equality at 16 and not the reviewer's 12/20 band. Findings F001 (the
README check moves out of test 7 to `docs-example`), F002 (`face()` gives distinct records), F003 (the
M3b and M3c commands), F004 (gap-test wording), F006 and F007 (CHANGELOG wording) are adopted.

All paths are relative to the repository root.

Every figure below marked "measured" was measured on 2026-11-25 on macOS with node 26.13.1, in a scratch
copy and a scratch clone of this tree at commit `7170554` with the face's files added. Nothing in the
worktree was changed by the research. The build that writes the face repeats each measurement.

## What the research found that the request did not know

Four findings change how the request's open items are settled. Each was measured, not inferred.

### 1. The touching pairs are 5 of several hundred, and they are not a Bold problem

The request names five pairs that touch at wght 700 (`rr`, `ro`, `er`, `RE`, `EO`) and asks for a choice
between hand kerns and a looser track for the Bold.

Measured on the built font (the trial's settings: automatic kerning, threshold 12, default sparse cap),
with HarfBuzz placing the second glyph and the distance taken between the two outlines:

| Location | pairs measured | outlines cross (gap 0) | gap under 12 units | gap under 16 units |
|---|---|---|---|---|
| Regular (400, LEAN 0) | 18,222 | 199 | 316 | 381 |
| Bold (700, 0) | 18,222 | 313 | 469 | 538 |
| Lean (400, 100) | 18,222 | 206 | 312 | 374 |
| Bold Lean (700, 100) | 18,222 | 313 | 456 | 518 |
| middle (550, 50) | 18,222 | 237 | 404 | 460 |

Over the five locations, 367 distinct two-character pairs cross, 531 come under 12 units and 624 come
under 16. With the three ligature glyphs counted (`fi`, `fl`, `ff` against every character, 19,038 pairs
per location), 14 more cross, 34 more come under 12 and 45 more come under 16. Examples that cross at
Bold: `az`, `hz`, `lZ`, `aJ`, `rt`, `ty`, `Er`, `ST`, `LA`, `7V`, `k2`.

Of the request's five pairs, two are tight and three are not (outline gap in units, Regular / Bold /
Lean / Bold Lean): `rr` 13.9 / 14.6 / 13.4 / 10.0; `EO` 18.1 / 18.5 / 23.7 / 18.1; `ro` 60.5 / 55.6 /
69.3 / 64.8; `RE` 88.0 / 54.2 / 99.8 / 60.1; `er` 110.3 / 97.6 / 119.2 / 110.0. At 120 px one unit is
0.12 px, so `rr` at Bold is 1.75 px apart and `er` is 11.7 px apart. The screenshot reading overstated
three of the five and missed the pairs that cross.

**Cause.** `gen.js` builds each glyph's spacing profile from polygon points only (`profs` in `glyph()`,
54 bins of 20 units). A stroke end that is square (`j`, `butt`, `cut`) is one straight segment with two
points, so the bins between its corners read whatever lies behind the end. The left profile of the Bold
`z` reads 8 units in one bin of the bottom bar and 278 to 334 in the bar's other bins, which is the
diagonal. `kern()` then sees a wide mean gap and pulls the pair together, and its clearance clamp
(`minClear − minRaw`) reads the same profile, so it does not stop the bar end. A serif end has many
points, which is why the serif examples show less of this. Measured another way, on the exported masters
with the exported kerns, over the 5,929 ordered pairs of the 77 kern-set characters: 122 pairs under 10
units on the neutral example's TextBold, 143 on the Driftwood example's Bold and 431 on Tiki Terminal's
Bold. The track figures below use that second measurement. `references/generator.md` says of the clamp "so no pair closes under the clearance".
That sentence is false where an end is square.

**Neither named remedy reaches it.**

- Hand kerns for five pairs leave about 530 pairs under 12 units. A hand value is also one number for
  all four masters, and the automatic value of `r|r` is −132, −154, −110 and −131 in the four.
- A looser Bold track was tried by giving the two Bold masters their own concepts with `track` 26 and
  46 in place of 6. Pairs under 10 units at Bold went from 431 to 356 and 242. `rt`, `Er` and `ST` still
  cross at both settings, because the kern grows by what the track adds wherever the clamp or the mean
  rule binds. The track also does nothing for the 258 pairs under 10 units at Regular.

**What does work without changing `gen.js`.** With no automatic kern a pair sits on its two sidebearings,
which are measured from the glyph's true extent and are 8 units or more each. With automatic kerning off
entirely, no pair of the 62 letters and figures crosses and the smallest gap is 15.7 units (Bold) and
21.8 (Regular), on the exported masters. So the defect is
confined to pairs that carry an automatic kern, and a zero hand pair (which `export.js` treats as "do not
kern this pair") removes it pair by pair.

### 2. Adding the folder breaks the font suite on the neutral and Driftwood fixtures

`scripts/tests/test_font.py::test_xh_moves_the_lowercase_lines_and_leaves_the_capitals` draws the first
concept of every `examples/*/concepts.js`. With `examples/tiki-terminal/concepts.js` present it fails on
the neutral fixture and on the Driftwood fixture (measured: `1 failed, 115 passed` on neutral), on this
assertion: "tiki-terminal: xh 600 at mult 1.5: the `d` bowl tops out at 611.83 (xh 500: 514.41), expected
it 100 higher". The bound is 1 unit and its own comment calls it "margins over measured values, not
derived from the generator" (0.45 on the three examples). Tiki Terminal's first concept, `phosphor`, a
monoline stroke of 144 units at mult 1.5, measures 2.58 at xh 600 and 4.04 at xh 400. Removing `joints`,
`crotch`, `roundGain`, `hzThin` and `diagThin` from the concept does not bring it under 1 (measured 2.06
to 4.91), so it is the heavy monoline stroke, not a knob the fixture forgot to clear.

Six more tests of the suite fail when the suite runs **on** the Tiki Terminal face. Each draws
`concepts[0]` of the face's file, which is `phosphor`, a round-1 concept no master of the face uses, and
each assumes that concept has flare or serif ends, or leaves `hzThin` and `xh` unset, or leaves `crotch`
unset on some master:

| Test | Why it fails on this face |
|---|---|
| `test_dropamt_scales_the_outer_inner_and_symmetric_teardrop` | no end of `phosphor` is a flare, so `tear: true` draws no teardrop |
| `test_dropamt_changes_the_teardrops_and_flareamt_with_tear_throws` | the same |
| `test_optical_corrections_change_only_the_strokes_they_name` | the fixture's "no knob" variant keeps `phosphor`'s own `hzThin` 0.92 (bar 88.32, expected 96.0) |
| `test_open_curve_extremes_stay_within_the_documented_bound_of_the_overshoot` | the same fixture |
| `test_an_unbracketed_serif_is_a_slab_with_the_bracketed_point_count` | the fixture keeps `phosphor`'s `xh` 560 and looks for the serif at 500 |
| `test_an_unset_crotch_leaves_the_0_1_branch_record` | every master of the face sets `crotch`, so the fixture reads 0 records and its floor of 1,000 fails |

With the Tiki Terminal file's bowl bound at 5 and those six excluded, the suite on the face reads `65 passed, 5 skipped, 6
deselected` (the 5 skips are the static-instance tests under `--static-dir none`), the neutral fixture
reads `116 passed` and the Driftwood fixture `95 passed, 5 skipped` (all measured).

### 3. FontBakery fails the face on two checks

`scripts/fontbakery-gate.py` on the built face (FontBakery 1.1.0, universal profile) reports two FAILs:

- `case_mapping` (`missing-case-counterparts`): the lowercase accented letters without capitals, as on
  the neutral example.
- `valid_glyphnames` (`found-invalid-names`): `build.py`'s `gname()` names a one-character ASCII key that
  is not in its `NAMES` table after the key itself, so the two glyphs `skeletons.js` adds are named `>`
  and `_`. FontBakery's message names the glyphs it refuses; `>` is one.

Fixing the second in `build.py` changes font output for any face that adds such a key, which is a
`VERSION` bump and a release. This plan accepts the finding in `requirements.json` with the reason and
records the fix as a follow-up.

### 4. Existing repo tests that count or sweep the concept files

- `tests/test_weight_decisions.py::test_the_weight_comparison_covers_the_concept_files` asserts exactly 5
  files and 220,080 comparisons. With the new file it reads `6 files, 264096 comparisons` (measured; the
  new file adds 7 concepts × 131 keys × 24 multipliers × 2 slants = 44,016, with 0 flips).
- These sweeps pick the new `concepts.js` up by glob and pass on it (measured): `test_every_font_json_validates`,
  `test_every_concept_passes_params`, `test_every_example_group_exports_and_matches_the_export_schema`,
  `test_no_branch_or_structure_changes_with_weight[tiki-terminal/concepts.js]`,
  `test_the_r_leg_is_buried_in_its_bowl_in_every_concept[tiki-terminal/concepts.js]`,
  `test_headsink_buries_the_stem_end_in_every_serif_concept_the_repo_ships`.
- `tests/test_r_leg_join.py::test_the_italic_leg_keeps_its_join_taper` fails on five drawings of the new
  file, all at mult 1.5: `cane`, `totem` and `canelean` roman (width at sample 20 about 11 % over the
  restated law) and `carvedslab` and `totem` italic (14 % and 6 %). Cause, measured with the test's own
  probe: the T-join cut at the leg's root pins 21 samples of one edge on those roman drawings and 19 on
  the italic ones, so sample 20 is a pinned point or the first point after one, and its "width" is the
  cut's geometry, not the pen's. Samples 23, 26, 40 and 60 of the same drawings are within 2 % of the
  law. Three shipped drawings pin 20 or 21 samples too (`blind`, `dune`, `anvil` at mult 1.5) and pass
  only because their swell is small. A rule that skips a sample at or one step past the pinned count
  leaves no failure on the six files (measured).
- **A full run of the repo tests** in a scratch clone with the face's files added and no test changed:
  `21 failed, 738 passed, 30 skipped` in 24 min 16 s. The 21 are: 4 from the bowl bound of finding 2
  (three in `tests/test_face_folder_in_a_site.py` and
  `tests/test_head_sink.py::test_a_face_that_sets_headsink_builds_with_its_spacing_unchanged`, each
  running the font suite on a copy of an example and reading `1 failed`); 1 from the count above; 1
  from the leg taper above; and 15 that are not about this change: the clone had no built neutral
  example, and six tests of `tests/test_fallback_metrics.py`, seven of
  `tests/test_site_wiring_template.py`, one of `tests/test_tools_and_templates.py` and one of
  `tests/test_mutate_harness.py` fail without `examples/neutral/out/`. A fresh worktree is in the same
  state, so the neutral example is built before any run of the repo tests (Verification).

## How the request's five open items are settled

1. **Spacing.** Neither hand kerns for five pairs nor a Bold track. The face keeps automatic kerning and
   suppresses it, with a zero hand pair, for every pair measured under 16 units at any of five locations
   (663 pairs measured: 618 two-character pairs and 45 with a ligature glyph). Two of the request's
   pairs get a real hand value because zero is too loose for them: `r|r` −90 and `E|O` −60. Two tests
   measure gaps on the built font: every pair of mapped characters keeps 12 units at five locations, and
   the request's five pairs keep 30 units at wght 700. Measured with that list: no pair under 12; the
   smallest gap is 15.0 units at Bold and Bold Lean, 16.0 at Regular and Lean and 16.4 at the middle;
   at wght 700 the five pairs read `rr` 50.7 and 35.4, `EO` 33.6 and 54.7, `ro` 55.6 and 64.8, `er` 97.6
   and 110.0, `RE` 54.2 and 60.1 (LEAN 0 and LEAN 100). The suppressed pairs are not left loose: with
   no kern their gaps have a median of 60 units at Bold and 83 at Regular, against 103 and 137 between
   two `n` stems.
2. **`requirements.json`.** Written in full below from the measured first build: floors 78 and 118 (the
   40 px target is 18.75), vertical metrics 1010 / −293 / 0, word space 256 and 273, `>` and `_`
   required and `<` not, seven titles, two accepted FontBakery findings.
3. **Where the face is exercised.** It joins `smoke.sh` steps 1, 2 and 2b (export, build, self-compare)
   and gets its own FontBakery step. The font suite runs on it from a new repo test, so the suite's six
   exclusions live in one place and the workflow's own test run sees them. It does not enter
   `tests/fixtures/baseline.json`: that fixture records what the baseline commit `6302b8a` built, the
   face did not exist there, and `baseline_digest.py --record` refuses a tree whose scripts differ from
   the baseline's. `tests/test_backward_compat.py` names its five groups and three examples explicitly
   and does not change. Cost, measured here: export 3 s, build 5 s, `diff.py` 4 s, FontBakery gate 11 s,
   the suite on the face 21 s, and the sweeps in finding 4. I estimate 2 to 4 minutes per CI machine from
   that; the estimate is not measured on a runner.
4. **Docs.** Listed under "Documentation to be updated". The CHANGELOG amends the 0.12.0 entry, as the
   0.10.0 follow-up did, with a line that starts `Font output: unchanged` and says the existing
   outputs are unchanged and Tiki Terminal is a new build.
5. **The three nicks** (the `a` heel, the `e` bar end, the `3` junction) are not touched. The source
   files are copied byte for byte. The README lists the nicks as open.

## Decisions the operator can overrule

1. **Suppress, do not wait.** The plan ships the face with 663 automatic kerns suppressed. The
   alternatives: (a) turn automatic kerning off for the face, which is safe and widens a title by 1.7
   to 10.1 % (measured on six trial titles at Regular and Bold); (b) fix the profile in `gen.js` first, in its own run, and build the
   face after it; (c) ship the trial's kerning with the crossings documented. Recommended: suppress now,
   and drop the list when the generator reads stroke edges (follow-up 1).
2. **The floor is 12 units, the list threshold 16.** 12 units is 0.48 px at 40 px and 1.44 px at 120 px.
   It is below the 15.0 that two 8-unit sidebearings give after rounding, so it cannot be raised past 15
   without a positive kern or a wider track. A pair at 12 to 20 units can still read as touching at Bold;
   that judgement is `spacing-review`. The 4 units between 16 and 12 are a margin for the outline
   differences between platforms that `tests/baseline_digest.py` documents; their size was not measured.
3. **`r|r` −90 and `E|O` −60.** One number serves four masters, so Regular is looser than Bold needs:
   `EO` reads 78.8 at Regular and 33.6 at Bold.
4. **The Sampler's hand pairs are not inherited.** The trial reused `A|I`, `I|A`, `L|T`, `L|V`, `L|Y`,
   `L|W`, `r|.`, `r|,` and `f|f` from the neutral example. With them `LT` stands 170 to 190 units apart;
   the automatic value brings it to 26 to 45. The concept rounds the operator approved were laid with
   automatic kerning only. The trial's 11 word-space pairs are kept.
5. **Titles.** The six titles of `content.json`, which the operator saw in round 1, plus `C:>_`, the
   prompt the operator named when choosing to carry `>` and `_`.
6. **Names.** Owner and designer John M. P. Knox, OFL 1.1 and `fs_type` 0 are the request's. Three
   strings are the plan's: vendor id `JMPK` (four letters, like `HOPS` and `MAVG` on the sites),
   vendor URL `https://github.com/windaddict/font-design-skill`, and no Reserved Font Name. The request's
   name search found no typeface called Tiki Terminal, and says that no hit is not proof the name is free.
7. **`valid_glyphnames` is accepted, not fixed** (finding 3).
8. **Six suite tests are excluded on this face, not generalised** (finding 2). They test the generator on
   the file's first concept, they run in full on the neutral and Driftwood fixtures in the same smoke
   run, and none reads the face's font or its masters.
9. **No statics.** The face has no site; the suite runs with `--static-dir none`.
10. **Font version 0.1.0 and build date 2026-11-26** (`source_date_epoch` 1795651200, the day the
    request gives for the approval).

## Findings outside this change

Each is a follow-up to file as an issue; none is built here.

1. **The spacing profile reads polygon points, so a square end is seen at two heights** (finding 1). It
   affects every face, most of all one with square-ended level bars. A fix changes font output and the
   compatibility baseline, so it needs an opt-in or a version.
2. **`build.py` names a glyph after its ASCII key** (finding 3).
3. **Six font-suite tests assume the first concept of a face's file** has flare or serif ends and leaves
   `hzThin`, `xh` and `crotch` unset (finding 2). A site that draws a sans face meets them at phase 7.
   Related to issue #16.
4. **The suite's bowl bound is a measured margin: 1 unit, and 5 for Tiki Terminal's file alone, keyed by
   folder name.** A bound derived from the stroke would replace the exception and be tighter for light
   faces.
5. **Tiki Terminal's outlines are pinned by nothing.** The baseline covers three examples. A generator
   change moves this face silently until someone decides to record it.

## Code to be changed

### `scripts/smoke.sh` (item `smoke-fourth-fixture`)

- Header comment and the three step titles: "three fixtures" becomes "four fixtures", and the header
  says what the fourth adds (a skeleton file, cut stem ends, a `LEAN` axis).
- Step 1: `for ex in neutral bract driftwood; do` becomes `for ex in neutral bract driftwood tiki-terminal; do`.
  The loop already passes `--requirements` when the example has the file.
- Step 2: after the Driftwood build line add
  `"$PY" "$HERE/build.py" --font "$ROOT/examples/tiki-terminal/font.json"`, with a comment saying the
  face is the only fixture built with `skeletons.js`, cut stem ends and a custom axis.
- Step 2b: the loop becomes `for ex in neutral bract driftwood tiki-terminal; do`, and its comment names
  the fourth (one group, two axes, no avar).
- New step 4c, inside `if want 4`, after 4b: the FontBakery gate on the face, with the same exit-3
  handling as 4b:
  `"$PY" "$HERE/fontbakery-gate.py" --font "$ROOT/examples/tiki-terminal/font.json" --requirements "$ROOT/examples/tiki-terminal/requirements.json"`.
- No step runs the font suite on the face: `tests/test_tiki_terminal.py` does, inside step 7.
- Steps 3, 5, 6 and 8 to 11 do not change. The mutations stay on the neutral fixture.

### `.github/workflows/ci.yml` (item `smoke-fourth-fixture`)

Wording only: the comment at the top ("every group of the three fixtures exported and built") and the
`test` job's step name say four fixtures and name the FontBakery step on two of them. No trigger, path
or command changes.

### Not changed

`scripts/gen.js`, `scripts/export.js`, `scripts/build.py`, `VERSION`, `package.json`,
`tests/fixtures/baseline.json`, `tests/baseline_digest.py`, `tests/test_backward_compat.py`,
`scripts/tests/mutate.py`.

## Code to be written

### `examples/tiki-terminal/concepts.js`, `skeletons.js`, `content.json` (item `face-sources`)

Copied byte for byte from the operator's working copy of the approved face. Nothing else is copied from that copy's `out/`. sha256 of the three files, checked after the copy with `shasum -a 256`:

- `concepts.js` `4f1b6760dde07980605f8c6ccb1cdecbe692c85b0c86d0b2034bb3cc6e006922`
- `skeletons.js` `70de29113147a240973219e3f0958f3c7226ea137ab7c0e442c7c0edef167a74`
- `content.json` `14eafc1c567f9e62b57a3965c0bc455b361ec5076dd10b864bff5a26b3432471`

`concepts.js` holds seven concepts in this order: `phosphor`, `teletype`, `cane`, `carvedslab`, `carved`,
`totem`, `canelean`. `canelean` differs from `cane` in `id`, `name`, `from`, `wonk` (`aeiokrAEIO`) and
`wonkAmount` (0.158) and nothing else (measured through `loadConcepts`). None of the three files holds a
string `tests/test_hygiene.py` forbids (checked).

### `examples/tiki-terminal/font.json` (item `face-config`)

Indented JSON, validated by `templates/font.schema.json`. Everything except the zero hand pairs is fixed
here:

```json
{
  "$comment": "Tiki Terminal: the skill's open example face. Design approved by the operator on 2026-11-26: the concept cane, and canelean (cane with the letters aeiokrAEIO leaning back) at the far end of a LEAN axis. No italic and no optical-size axis. The font is under the SIL Open Font License 1.1; these parameters are MIT like the rest of the repository. kerning.hand holds zero pairs that suppress the automatic kern wherever two outlines came closer than 16 units (README.md, 'Spacing'). Every key is documented in templates/font.example.json; paths are relative to this file.",
  "family": "Tiki Terminal",
  "version": "0.1.0",
  "concepts": "concepts.js",
  "skeletons": "skeletons.js",
  "out_dir": "out",
  "groups": {
    "roman": {
      "italic": false,
      "axes": [
        { "tag": "wght", "name": "Weight", "min": 400, "default": 400, "max": 700 },
        { "tag": "LEAN", "name": "Lean", "min": 0, "default": 0, "max": 100 }
      ],
      "masters": {
        "Reg": { "concept": "cane", "mult": 1, "location": { "wght": 400, "LEAN": 0 } },
        "Bold": { "concept": "cane", "mult": 1.5, "location": { "wght": 700, "LEAN": 0 } },
        "RegLean": { "concept": "canelean", "mult": 1, "location": { "wght": 400, "LEAN": 100 } },
        "BoldLean": { "concept": "canelean", "mult": 1.5, "location": { "wght": 700, "LEAN": 100 } }
      },
      "instances": [
        { "name": "Regular", "location": { "wght": 400, "LEAN": 0 } },
        { "name": "Bold", "location": { "wght": 700, "LEAN": 0 } },
        { "name": "Lean", "location": { "wght": 400, "LEAN": 100 } },
        { "name": "Bold Lean", "location": { "wght": 700, "LEAN": 100 } }
      ],
      "hairline_floors": { "Reg": 78, "Bold": 118, "RegLean": 78, "BoldLean": 118 }
    }
  },
  "charset": {
    "required": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,':;!?-–—…()[]/&#+*%$\"“”‘’ >_",
    "nbsp_to_space": true,
    "ascii_apostrophe_curly": true
  },
  "kerning": {
    "set": "^[A-Za-z0-9.,':;!?\\-–—…()\\[\\]/&#+*%$]$",
    "threshold": 12,
    "hand": { "r|r": -90, "E|O": -60, "...": "plus the zero pairs, see below" },
    "space": [[" ", "A", -45], [" ", "T", -20], [" ", "V", -35], [" ", "W", -30], [" ", "Y", -30],
              ["A", " ", -30], ["V", " ", -30], ["W", " ", -25], ["Y", " ", -25], ["r", " ", -25], ["f", " ", -25]]
  },
  "titles": ["Give your website a typeface no other site has", "LAST CALL AT THE LAGOON LOUNGE", "$ pour mai-tai --strong", "Six Concepts, Three Rounds & One Name", "Grog Log: 04:00, Bay #7", "Tiki Terminal", "C:>_"],
  "size_budget_bytes": 102400,
  "raster": { "budget": { "decimation": 48, "union": 48, "seam": 24 }, "sizes": [16, 40, 80] },
  "fold_units": { "raw": 4, "decimated": 10 },
  "decimation_eps": 1,
  "names": {
    "fs_type": 0,
    "copyright": "Copyright 2026 John M. P. Knox",
    "manufacturer": "John M. P. Knox",
    "designer": "John M. P. Knox",
    "vendor_id": "JMPK",
    "vendor_url": "https://github.com/windaddict/font-design-skill",
    "licence": "This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org",
    "licence_url": "https://openfontlicense.org",
    "description": "Tiki Terminal: a display face between a tiki-bar sign and an old console font. Heavy monoline strokes with cut stem ends, a weight axis, and a lean axis that tips the vowels and a few other letters back. Generated from centre-line skeletons with the font-design skill."
  },
  "source_date_epoch": 1795651200,
  "review": {
    "sizes": [40, 48, 64, 80, 96, 120, 140],
    "medium_below_px": 0,
    "surfaces": [
      { "name": "paper", "background": "#f3e7d3", "foreground": "#2a1a10" },
      { "name": "console", "background": "#10201a", "foreground": "#9be7a8" }
    ],
    "wordmark": "Tiki Terminal"
  }
}
```

The `"..."` entry above is a placeholder in this plan, not a key to write. Notes:

- The kern set does not include `>` and `_`. They carry no automatic kern and sit on their sidebearings.
- `raster.sizes` stays 16, 40, 80, the sizes the trial's self-checks passed at. The Bold reads 43 of the
  48 budget for decimation at 80 px (`ampersand`).
- The two surface colours are `paper`/`ink` and `cloth`/`cloth-ink` from `content.json`.

**The zero hand pairs.** They are produced by measurement, in this order:

1. Write `font.json` with `"hand": {}` and build: `.venv/bin/python3 scripts/build.py --font examples/tiki-terminal/font.json`.
2. Run `.venv/bin/python3 tests/pair_gap.py --font examples/tiki-terminal/font.json --under 16`. It prints
   one JSON object: `"a|b": 0` for every pair of kern-set keys (the three ligature keys included) whose
   outlines come closer than 16 units at any of the five locations. Expected: 664 entries (619 two-character pairs and 45 with a ligature glyph). Five of the 624 pairs of finding 1
   are outside the kern set (`Á` before `A`, `À`, `Á`, `Â`, `Ä`): they carry no kern, read 15 units on their
   sidebearings and are not listed.
3. Put those entries in `kerning.hand`, then set `"r|r": -90` and add `"E|O": -60`. Expected: 665 entries,
   663 of them zero.
4. Rebuild. Expected `kern_pairs` 4,660 and a woff2 of about 77,880 bytes (5,323 pairs and 78,952 bytes
   before the list).
5. Run `tests/test_tiki_terminal.py`. If the 12-unit test still names a pair, that pair is closer than 12
   with no kern at all: give it the smallest positive hand value that brings it to 16, and say so in the
   README. None was measured. If the 30-unit test names `rr` or `EO`, move that hand value toward zero in
   steps of 5 and update `hand_kerns` in `requirements.json`.

### `examples/tiki-terminal/requirements.json` (item `face-config`)

From `templates/requirements.example.json`, with a `$comment` saying the values are the operator's
decisions (axes, instances, names, required characters) or measured from this face's first build (floors,
vertical metrics, word space, cmap), and that the suite runs with six tests excluded (README).

```json
{
  "family": "Tiki Terminal",
  "groups": {
    "roman": {
      "axes": { "wght": [400, 400, 700], "LEAN": [0, 0, 100] },
      "masters": { "Reg": { "wght": 400, "LEAN": 0 }, "Bold": { "wght": 700, "LEAN": 0 }, "RegLean": { "wght": 400, "LEAN": 100 }, "BoldLean": { "wght": 700, "LEAN": 100 } },
      "instances": { "Regular": { "wght": 400, "LEAN": 0 }, "Bold": { "wght": 700, "LEAN": 0 }, "Lean": { "wght": 400, "LEAN": 100 }, "Bold Lean": { "wght": 700, "LEAN": 100 } },
      "hairline_floors": { "Reg": 78, "Bold": 118, "RegLean": 78, "BoldLean": 118 },
      "vertical_metrics": { "ascender": 1010, "descender": -293, "line_gap": 0 },
      "interpolated_check": { "location": { "wght": 550, "LEAN": 0 }, "between": ["Reg", "Bold"], "t": 0.5 },
      "word_space": { "Reg": 256, "Bold": 273, "RegLean": 256, "BoldLean": 273 }
    }
  },
  "cmap": "<the neutral example's cmap string with > and _ added: 137 characters, read from the built font>",
  "required_characters": "<the same string as charset.required in font.json>",
  "hand_kerns": { "r|r": -90, "E|O": -60, " |A": -45 },
  "titles": ["<the same seven titles as font.json>"],
  "size_budget_bytes": 102400,
  "fold_units": { "raw": 4, "decimated": 10 },
  "names": { "family": "Tiki Terminal", "copyright": "Copyright 2026 John M. P. Knox", "manufacturer": "John M. P. Knox", "designer": "John M. P. Knox", "vendor_id": "JMPK", "vendor_url": "https://github.com/windaddict/font-design-skill", "licence_contains": "SIL Open Font License, Version 1.1", "fs_type": 0 },
  "gasp": { "65535": 15 },
  "tables": { "code_page_range1": 1, "prep_hex": "B801FF85B0048D", "mac_names": false },
  "accepted_qa_findings": [
    { "id": "case_mapping", "codes": ["missing-case-counterparts"], "reason": "<the lowercase accented letters FontBakery lists have no capital in the generator's glyph set; a capital is a new skeleton>" },
    { "id": "valid_glyphnames", "codes": ["found-invalid-names"], "reason": "<build.py names a one-character ASCII key outside its name table after the key itself, so the glyphs skeletons.js adds are named > and _; renaming them changes font output and is a build.py change with a version>" }
  ]
}
```

Text in angle brackets is to be written out. The measured figures to confirm from the first build's
output: `min interior stroke` 78.78 (Reg, RegLean) and 118.18 (Bold, BoldLean), so the floors are those
rounded down; `vertical metrics written: hhea 1010/-293/0`; word space 256 and 273; 137 cmap entries;
140 glyphs. The 1010 / −293 extent gives `line-height: normal` of 1.303 em. No avar key: the face has no
intermediate named instance. Each accepted finding's reason is written after reading the gate's message,
and names the glyphs the message names.

### `examples/tiki-terminal/OFL.txt` (item `face-config`)

The licence text a built font must travel with. Seven header lines, then the licence body:

```
Copyright (c) 2026, John M. P. Knox (https://github.com/windaddict/font-design-skill).

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
https://openfontlicense.org


```

The body is the official text from its first line of dashes to its end: 4,128 bytes, ASCII, LF line
ends, sha256 `ebc109078c06f79af74cf2b27454c262830d12a65749f0e2bf25d1ac1db7a02a` (taken from
`https://openfontlicense.org/documents/OFL.txt` on 2026-11-25). It is reproduced here so the build needs
no network; the digest, which a test holds, is the check on the transcription:

```
-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.
```

No Reserved Font Name line is written (decision 6).

### `tests/pair_gap.py` (item `tiki-tests`)

WHAT IT'S FOR: measures how close two neighbouring glyphs of a built variable font come, so a face can
be held to a minimum gap and the pairs that need their automatic kern suppressed can be listed.

- `LOCATIONS`: `Regular` (400, 0), `Bold` (700, 0), `Lean` (400, 100), `Bold Lean` (700, 100) and
  `middle` (550, 50), as `{"wght": ..., "LEAN": ...}`.
- `scan(woff2_path, location, limit)` returns `{"measured": n, "close": {"a|b": gap}}`. It instances the
  font at the location with `fontTools.varLib.instancer`, reads every glyph's contours from `glyf` as
  straight segments (it asserts every point is on-curve, which holds for this builder's polygons), and
  shapes with `uharfbuzz` on the variable font at the same location, `kern` and `liga` on.
- Units: every mapped character whose glyph has contours, plus each of `fi`, `fl`, `ff` that HarfBuzz
  shapes to one glyph. A pair (a, b) is measured when the string a + b shapes to exactly the glyph of a
  alone followed by the glyph of b alone; otherwise it is skipped (a ligature formed across the pair).
- The gap of a pair is the smallest distance between any segment of a and any segment of b, with b moved
  right by the first glyph's shaped advance; 0 when two segments cross. Segments farther than `limit`
  from the other glyph's bounding edge are skipped, so only gaps under `limit` are returned.
- `hand_key(unit)` maps a unit to its generator key: U+2019 and U+0027 both give `'`.
- Command line: `--font FONT_JSON` (finds the group's woff2 where `build.py` writes it), `--woff2 PATH`
  to name another file, `--under UNITS`. It prints the JSON object described above, limited to pairs
  whose two keys match `kerning.set` or are a ligature key, and one line on stderr with the counts.

Exact guarantee: the contour distance between the outlines HarfBuzz would place, at the five named
locations. It is not a rendering, it does not see a glyph lying wholly inside another's counter without
crossing it (containment), and it says nothing about axis settings between the five (interior
locations). Test 4's and test 5's assertion messages, the README's Spacing and limits text and
`references/testing.md` section 14 say "contour distance at the five named locations" and repeat both
limits; no overlap check or interior sweep is added (the operator ruled F004 a stated limit).

The research prototype measured 19,038 pairs per location in about 1 second each.

## New automated tests

All in `tests/test_tiki_terminal.py`, item `tiki-tests`, proof: red-green. The file's header says what
each level is.

**How the tests reach the face.** Two module-scoped fixtures, and no test opens a face file any other
way:

- `face()` reads `examples/tiki-terminal/font.json` and `requirements.json` and returns the two
  dictionaries, or `{"missing": "<path>"}` for a file that is absent, or `{"invalid_json": "<path>",
  "error": "<the json error, one line>"}` for a file that exists and does not parse. It never raises.
- `built()` copies the face folder (without `out/`) to a temporary directory, runs
  `build.py --font <copy>/font.json` there, and returns the woff2 path and the manifest, or
  `{"missing": ...}` or `{"build_failed": "<last 2,000 characters of stderr>"}`. It never raises.

**What the red run proves, exactly.** Before the feature exists there is no face, so each test can fail
only because its observation is the `missing` record, and each red message must name the absent path
(an `invalid_json` record in the red run means a stray file, not the expected red: fix it). That proves
each test runs and can fail on its one assertion. It does not prove a test sees the defect it is named for. That proof is the eleven mutations (M1 to M8, M3b, M3c and M7b)
under Verification, run on the finished face and recorded in `references/testing.md`.

Each test has exactly one `assert`, whose message starts with the marker named here. The marker is the
`expected_failure` for the manifest.

| # | Test | Level | Marker | What it compares |
|---|---|---|---|---|
| 1 | `test_font_json_and_requirements_state_the_approved_design` | one unit: the two configuration files | `TIKI-DESIGN:` | a dictionary of facts read from both files against the operator's decisions written out in the test |
| 2 | `test_the_lean_masters_draw_cane_with_the_leaning_letters` | across a module boundary: `concepts.js` through `gen.js` `loadConcepts`, in node | `TIKI-CONCEPTS:` | the keys in which `canelean` differs from `cane`, and their values |
| 3 | `test_the_built_font_carries_the_approved_axes_names_and_characters` | the whole tool: sources to woff2, read with fontTools | `TIKI-FONT:` | a dictionary read from the built font against the same decisions |
| 4 | `test_no_two_mapped_characters_come_closer_than_12_units` | the whole tool and HarfBuzz: the data flow from skeleton to shaped text | `TIKI-PAIR-GAP:` | `pair_gap.scan` (contour distance, not containment) at the five named locations, limit 12 |
| 5 | `test_the_five_reported_pairs_keep_30_units_at_weight_700` | the same | `TIKI-BOLD-PAIRS:` | `rr`, `ro`, `er`, `RE`, `EO` at (700, 0) and (700, 100) |
| 6 | `test_every_suppressed_pair_is_one_the_measurement_found` | the same, on a second build | `TIKI-ZERO-LIST:` | the zero hand pairs against a build of the face without them |
| 7 | `test_the_font_suite_passes_on_the_face_with_six_first_concept_tests_excluded` | the software as a whole: the font suite run by path on the built copy | `TIKI-SUITE:` | the suite's exit code and summary line |
| 8 | `test_the_lean_axis_tips_the_wonk_letters_and_leaves_the_others_alone` | the whole tool: sources to woff2, glyph outlines read with fontTools at four instances | `TIKI-LEAN-GEOMETRY:` | outline coordinates at LEAN 0 and 100, at wght 400 and 700 |

Details, enough to write each without guessing:

1. **`TIKI-DESIGN:`** Observed, from `font.json`: `family`; the group names; `italic`; each axis as
   `[tag, min, default, max]`; each master as `[concept, mult, location]`; each instance as
   `[name, location]`; `concepts`; `skeletons`; `fold_units`; `names.fs_type`, `designer`, `manufacturer`,
   `copyright`, `licence_url`; whether `names.licence` contains `SIL Open Font License, Version 1.1`;
   whether `charset.required` holds `>`, holds `_`, and holds `<`. From `requirements.json`: `family`;
   `groups.roman.axes`, `masters`, `instances`; `names.fs_type` and `designer`; the same three character
   facts for `required_characters`; whether every hairline floor is at least 18.75 (1000 × 0.75 / 40);
   whether `font.json` and `requirements.json` agree on floors and titles. Expected: the values in this
   plan, written as a literal in the test, never read from either file. `assert observed == expected`.
2. **`TIKI-CONCEPTS:`** A `node -e` script given `scripts/gen.js` and the concepts path. It prints
   `{"ids": [...], "differ": [...], "wonk": ..., "wonkAmount": ..., "cane_wonk": ...}`, or
   `{"missing": ...}` when the file does not exist (the script checks before `loadConcepts`, and the test
   reports a non-zero exit the same way). Expected: `differ` is `["from", "id", "name", "wonk",
   "wonkAmount"]`, `wonk` is `aeiokrAEIO`, `wonkAmount` is 0.158, `cane_wonk` is absent, and `ids`
   contains `cane` and `canelean`.
3. **`TIKI-FONT:`** From the built woff2: `fvar` axes as `[tag, min, default, max]` (expected exactly
   `wght` 400/400/700 and `LEAN` 0/0/100, so no `opsz`); the named instances as `[name, coordinates]` in
   order (Regular, Bold, Lean, Bold Lean); name IDs 1, 9, 0, 14 and whether ID 13 contains the OFL
   sentence; `OS/2.fsType`; whether the cmap maps `>`, `_`, `<`; whether the glyph of U+0030 has three
   contours or more (the slashed zero: a ring is two); whether the manifest's `skeletons` names
   `skeletons.js`. Expected as in this plan.
4. **`TIKI-PAIR-GAP:`** For each of the five locations, `scan(woff2, location, 12)`. Observed:
   `{name: {"measured_at_least_18000": bool, "close": {...}}}`; when `built()` has no font, the `missing`
   or `build_failed` record. Expected: every location `{"measured_at_least_18000": True, "close": {}}`.
   The message lists the close pairs with their gaps, worst first, capped at 40, and ends with the
   `pair_gap.py --under 16` command that lists what to suppress.
5. **`TIKI-BOLD-PAIRS:`** `scan` at Bold and Bold Lean with limit 30. Observed: the entries of the five
   pairs that are under 30, per location, and the measured count as in test 4. Expected: none, with the
   count met.
6. **`TIKI-ZERO-LIST:`** A second temporary copy of the face whose `kerning.hand` keeps only its
   non-zero entries (`r|r` −90 and `E|O` −60, so those two pairs are kerned in both builds), built the
   same way, scanned at the five locations twice: with limit 17 (`BAND_HIGH`) and with limit 15
   (`BAND_LOW`). The list itself is still made at 16 (`pair_gap.py --under 16`); the band allows 1 unit
   of platform difference either side of it. The scan results are filtered to kern-set and ligature keys exactly as the
   command line filters them (the same function, imported from `tests/pair_gap.py`, not re-implemented).
   Each measured set is the union over the five locations. Observed:
   `{"zero_pairs": n, "not_found_under_17": [...], "under_15_not_suppressed": [...],
   "not_kern_set_keys": [...], "kern_pairs": m}`. `not_found_under_17` holds each zero pair that no
   location of the second build measures under 17. `under_15_not_suppressed` holds each pair the second
   build measures under 15 that is not a zero pair. `r|r` and `E|O` are the only named exception: they
   are kerned in the second build, so they do not appear in its measurement, and a module constant
   `NONZERO_HAND = {"r|r": -90, "E|O": -60}` with a comment states why. `not_kern_set_keys` holds each
   zero pair with a key outside `kerning.set` and the ligatures, and `m` is the face's own `kern_pairs`
   from its manifest. Expected: `zero_pairs` at least 400, all three lists empty (the under-15 set is
   contained in the zero-pair set, and the zero-pair set in the under-17 set), and `kern_pairs` at least
   4,000. This guards both ways: a list that grows past what was measured, up to and including "suppress
   everything" (which would pass test 4), and a list that misses a pair between 12 and 15 units (which
   test 4 does not see). What the band gives up, stated: an added zero pair at 16 to 17 units, or a
   missing one at 15 to 16, passes. The 1-unit size is an operator ruling, not a measurement of how far
   outlines move between platforms; `ci-run` is where that is first seen. (Plan-review history: the
   first draft scanned at 20, advisory F002 made it exact at 16, and the second review's escalation was
   ruled as this band.)
7. **`TIKI-SUITE:`** Runs `pytest scripts/tests/test_font.py -q -p no:cacheprovider --font <copy>/font.json
   --requirements <copy>/requirements.json --static-dir none --scripts=<repo>/scripts -k "<expression>"`
   with the module constant `SUITE_EXCLUSIONS`, the expression
   `not dropamt and not optical_corrections and not unbracketed_serif and not open_curve_extremes and not unset_crotch`.
   A comment beside the constant gives each excluded test's reason from finding 2. Observed:
   `{"exit": code, "six_deselected": "6 deselected" in output, "failed": "failed" in summary line}`.
   Expected: exit 0, `True`, `False`. The README does not exist until `docs-example`, so test 7 does not
   read it (plan-review finding F001); `docs-example` checks that the README's suite command carries the
   same expression. The count is in
   the assertion because `-k` matches substrings: a seventh test it swallowed would change it.

8. **`TIKI-LEAN-GEOMETRY:`** Closes the gap that tests 2 and 3 leave: they read concept values and font
   metadata, so a `LEAN` axis that draws no lean passes them. This test reads outlines. It instances the
   built woff2 with `fontTools.varLib.instancer` at (wght 400, LEAN 0), (400, 100), (700, 0) and (700,
   100), and reads each glyph's contour points from `glyf`. For each of the wonk letters `a e i o k r A E I
   O` and each weight it computes the displacement of every point between LEAN 0 and LEAN 100 (the two
   outlines have the same point count, because the masters are compatible; a different count is itself a
   failure, reported). Observed, per weight: `{"wonk_not_tipped": [letters whose largest point displacement
   is under MIN_TIP], "wonk_only_shifted": [letters whose displacement spread, the largest dx minus the
   smallest dx over the points, is under MIN_SPREAD, which is a plain shift and not a lean],
   "others_moved": [letters among n, H, m, T, x, z whose outline differs at all between the two LEAN
   values], "count_mismatch": [...]}`. Expected: all four lists empty at both weights. The wonk letters are
   read from the face's `canelean` concept through `loadConcepts`, not retyped, so the set the test checks
   is the set the face draws; the test also asserts it is the ten letters above, in the same assertion's
   dictionary. The control letters are outside that set (`n`, `H`, `m`, `T`, `x`, `z`), so an axis that
   moves every glyph fails too. `MIN_TIP` and `MIN_SPREAD` are module constants. Their values are set
   from the first build, at half the smallest value measured over the ten letters and two weights, and
   the plan does not state them because none was measured before this revision. The test needs only
   `built()`.
   What it can and cannot see: it sees a lean that is absent, a lean on the wrong letters, and a lean
   that is only a shift. It does not judge the angle or the look of the lean; that is `spacing-review`.

`tests/pair_gap.py` is used by tests 4, 5 and 6 and is written by the same item. Test 8 reads outlines
with fontTools directly and does not use it.

## Automated tests to be changed

### `scripts/tests/test_font.py` (item `suite-bowl-bound`)

In `test_xh_moves_the_lowercase_lines_and_leaves_the_capitals`, the `d` bowl bound stays `< 1` for
every concepts file except Tiki Terminal's. A module constant `D_BOWL_BOUND_BY_FOLDER = {"tiki-terminal":
5}` next to the test gives the one exception, keyed by `concepts.parent.name` (the name `where` already
prints), and the assertion uses `D_BOWL_BOUND_BY_FOLDER.get(concepts.parent.name, 1)`; the failure
message names the bound it used. The comment beside the constant gives the figures: 0.45 at most on
neutral, Bract and Driftwood, and 2.58 (xh 600) and 4.04 (xh 400) on Tiki Terminal's `phosphor` at mult
1.5, a 144-unit monoline stroke that no Tiki master uses; and it says the key is a folder name, so a
site face folder that happened to be called `tiki-terminal` would inherit the 5. Nothing else in the
suite changes. What this weakens, stated: on Tiki Terminal's first concept only, a defect that moves the
bowl's top by 1 to 5 units against its own xh 500 drawing passes. Neutral, Bract, Driftwood and a
project's own face keep the bound of 1. The `o` assertions before it (centre within 0.1, height within
2) and the flat-line assertions are unchanged. (Plan-review advisory F003: the earlier draft widened the
shared bound to 5 for every face.)

### `tests/test_weight_decisions.py` (item `weight-count`)

`test_the_weight_comparison_covers_the_concept_files`: `len(weight_flips) == 5 and total == 220080`
becomes `len(weight_flips) == 6 and total == 264096`, and the docstring says six files and that Tiki
Terminal's seven concepts add 44,016. The count is exact on purpose; the build confirms it by running
the test, and uses the number the run prints if it differs.

### `tests/test_r_leg_join.py` (item `leg-taper-pinned`)

`test_the_italic_leg_keeps_its_join_taper` compares the leg's width at samples 20, 23, 26, 40 and 60 with
the restated width law. It now leaves out a sample `j` when `j <= max(r["pinned"]) + 1`, where `pinned` is
the count of root samples the T-join cut pinned on each edge, which the probe `tests/r_leg_junction.js`
already reports. The docstring says why: at such a sample one edge point is the cut's corner, or the
first point after it, so the distance across is not a pen width. The floor `checked > 100` stays, and the
test also asserts that every drawing keeps at least three compared samples, so the skip cannot empty a
drawing. Measured on the six files before the change: 162 drawings, 650 samples, the largest pinned count
21, and exactly the five failures named in finding 4. No other test of the file changes.

### Tests that turn green with no edit

The four tests named in finding 4 that run the font suite on a copy of an example pass again once
`suite-bowl-bound` is in.

### Tests that change by themselves

`tests/test_docs_commands.py` gains one case per command line in the new README. Its flag check accepts
only flags the script or its conftest registers, so the README's suite command uses `-k`, never
`--deselect`.

## Documentation to be updated

All in item `docs-example`.

- **`examples/tiki-terminal/README.md`** (new). First lines: what the face is for (the skill's own open
  example, drawn through the three concept rounds, the only fixture with a skeleton file, cut stem ends
  and a custom axis). Then:
  - *Status*, in exact terms: the design was approved by the operator on 2026-11-26; this folder builds
    and passes its self-checks, the gap tests and the font suite less six tests; the built font's spacing
    has not been reviewed by a person until `spacing-review` is done; no font file is in the repository.
  - *Files*, one line each, with why each `skeletons.js` override exists left to that file's header.
  - *Licence*: the parameters (`concepts.js`, `skeletons.js`, `font.json`, `requirements.json`,
    `content.json`) are MIT like the repository; a font built from them carries the SIL Open Font License
    1.1 in its name table and travels with `OFL.txt`; no Reserved Font Name; the request's name-search
    note with its limit.
  - *Build*: the export pre-check, `build.py`, the suite command with the `-k` expression, the FontBakery
    gate, `tests/pair_gap.py`, and the round-1 concept page
    (`node scripts/concepts/build-page.js --template round1 --concepts examples/tiki-terminal/concepts.js --content examples/tiki-terminal/content.json --skeletons examples/tiki-terminal/skeletons.js out/tiki-round1.html`,
    which the research ran: 7 concepts, exit 0). Every Python command spells `.venv/bin/python3`.
  - *Numbers*, from the build that writes the face: glyphs, cmap entries, kern pairs, points per master
    before and after decimation, minimum strokes against floors, worst folds, woff2 bytes.
  - *Spacing*: finding 1 in short, the 16 and 12 unit figures, how the list is regenerated, and that it
    exists because of a generator limit.
  - *Known limits and open items*: the six excluded suite tests and why; the two accepted FontBakery
    findings; the three nicks; proportional figures; `LEAN` is a private axis tag and STAT names its
    values by number (`references/variable-font-build.md`, "Known limits of the STAT table"); the
    outlines are in no compatibility baseline.
- **`README.md`**: the `examples/` row of the layout table names `tiki-terminal/`; the Licence section
  says a font built from the Tiki Terminal parameters is under the OFL 1.1.
- **`NOTICE.md`**: the opening paragraph (it says the repository publishes the parameters of two
  typefaces that are not public), "What is not here" (no font file of any face, this one included, is
  tracked) and "What the examples are" (a paragraph for this face: real name table, MIT parameters, OFL
  font, the name).
- **`CHANGELOG.md`**: the 0.12.0 entry gains a dated subsection for this addition whose line starts
  `Font output: unchanged` (the form `tests/test_versions_and_skill.py` matches, `^Font output:
  (unchanged|changes)\b`) and continues with the narrower claim: the existing examples' outputs are
  unchanged and rebuild to the recorded digests, no font source (`gen.js`, `export.js`, `build.py`) is
  touched, and Tiki Terminal is a new build from three new source files (finding F007). The subsection lists the example, the smoke steps, the bowl bound and the new tests, and lists
  findings 1 to 3 under "Looked at and not changed". The `v0.12.0` row of `## Releases` notes that the
  later commit changed none of the three font sources. The existing 0.12.0 `Font output:` line keeps
  its form, but its sentence "No concept this repository ships sets wonkAmount" becomes "No concept this
  repository shipped at 0.12.0's release commit sets wonkAmount", and the new subsection says that
  `canelean` is the first shipped concept to set it (finding F006).
- **`SKILL.md`**: "three fixtures" at two places, and the `examples/neutral/` bullet names the fourth
  example. Edit inside existing lines: the file has 496 lines and a test holds it under 500.
- **`CLAUDE.md`**: "all three fixtures" in the layer list; the repo-test count from `pytest --co -q`; the
  duration of the smoke run this change makes, with the date, as that file asks.
- **`references/generator.md`**: (a) the automatic-kerning paragraph's "so no pair closes under the
  clearance" is restated exactly: the clamp holds where the profile has a point, and a square end has
  two, with the Tiki Terminal figures and a pointer to the face's README; (b) "No font this repository
  builds has a `cut` end" and the count of concept files and comparisons (220,080) are brought up to date.
- **`references/variable-font-build.md`**: section 10 says the smoke run builds four fixtures and names
  Tiki Terminal as the example with a `LEAN` axis, with its measured woff2 size.
- **`references/testing.md`**: a new section 14 with its Contents line, "The Tiki Terminal example
  guards": the eight tests, what the red run proved, the eleven mutations (M1 to M8, M3b, M3c and M7b) with their results, and any
  survivor as a finding about the test. Also the rows that state the bowl bound, "five concept files", 220,080 and
  what the leg taper test compares.
- **`docs/plan-tiki-terminal.md`**: this plan as built, with the plan review's findings and what each
  changed, free of machine paths, as the earlier `docs/plan-*.md` files are.

Not changed although they say "three": the CHANGELOG entries of earlier versions, `docs/plan-*.md` and
test docstrings that name three examples and still test exactly those three.

## Work items

| id | title | kind | files | verifiable_by |
|---|---|---|---|---|
| `tiki-tests` | Write the gap-measuring helper and the eight tests that hold the Tiki Terminal example to its approved design, the lean it draws, a minimum gap between outlines and its font suite. | test-new | tests/pair_gap.py, tests/test_tiki_terminal.py | agent |
| `face-sources` | Copy the three operator-approved source files of the face into the example folder byte for byte. | code-new | examples/tiki-terminal/concepts.js, examples/tiki-terminal/skeletons.js, examples/tiki-terminal/content.json | agent |
| `suite-bowl-bound` | Give the font suite's d bowl check in the x-height test a bound of 5 units for the Tiki Terminal concepts file alone, keeping 1 unit for every other face, because the new example's first concept measures 4.04. | test-change | scripts/tests/test_font.py | agent |
| `weight-count` | Raise the weight-comparison coverage count to six concept files and 264,096 comparisons. | test-change | tests/test_weight_decisions.py | agent |
| `leg-taper-pinned` | Leave out of the R leg taper test each width sample that the T-join cut pinned, because five drawings of the new concept file fail there for that reason. | test-change | tests/test_r_leg_join.py | agent |
| `face-config` | Write the face's font.json, requirements.json and licence text, with the automatic kern suppressed for every pair measured under 16 units. | code-new | examples/tiki-terminal/font.json, examples/tiki-terminal/requirements.json, examples/tiki-terminal/OFL.txt | agent |
| `smoke-fourth-fixture` | Export, build, self-compare and FontBakery-check the Tiki Terminal example in the smoke run, and name four fixtures in the CI workflow. | code-change | scripts/smoke.sh, .github/workflows/ci.yml | agent |
| `docs-example` | Document the example, its licence split and its limits, amend the 0.12.0 changelog entry, keep the plan, then run the smoke check last. | doc-change | examples/tiki-terminal/README.md, README.md, NOTICE.md, CHANGELOG.md, SKILL.md, CLAUDE.md, references/generator.md, references/variable-font-build.md, references/testing.md, docs/plan-tiki-terminal.md | agent |
| `spacing-review` | The operator reads the built face at 40 and 120 px in the four named instances and rules on its spacing and on the plan's decisions. | live-acceptance | | operator |
| `ci-run` | The operator runs CI by hand on the branch before the merge, because outlines differ between platforms and the gap floor has a 4-unit margin. | live-acceptance | | operator |

Order: `tiki-tests` (red), `face-sources`, `suite-bowl-bound`, `weight-count`, `leg-taper-pinned`, `face-config`,
`smoke-fourth-fixture`, `docs-example`. `spacing-review` accepts `face-config`. `ci-run` accepts
`smoke-fourth-fixture`. Neither operator item gates the build.

## Verification

Layers, per CLAUDE.md "Choosing how much to test": the change touches the font suite (layer 3, then
layer 4) and adds a fixture to `smoke.sh` (layer 4). It is not a release, so `--full` and layer 5 are
not required by that table; layer 5 is asked of the operator in `ci-run` for the reason given there.
Before any run of the repo tests, build the neutral example with its statics
(`.venv/bin/python3 scripts/build.py --font examples/neutral/font.json --static examples/neutral/out/static`):
15 repo tests read `examples/neutral/out/` and fail without it (finding 4). The agent runs layers 1 to 4
here, one at a time: `mutate.py` edits `gen.js`, `export.js` and `build.py`
in place and restores them, so nothing else may run during smoke step 5. The commit and the pull request
say which layers ran and how long the smoke run took.

To restore a file after a mutation, copy it aside first and copy it back with `cp`, then compare
`shasum -a 256` with the value taken before. Do not use `git checkout` or `git stash`.

### Per work item

- **`tiki-tests`, agent, proof: red-green.** `.venv/bin/python3 -m pytest tests/test_tiki_terminal.py -q`
  before the face exists: 8 failed, each on its own marker (`TIKI-DESIGN:`, `TIKI-CONCEPTS:`,
  `TIKI-FONT:`, `TIKI-PAIR-GAP:`, `TIKI-BOLD-PAIRS:`, `TIKI-ZERO-LIST:`, `TIKI-SUITE:`, `TIKI-LEAN-GEOMETRY:`), each message
  naming the missing file. A test that errors, or fails outside its one assertion, is not red for the
  expected reason: fix the test. `.venv/bin/python3 -m ruff check tests/` passes. Green after
  `face-config`. Then the eleven mutations (M1 to M8, M3b, M3c and M7b), each on the finished face, each restored and re-run green,
  each recorded in `references/testing.md` section 14 with the message seen:

  - **M1.** `examples/tiki-terminal/font.json`: delete the entry `"a|z": 0`. Must go red on
    `TIKI-PAIR-GAP:`, naming `a|z` at Bold with gap 0.0.
  - **M2.** The same file: `"r|r": -90` becomes `"r|r": -154`. Must go red on `TIKI-BOLD-PAIRS:`, naming
    `r|r` (14.6 measured at Bold).
  - **M3.** The same file: add `"n|n": 0` to `kerning.hand`. Must go red on `TIKI-ZERO-LIST:`, naming
    `n|n` under `not_found_under_17`.
  - **Picking the pairs for M3b and M3c.** Make the unsuppressed build once, in a scratch copy:
    `cp -R examples/tiki-terminal <scratch>/tiki-nozero` without its `out/`; in
    `<scratch>/tiki-nozero/font.json` set `kerning.hand` to `{"r|r": -90, "E|O": -60}` (the trial's 11
    word-space pairs stay as they are); run
    `.venv/bin/python3 scripts/build.py --font <scratch>/tiki-nozero/font.json`; then run
    `.venv/bin/python3 tests/pair_gap.py --font examples/tiki-terminal/font.json --woff2 <the woff2 that build wrote> --under U`
    for U = 20, 17, 15 and 12 (the `--font` gives the kern set the output is filtered to). Record each
    command and the chosen pair with its gap.
  - **M3b.** The weakest overgrowth: add a zero entry for the first pair in the `--under 20` list that is
    not in the `--under 17` list (a gap of 17 to 20 units). Must go red on `TIKI-ZERO-LIST:`, naming that
    pair under `not_found_under_17`.
  - **M3c.** The opposite direction: delete the zero entry of the first pair in the `--under 15` list that
    is not in the `--under 12` list (a gap of 12 to 15 units). Test 4 stays green on it by construction;
    the requirement is that `TIKI-ZERO-LIST:` goes red, naming that pair under
    `under_15_not_suppressed`.
  - **M4.** `"fs_type": 0` becomes `"fs_type": 4` in BOTH `examples/tiki-terminal/font.json` and
    `examples/tiki-terminal/requirements.json`, so `build.py`'s fsType self-check still agrees and the
    build succeeds. First confirm the build ran: `build.py` exits 0 and its fsType `SELF-CHECK` line
    reads `ok` with 4. Then the run must go red on `TIKI-DESIGN:` and on `TIKI-FONT:`, and the
    `TIKI-FONT:` message must show `OS/2.fsType` 4 read from the built woff2, not a `missing` or
    `build_failed` record. A `TIKI-FONT:` red that carries `build_failed` does not count: it proves the
    build refused, not that the test reads the font. (Plan-review advisory F005.)
  - **M5.** `examples/tiki-terminal/requirements.json`: remove `>` from `required_characters`. Must go
    red on `TIKI-DESIGN:`.
  - **M6.** `examples/tiki-terminal/concepts.js`: `wonkAmount: 0.158` becomes `wonkAmount: 0.045`. Must
    go red on `TIKI-CONCEPTS:`.
  - **M7.** `scripts/tests/test_font.py`: remove the `"tiki-terminal"` entry from
    `D_BOWL_BOUND_BY_FOLDER`. Must go red on `TIKI-SUITE:`, with the suite's own message naming the `d`
    bowl and the bound 1.
  - **M7b.** `scripts/tests/test_font.py`: change the default of the `.get` from 1 to 5, so every face
    gets the wider bound (the defect advisory F003 names). Run `scripts/tests/mutate.py`'s `xh-*`
    mutations on the neutral fixture with M7b in place. At least one must print GREEN where it printed
    RED without M7b; that run is the evidence that the default of 1 is observed. If every one still
    prints RED, no mutation sees a 1-to-5-unit bowl shift on the existing faces: record it in section 14
    and in the pull request as a finding about the tests, and do not count the per-face bound as guarded.
  - **M8.** `examples/tiki-terminal/font.json`: the masters `RegLean` and `BoldLean` change `"concept":
    "canelean"` to `"concept": "cane"`. `concepts.js` keeps `canelean` with its `wonk` and `wonkAmount`,
    and the axes, instance names and cmap are unchanged, so the built font has a `LEAN` axis that draws no
    lean. Must go red on `TIKI-LEAN-GEOMETRY:`, listing all ten wonk letters under `wonk_not_tipped` at
    both weights. `TIKI-DESIGN:` also goes red (it reads the master concepts), so run test 8 alone with
    `-k lean_axis_tips` and require it red by itself: that run is the evidence the geometry test sees the
    defect, not the configuration test. A second variant checks the control letters: set `wonk` of `canelean` in `concepts.js` to a string
    that adds `n`. `TIKI-CONCEPTS:` also goes red; the requirement is that `TIKI-LEAN-GEOMETRY:` also
    names `n` under `others_moved`, shown by the `-k lean_axis_tips` run.

  M4 also changes what the suite compares, so `TIKI-SUITE:` may go red with it; that is expected. A
  mutation that leaves its test green is a finding about the test: fix the test, and say so in section
  14 and in the pull request.
- **`face-sources`, agent.** `shasum -a 256 examples/tiki-terminal/concepts.js
  examples/tiki-terminal/skeletons.js examples/tiki-terminal/content.json` prints the three digests
  above. `ls examples/tiki-terminal` shows no `out` and no font file. Then
  `.venv/bin/python3 -m pytest tests/test_tiki_terminal.py -q -k lean_masters` passes (test 2 needs only
  this item). Test 8 needs the built font, so it first passes under `face-config`.
- **`suite-bowl-bound`, agent.** With `face-sources` in place and the bound still 1, build the neutral
  example (`.venv/bin/python3 scripts/build.py --font examples/neutral/font.json --static examples/neutral/out/static`)
  and run `.venv/bin/python3 -m pytest scripts/tests/test_font.py -q -p no:cacheprovider --font examples/neutral/font.json --requirements examples/neutral/requirements.json --static-dir examples/neutral/out/static -k xh_moves`:
  it fails naming `tiki-terminal` and the `d` bowl (the watched red of this change). After the edit the
  same command passes, and the whole suite reads `116 passed` on neutral and `95 passed, 5 skipped` on
  Driftwood (`--static-dir none`, after building it). Layer 4 then runs every `xh-*` mutation of
  `mutate.py` on the neutral fixture; each must still print RED, since neutral keeps the bound of 1. If
  one turns GREEN, the exception leaked to other faces: stop and report it. M7b (under `tiki-tests`)
  then shows whether those mutations can see the default at all.
- **`weight-count`, agent.** `.venv/bin/python3 -m pytest tests/test_weight_decisions.py -q -k "covers or no_branch"`:
  before the edit `covers` fails with "6 files, 264096 comparisons"; after it, it passes with the six
  `no_branch` cases.
- **`leg-taper-pinned`, agent.** With `face-sources` in place, before the edit
  `.venv/bin/python3 -m pytest tests/test_r_leg_join.py -q -k italic_leg_keeps` fails naming the five
  drawings of finding 4 and nothing else (the watched red of this change). After the edit it passes.
  Then the test's existing mutation is watched again: find the row of
  `test_the_italic_leg_keeps_its_join_taper` in `references/testing.md` section 8, apply the mutation it
  names to a copy of `scripts/gen.js` through `FONT_DESIGN_R_GEN` (the file's own mechanism, so the real
  generator is not edited), and require the test to go red on samples 23 or 26. If it stays green, the
  skip removed the test's sight of the taper: stop and report it. Report how many of the 650 samples the
  rule leaves out.
- **`face-config`, agent.** In order: `node scripts/export.js --font examples/tiki-terminal/font.json --group roman --requirements examples/tiki-terminal/requirements.json out/tiki-roman.json`
  exits 0; `.venv/bin/python3 scripts/build.py --font examples/tiki-terminal/font.json` exits 0 and
  every `SELF-CHECK` line reads `ok` (read the vertical-metrics, fsType and STAT lines against
  `requirements.json`); `.venv/bin/python3 scripts/build.py --font examples/tiki-terminal/font.json --check`
  prints `font identical, manifest identical`; `.venv/bin/python3 -m pytest tests/test_tiki_terminal.py -q`
  reads 8 passed; `.venv/bin/python3 scripts/fontbakery-gate.py --font examples/tiki-terminal/font.json --requirements examples/tiki-terminal/requirements.json`
  exits 0 with exactly the two accepted findings (exit 3 means FontBakery is missing: SKIPPED, NOT
  PASSED, and the item is not done); the body of `OFL.txt` from its first line of dashes hashes to
  `ebc10907…a02a`; `.venv/bin/python3 -m pytest tests/test_schemas_and_concepts.py tests/test_hygiene.py -q`
  passes; `git status --short` shows no font file.
- **`smoke-fourth-fixture`, agent.** `npm run lint:sh` (shellcheck is installed here) and
  `.venv/bin/python3 -m pytest tests/test_ci_workflow.py tests/test_genres.py -q` pass (both read
  `smoke.sh` or `ci.yml` as text). The run of the script itself is the last step of `docs-example`.
- **`docs-example`, agent.** `.venv/bin/python3 -m pytest tests/test_docs_commands.py tests/test_hygiene.py tests/test_versions_and_skill.py -q`
  passes. `grep -n "three fixtures" README.md SKILL.md CLAUDE.md scripts/smoke.sh .github/workflows/ci.yml references/variable-font-build.md`
  prints nothing. `grep -F "not dropamt and not optical_corrections and not unbracketed_serif and not open_curve_extremes and not unset_crotch" examples/tiki-terminal/README.md`
  prints the README's suite command (finding F001: this check left test 7, because the README is written
  here, after `face-config` requires the eight tests green). It is a text check on a document, not the
  authority on the expression; `SUITE_EXCLUSIONS` in the test is. Then, last and alone, layer 4: `bash scripts/smoke.sh --out out/smoke` in the
  background, waited for, exit 0, its last line "smoke: every step from 1 passed". Read in its log: step
  1 exports `tiki-terminal-roman.json`; step 2 builds `TikiTerminal-VF.woff2`; step 2b prints
  `0 of N renders changed` for `tiki-terminal`; step 4c passes the gate or says SKIPPED; step 5 prints
  RED for every mutation; step 7 passes with the new test file in it. Put the duration and the date in
  CLAUDE.md. The plan review's findings and this run's results go into `docs/plan-tiki-terminal.md`.

### Operator items

- **`spacing-review`, operator, post-build, live-acceptance of `face-config`.** It needs a person's eye
  and a browser. Build the face, write the specimen
  (`.venv/bin/python3 scripts/specimen.py --font examples/tiki-terminal/font.json --requirements examples/tiki-terminal/requirements.json --group roman --font-url /fonts/TikiTerminal-VF.woff2 out/tiki-review/specimen.html`,
  with the woff2 copied to `out/tiki-review/fonts/`), and shoot or open it. Judge, at 40 and 120 px, in
  Regular, Bold, Lean and Bold Lean:
  1. whether any pair still reads as touching, above all at Bold (pairs at 12 to 20 units remain);
  2. whether the suppressed pairs read as gaps (`az`, `rt`, `ty`, `Er`, `ST`, `LA`, `EO`, `rr`);
  3. the line height the 1010 / −293 extent gives;
  4. decisions 1 to 10 above where the operator's ruling differs.
  A ruling against decision 1 changes `kerning.hand`, `requirements.json` and the README, not the tests'
  floors unless the operator sets other floors.
  Limit of this item, stated (plan-review advisory F004, accepted as a limit, not fixed): the gap tests
  sample five locations (the four corners and the middle, 550/50), and this review reads the four
  corners. An overlap at another interior setting of `wght` and `LEAN` can ship unseen by either. The
  README's limits paragraph says so in the same words. If the specimen lets the axes be dragged, the
  operator may sweep them, but the item does not require it.
- **`ci-run`, operator, live-acceptance of `smoke-fourth-fixture`.** It needs GitHub credentials and
  runner minutes: `gh workflow run ci.yml --ref feature/tiki-terminal-example`, then the four `test`
  jobs and the lint job green. The reason to ask: every figure in this plan is from one Mac; the gap
  tests read outlines that differ between platforms and node versions; a pair that reads 16.1 here could
  read under 12 only if a platform moved it by more than 4 units, which nothing has measured. If a job
  fails `TIKI-PAIR-GAP:`, add the pairs it names to the zero list and rerun. If a job fails
  `TIKI-ZERO-LIST:`, a platform moved a pair by more than the 1-unit band: report the pairs and their
  gaps on both machines rather than widening the band. The merge and any issue
  filing for the five follow-ups are the operator's.

## As built

What the plan review changed, and what the build found. Figures are from 2026-11-25 on one Mac (node 26.13.1).

### Plan review

- **First review.** The medium advisories F002 (test 6 at 16 units with exact equality), F003 (a per-face bowl bound in place of a shared one) and F005 (M4 run so the build succeeds) were adopted. F006 became the wording of the opening paragraph. F004 (the gap tests see five locations only) is a stated limit in `spacing-review` and in the README, not a fix.
- **Second review and the operator's ruling.** The escalated question on test 6 was ruled as a 1-unit band: every suppressed pair measures under 17 units unsuppressed, and every pair under 15 units is suppressed. It is not exact equality at 16, and not the reviewer's 12 and 20. F001 (the README check moved from test 7 to `docs-example`), F002 (`face()` gives distinct records), F003 (the M3b and M3c commands), F004 (gap-test wording), F006 and F007 (CHANGELOG wording) were adopted.

### What the build found

- **All eleven mutations ran on the finished face** and each went red on the test named for it (`references/testing.md` section 14 has the table). Three findings about the tests came out of them. M7b: all 14 `xh-*` mutations of `mutate.py` stay RED with the bowl bound's default raised to 5, so the default of 1 is not guarded. M8b: an added `n` in `wonk` turns the geometry test red because the wonk-letter set changes, not because `n` is reported under `others_moved`. M7: `TIKI-SUITE:` carries the summary line, not the name of the failing suite test.
- **Test 8's thresholds.** `MIN_TIP` and `MIN_SPREAD` are 20 units each, set from the first build.
- **The number of tests.** The repository has 806 tests in 33 files (`pytest --co -q`), up from 783 in 32.
- **Figures confirmed from the built face:** 140 glyphs, 137 cmap entries, 4,660 kern pairs, 78,020 bytes as woff2, minimum strokes 78.78 and 118.18 units against floors 78 and 118, worst decimated fold 4.13 units.
- **The README's suite command** carries the same `-k` expression as `SUITE_EXCLUSIONS` in `tests/test_tiki_terminal.py` (checked with `grep -F`).

### Not built, left to the operator

`spacing-review` (a person reads the built face at 40 and 120 px in the four instances) and `ci-run` (CI by hand on the branch). The follow-ups under "Findings outside this change" are not filed.

### The smoke run

`bash scripts/smoke.sh --out out/smoke` (steps 1 to 7, no `--full`), run last and alone on 2026-11-26 UTC: exit 0 and the last line "smoke: every step from 1 passed", 46 min 35 s from launch (04:24:12Z) to the log's last line (05:10:47Z). Step 1 exported the four fixtures, step 2 built `TikiTerminal-VF.woff2` (78,020 bytes), step 2b printed `diff.py: 0 of 56 renders changed` for `tiki-terminal`, step 4c passed the FontBakery gate with 0 unaccepted and 2 accepted findings (`case_mapping`, `valid_glyphnames`), step 5 ran 126 mutations and all 126 were RED, and step 7 (layer 2) read 799 passed, 7 skipped in 30 min 51 s, with `tests/test_tiki_terminal.py` in it. The `--full` Chrome steps and layer 5 (CI by hand, `ci-run`) were not run.
