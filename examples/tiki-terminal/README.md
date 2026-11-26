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
  the slashed zero.
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
.venv/bin/python3 tests/pair_gap.py --font examples/tiki-terminal/font.json --under 16
node scripts/concepts/build-page.js --template round1 --concepts examples/tiki-terminal/concepts.js --content examples/tiki-terminal/content.json --skeletons examples/tiki-terminal/skeletons.js out/tiki-round1.html
```

The output is `out/TikiTerminal-VF.woff2` and `out/manifest.json`. The suite's `-k` expression leaves out
six tests (see "Known limits"). `tests/test_tiki_terminal.py` holds the same expression as
`SUITE_EXCLUSIONS` and is the authority on it: the command above is a text copy.

## Numbers

From the build that wrote the face (`out/manifest.json`, 2026-11-26, skill 0.13.0, node 26.13.1; the glyph and cmap counts and the vertical metrics and word space are from the 0.12.0 build of 2026-11-25, which 0.13.0 does not change):

| Quantity | Value |
|---|---|
| Glyphs, cmap entries | 140, 137 |
| Kern pairs written | 4,766 (5,432 before the zero pairs below) |
| Points per master | 154,282 raw, 21,503 after decimation (the same in all four masters) |
| Minimum stroke, Regular and Lean | 78.78 units (floor 78), at `_` |
| Minimum stroke, Bold and Bold Lean | 118.18 units (floor 118), at `ë` |
| Worst fold after decimation | 4.13 units (Regular, `1`) and 0.7 (Bold, `Ñ`) |
| woff2 size | 77,592 bytes (budget 102,400) |
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

What the face does about it: `kerning.hand` holds 666 zero pairs (re-measured for 0.13.0, which moves the cut corners of the `cane` and `totem` strokes onto their edges). A zero hand pair makes `export.js` skip
the automatic kern for that pair, so the two glyphs sit on their sidebearings (8 units or more each). The
list holds every pair of kern-set keys, with the three ligature keys, whose outlines came closer than 16
units at any of the five locations. Two pairs have a real value because zero is too loose for them:
`r|r` -90 and `E|O` -60. One number serves all four masters, so Regular is looser than Bold needs.

Regenerate the list after a change to the glyphs, the concepts or the track: build with `"hand": {}`
(keeping the two real values and the word-space pairs), run `tests/pair_gap.py --under 16`, and put its
output in `kerning.hand`. The list exists because of the generator limit above. When the generator reads
stroke edges instead of polygon points, drop it.

What the tests hold (all contour distance at the five named locations):

- no pair of mapped characters comes closer than 12 units;
- `rr`, `ro`, `er`, `RE` and `EO` keep 30 units at weight 700, at LEAN 0 and 100;
- every zero pair is one the unsuppressed build puts under 17 units, and every pair under 15 units is a
  zero pair. The 1-unit band either side of 16 is an operator ruling, not a measurement of how far
  outlines move between platforms.

## Known limits and open items

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
