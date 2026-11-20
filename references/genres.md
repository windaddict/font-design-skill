# Genres: which typeface genres the generator reaches, with a recipe for each

WHAT IT'S FOR: the vocabulary for phase 3. A client says "a Didone" or "something like Futura", and
the concept spectrum needs parameter sets that stand for those words, so that the operator, the
reviewer and the generator mean the same thing. This file names each genre, says what defines it,
gives the parameter set (the recipe) in `templates/concepts.genres.js`, and says plainly whether
the generator reaches it. Read it before you build a round-1 spectrum, and again when a reviewer
asks "is this really a slab?".

Contents: 1 how to read the table · 2 the table · 3 genres the generator cannot reach · 4 notes on
single recipes · 5 lineage · 6 render the page · 7 known rendering defects

## 1. How to read the table

The last column, "reaches it today?", opens with one of three verdicts, then the date of the render
review and one sentence of what the reviewer saw. A recipe changes verdict only by a render review, never by
the author's own opinion of the parameters.

| Verdict | Meaning |
|---|---|
| **reaches** | rendered and read by a reviewer, and it reads as the genre |
| **partly** | rendered and read; it reads as the genre except for the limit the sentence names |
| **no** | rendered and read; it does not read as the genre, and the sentence says what would be needed |

An undated verdict, or a recipe row with no verdict, is a defect (`tests/test_genres.py`). The rows in
section 3 are different: they carry no recipe, so there was nothing to render, and they say **no** with
what the generator would need.

**What the tests prove about a recipe, and what they do not.** They prove that the recipe is a
legal concept, that every coordinate of every glyph is finite, and that its Regular and its 1.5 × Bold
take the same branch in every glyph, so the pair can be a variable font. They do not prove that it
looks like the genre. That is the render review (section 6), and the verdict and its date record it.

## 2. The table

The first column carries the recipe's concept id in backticks; `tests/test_genres.py` holds this
table and `templates/concepts.genres.js` to the same ids. A recipe sets only the knobs listed; the
rest are the file's own (read it for the exact numbers, and `generator.md` section 4 for the ranges).

| Genre | What defines it | Knobs that reach it | Reaches it today? |
|---|---|---|---|
| Didone / modern (`didone`) | vertical stress, hairline unbracketed serifs and horizontals, ball terminals | `nib 0, thin 0.28, pow 2.2, serifH 0.13, serifLen 0.7, serifBracket 0, tear false, flareAmt 0.2` | **partly** (2026-11-19): Moderate contrast because of the hairline floor, and equal-weight diagonals on `A V W M N v w x y`, so it reads as a light modern, not a Didone. The diagonals need an expansion model, which is out of scope |
| Fat face (`fatface`) | a Didone at poster weight, counters reduced to slits | the Didone knobs at `W 130`, `thin 0.22`, `xs 0.98`, `track -4`; the Bold is `mult 1.5` | **no** (2026-11-19): Stems are about 1/6 of the cap height even at the Bold; `W` past its range cannot reach 1/3-cap stems without collapsing the counters. It needs new shapes |
| Scotch roman / transitional (`scotch`) | slightly oblique or vertical stress, bracketed serifs, moderate to high contrast | Bract's `foil` (`examples/bract/concepts.js`): `nib 0, thin 0.27, pow 2.4, xs 0.9, serifH 0.13, serifLen 0.72, tear true` | **reaches** (2026-11-19): A near-twin of the Didone at these sizes; the bracket and the `a` terminal are what differ. Also shipped and reviewed as Bract's `foil` on hopsafari.com (2026-11-15).. Its italic exported since 0.7.0 (section 4) |
| Clarendon (`clarendon`) | bracketed slab serifs, moderate contrast, drawn as a bold companion | `thin 0.74, serifH 0.85, serifLen 0.5, serifBracket 1, serifGrow 0.6`, with the three optical knobs because `thin` is above 0.7 | **no** (2026-11-19): The serifs are short pointed wedges, not square bracketed slabs, so it reads as a wedge serif. A longer `serifLen` with `serifGrow 0` might fix it; untested. Rendering defects: section 7 |
| Egyptian / slab (`slab`) | unbracketed slab serifs | the Clarendon knobs with `serifBracket 0` | **reaches** (2026-11-19): Square unbracketed slabs at stem weight, low contrast, in Rockwell or Memphis proportion. Rendering defects: section 7 |
| Grotesque (`grot`) | near-uniform stroke, flat apexes, horizontal terminals on the curves | `thin 1, nib 0, pow 1`, no `thinGrow`, `ends` butt and cut, `hzThin 0.92, roundGain 1.04, diagThin 0.95, xh 540, joints true, crotch 0.3` | **partly** (2026-11-19): A monoline neo-grotesque with level-cut joints and a straight-leg `R`; the double-storey `g` with its sharp ear and the hooked `a` read humanist, which needs skeleton work. Seen after the `cut` default was fixed (section 7) |
| Geometric (`geometric`) | circles and squares, a monoline stroke, an even colour | the grotesque knobs with `W 92, xs 1.08, track 4, xh 500, crotch 0.2` and no `apex` | **no** (2026-11-19): A wide humanist sans, not Futura-like: it needs a circular `O`, a single-storey `a` and pointed apexes, all unbuilt |
| Reverse contrast, French Clarendon (`reverse`) | thin verticals, thick horizontals, heavy slabs | `nib 90 * DEG, thin 0.4, serifH 0.85, serifBracket 0` | **partly** (2026-11-19): Reverse contrast, but light, at typewriter weight; a larger `W` and a lower `thin` might reach a French Clarendon (untested). Rendering defects, and a lump where the bowls of `P`, `B` and `R` meet the thin stem: section 7 |
| Optical sizes, the metal lesson (`opsz-text`, `opsz-display`) | small sizes wider, taller x-height, less contrast, looser; large sizes the reverse | two cuts of one design: `xs`, `thin`, `track`, `serifLen`, `serifH` and `xh` (540 against 480) differ | **reaches** (2026-11-19): As a pair: a wider, looser text cut with a taller x-height beside a narrower, higher-contrast display cut. The display cut is close to the Didone |

