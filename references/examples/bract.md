# Worked example: Bract (hopsafari.com, 2026-11-15)

WHAT IT'S FOR: the skill's first full run through the nine phases, written from the site's own
records (`docs/bract-font.md`, `docs/plan-display-font.md`, `docs/design-review-2026-11-15.md`, the
build and mutation logs) so a run on another site can see what each phase produced, which numbers
came out, what failed and how the operator picked. Parameters and numbers only: the font and the
site's content are not in this repo, and reviewer prose is paraphrased. Bract shipped as
hopsafari.com's display face at commit `90a085c`. `examples/bract/` holds its `font.json` and
`concepts.js`.

Contents: 1 brief · 2 audit · 3 guidelines · 4 round 1 · 5 rounds 2–3 and the pick · 6 the two
cuts and the opsz decision · 7 the plan review · 8 the build · 9 what failed · 10 the review loop
· 11 the diff review and re-review · 12 mutations · 13 open items

## 1. The brief

The site: a photography-and-food essay archive (86 essays, 2010–2014) presented as a cloth-bound
open volume (paper, cloth, brass rules and numerals), with a hop-cone mark incised with page-lines.
The display face was Bodoni Moda over Newsreader body text and Archivo labels. The operator's words:
**"a readable and unique font that complements the design and branding."** The three tests every
round applied, in order: readable at every size the site uses; unique, not mistakable for Bodoni,
Newsreader or a stock transitional; in keeping with the volume and the mark, so it reads as the
caption engraving on a natural-history plate. The operator said not to worry about time or cost, so
the plan took the correct build (a true variable font) over the static fallback and budgeted six
review rounds.

## 2. The audit (phase 1)

Ten items, from headless-Chrome screenshots at 360 (iframe), 500, 1280 and 1600 px and computed
styles. Status after the deploy:

| # | Item | Status |
|---|---|---|
| 1 | "READ NEXT" rendered as a 28 px tracked-caps bar between two rules on every essay (a label class outranked by two heading rules) | fixed: heading visually hidden, list unboxed |
| 2 | 14 labels repeating the heading under them on the home page | fixed |
| 3 | Bodoni Moda could not hold the 16.8 px titles | fixed by Bract, with Medium on the 15.2–16.8 px elements |
| 4 | boxed cards with a hover lift | fixed |
| 5 | two date formats, two navs | partly: one nav, spelled dates on contents and tag pages; essay pages still print the ISO date (a shared-builder change) |
| 6 | sixteen chips on the contents page, one count in both rows | open |
| 7 | rules as decoration | open; the Bold now separates H2s without the rule |
| 8 | formulaic and repeated copy | partly: riddle H2s renamed, one lede; a fact still twice |
| 9 | the name twice in 250 px | fixed as recommended: eyebrow dropped, wordmark and H1 kept |
| 10 | the essay sheet floats on a shadow | open |

Not seen: arrows (0 in the built HTML), all-caps titles (0 of 93). Items 1, 2, 4 and 5 were fixed
on a branch first so the concepts were judged on pages without eyebrows, boxes or rules (commit
`2daac34`). Each fix has a guard in the site's `tests/test_design_audit.py`.

## 3. The guidelines (phase 2)

- Contrast with Newsreader on at least two of contrast, stress, serif structure, width.
- Sizes: 15.2 px numerals, 16.8 px grid titles (88 of them), 17.6–27 px H3, 25.6–35 px H2,
  32–48 px essay H1, 38–64 px contents H1, 48–80 px frontispiece, wordmark 24–30 px caps tracked
  .06em. At 16.8 px one CSS pixel is 60 units, so the Regular's thinnest stroke stays at or above
  about 45 units. A Didone hairline (12–20 units) is what failed.
- Weights: Regular and a Bold that is a clear step; a Medium optional for 16.8 px (shipped).
- Case: titles Title Case; only wordmark, buttons and nav are caps.
- Character set from the 93 titles: A–Z, a–z, 0–9, `& ( ) ' : ? . - + # ! ,` and `’`. Traps: 83 of
  93 titles carry U+00A0 before the last word; 55 of 56 apostrophes typed as ASCII `'`.
