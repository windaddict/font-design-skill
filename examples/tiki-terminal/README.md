# Tiki Terminal: the skill's open example face

WHAT IT'S FOR: the skill's own open example of a face drawn through the three concept rounds, and the
only fixture that uses a skeleton file (`skeletons.js`), cut stem ends and a custom axis (`LEAN`). The
other three examples are serif faces built from one concept file. This one is a heavy monoline display
face between a tiki-bar sign and an old console font, with a weight axis and a lean axis that tips ten
letters (`a e i o k r A E I O`) back. It builds under its own name table and its own licence, so a reader
can see a finished face folder (`references/face-folder.md`) whose font is under the SIL Open Font
License 1.1, not a neutral placeholder.

## Status

Stated exactly, because a rounded-up status would mislead:

- The operator approved the design on 2026-11-26: the concept `cane`, and `canelean` (Cane with the
  letters `aeiokrAEIO` leaning back) at the far end of the `LEAN` axis, the accent design of round 3 and
  the slashed zero. During the design review (2026-11-27) the operator chose a zero whose slash crosses the
  counter and ends in the bowl (a short bar inside it read as a theta at Bold; round 5 widened its bowl by
  60 units so its two counters stay open at 40 px), and an `I` with bars, so
  "Il1" reads as three glyphs.
- This folder builds and passes its self-checks (`build.py`, including `--check`), the eight tests of
  `tests/test_tiki_terminal.py` (the approved design, the lean, the gap floors and the font suite less six
  tests) and the FontBakery gate with two accepted findings.
- A person has not yet reviewed the built font's spacing at display sizes. That review is the plan's
  `spacing-review` item, which is the operator's (`docs/plan-tiki-terminal.md`).
- No font file is in the repository, this face's included (`NOTICE.md`). `out/` is git-ignored.
- Three small drawing faults of the approved design are open and are not touched here: the heel of the
  `a`, the end of the `e` bar and the junction of the `3`.

## Files

- `font.json`: the build configuration. One roman group, four masters (`Reg`, `Bold`, `RegLean`,
  `BoldLean`), four named instances (Regular, Bold, Lean, Bold Lean), the kern set and its hand pairs,
  the name table, seven titles, `size_budget_bytes` 102,400.
- `concepts.js`: seven concepts in the order `phosphor`, `teletype`, `cane`, `carvedslab`, `carved`,
  `totem`, `canelean`. The masters use `cane` and `canelean`; `canelean` differs from `cane` in `id`,
  `name`, `from`, `wonk` and `wonkAmount` only.
- `skeletons.js`: the glyphs this face draws itself over the shared tables (`>`, `_`, and redrawn `e`,
  `a`, `c`, `t`, `T`, `r`, `1`, `0`, `7`, the accents and the stems cut square). Its header says why each
  override exists.
- `content.json`: the copy for the round-1 concept page.
- `requirements.json`: what the font suite and the build compare the face against. The axes, instances,
  names and required characters are the operator's decisions. The floors, vertical metrics, word space and
  character map are measured from the first build.
- `OFL.txt`: the licence text a built font must travel with.

## Licence

Two licences, split by what the file is:

- The parameters (`concepts.js`, `skeletons.js`, `font.json`, `requirements.json`, `content.json`) and the
  tests are MIT like the rest of the repository.
- A font built from them carries the SIL Open Font License, Version 1.1 in its name table (name ID 13)
  and travels with `OFL.txt`. Copyright 2026 John M. P. Knox. `fs_type` is 0 (installable embedding). No
  Reserved Font Name is declared.
- The name "Tiki Terminal" was searched for before it was used, and the search found no typeface of that
  name. A search with no hit is not proof that the name is free.

## Build

Every Python command spells `.venv/bin/python3`. Run these from the repository root.

