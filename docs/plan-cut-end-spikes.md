# Plan: a `cut` end pins the edge samples its corner moved past (0.11.0), as built

WHAT IT'S FOR: `scripts/gen.js` draws a `cut` end by moving the last point of each edge onto the cut line and
leaving the edge samples before it where they were. On the edge whose corner moves back, those samples stand
past the cut line, so the outline runs out to the old end and returns: a spike. This plan removes the spike,
holds the change to the samples the cut reaches, and releases it as 0.11.0.

Every path in this file is relative to the repository root. Every figure was measured on 2026-11-24 and 2026-11-25 on this
machine (node 26.13.1) with prototype copies of `scripts/` outside the repository; none of the prototype
files is kept. "0.10.0" means `scripts/gen.js` at commit `d9974f3`, the last commit that changed it.

## Summary of what was found

1. **The defect is larger than a spike on a concept page: a face with `cut` stem ends cannot be built.**
   `scripts/export.js` counts a spike as a folded edge, and `scripts/build.py` refuses a master with one. A copy
   of `examples/neutral` with `s: "serif"` changed to `s: "cut"` and `cut: 32 * DEG` exports with 101, 102, 101
   and 102 folded edges in the four roman masters and 77 and 77 in the two italic ones, and `build.py` exits 1
   with `SELF-CHECK FAILED: TextRegular: 101 stroke edge(s) fold back`. With the fix it exports 0 folded edges
   in all six masters and builds in 9 seconds.
2. **The one line the request names removes every spike, and also moves points the cut never reached.**
   `clipPast(Lp, k, sg, T, Dv); clipPast(Rp, k, sg, T, Dv);` pins every sample past the infinite cut line for
   up to 80 steps. On a straight stem that is the spike. On a curved terminal the body of the stroke itself
   lies past that line, so the call replaces up to 80 samples of the inner edge by one straight chord. It also
   runs on an end that `cutSide` declined to cut (an end within 14.5 degrees of the cut direction), where the
   sign of a cross product near zero picks the side.
3. **This plan bounds the pin by how far the corner moved.** The walk stops at the first sample that lies
   farther from the uncut corner, measured along the edge, than the corner moved. On the Cane concept the
   bounded call and the unbounded line draw the same outlines (identical in the roman at mult 1, 1.5 and 1.65;
   the italic `K` differs by 0.2 units at 1.5 and 1.2 at 1.65). On `grot` they differ by up to 66.2 units
   (`r` at mult 1.65).

Measured over 11,616 edges of `cut` ends (the Cane concept of the request plus the six shipped concepts that
map an end to `cut`, roman and italic, mult 1, 1.3, 1.5, 1.65):

| Generator | Edges with a spike over 0.05 units | Edges with a sample moved beyond the cut's reach | Of those, ends the cut did not move |
|---|---|---|---|
| 0.10.0 | 4,748 (worst 126.26, `grot` `t` at mult 1.65) | 0 | 0 |
| the request's one line, unbounded | 0 | 1,176 | 106 |
| this plan, bounded | 0 | 0 | 0 |

The two measures are defined under "New automated tests".

## Decisions the operator can overrule

Each is a `design-acceptance` check (see Work items). The plan proceeds on the stated choice.

- **Bounded, not the literal line.** Reason: finding 2. What the bounded clip leaves: on a curved terminal the
  cut corner stands off the curved edge, because `cutSide` moves it along the end tangent, so a small step
  remains where the edge meets the corner. The unbounded line hides that step under a chord. In prototype
  renders of `grot`, read by the planner alone, the chord looks cleaner on `c s e a` at mult 1 and fills the
  counter of `r f t 9 J 6` at mult 1.5 and above (measured: the outline moves by 57.5 units on `r` and 62.9 on
  `f` at 1.5). If the operator prefers the unbounded clip, the change is the one
  edit named as watch W2 under Verification, and the test `CUT-REACH` and `CUT-SCOPE` are then removed, not
  loosened.
- **Spacing follows the clipped outline.** The spike points were read by the spacing profile. No `prof` is
  kept for a `cut` end, so advances and kerns of a concept with `cut` ends move. Reason: no font this
  repository builds has a `cut` end, the 0.10.0 freeze existed to protect shipped faces, and the old values
  measured ink that was not there. Measured moves: Cane roman up to -11.73 units (`I` at mult 1.65), 210 of
  524 glyph draws; Cane italic up to -8.89 (`y` at 1.5); `windswept` up to -3.16; `field` and `brush` roman up
  to -3.43; `grot` and `geometric` roman up to -2.45. Three larger moves, all in italic drawings of unshipped
  concepts: the `T` of `field` and `brush` loses 56.3 to 91.47 units, the apostrophe of `field` and `brush`
  loses 63.15 at mult 1, and the apostrophe of `geometric` gains 145.85 to 210.63. The last one is a repair:
  in 0.10.0 that glyph's ink ran from x -83 to 96 against an advance of 55.1, and now from 11 to 190 against
  201.0.
- **The 80-step limit of `clipPast` stays.** The longest run the bounded call pins on any measured edge is 65
  samples, so no test here can see the limit. A face whose run is longer keeps the far end of its spike, and
  `CUT-SPIKE` reports it.

## Findings outside this change

Not fixed here. Each deserves an issue.