- Driftwood's lessons kept (references/guidelines.md section 7).

## 4. Round 1, the spectrum (phase 3)

Six concepts named for the book and the hop, closest to Bodoni first; parameters as in
`examples/bract/concepts.js` (ends `s: serif, t: flare, u: flareS, "": disk, x: exit` unless
stated):

| Concept | From | W | nib | thin | pow | xs | swell | track | ends and terminals |
|---|---|---|---|---|---|---|---|---|---|
| Foil | brass foil stamped on the cloth | 110 | 0 | 0.27 | 2.4 | 0.9 | 0 | 0 | tear; serifLen 0.72, serifH 0.13 (a flat Scotch slab) |
| Burin | engraved captions on natural-history plates | 94 | 12° | 0.40 | 1.5 | 0.9 | 0.03 | 0 | tear; serifLen 0.6, serifH 0.3 |
| Blind | the title pressed blind into the cover | 114 | 0 | 0.74 | 1 | 1.08 | 0 | 6 | t/u butt; serifLen 0.5, serifH 0.85 |
| Field | lettering in a field notebook | 92 | 38° | 0.30 | 1 | 0.86 | 0.14 | 0 | t/u cut at 30°; serifLen 0.32, serifH 0.45 |
| Cone | the bracts of the hop cone in the mark | 96 | 24° | 0.36 | 1.3 | 0.92 | 0.06 | 0 | t/u taper 170 at 40°; leaf dots; serifLen 0.3, serifH 0.75 |
| Bine | the climbing hop vine | 92 | 8° | 0.62 | 1 | 0.98 | 0 | 6 | s butt, t/u curl |

All six on real titles at real sizes on paper and cloth. The reviewer suggested prototyping Foil,
Blind, Cone and Burin, after the four audit items were applied. Field was flagged as sharing a hand
with the sister site's Driftwood; Bine's twin (Tideline) had already lost on that site.

## 5. Rounds 2–3 and the pick (phases 4–5)

Round 2 set the six beside Bodoni Moda on mock-ups of the redesigned pages. The reviewer revised
Burin on those pages: a Medium (`W × 1.3`) for the small titles, bigger serifs that grow with weight
(`serifGrow`), slightly heavier hairlines. The operator then asked to compare the revised Burin with
Foil and Cone (round 3). The reviewer ranked them Burin, Foil, Cone, for reasons that paraphrase as:
Burin alone held the 16.8 px titles at 1× and its 35 px Bold read as a heading; Foil was the most
dramatic at 64–80 px but its hairlines fell under a pixel at 16.8 px, and thickening them made it an
upright Burin; Cone was crisp at 16.8 px but its leaf-shaped dot read as an accent at every size.
Burin's weak point was presence at 48–80 px, which led to the two cuts (section 6). The operator
chose Burin; Monotype sells a Burin, so the face was renamed **Bract** (the hop cone's overlapping
scales) before any file existed.

## 6. The two cuts and the opsz decision

The site sets display type from 15.2 px to 80 px and one set of strokes cannot serve both ends:
hairlines that engrave at 80 px break up at 17 px. The first display sketch only thinned hairlines
and lengthened serifs and changed nothing visible; the second ("D2") made the stems 8 % heavier as
well. The build plan made the two cuts one variable font on an optical-size axis:

| Cut | W | thin | pow | track | serifLen | serifH | shared |
|---|---|---|---|---|---|---|---|
| text | 96 | 0.44 | 1.5 | 0 | 0.75 | 0.50 | nib 12°, xs 0.9, swell 0.03, flareLen 90, dot 0.5, overshoot 10, beak, tear, thinGrow 0.5, serifGrow 0.35 |
| display | 104 | 0.32 | 1.8 | −10 | 1.0 | 0.40 | same |

`flareAmt` (0.28 and 0.34 in the sketches) had no effect with teardrop terminals and is dropped in
`examples/bract/concepts.js`; `dropAmt` stays at its default 0.55, so the outlines are unchanged.

`opsz` 40–80, measured in CSS px with Chrome 157 (`opsz.py`): 64 px rendered identically to
`"opsz" 64` only; 80 px to 80 and the clamped values; 32 and 40 px to every value ≤ 40. Every element
under 40 px gets the text cut unchanged; the two fluid H1s cross into the display cut smoothly; the
80 px frontispiece gets the display cut. Safari and Firefox unmeasured.

