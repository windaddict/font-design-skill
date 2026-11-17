# Worked example: Driftwood MA (movingavg.com, 2026-11-14)

WHAT IT'S FOR: the precedent the generator comes from, written from the site's record
(`docs/driftwood-font.md`, the tool README and GitHub issues 22–24 on the site's repository) so a
run can see the earlier shape of the process, the lessons that became the skill's rules, and the
three bugs found in it later and fixed in this skill. Parameters and numbers only; the fonts and the
site's content are not in this repo. Driftwood shipped at commit `67a4e5b` as five static CFF fonts
built by a union pipeline; `examples/driftwood/` re-expresses it for this skill's variable pipeline,
built and self-checked here, **not design-reviewed in that form**.

Contents: 1 brief · 2 three rounds · 3 the four concepts · 4 the static family with an italic ·
5 how it was reviewed · 6 what failed · 7 the three bugs found later · 8 how the example here
differs from what shipped · 9 open items

## 1. The brief

By November 2026 Fraunces, the site's display face since June, was turning up on many other sites.
The operator wanted a headline face nobody else had, kept IBM Plex Sans for body text, and asked
for three things: take the look from the logo (a wind-bent tree on a cliff above sand and sea, roots
showing; a slightly organic feel welcome); contrast organic headlines with mechanical Plex, visibly,
within good design practice; look professional, not novel, judged on real headlines at real sizes.

## 2. Three rounds

1. **Round 1**: five concepts made by **styling existing fonts** around the brand's roots and
   hidden-misalignment ideas. The operator found one "weird"; literal gimmicks read as decoration.
2. **Round 2**: five quieter concepts, still on existing fonts. The operator's reaction, that the
   existing fonts "have become common", reframed the job from choosing a face to drawing one.
3. **Round 3**: the first **generated** letterforms, one concept per element of the logo
   (section 3). The operator chose Driftwood. A cheaper alternative, Fraunces at unusual settings,
   was shown on an essay comparison page and judged to "just look heavier".

The skill starts at the generated round because of rounds 1 and 2.

## 3. The four concepts (round 3)

Parameters as in `examples/driftwood/concepts.js`:

| Concept | From | W | nib | thin | pow | xs | track | ends and transforms |
|---|---|---|---|---|---|---|---|---|
| Driftwood | the tree | 88 | 25° | 0.36 | 1.4 | 0.86 | 0 | s serif, t flare, u flareS, "" disk, x exit; flareLen 90; serifLen 0.64, serifH 0.4; dot 0.47; overshoot 10; beak; tear; swell 0.08 |
| Tideline | the sea | 90 | 10° | 0.66 | 1 | 0.98 | 6 | s butt, t curl, "" disk; dot 0.6 |
| Dune | the sand | 104 | 0 | 0.82 | 1 | 1.12 | 10 | every end disk; dot 0.74 |
| Windswept | the tree on the cliff | 90 | 40° | 0.48 | 1.3 | 0.92 | 0 | s cut, t taper 120, "" disk; cut 22°; shear tan 8°; bend 0.00022; leaf dots |

Driftwood shipped with `flareAmt 0.28` beside `tear: true`, a dead knob (section 7); the example
drops it and keeps the default `dropAmt`, so the outlines are unchanged. No `thinGrow` and no
`serifGrow`: Driftwood's Bold hairlines grew in proportion to its stems and its serifs stayed at
Regular size (the generator's behaviour when `serifGrow` is unset).

## 4. The static family with an italic

Five styles: Regular (`W 88`), Medium (`×1.3`), Bold (`×1.65`), Italic and Medium Italic (10°).
Each glyph's overlapping strokes were **unioned** with skia-pathops and slivers removed, then
written as CFF OTF and woff2 with GPOS kerning, the `fi fl ff` ligatures and the name table
(Moving Average Inc., a proprietary licence note). The italic: `GI` lowercase overrides (single-
storey `a`, exit stems), `GI_CAPS` for A T W M R K V U N J Y, the shear and 0.95 narrowing, serifs
×0.6, the sidebearing band so hooks overhang, the `J` rule, extra italic kern pairs, a slanted
tick. Version history: v1 (overshoot 8 %, flat capitals hung below the baseline, n/h/m leaned back);
v2 (fixed, beak serifs, missing characters); v3–v4 (a real weight step, a narrower set, the Medium,
joins that taper into stems); v5–v6 (the italic, teardrops in place of balls); v0.7–0.9 (straight
quotes, `; … [ ]`, accented letters, word-space kerning, shorter italic serifs); v0.10 (true italic
capitals); 1.000 shipped site-wide.

## 5. How it was reviewed

The loop the skill formalises: render real headlines in headless Chrome at the sizes the site uses
(17.6–48 px) plus 150–400 px zooms for construction; measure with fontTools (bounds against the
baseline and cap height, stray contours, advances, the cmap); review independently with a strong
model after every round, findings ranked by how noticeable they are at real sizes, each claim
spot-checked before anything was built on it (one width figure was corrected that way); check the
comparison page; **watch each guard fail** before trusting it.

## 6. What failed

- **Pebble terminals dropped on the stroke end**, twice (an ellipse, a bigger flare): a shape placed
  on a stroke meets its edges at an angle and leaves a notch or a spur. The teardrop built from the
  stroke's own edges with a smoothstep swell replaced them.
- **A wear pass** that rounded every corner (shrink and regrow with pyclipper): no visible
  difference at real sizes, 38 % more points; now off, behind a flag.
- **A back-lean on n, h and m**: read as an error, not character. Save gestures for rare letters.
- **A cursive italic x**: read as a Greek chi.
- **ASCII `'` mapped to a straight tick**: every "Don't" showed a typewriter mark, because the
  content types `'` and the builder does not smarten quotes. `'` now draws the curly apostrophe.
- **Shortening italic serifs in `serifPoly`**: no effect, because the slant sends every italic stem
  through `diagSerifPoly`.

## 7. The three bugs found later, and their fixes in this skill

Found 2026-11-15 while forking the generator for Bract; filed on the site's repository:

| Issue | What | Fix in this skill |
|---|---|---|
| #22 | **Bold outline folds leave lumps** on `t`, `f`, `ff`, `r` and `&`: where the Bold half-width exceeds a bend's inner radius the inside offset edge folds back, and the union keeps the loop as filled area; the Regular folds only at sharp corners (G, ç, Ç) | the fold pin in `strokePolys` (`scripts/gen.js`); the fold guard in `scripts/export.js` on raw and decimated edges (4 / 10 units); the fixture test; overlapping contours shipped instead of a union |
| #23 | **`quotedblleft` advance ignores the second mark's offset**: it took the straight quotes' advance while placing its second mark 1.45 apostrophe-widths out (Bold: advance 345, ink to 356) | both double curly quotes advance by the apostrophe plus the gap; the test re-derives all six quote glyphs from the exported apostrophe at every master |
| #24 | **`flareAmt` has no effect when `tear` is on**: `endMod` applies the flare swell only without teardrops; Driftwood's 0.28 did nothing, and a Bract review round changed it with no change in the outlines | `dropAmt` sizes the teardrop and scales all three of its constants; `params()` throws on `flareAmt` with `tear: true` and on `dropAmt` without it |

The shipped Driftwood 1.000 still carries #22 and #23; the issues are open on the site's repository.

## 8. How the example here differs from what shipped

`examples/driftwood/font.json` is **the same design through the variable pipeline**: a wght-only
roman group (Regular `×1`, Bold `×1.65`, Medium through `avar` user 500 → design 538, which is
`×1.3`) and a wght-only italic group (Regular `×1`, Medium `×1.3`, the axis 400–500), each its own
variable font with overlapping contours and the fold pin, not five unioned CFF statics. Floors as
this repo's exporter measures them: roman 30.5 / 50.4 (set 30 / 50), italic 30.4 / 39.6 (set
30 / 39); the record's "48-unit Regular hairline" is that record's figure, not a measurement made
here (the concept's `W 88 × thin 0.36` is 32 nominal). It builds and passes the self-checks in the
smoke run; **nobody has design-reviewed Driftwood in this form**, and the italic path in general is
pipeline-tested only (references/generator.md section 9). The kerning threshold is 8, as the
original exporter's. The name table is neutral ("Driftwood Example", `{{operator}}` placeholders,
vendor id `EXMP`): the shipped font's strings named Moving Average Inc. and its proprietary licence,
and the name Driftwood MA is not licensed for reuse as a font name (`NOTICE.md`).

## 9. Open items (as recorded on the site)

Rendering: the Regular's thin strokes on Windows at 22–30 px and on a real phone. Font: old-style
figures; a Bold Italic ("The takeaway:" inside an italic quote falls back to Medium Italic); italic
forms for the remaining capitals and a cursive `z`; a notch where the Bold `r` drop meets its arm
above about 150 px; the © ring slightly low above 100 px; small capital accents at display sizes.
Site: curly quotes in the shared builder; dropping the Fraunces fallback request; the wordmark now
in Driftwood Bold (confirm wanted); the audit's rules applied to the remaining pages.
