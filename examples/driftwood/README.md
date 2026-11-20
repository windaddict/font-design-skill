# Driftwood MA (movingavg.com): parameters and configuration

WHAT IT'S FOR: the face the generator comes from, re-expressed as a `font.json` and `concepts.js`
for this skill's variable pipeline, so the skill can build a wght-only roman and a wght-only italic
(the two one-axis fixtures the smoke run needs) from a real design. **Parameters only**, MIT like
the rest of the repo: the shipped woff2 files are not here and may not be added; Driftwood MA is
proprietary to Moving Average Inc. The name table in `font.json` is neutral — family "Driftwood
Example", `{{operator}}` placeholders for the owner strings, vendor id `EXMP` — because the name
Driftwood MA identifies the site's face and is not licensed for reuse as a font name (`NOTICE.md`).
The precedent's record, with the brief, the three rounds, what failed and the three bugs found
later, is `references/examples/driftwood.md`.

Files: `font.json` (roman group: Regular `×1`, Bold `×1.65`, `avar` user 500 → design 538 for the
`×1.3` Medium; italic group at 10°: Regular `×1`, Medium `×1.3`, axis 400–500; the kern set with
threshold 8, the hand, space, italic hand and italic space pairs; three public page titles as
character-set illustrations), `concepts.js` (Driftwood, the concept that shipped, and the three
it was chosen over: Tideline, Dune, Windswept) and `requirements.json` (since 0.7.1: the expectations
the font suite compares this example's build against, every value measured from that build or copied
from `font.json`, so the suite runs on a second face beside the Sampler; `smoke.sh` step 4a).

## Build

```
node scripts/export.js --font examples/driftwood/font.json --group roman out/driftwood-roman.json
node scripts/export.js --font examples/driftwood/font.json --group italic out/driftwood-italic.json
.venv/bin/python3 scripts/build.py --font examples/driftwood/font.json
.venv/bin/python3 -m pytest scripts/tests/test_font.py -q --font examples/driftwood/font.json --requirements examples/driftwood/requirements.json --static-dir none
```

`build.py` reads the `requirements.json` beside `font.json` for the required-character check. Its
`hand_kerns` list the non-zero hand pairs only: a zero pair (`f|f`) suppresses the automatic kern and
is not emitted, so there is no value to compare. Until 0.7.1 this example carried no
`requirements.json` and was built with `--no-requirements`; the suite ran on the Sampler alone, and
two of its tests held only for the Sampler's proportions (`CHANGELOG.md`, 0.7.1).

The output is `out/DriftwoodExample-VF.woff2` and `out/DriftwoodExample-Italic-VF.woff2` under the
neutral name table. **What shipped, as history:** the site's five statics carried copyright,
manufacturer and designer Moving Average Inc., vendor id `MAVG` and a proprietary licence note
naming movingavg.com — the site's name table, not what this file builds.

## Outcome and status

Driftwood shipped site-wide on 2026-11-14 (site commit `67a4e5b`) as **five static CFF fonts**
(Regular, Medium, Bold, Italic, Medium Italic) from a skia-pathops union build. What this example
builds is **different**: two variable TrueType fonts with overlapping contours, the fold pin and the
pinned sampling, which the shipped fonts did not have. It is built and self-checked here and has
**not been design-reviewed in this form**; the italic path in particular is pipeline-tested only.
`flareAmt 0.28` was dropped (dead beside `tear: true`, issue #24); `dropAmt` stays at its default so
the teardrops are unchanged.

Exported with this repository's generator: roman 131 glyphs, 4,363 kern pairs, 156,184 → 20,193
points per master, minimum interior strokes 30.5 / 50.4 units (floors 30 / 50), 0 folded edges;
italic 4,806 pairs, 157,631 → 19,612 points, minima 30.4 / 39.6 (floors 30 / 39), 0 folded edges.
The site record's "48-unit Regular hairline" is that record's figure; the nominal is `88 × 0.36 =
32`. The shipped fonts still carry issues #22 (fold lumps) and #23 (`quotedblleft` advance), both
fixed in this generator and builder.