## 7. The plan review (phase 6)

Impasse (Codex backend, 2026-11-15): 13 findings, all accepted, each checked against the code.
F001 equal point counts do not prove the same shape → the branch record. F002 opsz units are a
browser decision → `opsz.py`. F003 the unreviewed Bold-display corner is reachable through the
reader's root font size → **four masters**, not three. F004 shared-index RDP needs seam, count,
winding and raster checks → all four. F005 per-pair kerning cannot replace `track −10` → the track
stays in the advances. F006 the patched generator had no `module.exports` → restored and smoke-
tested first. F007 quote glyphs are built in the builder → ported and the cmap pinned to a declared
set. F008 overlap rendering verified on Mac Chrome only → stated as the limit; FreeType union
check added. F009 the floor measured parameters → measured on interior samples. F010 kerning tested
at one location → every reviewed location and whole-title widths. F011 the static fallback had no
CSS mapping → a contingency needing its own plan. F012 metrics copied from Driftwood → measured from
every glyph. F013 a `gvar` entry does not prove both axes → instancing at every master.

Operator answers: name Bract; copyright John Knox, maker Hop Safari, licensed for hopsafari.com
only (the shipped name table; `examples/bract/font.json` carries a neutral one, family "Bract
Example", because the name Bract is not licensed for reuse as a font name — `NOTICE.md`); fix the
literal-asterisk H2 as content (the font carries `*` anyway); remove the Bodoni files.

## 8. The build (phase 7)

One TrueType variable font, two axes, four masters:

| Master | wght | opsz | Cut | Pen | nominal thin | measured minimum | floor |
|---|---|---|---|---|---|---|---|
| TextRegular (default) | 400 | 40 | text | W 96 | 42.2 | 41.61 (`r`) | 41 |
| TextBold | 700 | 40 | text | W 144, thin 0.3593 | 51.7 | 50.99 (`r`) | 50 |
| DisplayRegular | 400 | 80 | display | W 104 | 33.3 | 32.78 (`r`) | 32 |
| DisplayBold | 700 | 80 | display | W 156, thin 0.2613 | 40.8 | 40.16 (`U`) | 40 |

`avar` user 500 → design 580 (`W × 1.3`, the reviewed Medium) on `.plate-title`,
`.read-next-title`, `.chapter-num`. Named instances Regular, Medium, Bold, Display, Display Bold.
Hairlines at the site's sizes: 15.2 and 16.8 px Medium ≈ 46 units interpolated, 0.70–0.78 px; Bold
17.6–35.2 px 0.90–1.79 px; Regular 40 px 1.66 px; Regular 80 px 2.62 px. `gasp` 0xFFFF → 0x000F.
Vertical metrics measured: hhea and win ascent 976, descent 254; typo 760 / −240 / 200 with
USE_TYPO_METRICS. Decimation at 1 unit: 155,042 → 28,457 points per master. 4,100 kern pairs.
Cmap: U+0027 → the curly apostrophe (tick unmapped), U+00A0 → space; 137 glyphs, 134 cmap entries.
Size: 86,580 bytes woff2 against 102,400 (Bodoni Moda 400 + 700 had been 53,980). Reproducible with
`SOURCE_DATE_EPOCH` assigned; `--check` byte-identical. The (700, 80) corner is built and
self-checked, **not visually reviewed for use**.

## 9. What failed on the way

- **Rings lost a point in some masters**: the ring's repeated start point was dropped by
  `TTGlyphPen` in whichever master it rounded onto its twin; 16 ring glyphs skipped on the first
  build; fixed at the source.
- **Small rings closed on the same rounded point in one master** (the inner ring of `%` in
  TextBold, round 3); a first fix moved the point and failed F013 at 4.5 units; glyphs are now built
  verbatim from the rounded points.
- **FreeType autohinting** made raw-vs-decimated rasters differ by 209 levels; a one-instruction
  `fpgm` fixed the measurement.
- **The first fold-guard metric** could not tell a fold from a sharp corner; the shipped metric
  accumulates consecutive backward steps, measures raw and decimated edges at their own thresholds
  (4 and 10), and walks the first segment.
- **`flareAmt` dead** with teardrops: round 1's 0.34 → 0.28 changed nothing; the display `r`'s drop
  was moved by lengthening its arm instead (`C 345 510 385 495 405 455`).
- **Decimation count**: the plan estimated 13,240 points from the Regular alone; the union over
  four masters is 28,457.

## 10. The review loop (phase 8)

Each round: build → `shoot.py` (eight pages at 500, 667, 889, 1280, 1600 px, 1× and 2×, plus the
specimen: real titles 15.2–80 px, paper and cloth, Bract beside Bodoni Moda, Newsreader and
Georgia, the opsz crossing, intermediate instances, a kerning row, an NBSP row) → a fresh reviewer
against the checklist → ranked findings → changes.

- **Round 1.** Readable and unique met. The Bold read as a different family: serifs grew into
  bracketed slabs at 35.2 px. The Bold `t` had a lump at its foot. Changes: `serifGrow` 0.6 → 0.35;
  the fold pin; the `t`'s top end `s` → `x` (its head serif read as a flag); the `a` bowl joined the
  stem at 290 instead of 270 so the Bold's counter stays open at 17.6 px.
- **Round 2.** Folds gone, serifs right; the Bold still read as another family because hairlines
  thickened as much as stems. Changes: `thinGrow` 0.5 (Bold floors 62 → 50 and 49 → 40); the `r` arm
  lengthened; the fold guard added and watched red; the `t` foot measured rather than changed (its
  lowest ink row at 1× equals the round letters' overshoot row).
- **Round 3.** Stop: the face met the goal and no font defect was visible at 1×. A pre-existing
  layout fault surfaced: at 500 px the inner pages' wordmark wrapped; fixed in CSS with
  `white-space: nowrap` and a step-down below 560 px.
- **Enlarged-root check** (`--root 150`): at 1280 px the Bold H2s came out at 41 px, one unit into
  the opsz range; nothing visible. One width, one size; the rest of that region is unchecked.

## 11. The diff review and re-review (phase 9)

Diff review, 8 findings, all accepted and fixed: the `quotedblleft` advance ignored its second
mark's 1.45× shift (issue #23); the fold guard measured raw polygons only and skipped each edge's
first segment; `shoot.py` ignored Chrome's exit code and could accept a stale PNG; the
master-reproduction test skipped the builder-made quote glyphs; the branch signature recorded
partner presence, not identity; `SOURCE_DATE_EPOCH` used `setdefault`; `bounds.js` required the
wrong module; the plan called the (700, 80) corner reviewed. Re-review, 5 findings, all fixed
without a third review: `--masters` bypassed the branch and fold checks; a 404 or fallback-font
screenshot could pass as evidence; the docs again said Bold cannot exceed 35.2 px; the fold test
trusted the exporter's metric (hence the fixture test); the reproducibility test did not pass a
foreign epoch.

## 12. Mutations

28 mutations on the first run, 26 red, 2 survivors: `i` (U+0027 to the straight tick) needed three
edits because the builder's own cmap checks refused the build first; `overlap` (flag not set) was
refused by the raster self-check ("overlap rendering of B differs from its union by 120 levels"),
so the raster budgets had to be lifted for the mutation to reach the test. A third shape, the
partner-identity recording, could not be reached through geometry (no end has two partners) and was
mutated in the recording. All three are in `references/testing.md` section 4. Final: every
mutation red, restored by digest, green again.

## 13. Open items (as recorded)

Rendering, not checkable from a Mac: Windows rendering of the 0.70–0.78 px Medium hairlines and of
the overlapping contours; Safari and Firefox `opsz` mapping. Font polish: Bold capital `I` serifs
heavy at the wordmark's 24–30 px; `r.` at 80 px overhangs the period after the arm was lengthened
(the hand pair −50 was set for the short arm); the (700, opsz > 40) region built and self-checked,
not reviewed; accented letters beyond the lowercase vowels unused by any title. Site: essay pages
print the ISO date; converting quotes to curly in the shared builder would let U+0027 return to the
straight tick.