- `references/generator.md` section 4 says only `id`, `W` and `ends` are required. A concept without `pow`,
  `xs`, `track` and `dot` draws non-finite coordinates (the Cane concept as the request states it: `l n L i o`
  non-finite, `R` throws). The fixture below sets them.
- The italic apostrophe's advance is read from the few points that dip below the x-height band, so it jumps
  between multipliers (`field` italic: 81.4 at mult 1 and 33.0 at 1.5 in 0.10.0). This change moves the
  numbers and does not cause the fragility.
- No concept in the repository maps the hidden-join end `""` to `cut`. With `joints` on, such an end takes
  the cut and then the corner or joint cut. The clip now runs between the two. Not measured.
- `CHANGELOG.md`, `## Releases`, has no row for v0.10.0, though the tag exists (`git rev-list -n1 v0.10.0`
  prints `1b3c2c7`). The `version-bump` item adds it.
- In a fresh worktree 15 repository tests fail on "the neutral example is not built" until
  `.venv/bin/python3 scripts/build.py --font examples/neutral/font.json --static examples/neutral/out/static`
  has run (6 in `tests/test_fallback_metrics.py`, 7 in `tests/test_site_wiring_template.py`, 1 each in
  `tests/test_mutate_harness.py` and `tests/test_tools_and_templates.py`).

## Code to be changed

### `scripts/gen.js`

Three edits. Line numbers are those of commit `d9974f3`.

1. **`clipPast` (line 671) takes an optional sixth argument `X0`, the corner before the cut moved it.** Without
   it the function is the 0.10.0 one, statement for statement, so the corner branch (line 905), the joint and
   leaning-serif branch (line 913) and `teeCut` (line 747) draw what they drew. Replace the function by:

   ```js
   /* clipPast: after an end's corner arr[k] was moved onto a cut line, pins to that corner the edge samples before it that lie past
      the line (the line through the corner along Dv, on the side the outward tangent T points to). WHAT IT'S FOR: the corner moves
      back along the edge, and the samples it passed would otherwise stay beyond the cut, so the outline would run out to the old end
      and return as a spike. The count of points is unchanged, so masters stay compatible. The walk skips a sample that is not past
      the line during its first seven steps, stops at the first such sample after them, and takes 80 steps at most.
      X0, when given, is the corner before the cut moved it (a `cut` end): the walk also stops at the first sample farther from X0,
      measured along the edge, than the corner moved. A `cut` moves its corner by the stroke width at most (cutSide's clamp), and on
      a curved terminal the body of the stroke lies past the infinite cut line, so an unbounded walk replaced up to 80 samples of the
      inner edge by one chord (r, f, t, 9 of a sans concept at mult 1.5). An end the cut did not move has a reach of 0 and keeps
      every point. Returns how many samples it pinned. */
   function clipPast(arr, k, sg, T, Dv, X0) {
     var C = arr[k], ref = Dv[0] * T[1] - Dv[1] * T[0], pinned = 0, reach = X0 ? dist(X0, C) + 1e-6 : Infinity, along = 0, prev = X0;
     for (var j = k - sg, steps = 0; j >= 0 && j < arr.length && steps < 80; j -= sg, steps++) {
       var q = arr[j], side = Dv[0] * (q[1] - C[1]) - Dv[1] * (q[0] - C[0]);
       if (X0) { along += dist(prev, q); prev = q; if (along > reach) break; }
       if (side * ref > 1e-6) { arr[j] = [C[0], C[1]]; pinned++; } else if (steps > 6) break;
     }
     return pinned;
   }
   ```

   `dist` is the helper at line 443.

2. **The `cut` branch of `cutEnds` (lines 885 to 888) keeps the two uncut corners and calls `clipPast` with
   them.** Replace the branch by:

   ```js
       if (mode === "cut") {
         var Dv = [Math.cos(P.cut), Math.sin(P.cut)], Lu = Lp[k], Ru = Rp[k];
         Lp[k] = cutSide(Lp[k], T, pts[k], Dv, Ws[k]); Rp[k] = cutSide(Rp[k], T, pts[k], Dv, Ws[k]);
         // the samples each corner moved past are pinned to it (0.11.0): they stood beyond the cut and drew a spike. The same in the
         // `legacy` pass, so the spacing profile of a cut end follows the outline (references/generator.md, section 8)
         clipPast(Lp, k, sg, T, Dv, Lu); clipPast(Rp, k, sg, T, Dv, Ru);
       }
   ```

   The call is not conditioned on `legacy`, and `cutEnds` does not set `differs` for it: a `cut` end carries no
   `prof`. The branch record (`sig`) is unchanged; measured, no record differs in 36,156 glyph draws.

3. **The header's ORIGIN list gains item 11** after item 10 (line 39): "Cut ends (0.11.0). A `cut` end pins the
   edge samples its corner moved past, bounded by how far the corner moved; before, they stood beyond the cut
   as a spike, and export.js counted each as a folded edge, so a face with cut stem ends did not build.
   Spacing follows the clipped outline." The comment above `cutEnds` (lines 877 to 879) gains one sentence:
   a `cut` end is clipped in both passes.

The prototype of exactly these two code edits is what produced the "this plan, bounded" row above.

### Version carriers

`VERSION` (`0.11.0`), `package.json` (`"version": "0.11.0"`), `SKILL.md` (frontmatter `version: 0.11.0` and the
line `**Version 0.11.0**`), `README.md` (the badge, `version-0.11.0-blue`).
`tests/test_versions_and_skill.py::test_version_is_the_same_everywhere` holds the four to `VERSION`.

