# {{Family}}: how the site's display face was made

<!-- WHAT THIS TEMPLATE IS FOR: the record a run writes at phase 9, in the shape of the two
precedents' records (Bract's docs/bract-font.md, Driftwood's docs/driftwood-font.md). It is the
file the next change to the face starts from, so it states what is known, how it was measured, and
what is not known. Fill every {{slot}}; delete the HTML comments; keep the section order. Every
number must be read from manifest.json, the exporter's output or the code on the date you name,
and a statement that rests on something not measured must say so. Never describe a planned thing
in the present tense as built. -->

WHAT IT'S FOR: the record of how {{site}}'s own display typeface was designed, built and reviewed,
so the next change to it starts from what is known rather than from the code. It covers why the
font exists, where the look came from, how the generator and the build work, what each self-check
guarantees, the review rounds and why they stopped, what failed on the way, and what is still open.

The source is `{{tools/<face>/}}` (its README has the build commands). The shipped file is
`{{path/to/Family-VF.woff2}}`; its measurements are in `{{tools/<face>/manifest.json}}`. The guards
are `{{tests/test_<face>_font.py}}` and `{{tests/test_<face>_site.py}}`. The plan this was built
from, with the independent review of the plan, is `{{docs/plan-<face>.md}}`.

Every number below was read from `manifest.json` or the code on {{YYYY-MM-DD}}, after round
{{N}}. Where a statement rests on something not measured here, it says so.

## Why a custom font

<!-- The face it replaces and why; the site's design language in two sentences; the operator's
brief VERBATIM; the tests every review round applied, in order. -->

Until {{date}} the display face was {{old face}} over {{body face}}. {{Two sentences on the site's
design language and mark.}} The operator's brief, in their words: "{{goal sentence}}." The tests
every review round applied, in order: {{readable at …; unique, not mistakable for …; in keeping
with …}}.

## How the design was chosen

<!-- The concept pages and where they live; one numbered item per round with the concepts named
and the pick paraphrased; the name decision and the collision check. Parameters and numbers, not
reviewer prose. -->

The concept pages are in `{{tools/<face>/concepts/}}` (self-contained HTML).

1. **Round 1, `{{round1.html}}`**: {{N}} concepts named for {{the brand}}: {{names and one-line
   sources}}, each a parameter set rendered on real titles.
2. **Round 2, `{{round2.html}}`**: {{the shortlist}} on mock-ups of the redesigned pages beside
   {{old face}}. The reviewer revised {{leader}}: {{parameter changes and why}}.
3. **Round 3, `{{round3.html}}`**: {{finalists}}. Ranked {{order}}; the reasons in one sentence each.
   {{Chosen concept}} is the design that was built. Its values as chosen: {{W, nib, thin, pow, xs,
   swell, track, ends, serifLen, serifH, dot, overshoot, beak/tear, thinGrow, serifGrow}}.