```
node scripts/export.js --font examples/tiki-terminal/font.json --group roman --requirements examples/tiki-terminal/requirements.json out/tiki-roman.json
.venv/bin/python3 scripts/build.py --font examples/tiki-terminal/font.json
.venv/bin/python3 scripts/build.py --font examples/tiki-terminal/font.json --check
.venv/bin/python3 -m pytest scripts/tests/test_font.py -q --font examples/tiki-terminal/font.json --requirements examples/tiki-terminal/requirements.json --static-dir none -k "not dropamt and not optical_corrections and not unbracketed_serif and not open_curve_extremes and not unset_crotch"
.venv/bin/python3 scripts/fontbakery-gate.py --font examples/tiki-terminal/font.json --requirements examples/tiki-terminal/requirements.json
.venv/bin/python3 tests/pair_gap.py --font examples/tiki-terminal/font.json --under 30
node scripts/concepts/build-page.js --template round1 --concepts examples/tiki-terminal/concepts.js --content examples/tiki-terminal/content.json --skeletons examples/tiki-terminal/skeletons.js out/tiki-round1.html
```

The output is `out/TikiTerminal-VF.woff2` and `out/manifest.json`. The suite's `-k` expression leaves out
six tests (see "Known limits"). `tests/test_tiki_terminal.py` holds the same expression as
`SUITE_EXCLUSIONS` and is the authority on it: the command above is a text copy.

## Numbers

From the build that wrote the face (`out/manifest.json`, 2026-11-27 after round 5 of the design review, skill 0.13.0, node 26.13.1; the glyph and cmap counts and the vertical metrics and word space are from the 0.12.0 build of 2026-11-25, which 0.13.0 does not change):

| Quantity | Value |
|---|---|
| Glyphs, cmap entries | 140, 137 |
| Kern pairs written | 2,822 (5,499 before the zero pairs below) |
| Points per master | 156,010 raw, 21,826 after decimation (the same in all four masters) |
| Minimum stroke, Regular and Lean | 78.78 units (floor 78), at `_` |
| Minimum stroke, Bold and Bold Lean | 118.18 units (floor 118), at `ë` |
| Worst fold after decimation | 4.13 units (Regular, `1`) and 0.7 (Bold, `Ñ`) |
| woff2 size | 71,060 bytes (budget 102,400) |
| Vertical metrics | ascender 1010, descender -293, line gap 0 (`line-height: normal` reads 1.303 em) |
| Word space | 256 (Regular), 273 (Bold) |

## Spacing

The generator reads each glyph's spacing profile from polygon points only (`profs` in `glyph()`, 54 bins
of 20 units). A square stroke end (`j`, `butt` or `cut`) is one straight segment with two points, so the
bins between its corners read whatever lies behind the end. The automatic kern then sees a wider gap than
the outlines leave, and its clearance clamp reads the same profile, so the clamp does not stop the bar end.
This face has square ends on most strokes, so its automatic kerns pull some pairs together until the
outlines touch.

Measured at the five locations of `tests/pair_gap.py` (Regular, Bold, Lean, Bold Lean and the middle at
550 and 50), on the 0.12.0 build: 367 two-character pairs cross, 531 come under 12 units and 624 come under 16, before any
suppression.

What the face does about it: `kerning.hand` holds 2,711 zero pairs (re-measured for 0.13.0, which moves the cut corners of the `cane` and `totem` strokes onto their edges, after round 1 of the design review redrew the `t` foot, after round 2 raised the limit to 30 units, after round 3 redrew the brackets, after round 4 redrew the zero, the `I` and the accents, and after round 5 widened the zero). A zero hand pair makes `export.js` skip
the automatic kern for that pair, so the two glyphs sit on their sidebearings (8 units or more each). The
list holds every pair of kern-set keys, with the three ligature keys, whose outlines came closer than 30
units at any of the five locations. The limit was 16 units until round 2 of the design review
(2026-11-27): pairs between 16 and 30 units still drew as touching at 40 to 48 px (`c|o` at -113, `E|C`,
`5|s`), and the operator raised it to 30, about 1.2 px at 40 px. Two pairs have a real value because zero is too loose for them:
`r|r` -80 (-90 until round 2, which came within 25 units at Lean) and `E|O` -60. One number serves all four masters, so Regular is looser than Bold needs.
Fourteen more have a real value from round 1 of the design review (2026-11-26), where the automatic kern
did not make the outlines touch but drew the pair wrong on the page: `c|l`, `c|b`, `c|h`, `c|k` and `c|i`
at -30 (the automatic -99 tucked the stem into the `c`, so "cl" read as "d"); `C|:` -15, `$|1` -15,
`v|1` -30, `s|t` -25 and `r|)` -60, which touched at 40 px; and
`1|2` +20, where the `1` met the `2` with no kern at all. Round 1 also set `(|1` -25; round 2 found it
under 30 units and it is now a zero pair. Round 1 also set `[|y`, `n|]` and `]|?`; round 3 lengthened the
bracket arms and left those pairs to the 30-unit rule. Round 3 set `t|'` -15 (the automatic -50 put the
apostrophe on the `t` crossbar in "Tonight's"). `tests/test_tiki_terminal.py` lists all fourteen as
`NONZERO_HAND`.