## Code to be written

No new shipped code. The new files are tests (next section).

## New automated tests

Three new files. `FONT_DESIGN_CUT_SCRIPTS` names another copy of the whole `scripts/` folder, with a copy of
`VERSION` beside it, for the watches; unset, the real folder. Every assertion is in Python; the node script
only measures. Nothing is computed from the generator's formulas except the cut direction, which is the
concept's own `cut` value (an input).

### `tests/cut_end_probe.js` (written by `tests-cut-spike`, used by both test files)

`node tests/cut_end_probe.js MODE SCRIPTS_DIR SPEC_JSON`. It follows `tests/joint_probe.js`: the same rules for
reading a body polygon and its two edge runs (`L(j)`, `R(j)`), a header that defines every figure, a non-zero
exit on a glyph that throws or a coordinate that is not finite, never a skip. The Python side starts one node
process per concept (`spec.only`), side by side in a thread pool: a process that loads many generators runs
out of heap, because node keeps every required module alive (the prototype failed at 4 GB with five concept
files in one process).

SPEC: `files` (concept files), `inline` (concept objects, for the Cane concept), `only` (one concept id),
`mults`, `styles` (`roman`, `italic` at 10 degrees and only when the concept maps `x`), and for `glyphs` mode
`old` (the path of another `gen.js`).

**Mode `ends`.** One row per EDGE (`L`, `R`) of every stroke end whose branch record reads `A=cut` or `B=cut`
and whose `ends=` outcome is still `cut`, for every concept that maps an end to `cut`.

- The **uncut stroke** is the same concept drawn by the same generator with every `cut` end mode replaced by
  `butt`. The two modes share every width rule, so the two bodies have the same point count (the probe throws
  if not) and differ only in what the cut moved.
- Both drawings are brought into one frame: `glyph()` shifts a glyph by its sidebearing, so the x shift is the
  median over the body's points of `x_cut - x_uncut`.
- `reach`: the distance from the edge's end corner in the cut drawing to the same corner in the uncut drawing.
  0 means the cut did not move the corner.
- `inReach`: walking back from the end, how many samples stood within `reach + 1e-6` of the uncut corner,
  measured along the uncut edge (the sum of the steps between consecutive uncut samples), before the first
  that did not. The walk stops at the middle of the stroke.
- `spike` and `run`: over those samples, in the cut drawing, skipping the leading samples equal to the corner:
  the run of consecutive samples that lie more than 1e-6 past the cut line, and the largest such distance.
  The cut line passes through the edge's cut corner along `[cos cut, sin cut]`; "past" is the side the stroke's
  outward direction points to, read from the uncut drawing's centre line (from the midpoint of the two edges 4
  samples in to the midpoint at the end). The run ends at the first sample that is not past the line. In
  words: having reached the cut corner, does the outline continue beyond the cut.
- `beyond` and `beyondMax`: from the first sample outside the reach to the middle of the stroke, how many
  samples differ from the uncut drawing by more than 1e-6, and the largest difference.

Row: `file`, `concept`, `style`, `mult`, `key`, `stroke`, `end`, `edge`, `n`, `reach`, `inReach`, `spike`,
`run`, `beyond`, `beyondMax`.

**Mode `glyphs`.** One row per drawn glyph of every concept of `spec.files` and `spec.inline`, cut end or not:
`same` (polygons, advance and both spacing profiles equal those of the generator at `spec.old`, exactly) and
`movedCut` (the glyph has an edge with `reach > 1e-6`, measured as above with the generator under test).

### `tests/test_cut_ends.py` (item `tests-cut-spike`, proof: red-green)

Module docstring in the form of `tests/test_serif_joints.py`: what the defect was, how the measure works, the
markers, the environment variable. `TOL = 0.05` units. The Cane concept is a Python dict passed as
`spec.inline`: the request's values (`W` 114, `nib` 0, `thin` 0.85, `swell` 0.35, `wob` 0.015,
`ends` `{s: cut, t: butt, u: butt, "": disk, x: exit}`, `cut` 32 degrees in radians, `joints` true, `crotch`
0.3, `xh` 550) plus `pow` 1, `xs` 1, `track` 0, `dot` 0.55 and `overshoot` 10, which the request does not state
and without which the concept draws non-finite coordinates. A comment says so. `MULTS = [1, 1.3, 1.5, 1.65]`.