4. **The name.** {{Candidate}} → {{Family}}: {{the collision found, or "no collision found at
   <where searched>"}}, decided {{date}} before any file existed.

{{If two cuts: the two-cut decision in one paragraph: the size span, why one set of strokes cannot
serve both ends, the cut boundary.}}

## How the generator works

<!-- The generator's origin (this skill, version; derived from Driftwood 67a4e5b and Bract
90a085c); the skeleton model in one bullet; the pen formula; each parameter that departs from the
defaults and why (thinGrow, serifGrow, dropAmt); the vertical fit; end types; pinned sampling;
fold pinning; branch recording; spacing and kerning with the pair count. -->

{{Family}} is generated, not hand-drawn. `{{tools/<face>/gen.js}}` is `scripts/gen.js` from the
font-design skill {{version}}, which derives from John Knox's Driftwood (movingavg.com, 67a4e5b)
and Bract (hopsafari.com, 90a085c) generators.

- **Skeletons.** {{Any skeletons added, and which titles needed them.}}
- **The pen.** `W × (thin + (1 − thin)·|sin(θ − nib)|^pow)`, {{swell}} % swell. `W` {{value}}; the
  Bold masters are `W × {{mult}}`.
- **{{serifGrow N}}.** {{Why this value.}}
- **{{thinGrow N}}.** {{Why this value.}}
- **End types.** {{Which modes the ends table maps, in one sentence each.}}
- **Spacing and kerning.** {{Track per cut; hand pairs; word-space pairs; threshold; pair count.}}

## The variable font

<!-- One table per group: master, axis location(s), cut, pen (W and effective thin). State which
masters were drawn and which regions were reviewed; the (Bold, large opsz) corner is "built and
self-checked, not visually reviewed for use" if that is the truth. Then avar, opsz as measured,
hairlines as built (nominal, measured minimum, floor per master; px at the site's sizes), vertical
metrics, overlaps, decimation (points before and after), quotes and cmap (counts), size, reproducible. -->

One TrueType file (`glyf` + `gvar`), {{N}} axes, **{{N}} masters** drawn by the generator:

| Master | `wght` | {{`opsz`}} | Cut | Pen |
|---|---|---|---|---|
| {{TextRegular}} (default) | {{400}} | {{40}} | {{text}} | W {{96}} |
| … | | | | |

{{Which region is built and self-checked but not visually reviewed, and why it is reachable.}}

- **`wght` {{400–700}}, avar.** User 500 maps to design {{580}} (normalized 0.333 → {{0.6}}), which is
  `W × {{1.3}}`, the Medium the concept pages reviewed; used on {{selectors}}.
- **{{`opsz` 40–80, measured in CSS pixels.}}** {{Browser and version}} on {{OS}} rendered {{the
  measurement}} (`opsz.py`, {{date}}, recorded in `manifest.json`). **{{Browsers}} were not
  measured.**
- **Hairlines as built** (font units; the thin stroke is `W × thin`, less the swell's half):

  | Master | nominal thin | measured minimum interior stroke | floor |
  |---|---|---|---|
  | {{TextRegular}} | {{42.2}} | {{41.61 (`r`)}} | {{41}} |

  At the sizes the site uses: {{px per element}}. A `gasp` table (0xFFFF → 0x000F) asks Windows to
  antialias every size.
- **Vertical metrics**: win ascent {{976}} and descent {{254}} measured from every glyph in every master;
  hhea and OS/2 typo {{976/−254}} with a line gap of 0 and USE_TYPO_METRICS (the measured extent, or the
  `typo_metrics` override {{none}}); `line-height: normal` is {{1.230}} em where the platform reads hhea or typo (win metrics not covered), against
  {{the value the live site had before, if the face replaces one}}; embedding permission fsType {{4}}
  ({{the operator's licence decision}}); STAT axis values for every named instance, a smart-dropout `prep`,
  no Macintosh names, the Latin 1 code-page bit; FontBakery universal profile {{version}}: {{N}} accepted
  findings ({{ids and reasons}}), the rest passing.
- **Overlapping contours** with OVERLAP_SIMPLE; the cost is checked, not assumed (below).
- **Decimation** at {{1}} unit per edge run, kept indices shared by all masters: {{before}} →
  {{after}} points per master.
- **Quotes and the cmap.** {{U+0027 and U+00A0 decisions with the counts that justified them}};
  {{N}} glyphs, {{N}} cmap entries, pinned by the cmap test.
- **Size.** {{bytes}} woff2 against a {{budget}} budget ({{old face}} was {{bytes}}).
- **Reproducible.** `SOURCE_DATE_EPOCH` is assigned from `font.json`; `build.py --check` rebuilds and
  compares bytes; the suite runs it.

{{If an italic group: the same for the second file, plus its metadata (subfamily, italicAngle,
fsSelection) and its status: "pipeline-tested, design-reviewed in rounds …" or "not design-reviewed".}}

## The build's self-checks, and what each one proves

<!-- Copy the table from references/variable-font-build.md section 6 and replace the measured
figures with this build's (the raster maxima and the glyphs they occurred on). Keep the exact
guarantees; never round one up. Keep the FreeType paragraph. -->

| Check | Exact guarantee |
|---|---|
| Masters compatible | Same contour count, same point count per contour, same branch record in every master. Not a proof that corresponding points are the same feature. |
| … | |

**The rasters are FreeType via Pillow on {{machine}}.** They say nothing about CoreText, DirectWrite
or Android. The review screenshots are {{browser}} on {{OS}}; {{what they showed at 2×}}. Windows
has not been looked at.

## How it was reviewed

<!-- The round protocol in one sentence; one bullet per round: what the reviewer found (ranked by
visibility at 1× on a real page), what changed (parameters, skeletons, kerns, CSS), and why the
loop stopped. The enlarged-root check: what it covered and what it did not. Screenshots are not
tracked; name the tool that reproduces them. -->

Each round: build → `shoot.py` ({{pages, widths, scales}}, plus the specimen) → a fresh reviewer
against the checklist in `{{docs/plan-<face>.md}}` section {{7}} → changes → next build. Every
build ended with the full suite green.

Each round from the second also ran `scripts/diff.py` against the previous round's `out/` (kept at
`{{work/round-N/}}`, diff output at `{{work/diff-N/}}`; neither is tracked): FreeType renders of the titles at the
review sizes, unhinted, not browser evidence. {{Per round: N of M renders changed, and which two the host spot-checked.}}

- **Round 1.** {{Findings; changes.}}
- **Round 2.** {{Findings; changes.}}
- **Round {{N}}.** Stop: {{why}}.

**The enlarged-root check.** `shoot.py --root 150` {{what it showed at which width and size; what
remains unchecked}}.

## What failed on the way

<!-- One bullet per failure: symptom, cause, fix. Include the mutation survivors and what they
revealed about the tests. -->

- {{…}}

## Open items

**Rendering, not checkable from this machine**
- {{Windows; Safari and Firefox opsz; …}}

**Font (polish, reviewer round {{N}})**
- {{…}}

**Site**
- {{…}}
