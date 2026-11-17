# Sampler: the neutral example

WHAT IT'S FOR: the fixture the skill's smoke run and CI build end to end, so every path through the
scripts is exercised on a face that belongs to nobody. "Sampler" is **not a real typeface** and has
never been design-reviewed; it is an upright, low-contrast, bracketed serif chosen to be unlike both
shipped faces and to use the one terminal path they did not (`tear: false`, so the flare swell and
`flareAmt` are live). Two groups: a two-axis roman (wght 400–700 × opsz 24–72, four masters) and a
wght-only italic (two masters), so the full master rectangle, `avar`, `opsz`, a one-axis build and
the italic path are all built in one run.

Files: `font.json` (configuration), `requirements.json` (the reviewed expectations the tests read;
here "reviewed" means "set by the smoke run"), `concepts.js` (two concepts: `text` and `display`),
and `content.json` (with the `slot_sizes` block rounds 2 and 3 require, sample sizes for the
invented site) and `titles.txt` for the concept pages (invented titles). No font files are tracked; the build writes to `out/`, which is ignored.

## Build

From the skill directory, on its venv (`.venv/bin/python3`, never a bare `python3`):

```
node scripts/export.js --font examples/neutral/font.json --group roman --requirements examples/neutral/requirements.json out/neutral-roman.json
node scripts/export.js --font examples/neutral/font.json --group italic --requirements examples/neutral/requirements.json out/neutral-italic.json
.venv/bin/python3 scripts/build.py --font examples/neutral/font.json --static examples/neutral/out/static
.venv/bin/python3 -m pytest scripts/tests/test_font.py -q --font examples/neutral/font.json --requirements examples/neutral/requirements.json --static-dir examples/neutral/out/static
.venv/bin/python3 scripts/tests/mutate.py --font examples/neutral/font.json --requirements examples/neutral/requirements.json --static-dir examples/neutral/out/static
.venv/bin/python3 scripts/fontbakery-gate.py --font examples/neutral/font.json --requirements examples/neutral/requirements.json
```

The gate line builds each group's variable TTF into a temporary folder and runs FontBakery's universal
profile on both files at once; it passes with the five findings `requirements.json` accepts, each with its
reason (`accepted_qa_findings`), and exits 3, saying SKIPPED, when FontBakery is not installed
(`requirements-dev.txt`).

The two exports are the `--requirements` pre-check only (they name a required character without a
skeleton); `build.py` runs its own export. `mutate.py` runs every mutation by default (`--only NAME`
for a subset, `--list` to see them; there is no `--all`). Every path on these command lines
(`--static`, `--static-dir`, the export's output) resolves relative to the working directory, the
skill directory here, so the `--static` folder the build writes is the `--static-dir` folder the
tests read; `tests/test_neutral_readme_commands.py` runs the build and test lines above as written
and checks that. `scripts/smoke.sh` runs these plus the three concept pages and, with `--full`, the
Chrome steps.

## Status and numbers

Exported with this repository's `scripts/export.js` (131 glyphs per master):

| Group / master | min interior stroke (units) | floor | folded edges | worst decimated excursion |
|---|---|---|---|---|
| roman / TextRegular | 59.4 | 58 | 0 | 1.48 |
| roman / TextBold | 75.8 | 69 | 0 | 3.01 |
| roman / DisplayRegular | 53.5 | 52 | 0 | 2.42 |
| roman / DisplayBold | 68.2 | 62 | 0 | 9.79 (`Ç`, close to the 10-unit threshold) |
| italic / Regular | 59.4 | 58 | 0 | 7.63 (`k`) |
| italic / Bold | 75.8 | 69 | 0 | 8.27 (`fi`) |

Decimation at 1 unit: roman 159,186 → 30,600 points per master; italic 160,720 → 22,126. Kern
pairs: 4,367 roman, 4,726 italic. Three decimated-edge readings sit within 2.5 units of the fold
threshold; they are sharp-corner steps, not folds, and a change to the concept should re-check them.

Never ship Sampler. It exists to prove the pipeline, and its name-table strings say so.

## What this example is, and is not

It is a finished sample, built to run every code path quickly: two concepts (`text`, `display`)
where a real run writes about six; floors and the opsz ends (24–72) chosen for the fixture, where a
real run measures its own floors from the export and takes the opsz ends from `mine-sizes.py`
(an 80 px site needs an axis that reaches 80). The audit list and the reviewer's verdict in
`content.json` are sample text written for the invented "Harbour Review" site, not findings about
any real page. Its round-1 comparison row is the built Sampler itself, which only a finished sample
can show: a real round 1 compares against the face the site uses today
(`scripts/concepts/content.minimal.json` starts that way). `titles.txt` holds the same six titles
as `font.json` for `mine-charset.py --titles`.