## 3. Genres the generator cannot reach

These rows carry no recipe, because a recipe would only paraphrase a parameter set that does not
make the shape. Each names what the next version would have to add.

| Genre or feature | What defines it | Reaches it today? |
|---|---|---|
| Tuscan (bifurcated serifs) | split, curled serif ends | **no**: a serif with a notch is a new construction in `serifPoly`; no knob forks a serif |
| Art Deco (Broadway, Bifur) | one-idea letters, two-tone strokes, high or low waists | **no**: the pen has no two-tone stroke and no bar-height knob; `shear` and `bend` are a lean, not Deco |
| A circular `O` (the geometric genre's anchor) | the `O` is a circle | **no**: the skeleton's ring is 600 by 720, and `xs` scales it to a wider oval, never a circle; it needs a skeleton change in `G.O` |
| A single-storey roman `a` | the geometric and Futura-style `a` | **no** in the library: the roman `G.a` is double-storey. A site can set `G.a = GI.a` in its `skeletons` file (`generator.md`, "Per-face skeletons"), provided its `ends` maps `x` |
| A spurred `G` | the grotesque's `G` with a spur | **no**: the skeleton's `G` has a bar; a spur needs a skeleton change |
| Pointed apexes (`A`, `M`, `N`, `V`, `W` meeting in a point) | the strokes meet at a sharp apex | **no**: `apex` is designed, not built (`generator.md`, "Designed, not built: `apex`"); `params()` refuses it, and no recipe sets it |
| An expansion (pointed-pen) contrast model | thick and thin diagonals from a flexible pen | **no**: the pen is a translation model, so mirrored diagonals share a width; it is the limit behind every "partly" in the Didone rows |

## 4. Notes on single recipes

- **`scotch`** is Bract's `foil` with a new id and labels. Until 0.7.0 its `xs 0.9` made the italic
  `w` take a different serif branch at mult 1 and mult 1.5 (the serif kind read the drawn tangent, which
  the Bold's `xs` widening moved; `generator.md` section 12), so the exporter refused an italic group and
  the test recorded that one refusal by name. Since 0.7.0 every decision reads the geometry at mult 1 and
  the italic exports (`KNOWN_ITALIC_REFUSALS` in `tests/test_genres.py` is empty, and fails if a recipe
  is refused again). The recipe is still a roman recipe: its italic is built and self-checked, not reviewed.
- **`clarendon` and `slab`** set `hzThin`, `roundGain` and `diagThin` because their `thin` is above
  0.7: contrast no longer supplies the optical correction by accident (`guidelines.md` section 3).
  Re-read `minStrokeWidth` after any change: `hzThin` lowers the hairline of a concept whose thin
  direction is level.
- **`grot` and `geometric`** are monoline (`thin 1`), so their stroke variation is entirely the three
  optical knobs. Both set `joints: true`, which gives a sans concept the serif concepts' joint and corner
  pass (level cuts where `V W A M N` strokes meet, squared corners), and a `crotch` (0.3 and 0.2) that
  thins the inner edge at acute joints so the counter opens while the apex stays put.
- **`opsz-text` and `opsz-display`** differ in `xh`, so they test that an `xh` change does not move a
  branch; they are two concepts of one design, and `font.json` would make them two masters of one group.
- **Each recipe carries `name`, `from` and `desc`.** `desc` holds the limit as the table states it.
  The round-1 template shows a concept's text only from the content JSON's `concepts` block
  (`content.concepts.<id>.desc`, `.risk`), not from the concept's own `desc`, so put the limit in that
  block when you build the page (section 6).

## 5. Lineage

The generator is a pen drawn along a skeleton, with masters interpolated between weights: the family
of Metafont and of multiple-master fonts, not a new idea. Two standard criticisms of that family are
skeleton-first letters that read as mechanical and a parameter set large enough to tune instead of
draw; the review loop (`references/review-loop.md`) exists to catch both, and the table above is
where a genre's known shortfall is written down.

## 6. Render the page, then read it

```
node scripts/concepts/build-page.js --template round1 --concepts templates/concepts.genres.js --content scripts/concepts/content.genres.json out/smoke/pages/genres.html
mkdir -p out/smoke/pages/fonts && cp examples/neutral/out/Sampler-VF.woff2 out/smoke/pages/fonts/
.venv/bin/python3 scripts/shoot.py out/smoke/shots-genres --serve out/smoke/pages --pages genres.html --widths 500 1280 --scales 1 --dump-dom --family Sampler --font-url /fonts/Sampler-VF.woff2
```

`scripts/concepts/content.genres.json` is `content.minimal.json` with its `concepts` block replaced by one
entry per recipe id: the minimal file's block names `text` and `display`, which the builder refuses
beside these ids, and the round-1 template shows a recipe's limit only from `concepts.<id>.risk`, never
from the recipe's own `desc`. Each `risk` is the recipe's "reaches it today?" cell from the table above,
without markup, and `tests/test_genres.py` fails when a recipe or a cell and the file disagree. No
`--family`: the comparison face is the built neutral Sampler, a woff2 beside the page (smoke step 8
copies it to `pages/fonts/`), not an installed family, because Georgia is missing on a Linux runner and
the page's probe then fails the shot; with `--family Sampler --font-url /fonts/Sampler-VF.woff2` the
shot proves the face was drawn. Then a fresh strong-model reviewer reads the shots with a brief
derived from `templates/reviewer-brief-concepts.md` and answers, per recipe, "does this read as the
genre named, and what is the first thing that says it does not?".

**Status of the review:** first run on 2026-11-16 by one fresh strong-model reviewer reading the page at 1280 px, 2×, in
headless Chrome, and re-run on 2026-11-19 after the `R`'s leg root changed (0.5.0; `docs/reviews/genres-2026-11-19.md`), reading
every recipe's `R` and, for the rest of each recipe, only what that change could touch. It is one reading, not a panel; the shots are not kept in the repository. The reading
also found the `cut` defect (section 7), which is fixed, so the `grot` and `geometric` verdicts are for
the fixed generator. A later change to a recipe or to `gen.js` makes the verdict stale until the page is
read again. That is enforced: `docs/reviews/genres-2026-11-19.md` records each verdict and a digest of every
recipe's outlines as drawn then (the 2026-11-16 record stays beside it as history), and `tests/test_genres.py` fails with "the genre verdict for <id> is stale" when
the current digest differs. The remedy is a new review and a new record, not editing the digest.

## 7. Known rendering defects

Found in 0.2 ([issue #1](https://github.com/windaddict/font-design-skill/issues/1)). Each reads as a broken join, not as a style, once the title is large.

- **Butt-ended curves draw a hooked flag with a notch.** It shows at the top terminal of `a` and on
  `f r j y`, for the recipes whose curved terminals are `butt` (`clarendon`, `slab`, `reverse`) and for
  `grot` with `cut` 0 (an unset `cut` is 0 rad, a horizontal cut). It reads as a broken join at 44 px and up.
- **The `R`'s leg left the bowl under a round lump: fixed in 0.5.0** (`docs/plan-r-leg.md`). The leg started on
  the bowl's thin closing bar as a hidden join whose disk cap was wider than the bar, so the cap showed in the
  counter: 15 to 36 units on Bract's four masters, 9 to 25 on the neutral example, on every recipe here but the
  two `joints: true` sans, `reverse` (whose bar is the thick stroke) and most italics. The leg's start is now a
  T-join (`i`, `generator.md` section 2): cut level on the bar's centre line and buried. Nothing else moved:
  `tests/test_r_leg_join.py` holds every other glyph, advance and kern to the 0.4.0 generator.
- **`reverse`, `P`, `B` and `R`: a lump on the stem's left at bar height.** What issue #1 item 2 called "the `R`
  has a bump where the bowl meets the leg" is at the bar's other end: the bowl stroke ends at the stem with
  the join taper and a disk of `0.42 · 0.7` of the bar's width, and in reverse contrast the bar is 2.5 times
  the stem, so the disk pokes 9.4 units left of the stem at mult 1 and 14.1 at 1.5 on `P` and `R`, 22 and 33 on
  `B` (measured 2026-11-18). Open; the T-join supports typing those ends `i` too, but that changes `B`, `D`, `P`
  and `R`'s bar-to-stem joins on every face, a design decision not taken.
- **Fixed in 0.2, recorded because it was silent:** a concept that used `cut` ends and left `cut` unset
  reached `Math.cos(undefined)` and drew non-finite coordinates in `C E G S T a c e g s t y 1 2 3 &`.
  Chrome stops an SVG path at its first NaN, so whole words vanished while the page's self-test still
  counted them drawn. `params()` now sets `cut` to 0 as `generator.md` section 4 says, `render.js` sets
  `data-fd-error` when a drawn path holds NaN or Infinity, and `export.js` refuses non-finite coordinates.