Four zero pairs come from round 3 of the design review, not from the measurement: `2|.`, `2|,`, `D|S` and
`R|D`. Their outlines are 30 units or more apart, yet they drew as one shape at 40 to 51 px ("$12.00",
"RECORDS"). The test lists them as `REVIEW_ZEROS` and keeps them in the list by name; regenerating the list
must carry them over. A hand pair must name kern-set keys: `>` is not one, and a pair naming it
fails the build in `feaLib` (`build.py`'s `gname` has no glyph name for it).

Regenerate the list after a change to the glyphs, the concepts or the track: build with `"hand": {}`
(keeping the fourteen real values and the word-space pairs), run `tests/pair_gap.py --under 30`, and put its
output in `kerning.hand` with the four review zeros. The list exists because of the generator limit above. When the generator reads
stroke edges instead of polygon points, drop it.

What the tests hold (all contour distance at the five named locations):

- no pair of mapped characters comes closer than 12 units;
- `rr`, `ro`, `er`, `RE` and `EO` keep 30 units at weight 700, at LEAN 0 and 100;
- every zero pair is one the unsuppressed build puts under 31 units (the four review zeros excepted), and
  every pair under 29 units is a zero pair or one of the fourteen real values. The 1-unit band either side
  of 30 is an operator ruling, not a measurement of how far outlines move between platforms;
- the four review zeros and the fourteen real values are in `kerning.hand` with those values.

## Known limits and open items

- **Line height.** The `i` and `j` dots stand at y 760 (Bold dot top 862) and the Bold `p` and `q` reach
  -292, so at Bold a `p` over an `i` needs 1,154 units: set the face at `line-height: 1.16` or more where a
  title can wrap. At 1.1 a Bold descender meets the dot on the next line (design review round 3).

- **The gap tests see contour distance at five locations.** A glyph that lies wholly inside another's
  counter without crossing it is not seen. An axis setting between the five locations is not seen. A pair
  at 12 to 20 units can still read as touching at Bold; that is a judgement for the spacing review.
- **Six font-suite tests are left out of the suite run.** They draw the first concept of the face's file,
  `phosphor`, a round-1 concept no master uses, and assume it has flare or serif ends, or leaves `hzThin`,
  `xh` or `crotch` unset: `dropamt` (two tests), `optical_corrections`, `open_curve_extremes`,
  `unbracketed_serif` and `unset_crotch`. They run in full on the neutral and Driftwood fixtures in the
  same smoke run. The face's `d` bowl bound in `scripts/tests/test_font.py` is 5 units for this folder's
  name alone, where every other face keeps 1.
- **Two FontBakery findings are accepted** in `requirements.json`: `case_mapping` (the lowercase accented
  letters have no capitals in the generator's glyph set) and `valid_glyphnames` (`build.py` names a
  one-character ASCII key outside its name table after the key itself, so the glyphs `skeletons.js` adds
  are named `>` and `_`; renaming them changes font output and is a `build.py` change with a version).
- **The three drawing faults** named in "Status" are open.
- **Figures are proportional, not tabular.** The face has no tabular figures.
- **`LEAN` is a private axis tag.** STAT names its values by number, not by a label
  (`references/variable-font-build.md`, "Known limits of the STAT table").
- **No compatibility baseline holds the outlines.** `tests/fixtures/baseline.json` records three
  examples; a generator change moves this face's outlines until someone records them.
- **No static instances and no site.** The suite runs with `--static-dir none`.