| Test | Level | Setup assertions (pass on 0.10.0) | First assertion about the new behaviour | Fails on 0.10.0 with |
|---|---|---|---|---|
| `test_no_cut_end_keeps_a_sample_past_its_cut_line_on_the_cane_concept` | one module: `glyph()` of `gen.js` | the probe exits 0; at least 1,800 rows (measured 1,912); at least 1,800 with `reach > 1e-6` (1,884); each of `l n L i` has a roman row at mult 1.5 with `reach > 30` (62.8 to 63.7) | no row has `spike > TOL`; message starts `CUT-SPIKE:` and gives the count, the total and the three worst rows | `CUT-SPIKE:` 931 of 1,912 edges, worst 95.68 |
| `test_no_cut_end_keeps_a_sample_past_its_cut_line_in_any_shipped_concept` | one module, every shipped concept with a `cut` end | the (file, concept) pairs are found by reading the five concept files for a `cut` mode, and they include `bract/concepts.js field`, `driftwood/concepts.js windswept`, `templates/concepts.example.js grot` and `brush`, `templates/concepts.genres.js grot` and `geometric`; each pair has at least 1,000 rows with `reach > 1e-6` (1,144 to 1,644); at least 9,000 rows in all (9,704) | no row has `spike > TOL`; message starts `CUT-SPIKE-SHIPPED:` | `CUT-SPIKE-SHIPPED:` 3,817 of 9,704 edges, worst 126.26 |
| `test_a_face_with_cut_stem_ends_exports_without_a_folded_edge` | two modules: `gen.js` into `export.js` (the exporter's own fold measure, master compatibility, decimation) | the face folder is made (below); `node export.js --font ... --group roman` and `--group italic` exit 0; 4 and 2 masters; every master has at least 50 glyphs whose record holds an end drawn `cut` (70 roman, 61 italic) | `foldedEdges == 0` in every master; message starts `CUT-EXPORT-FOLD:` and names each master with its count and `worstFoldAt` | `CUT-EXPORT-FOLD:` 101, 102, 101, 102, 77, 77 |
| `test_a_face_with_cut_stem_ends_builds` | the whole tool: `concepts.js` to `export.js` to `build.py` to the woff2 files, with the builder's self-checks | the face folder is made; `build.py` was started (a `returncode` exists) | `returncode == 0`; message starts `CUT-FACE-BUILD:` and carries the last 2,000 characters of stderr. Then: both woff2 files and `manifest.json` exist | `CUT-FACE-BUILD:` exit 1, `SELF-CHECK FAILED: TextRegular: 101 stroke edge(s) fold back` |

Each marker appears in exactly one assertion of the file. The expected failure text for the red gate is the
marker with its colon: `CUT-SPIKE:`, `CUT-SPIKE-SHIPPED:`, `CUT-EXPORT-FOLD:`, `CUT-FACE-BUILD:`. With the
colon, `CUT-SPIKE:` is not a substring of `CUT-SPIKE-SHIPPED:`, so each of the four texts identifies one
assertion. No message of the first test may contain the word `SHIPPED`.

**The face folder** (both face tests, `build_face(dest)` in the form of `tests/test_head_sink.py::build_face`):
copy `font.json`, `concepts.js` and `requirements.json` from `examples/neutral` into `tmp_path`; in
`concepts.js` replace the anchor `ends: { s: "serif", t: "flare", u: "flare", "": "disk", x: "exit" },`, which
must occur exactly twice (asserted), by
`ends: { s: "cut", t: "flare", u: "flare", "": "disk", x: "exit" }, cut: 32 * DEG,`. The build command is
`build.py --font <dest>/font.json --requirements <dest>/requirements.json --keep-masters <dest>/keep/export.json`.

Why no test was added to the font suite (`scripts/tests/test_font.py`): none of the three fixtures draws a
`cut` end, so a suite test would measure nothing on them, and `build.py`'s fold self-check already refuses a
face with a spike, which `CUT-FACE-BUILD` now holds from the outside.

### `tests/test_cut_reach.py` (item `tests-cut-reach`, proof: mutation)

Both tests pin behaviour 0.10.0 already has (a cut moves two corners and nothing else), so they pass when
written. They are what separates this plan's bounded clip from the unbounded line.

| Test | Level | Coverage assertions | The assertion |
|---|---|---|---|
| `test_a_cut_moves_no_sample_beyond_its_own_reach` | across functions: the `cut` and the `butt` drawing of one stroke, through `params()`, `strokePolys()` and `cutEnds()` | the `ends` rows of the Cane concept and of the six shipped pairs, four multipliers: at least 11,000 rows (11,616); at least 1,500 with `reach <= 1e-6` (1,844), so ends the cut does not move are measured | no row has `beyond > 0`; message starts `CUT-REACH:` and gives the count, how many of them have `reach <= 1e-6`, and the three worst by `beyondMax` |
| `test_only_glyphs_with_a_moved_cut_end_changed_since_0_10_0` | the whole generator against the previous release: every concept of the five concept files and the Cane concept, roman and italic, mult 1 and 1.65, `glyphs` mode with `old` = `git show d9974f3:scripts/gen.js` written to `tmp_path` | at least 60 concept and style runs (69); at least 15,000 glyph draws; at least 50 runs in which every glyph is `same` (56 after the fix, 69 before) | no row has `same` false and `movedCut` false; message starts `CUT-SCOPE:` and names up to ten (concept, style, mult, key) |

`GEN_0_10_0 = "d9974f3"` is a constant with the comment "the last commit that changed scripts/gen.js before
0.11.0". The scope test needs a git checkout, as `tests/test_serif_joints.py` does, and fails (not skips) when
`git show` fails. It also holds the three callers of `clipPast` this change does not mean to touch: a corner,
a joint or a T-join that drew differently would be a glyph that changed without a moved cut end.

## Automated tests to be changed

- `tests/test_genres.py`: `RECORD` points at `docs/reviews/genres-2026-11-25.md`; the docstring of
  `test_the_review_record_holds_the_verdicts_the_table_states`, the docstring of
  `test_a_verdict_is_stale_when_the_recipe_outlines_change` ("on 2026-11-22") and the path in its "no digests
  are recorded" message follow. No assertion changes. This is the only existing test the generator change
  turns red: `test_a_verdict_is_stale_when_the_recipe_outlines_change` fails with "the genre verdict for grot
  is stale". Measured: of the ten recipe digests, `grot` and `geometric` change and the other eight do not.
- Nothing else, by two runs on a clone outside the repository. (1) All of layer 2,
  `.venv/bin/python3 -m pytest -q`, on an earlier form of the bounded clip (the walk bounded by straight-line
  distance): 16 failed, 707 passed, 30 skipped in 1,410.83 s. The 16 are the stale verdict and the 15 "neutral
  example is not built" failures listed under "Findings outside this change". (2) With the neutral example
  built and `scripts/gen.js` exactly as this plan writes it, the twelve files that read the generator or
  failed in run 1 (`tests/test_fallback_metrics.py`, `test_site_wiring_template.py`, `test_mutate_harness.py`,
  `test_tools_and_templates.py`, `test_genres.py`, `test_backward_compat.py`, `test_serif_joints.py`,
  `test_joint_spacing.py`, `test_head_sink.py`, `test_r_leg_join.py`, `test_weight_decisions.py`,
  `test_schemas_and_concepts.py`): 1 failed, 177 passed in 775.52 s, the one failure being the stale verdict.
  `tests/test_backward_compat.py` passed in both runs, so the three examples build to the recorded digests and
  `tests/fixtures/baseline.json` and `BASELINE_REV` do not move. The other sixteen test files were not run on
  the final form; the implementer runs all of layer 2 on it.
- `scripts/tests/mutate.py`: no change. No mutation's target text is in the lines this change edits
  (`grep -n 'clipPast\|cutSide' scripts/tests/mutate.py` prints nothing).

## Documentation to be updated

- `CHANGELOG.md`: a `## [0.11.0]` entry above 0.10.0. First line:
  `Font output: changes: every glyph with a cut end whose corner the cut moves is redrawn, and the advances and
  kerns of those glyphs move with it. No concept that the three examples build has a cut end, so every example
  rebuilds to the recorded digests (tests/test_backward_compat.py).` Under **Fixed**: the spike, with the
  figures of this plan (4,748 of 11,616 edges, worst 126.26; the unbuildable face, 101 folded edges). Under
  **Changed**: spacing follows the clipped outline, with the measured moves and the three large italic ones;
  the genre verdicts for `grot` and `geometric` were re-read. Under **Looked at and not changed**: the
  unbounded clip (finding 2 with its figures), the step where a curved terminal meets its cut corner, the
  80-step limit. In `## Releases`: add `| v0.10.0 | 1b3c2c7 | merge of PR #25 |` and
  `| v0.11.0 | the merge commit of the release branch | tagged after the merge |`.
- `references/generator.md`:
  - section 5, the `cut` row: since 0.11.0 the samples each corner moved past are pinned to the corner,
    bounded by how far the corner moved along the edge; an end within 14.5 degrees of the cut direction is not
    cut and is the butt end. The exact guarantee, in these words or closer: "walking back from a cut corner,
    the run of samples that stood within the corner's displacement of the uncut end and lie past the cut line
    is pinned to the corner. It is not a guarantee that no point of the stroke lies past the infinite cut
    line: on a curled terminal the body does. On a curved terminal the corner stands off the curved edge, so a
    step remains."
  - section 8: a paragraph "Cut ends (0.11.0)": no `prof`; the clip runs in the `legacy` pass too; the
    measured advance moves; the sentence "for every glyph except `G` and the italic `r` ... the values 0.9.0
    computes" gains "in a concept with no `cut` end".
  - section 12, the sentence that lists what reads drawn coordinates and is not in the record: `clipPast` is
    already there; add that the number of samples a cut pins is a width and differs between weights, like the
    fold pin's reach.
  - section 4: no change to the table. Do not fix the "Required" sentence here (a finding above).
- `references/genres.md`: section 6, "Status of the review", gains the 0.11.0 re-read and names the new
  record; section 7 gains an entry "A `cut` end drew a spike at its corner: fixed in 0.11.0" with the two
  recipes it showed on (`grot` and `geometric`: 280 of the 856 edges of `cut` ends in each roman, over four
  multipliers) and the test names; the table rows
  of `grot` and `geometric` take the new verdict date.
- `templates/concepts.genres.js` and `scripts/concepts/content.genres.json`: the `desc` and the `risk` of
  `grot` and `geometric` take the same verdict word, date and text as the table (`tests/test_genres.py` holds
  the three in step). No drawing parameter changes.
- `docs/reviews/genres-2026-11-25.md`: the new review record (item `genre-review-record`).
- `references/traps.md`: row 44 under a line "One more, met in 0.11.0": symptom (a thin spike at one corner of
  every cut stem end; `build.py` refuses the face for folded edges), cause (the corner moved, the samples
  before it did not), guard (`CUT-SPIKE`, `CUT-FACE-BUILD`), where.
- `references/testing.md`: section 12, "The cut-end guards (0.11.0)", in the form of section 11: the table of
  tests and markers, the watches with the figure each fired on as run, the mutation proof of
  `tests/test_cut_reach.py`, the layers run with their times. Add the section to the table of contents at the
  top of the file (`tests/test_versions_and_skill.py::test_long_reference_files_carry_a_table_of_contents`).
- `docs/plan-cut-end-spikes.md`: this plan as released, with an "As built" paragraph for every departure.
  Repository-relative paths only (`tests/test_hygiene.py`).
- `CLAUDE.md`: the test count and date of layer 2, from `.venv/bin/python3 -m pytest --co -q` (753 tests in 28
  files today; six tests and two files more after this change), and any layer time measured.
- `SKILL.md`, `README.md`: the version only. Neither describes the `cut` end.

## Work items

| id | title | kind | files | verifiable_by |
|---|---|---|---|---|
| `tests-cut-spike` | Write the probe and the four tests that fail on 0.10.0 because a cut end keeps edge samples past its cut line. | test-new | tests/cut_end_probe.js, tests/test_cut_ends.py | agent |
| `tests-cut-reach` | Write the two tests that hold a cut to its own reach and the change to glyphs with a moved cut end. | test-new | tests/test_cut_reach.py | agent |
| `gen-cut-clip` | Pin the edge samples a cut corner moved past, bounded by how far the corner moved. | code-change | scripts/gen.js | agent |
| `version-bump` | Bump the version to 0.11.0 and write the changelog entry with its font-output line. | code-change | VERSION, package.json, SKILL.md, README.md, CHANGELOG.md | agent |
| `genre-review-record` | Re-read the cut terminals of the grot and geometric recipes and write the new review record with the digests for node 20, 22 and 26. | doc-change | docs/reviews/genres-2026-11-25.md, references/genres.md, templates/concepts.genres.js, scripts/concepts/content.genres.json, tests/test_genres.py | agent |
| `docs-generator-testing` | Update the generator reference, the traps list, the testing log, the released plan and the test count, then run the full smoke check last. | doc-change | references/generator.md, references/traps.md, references/testing.md, docs/plan-cut-end-spikes.md, CLAUDE.md | agent |
| `design-acceptance` | The operator looks at the cut ends as drawn on the genres page and rules on the bounded clip and on spacing that follows it. | live-acceptance | | operator |
| `genre-review-acceptance` | The operator rules on the re-read verdicts of grot and geometric in the review record. | live-acceptance | | operator |
| `release-acceptance` | The operator runs CI by hand on the branch, merges, and tags v0.11.0. | live-acceptance | | operator |

Order: `tests-cut-spike` (it writes the probe), `tests-cut-reach`, `gen-cut-clip`, `version-bump`,
`genre-review-record` (it needs the final generator, and it writes every byte of the record that the tests
read, digests included), `docs-generator-testing`, whose verification ends with the full smoke run on those
final bytes. The operator items follow the full run.

## Verification

Layers are those of `CLAUDE.md`. The change touches what draws a glyph, so layer 4 applies, and it is a
release, so `--full`, then layer 5. Before any layer in a fresh worktree, build the neutral example:
`.venv/bin/python3 scripts/build.py --font examples/neutral/font.json --static examples/neutral/out/static`.
Every pytest command below takes `-p no:cacheprovider`.

### Per work item

- **`tests-cut-spike`, agent, proof: red-green.** `.venv/bin/python3 -m pytest tests/test_cut_ends.py -q` on
  the unmodified generator: four failed, each on its own marker, with figures near those in the table
  (931 of 1,912; 3,817 of 9,704; 101, 102, 101, 102, 77, 77; exit 1). A test that fails on a setup assertion,
  on a probe crash or on a count below its floor is not red for the expected reason: fix the test.
  `ruff check tests/` and `npm run lint:js` pass. Green after `gen-cut-clip`.
- **`tests-cut-reach`, agent, proof: mutation.** Both tests pass when written, on the unmodified generator.
  The mutation is the request's unbounded line. Recipe, on the tree before `gen-cut-clip`:
  - File: `scripts/gen.js`. `mutation_files`: `scripts/gen.js` only.
  - Find the one line whose text, after its indentation, is
    `Lp[k] = cutSide(Lp[k], T, pts[k], Dv, Ws[k]); Rp[k] = cutSide(Rp[k], T, pts[k], Dv, Ws[k]);`
    (line 887; the text occurs once in the file, and the lines at 904 and 912 differ from it).
  - Insert directly after it one new line, indented by six spaces:
    `clipPast(Lp, k, sg, T, Dv); clipPast(Rp, k, sg, T, Dv);`
  - No rebuild or restamp: the tests run node on the file.
  - Run `.venv/bin/python3 -m pytest tests/test_cut_reach.py -q`. Both tests must fail on their assertions:
    `CUT-REACH:` (measured: 1,176 of 11,616 edges, 106 of them with a reach of 0) and `CUT-SCOPE:` (measured on
    `templates/concepts.genres.js` alone at mult 1 and 1.65: 14 glyph draws, the `j` and `y` of `grot` and
    `geometric`, whose only `cut` end the cut does not move).
  - Restore `scripts/gen.js` by digest. Both tests pass again.
- **`gen-cut-clip`, agent.** `tests/test_cut_ends.py` and `tests/test_cut_reach.py` green (six tests).
  `tests/test_backward_compat.py`, `tests/test_serif_joints.py`, `tests/test_joint_spacing.py`,
  `tests/test_head_sink.py`, `tests/test_r_leg_join.py`, `tests/test_weight_decisions.py` green, unchanged.
  `tests/test_genres.py::test_a_verdict_is_stale_when_the_recipe_outlines_change` red for `grot` until
  `genre-review-record` lands; that is the one expected red. Watches, each one exact replacement that matches
  once, applied to a copy of `scripts/` outside the repository with a copy of `VERSION` beside it, the test
  files run with `FONT_DESIGN_CUT_SCRIPTS` on the copy, the real file checked by `shasum -a 256` after. Log
  each in `references/testing.md` section 12 with the figure it fired on. A watch that stays green is a
  finding about the test: say so in the log and the pull request, and strengthen the test.
  - W1, the fix removed: delete the line `clipPast(Lp, k, sg, T, Dv, Lu); clipPast(Rp, k, sg, T, Dv, Ru);`.
    Expected red: all four of `tests/test_cut_ends.py`.
  - W2, the unbounded line: that line to `clipPast(Lp, k, sg, T, Dv); clipPast(Rp, k, sg, T, Dv);`. Expected:
    `CUT-REACH` and `CUT-SCOPE` red, the four spike tests green (prototype: 0 spiked, 1,176 beyond reach).
  - W3, one edge only: that line to `clipPast(Lp, k, sg, T, Dv, Lu);`. Expected `CUT-SPIKE` red (prototype:
    2,461 of 11,616 edges spiked).
  - W4, the weakest clip, one step: `if (along > reach) break;` to `if (along > reach || steps > 0) break;`.
    Expected `CUT-SPIKE` red (prototype: 4,620 edges).
  - W5, reach as a straight line: `along += dist(prev, q); prev = q;` to `along = dist(X0, q);`. Expected
    `CUT-REACH` red (prototype: 750 edges).
- **`version-bump`, agent.** `tests/test_versions_and_skill.py`, `tests/test_docs_commands.py`,
  `tests/test_hygiene.py` green. The `Font output:` line is the one quoted above.
- **`genre-review-record`, agent.** Steps: build the page and shoot it with the commands of
  `references/genres.md` section 6 (headless Chrome through `scripts/shoot.py`, which the repository's Chrome
  tests use on this machine); read, for `grot` and `geometric` only, every letter with a `cut` end that moved
  (measured in the roman, which is what the page sets: `C G J S a c e f g r s t`, the ligatures `ff fi`, the
  digits `1 2 3 5 6 9`, `$ & ' * , ; ?` and `©`, with the accented forms of those letters; 53 keys per recipe) at Regular and at the heaviest
  weight the page sets, and say in the record which weights were read; state per recipe whether the verdict
  word changes. Write `docs/reviews/genres-2026-11-25.md` in the form of the 2026-11-22 record: what was
  reviewed, by whom (the implementer, not a fresh reviewer, if that is so), the limits of the reading, the
  verdict table for all ten recipes (eight rows carried over with their 2026-11-22 date, `grot` and
  `geometric` with the date of this reading), and the digests block with `by_node_major` holding node 20, 22 and 26.
  Node 26 comes from `tests/test_genres.py::current_digests()`. Node 20 and 22 come from the same `DIGEST`
  script and the same `GEN` and `GENRES_JS` arguments that function uses, run by the agent under node 20.20.2
  and node 22.23.5 (the versions the 2026-11-22 record's CI run used), each fetched with
  `npx --yes -p node@<version> node -e "$DIGEST" <gen.js> <concepts.genres.js>` (the `node` npm package; `DIGEST`
  is read from the test module, not retyped). The record states the version each digest came from and that the
  two older majors ran on this machine, not on CI. If a binary of either version cannot be fetched, the item
  stops and reports the failure: it does not write a record that lacks a major, and it does not defer the
  digests to a person. The record states that eight digests equal the 2026-11-22 record's and two differ. The file keeps the name in this plan whatever day the reading happens; its first
  paragraph states the day. Then the two table rows in `references/genres.md`, the two `desc` strings, the two
  `risk` strings and `RECORD`. Checks, on the final bytes of the record and of `scripts/gen.js`: `.venv/bin/python3 -m pytest
  tests/test_genres.py -q` green under node 26; the node 20 and 22 digests in the record equal a second
  computation of them (the same command, run again, byte-equal); `tests/test_docs_commands.py` and
  `tests/test_hygiene.py` green. Take `shasum -a 256` of the record and of `scripts/gen.js` and log them in the
  commit message; `docs-generator-testing` compares them before its full runs. Not this item's check: whether
  the reading is right (`genre-review-acceptance`). A ruling that changes a verdict edits the record after the
  full runs, so it reruns `tests/test_genres.py`, `tests/test_docs_commands.py`, `tests/test_hygiene.py` and
  layer 2 on the edited bytes.
- **`docs-generator-testing`, agent.** `tests/test_docs_commands.py`, `tests/test_hygiene.py`,
  `tests/test_versions_and_skill.py` green; every figure in the new text is one a test or a logged watch
  printed in this run, not one copied from this plan. This item runs last, so it owns the full runs: layer 2,
  `.venv/bin/python3 -m pytest -q`, then layer 4, `bash scripts/smoke.sh --full`, in the background, after
  every other agent item has landed. Before the first full run it takes `shasum -a 256` of
  `docs/reviews/genres-2026-11-25.md` and `scripts/gen.js`, checks them against the digests that
  `genre-review-record` logged, and takes them again after `smoke.sh --full`: a difference means a file changed
  during the runs and the runs are repeated. Expected red: none. Record the measured times in `CLAUDE.md` and in
  section 12. State in the commit which layers ran.

### Operator items

- **`design-acceptance`, operator.** Accepts `gen-cut-clip`. Requires the operator's judgment of drawn
  letterforms, which no test here stands in for. Every page it names is one this plan produces: the genres page
  that `genre-review-record` builds and shoots with the commands of `references/genres.md` section 6 (the
  operator can rebuild it with the same commands). The Cane concept has no page in this plan; its outlines are
  held by `CUT-SPIKE`, `CUT-EXPORT-FOLD` and `CUT-FACE-BUILD`, not by a look. (1) `grot` and `geometric` `J f t r 9`
  at Regular and Bold: no spike at a cut corner; (2) the same recipes, `c s e a f t r 9` at Regular and Bold: the
  step where a curved terminal meets its cut corner is acceptable, or the operator asks for the unbounded clip
  (W2); (3) spacing that follows the clipped outline, with the advance moves listed under "Decisions the
  operator can overrule", is accepted, or the operator asks for a `prof` on cut ends.
- **`genre-review-acceptance`, operator.** Accepts `genre-review-record`. Requires only the operator's ruling on
  the two re-read verdicts (`grot` and `geometric`) in `docs/reviews/genres-2026-11-25.md`. The digests for node
  20 and 22 are not part of it: `genre-review-record` collects them. If the operator changes a verdict, the
  edit and its reruns are described under `genre-review-record`.
- **`release-acceptance`, operator.** Accepts `version-bump`. Requires: `gh workflow run ci.yml --ref <branch>`
  (layer 5; GitHub Actions, whose node 20 and 22 legs run `tests/test_genres.py` against the recorded digests), the merge of the pull request, and the tag `v0.11.0` on the first `main` commit
  that carries the version, pushed after the merge.

## As built

The plan above is the one the change was built from. Every departure and every figure that differs is here.

- **Figures.** The tests reproduce the plan's figures on the final tree: with the fix removed (W1) `CUT-SPIKE` reads 931 of 1912 edges (worst
  95.68), `CUT-SPIKE-SHIPPED` 3817 of 9704 (worst 126.26), `CUT-EXPORT-FOLD` 101, 102, 101, 102, 77 and 77 folded edges, and `CUT-FACE-BUILD` exit 1.
  The other watches are logged in `references/testing.md` section 12.
- **The mutation proof of `tests/test_cut_reach.py`.** It was run as W2 on a copy of the fixed `scripts/`, not by inserting the unbounded line after
  the `cutSide` line of the tree before the fix. The two give the same drawing: the fixed `cut` branch with its last line replaced by the unbounded
  call. `CUT-REACH` fired with 1176 of 11616 edges, 106 of them on an end the cut did not move, as the plan measured. `CUT-SCOPE` fired with 25 of
  18078 glyph draws over all five concept files and the Cane concept; the plan's figure of 14 was for `templates/concepts.genres.js` alone.
- **The genre re-read.** `grot` and `geometric` keep their verdict words (**partly** and **no**). The page sets a specimen line of letters, digits
  and a few marks. A second reading, after the build review, set `ff fi $ * ;` and `š ā é á à è â ê ä ë ç Ç ©` on a page built from a scratch copy of the
  content file and read `grot` and `geometric` at Regular and at Bold (not Medium). The list the review gave as 53 keys came to 41 when the
  NFD rule was run on `G`, so 41 keys were the set; of those, `C G J S c g r s t`, `1 2 3 5 6 9`, `& , '` and `?` were read at Regular in the specimen
  line and at the heavier weights in the headline words only. The record says so. The second reading saw no thin spike at a cut corner, a tapering flick at the
  top of the `f` of `ff` and `fi`, and accent fusion and a heavy cedilla at Bold that are not cut corners. The reading found the small step the plan
  predicted at the foot of `t`, the top of `f` and the tail of `J`; the two table rows, the two `desc` strings and the two `risk` strings
  carry one added sentence about it, and `genres.md` section 7 lists it. The node 20 and 22 digests came from `npx --yes -p node@20.20.2` and
  `node@22.23.5` on this machine, each run twice with byte-equal output, and equal the node 26 digests.
- **Build review fixes (2026-11-25).** `test_a_face_with_cut_stem_ends_builds` has no setup assertion: the plan's setup column asked that a `returncode` exist, and `assert r.returncode is not None` could not fail (`run()` returns a finished `subprocess.run`), so it was deleted; the `CUT-FACE-BUILD:` assertion is now the only one before the file checks. `test_cut_reach.py::test_a_moved_cut_end_moves_the_spacing_with_its_outline` (marker `CUT-SPACING:`) was added: the probe's `glyphs` rows now carry `adv` and `oldAdv`, and the test needs 161 of the 262 Cane draws with a moved cut end (measured 179, 2026-11-25) to have an advance different from 0.10.0's. Mutation W6 (`references/testing.md` section 12) turned it red. The spike measure's coverage limit (a later sample past the line on a curved terminal) is stated in `tests/test_cut_ends.py` and in `testing.md` section 12. The advance moves were measured and added to the 0.11.0 CHANGELOG; every figure equals the Decisions paragraph's.
- **The full runs.** `scripts/smoke.sh --full` runs layer 2 as its step 7, so layer 2 was not run a second time on its own. The measured times
  are in `CLAUDE.md` and in `references/testing.md` section 12.
- **Not run by this change.** The operator items (`design-acceptance`, `genre-review-acceptance`, `release-acceptance`) and layer 5, which is the
  operator's `gh workflow run ci.yml`.
