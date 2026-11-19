# Plan: the capital R's leg meets its bowl without a nub

WHAT IT'S FOR: the implementation plan for fixing the one-glyph defect that issue #1 item 2 and the
Bract design review both saw, written by Claude (Fable 5.1) on 2026-11-18 on branch `fix/r-leg` from
`origin/main` at `598044b` (0.4.0), before any code, for independent review (Impasse) and then
implementation. Revision 2: the first draft's construction (the leg run out to the bar's far edge and
cut flush with it, the bowl split in two) was rejected by the operator on 2026-11-18 because two
outlines meeting edge-to-edge is a fragile joint (section 12). This draft replaces it with a T-join:
the leg ends on the bar's centre line, cut parallel to the bar, so the whole end is buried and no
two edges coincide anywhere.

Status: **built (2026-11-19), reviewed twice by Impasse after the build (section 12); not yet committed.**
Sections 0 to 11 are the plan as reviewed before code, kept as the record of what was decided and why;
where the build departed from them the "As built" paragraph below and section 12 say so, and those win.
The numbers in sections 0 to 4 were produced before the build by running node against the unmodified
`scripts/gen.js` and against modified copies of `scripts/` in the session's scratch folder, outside the
repository (there: `patch2.py` makes the copies `modE/`, `modE2/` and `modF/`; `measure2.js`, `teediag.js`,
`union_check.py`, `universal.js`, `svg2.js` measure and draw; `exports/` holds the export JSON of
every example group before and after; `r-tjoin.png` is the before/after picture), which is
session-scoped and not evidence anyone else can re-run. The implementation commits the measurement
as `tests/r_leg_junction.js` (the node half: the nub, burial, cut and continuity figures of section
2 and the union check's polygon dump) and `tests/test_r_leg_join.py` (the Python half: the tests of
section 5, the skia-pathops union check and the 0.4.0-versus-fix comparison), and every figure here
is re-stated from their output in the record before the version is bumped (review finding F008). After the
build the committed tests reproduce them: nub 0 on all 134 drawings, every other glyph, advance and kern
unchanged against 0.4.0, and the measurements of section 2 within their stated tolerances.

**As built (2026-11-19).** Implemented as planned with four departures, each recorded in `references/testing.md` section 8 and
the commit: (1) the interior rule alone let an `i` end 2.5 units from a bar's end draw a cut that stuck out past the bar, so
`teeCut` also checks both cut corners inside the partner's drawn polygons and throws otherwise, which needs the partner stroke to
come earlier in the skeleton; (2) the clamp refusal is unreachable (the 14.5° refusal bounds the reach at 1.87 widths), so test c
asserts that arithmetic instead of a clamp case; (3) test e is red before the fix ("outlines changed on [], expected ['R']"), not
green as section 9 said: it pins that the `R` differs from 0.4.0 and nothing else does; (4) the first mutation run found two
survivors in the tests (the union check read vertices only; the control asserted only "at least 10"), both fixed before the
second run. The cut corners are the leg body's first and last points (the closing seam), not "the first point of each edge run".

**Markers.** **(read)** = checked against the named file. **(measured)** = run or counted here.
**(inferred)** = not verified; the implementer must check before relying on it.

## 0. The defect, exactly

The roman `R` is three strokes (read: `scripts/gen.js` line 114): the stem, one bowl stroke that
starts at the stem top, rounds the bowl and runs back level along `y = 340` to the stem, and the leg
`S("M 320 340 L 570 0", "", "s")`. The leg starts on the bowl's closing bar with the hidden-join end
type `""`, which every shipped `ends` table maps to `disk` (read: the five concept files). The bar
runs level there, so it is drawn at the pen's thinnest width; the leg runs at about 54° and is drawn
near full width. `strokePolys` gives the leg's start a square cut perpendicular to its own direction
and a disk of radius `0.42 · w_leg` centred on the bar's centre line (read: lines 735–737). The disk
is bigger than the bar is thick, so it shows.

What is visible, measured on every concept of the five concept files at mult 1 and 1.5, roman and
italic where `x` is mapped, 134 drawings:

- **Into the counter, above the bar:** the disk's top and the cut's upper corner. Bract's four
  masters: 15.0 (TextRegular), 26.4 (TextBold), 22.0 (DisplayRegular), 35.7 (DisplayBold) units above
  the bar's upper edge; 0.6 px at 40 px and 1.8 px at 80 px for the Regulars, 2.9 px for
  DisplayBold at 80 px. The neutral example 9.0 to 24.8, Driftwood 20.8 at Bold, `bine` 6.0,
  `tideline` 4.2, `blind` 3.0, `clarendon` 2.9. 95 of the 134 drawings have a nub over 1 unit; the
  exceptions are `dune` (near-monoline, the disk fits inside the bar), the sans recipes with
  `joints: true` (`grot`, `geometric`), `reverse` (its bar is the thick stroke) and most italics (the
  italic leg is a curve, so the join taper thins its root to 70 % before the disk is sized).
- **Below the bar:** nothing protrudes. The square cut's lower corner lies on the leg's own left-edge
  line, so below the bar the drawn leg is a subset of the ideal one; the cut removes a small wedge
  (about 5 units deep in Bract TextRegular), a notch rather than a bump. The caller's zoom
  the caller's zoom `junc.png`, in the same scratch folder (4 px per unit, orange = the bar's edges, red = the disk, magenta = the leg)
  shows exactly this (read).
- **`reverse` (issue #1 item 2) has no nub at the leg root** (measured: 0.0 at both weights). Its
  lump is at the other end of the same bar: the bowl stroke ends at the stem with the join taper and
  a disk of radius `0.42 · 0.7 · w_bar`, and in reverse contrast the bar (100 units) is 2.5 times the
  stem (40), so the disk pokes 9.4 units left of the stem at mult 1 and 14.1 at 1.5 (`pb.js`). `P`
  and `B` carry the same lump there (9.4 / 22.0 at mult 1, 14.1 / 33.0 at 1.5). This plan does not
  touch the bar's stem end, so that lump stays on all three and goes back to issue #1 (section 11).

So the defect is a hidden-join terminal drawn on a stroke thinner than the terminal, on the counter
side. `references/generator.md` line 239 names the rule the skeleton breaks: "keep the cap inside
the stroke it meets or it shows as a nub" (read).

## 1. The fix: a T-join end type

### 1.1 The construction

The leg keeps its root at (320, 340) on the bar's centre line. Its end is cut **level, parallel to the
bar's tangent at that point**, through the root, and no terminal is drawn. The cut is then a segment
of the centre line, so it is buried by the bar's full half-thickness on both sides whatever the pen,
the weight or the swell; the leg's two side edges cross the bar's lower edge and nothing else meets
anything. The bar is not split and the bowl stroke is the 0.4.0 one, point for point.

Why not a square cut at the centre line (the caller's arithmetic, confirmed): a cut perpendicular to
the leg spans `±0.3 · w_leg` vertically about the root, 26 units on Bract TextRegular against a bar
half-thickness of 21.5, so its upper corner would still show. A level cut spans `±0.62 · w_leg`
horizontally along the centre line and 0 vertically.

Why not the first draft's corner (section 12): the leg's level cut placed at the bar's far edge
coincides with that edge, and the bar's drawn edge is not where the nominal width puts it (swell,
and in general any modifier), so the cut sat 0.28 units proud on Bract TextRegular and 3.1 on
`brush` Bold. A cut on the centre line has no edge to disagree with.

### 1.2 The skeleton

The only skeleton change is the leg's start letter, roman and italic:

```js
// scripts/gen.js line 116        S("M 320 340 L 570 0", "", "s")   ->   S("M 320 340 L 570 0", "i", "s")
// scripts/gen.js line 221        S("M 310 340 C 390 260 450 130 490 50 C 510 10 535 -10 590 -10", "", "x")   ->   ... "i", "x")
```

`i` is a new end-type letter: "this end runs **into** another stroke's interior; cut it parallel to
that stroke there and draw no terminal". A letter is needed, rather than a rule that fires wherever
the geometry matches, because the matching geometry occurs at 35 roman and 38 italic glyphs and
the rule changes every one of them (section 3). The letter is used by `R` only.

### 1.3 The generator change (`scripts/gen.js`)

Prototyped in full in the scratch copy `modE/scripts/gen.js` (the diff is what `patch2.py` applies;
about 40 lines), measured in sections 2 and 4. The pieces:

1. **Detection, in `glyph()`.** Every stroke is sampled once up front (today only open strokes are,
   for `ends`; rings join the list). For an end typed `i`, `tee(e, si)` finds the other stroke
   (open or ring) whose **unmapped** sampled centre line has a point within 2 units of the end,
   that point being an interior sample (more than 2 units from either of that stroke's ends;
   anywhere on a ring), nearest first. It returns the stroke's index and the tangent there, drawn
   (`dirM`, from the drawn samples on either side of the nearest one) and unmapped (`dir`), the way
   `partner()` returns a joint's partner. The unmapped points decide, the drawn ones draw, as every
   decision in `glyph()` does since 0.2 (read: generator.md section 12).
2. **Refusals, loud.** An `i` end that has a stroke-end partner within 2 units (`partner()` found one:
   that is a joint or a corner, not a T-join), or that lies on no stroke's interior, throws naming
   the glyph, the stroke and the end. Then, **on the drawn geometry of each master** (review finding
   F002: `cutSide`, lines 411–416, reads the drawn tangent and silently returns the point unchanged
   when `|T × D| < 0.25`, and clamps the move at its reach; the x-height map, the shear, `bend` and
   `xs` all change drawn directions, so a decision on the unmapped skeleton alone could leave a
   master with a `tee` record and an uncut end), the T-join computes the reach each edge point needs
   (`t = ((p − X) × D) / (T × D)`) and throws if the drawn `|T × D|` is under 0.25 or either `|t|`
   exceeds the clamp, naming the glyph, the end and the two numbers. A refusal in one master fails
   that master's draw, so the exporter never sees a group with a half-cut `R`. Measured on the 134
   drawings (`teediag.js`): drawn `|T × D|` is at least 0.735 (the italic `blind` Bold; the refusal
   is 0.25) and the needed reach is at most `0.462 · w` (the clamp is `3 · w`).
3. **The cut, in `strokePolys`.** The T-join direction reaches `strokePolys` beside `joins`. At that
   end: `modeA` (or `modeB`) becomes `"tee"` before the taper and teardrop decisions; in the ends
   pass, both edge points are moved along the stroke's own tangent to the line through the end point
   with the partner's direction (`cutSide(…, teeD, 3 · w)`: the clamp is widened from `w` to `3 · w`
   because a level cut across a 54° stroke needs `0.37 · w` and a shallower meeting would need more;
   the 14.5° refusal bounds it at `3.9 · w`, so a stroke at 15–20° would still be clamped and partly
   square: documented, not reached by `R`), earlier samples past that line are pinned to it
   (`clipPast`), the end outcome is `tee`, and the second pass draws nothing for it. A curved stroke
   with a `tee` end keeps the join taper it would have had as a `disk` end with no partner
   (`tapA = curved && (modeA === "tee" || …)`), so the italic leg's root is drawn as today apart from
   the cut (section 2 says what the alternative looks like; section 11 asks).
4. **The record.** The stroke's record gains ` tee=<stroke>@<sample>/…` per end (`-` for none): the
   partner stroke's index **and the index of the nearest sample on it**, written only for a stroke
   that has an `i` end, the way `curlsg` is written only for a curl (read: line 706), so no other
   glyph's record changes. The sample index is recorded (review finding F003) so that two masters
   whose geometry picks neighbouring samples, and so slightly different tangents, are refused by the
   exporter rather than interpolated. For `R` it cannot differ: the root and the bar's samples are
   skeleton points that `xf()` scales and shears together, and the unmapped points decide. Measured
   (`teediag.js`): sample 314 of the bowl's 389 in every roman drawing, 318 of 392 in every italic
   one, identical between mult 1 and 1.5 for all 67 concept-and-slant pairs; the root is 0.74 to
   1.26 units from that sample (the bar is sampled every 2.99 units and the root is not a sample).
   The modes read `A=tee` and `ends=tee/serif`. Masters that find different partner strokes or
   samples, or one that throws, are refused by the exporter as today; test (c) pins the token's
   shape and test (a) that both weights of every concept carry the same one.
5. `crotchEnd` is untouched: an `i` end is not `""`, so it is never a joint and `crotch` ignores it.
   `g.minw` is untouched: the cut moves two points, the interior exclusion is unchanged.

The leg's record in every master of every example group (measured, `exports/modE-*.json`, before the
sample index was added to the token; with it the token reads `tee=1@314/-` roman and `tee=1@318/-`
italic):
`open n=142 A=tee B=serif curved=false tap=00 tear=null/null joins=-/- ends=tee/serif tee=1/- serifB=diag`
(roman); `open n=161 A=tee B=exit curved=true tap=10 tear=null/null joins=-/- ends=tee/exit tee=1/-`
(italic, with the taper kept; `tap=00` without it).

## 2. Measured result

Definitions, as `measure2.js` computes them and the test of section 5 restates them: the **nub** is,
over every vertex of the leg's polygons with `y > 150` that lies outside every bowl polygon and
above the bowl's lower edge at that `x`, the largest distance to the bowl's boundary; **below** is the
same restricted to vertices under the bowl's upper edge; **continuity** is the count of leg-body
vertices strictly inside a bowl polygon; the **burial margin** is the smaller of the two cut corners'
distances inside the bowl's boundary (negative if outside); the **bar half-thickness** is half the
gap between the bowl's edges at the corner's `x`; **cut tilt** is the two corners' difference in
`y`; **bowl identical** compares the bowl's and the stem's polygons with 0.4.0's point for point after
the sidebearing shift; **leg shift** is the largest distance from an old visible leg vertex between
the bar's lower edge and `y = 150` to the new leg's outline.

Over all 134 drawings with the taper kept on curved `i` ends (`modE2`; the figures with it removed
differ only where stated):

| Measure | Result |
|---|---|
| nub into the counter | **0 in all 134** (before: 95 drawings over 1 unit, up to 35.7) |
| nub below the bar | **0 in all 134** |
| continuity | ≥ 15 in every drawing |
| cut tilt | 0 in every drawing (the cut is level to floating-point) |
| burial margin | ≥ 11.56 units (Bract DisplayBold, bar half-thickness 21.22); `foil` roman 12.60 against 14.85, the thinnest bar in the set (thin 0.27); `foil` italic 14.40 against 14.85 |
| bar half-thickness at the cut | ≥ 14.3 units in every drawing |
| cut length (the buried segment) | `1.24 · w_leg`: 110 units on Bract TextRegular, 174 on DisplayBold, 77 on the tapered italic root |
| bowl and stem polygons | identical to 0.4.0 in all 134 |
| advance of `R` | unchanged in all 134 |
| leg shift below the bar, roman | ≤ 0.11 units (the pinned first sample) |
| leg shift below the bar, italic | ≤ 0.91 with the taper kept; up to 21.3 with the taper removed (the italic leg's root at full width instead of 70 %) |
| polygons, points per `R` | 9 → 8 roman, 8 → 7 italic (the disk); raw points 1802 → 1738 and 1814 → 1750; decimated 359 → 303 on Bract |

Per Bract master, nub before → after: TextRegular 14.97 → 0, TextBold 26.42 → 0, DisplayRegular
21.98 → 0, DisplayBold 35.66 → 0; italic text ×1 3.31 → 0, display ×1.5 17.43 → 0. The picture
`r-tjoin.png` (the scratch folder) shows 0.4.0, the T-join and the T-join with the italic taper kept, each
with a zoom of the junction, for Bract text, display Bold, both italics, `foil` roman and italic,
`bine`, `reverse` and `brush` Bold (read): the leg leaves the bar in a sharp notch on the lower
edge and the counter is clean in every row. The italic rows are the one visible choice: with the
taper removed the italic leg springs from the bar at full weight; with it kept the leg is drawn as
0.4.0 drew it, minus the lump.

**The filled union, not only the vertices** (review finding F006: the eye sees the nonzero union,
whose boundary includes the crossings of the leg's sides with the bar's edges, and a vertex test
cannot see a crossing). `union_check.py` unions each drawing's polygons with skia-pathops (the
library `build.py`'s raster check uses) and walks the union's boundary in a window around the
junction (`y` 150–450, from the stem to past the root): every boundary vertex there lies on the
0.4.0 stem-and-bowl outline or on one of the leg's two side edges, **worst 0.015 units** in 134
drawings (skia's float rounding); and between the stem and the point where either construction
first touches the bar (the new cut's left corner, the old disk's left extreme), above the bar's
centre line, the old and new unions' boundaries coincide both ways, **worst 0.000**: no step on the
bar's top edge. The union's contour count is unchanged (2, or 3 for an italic with its separate
foot). Two things the check had to get right, recorded so the committed version does: compare
union with union, not a union with a raw polygon (a raw polygon carries vertices hidden in its own
folds and under the stem, which are not on any boundary; the first run reported those as a 49-unit
step), and stop the top-edge window at the first point either construction touches the bar, or the
old lump itself reads as a step.

**Steps along the bar's edges from the polygons:** none can exist, because the bowl's polygons are
the 0.4.0 polygons and the leg adds no vertex on them (measured: bowl identical in all 134; nub 0
on both sides); the union check above is the statement about what is drawn.

## 3. Every other place the rule would fire, and why it is opt-in

`modF/scripts/gen.js` applies the same T-join to every `""` or `j` end that has no stroke-end
partner, with the taper kept. `universal.js` then draws every key of `G` (and of `GI` for the
italic) with Bract's `text` concept and lists the glyphs whose polygons or advance change, with the
largest visible displacement (old visible vertices to the new outline and back; hidden overlaps
excluded). Measured:

| Glyph | Where the end lies | Change at mult 1 (units) | mult 1.5 | Fix or regression |
|---|---|---|---|---|
| `9` | the tail's `""` start on the ring, 2.4 units off its centre line, nearly tangent | **throws** ("nearly parallel") | throws | neither: the rule cannot serve it, which is the fragility the letter avoids |
| `a` `à á â ä ā` | both bowl ends on the stem | 2.97 | 4.86 | a change: the bowl joins the stem at full width (today the join taper pinches it) |
| `b` `p` | both bowl ends on the stem | 6.05 | 4.3 | the same change |
| `d` `g` `q` | both bowl ends on the stem | 6.3–6.8 | 5.0–5.7 | the same |
| `h` `m` `n` `r` `ñ` | the arch's `""` start on the stem | 3.7–4.1 | 0.6–5.0 | the same, on the glyphs the caller put out of scope |
| `u` `ù ú û ü` | the bowl's `""` end on the right stem | 3.57 | 0.88 | the same |
| `B` `D` `P` | a bowl's `""` end on the stem | 1.1–2.0 | 0.45–0.6 | the same; in `reverse` it would remove the stem-side lumps of section 0 |
| `E` `F` `È É Ê Ë` `H` `K` `k` `T` `™` | a level or plumb `""`/`j` end on a stem or bar | 0.00 | 0.00 | the cut parallel to a stem is the square cut these ends already have; only the hidden disk goes |
| italic `T` | the stem's `j` start on the curved bar | 1.07 | — | the cut tilts with the bar's tangent (2°), hidden inside the bar; a digest change |
| italic `Y` | the stem's `j` start near the arms | 3.55 | — | a change at the fork |
| `K` and italic `K` | the leg's `j` start 2.5 units from the arm's centre line | not reached (outside the 2-unit tolerance) | | would flip with the tolerance: another reason not to make the rule geometric |
| `R` | the leg's `""` start on the bar, and the bowl's `""` end on the stem | 14.97 | 26.42 | the fix, plus the stem-side change the other bowls get |

35 roman and 38 italic glyphs in all (`r-tjoin.png` in the scratch folder, lower half, shows the roman and the
italic strips before and after). The rule is therefore not confinable to fixes: on every bowl and
arch it replaces the join taper's pinch with a full-width entry into the stem, which is a design
change on twenty-odd glyphs including the four the caller froze (`n m h r`), and it throws on `9`.
Hence the letter: `i` makes the T-join a decision the skeleton author takes per end, exactly as `j`
makes a square end one. With the letter on `R`'s leg only, the export comparison of section 4 shows
`R` as the only glyph that changes, in every master of every group.

## 4. Interpolation safety and blast radius

- **Point counts**: from the unfitted skeleton, unchanged (the leg has 142 samples roman, 161
  italic, as today); the disk's 64 points go. **Records**: section 1.3; `export.js` accepted all five
  example groups (14 masters) with the patched generator, and
  `tests/test_genres.py::test_every_genre_recipe_passes_params_and_exports_two_compatible_masters`
  passes against it through `FONT_DESIGN_GENRES_GEN` (measured). The T-join's partner sample is
  the same one in every master (section 1.3 item 4: sample 314 roman, 318 italic, 0.74–1.26 units
  from the root; the first draft of this section claimed distance 0, which was wrong: the root is
  a skeleton point of the bar but not one of its samples, review finding F003), the drawn
  `|T × D|` is at least 0.735 against the 0.25 refusal and the reach at most `0.462 · w` against
  the `3 · w` clamp, so no shipped `xs`, weight or slant is near a threshold; the guarantee the
  tests cover is section 5's, not more.
- **Blast radius**, from the export comparison (`exports/orig-*` against `exports/modE2-*` for the
  italic groups and `modE-*` for the roman ones, which the taper does not reach): in every master,
  the set of glyphs whose `{adv, polys, raw, runs, keptIdx, minw}` differ is exactly `['R']`; the
  set whose record differs is exactly `['R']`; **every advance is unchanged; every kern pair is
  unchanged** (0 of 4,100 in Bract; 0 in the neutral and Driftwood groups, roman and italic, with the
  taper kept; 1–2 italic pairs with it removed); title widths, word spaces and `minStrokeWidth` are
  unchanged per master; `R`'s `minw` is unchanged. That comparison becomes a committed test, (e) in
  section 5, so that after the baseline is re-recorded something persistent still says this change
  left every other glyph alone (review finding F005).

Fixtures that pin geometry or digests, and what happens to each:

| Fixture or test | Pins | Goes red? | Legitimate update |
|---|---|---|---|
| `tests/fixtures/baseline-0.1.0.json` + `tests/test_backward_compat.py` | export, decoded-TTF and manifest digests of the five example groups, from 0.1.0 | yes, all five groups, every platform key (the export digest moves with `R`'s coordinates, the TTF digest with `glyf` and `gvar`; the manifest digest does not, since no per-master figure moves) | the baseline is re-recorded from the fix commit (section 6) |
| `docs/reviews/genres-2026-11-16.md` + `tests/test_genres.py::test_a_verdict_is_stale_when_the_recipe_outlines_change` | a digest of every glyph of every recipe | yes, all ten recipes (watched red under the first draft's copy; the digest covers `R`) | a new render review and record (section 6) |
| `tests/test_genres.py` verdict/desc/risk agreement tests | the `reverse` row's "rendering defects, including the R" wording in three places | yes, once reworded | the three texts move together with the new review's date |
| hop-safari `tests/test_bract_font.py::test_the_shipped_font_matches_its_manifest`, `build.py --check` | sha256 of `gen.js` | yes, on the pin bump | rebuild and commit font and manifest together (section 10) |
| hop-safari `HAIRLINE_FLOORS`, the kern tests, `test_sparse_pairs_are_capped_at_minus_fifty` | floors; every emitted pair equals the exporter's | no (minima and every kern unchanged, measured) | none |
| `scripts/tests/test_font.py` (the font suite) | consistency with a fresh export; `want_disks` on `V A W M N v w`; the acute-joint list | no | none |
| `tests/test_versions_and_skill.py` | VERSION = SKILL.md = README badge = CHANGELOG top = package.json | yes, on the bump | all five move (section 8) |

## 5. Tests

A new `tests/test_r_leg_join.py` in the repo's tests (the property is about the shared skeleton and
the five concept files cover both shipped faces; `examples/bract/concepts.js` equals hop-safari's
`tools/bract/concepts.js` apart from the header comment, diffed). Each test runs `scripts/gen.js`
through node; none reads its source. Mutations are applied to a scratch copy named by
`FONT_DESIGN_R_GEN` (as `test_genres.py` reads `FONT_DESIGN_GENRES_GEN`, line 54), recorded in the
docstrings and in `references/testing.md` section 8.

| | Test | Asserts | Mutations that must turn it red |
|---|---|---|---|
| a | `test_the_r_leg_is_buried_in_its_bowl_in_every_concept[file]` (over the five concept files; every concept, mult 1 and 1.5, roman and italic where `x` is mapped) | nub into the counter **= 0** (under 1e-6) and nub below the bar = 0; continuity ≥ 1; the leg's polygon count is its body plus its foot's terminals (no 64-point polygon whose centre is within the bar band: no disk); **the cut's two corners, found from the body's `runs` as the first point of each edge run** (not "the first two points": `strokePolys` builds the body as `Lp` followed by `Rp` reversed, line 700, and `glyph()` may reverse the whole polygon by area, lines 961–972, so points 0 and 1 are on one edge; review finding F001; the scratch measurement used indices 0 and `2n − 1`, which the flip maps onto each other, so its figures stand), have equal `y` (level), lie **on the bar's centre line** (their `y` within `0.05 × half-thickness` of the midpoint of the bowl's edges at their `x`), inside the bowl with a burial margin ≥ `0.4 × half-thickness` (measured minimum 0.54), and **`1.24 · w` apart** (the whole cut; `0.62 · w` is the reach per side; measured 110 units on Bract TextRegular); the roman leg's direction is within 0.5° of `atan2(−340, 250 · xs_eff)` with `xs_eff` restated from `xs`, `mult` and the italic factor, and its last centre sample is on the baseline; the leg's `tee=` token names the same stroke and sample at mult 1 and 1.5 | **M1** `i` back to `""` on the leg (95 of 134 red on the nub). **M2** the cut placed at the partner's far edge, the first draft's flush corner (`pts[k] + T · reach`, reach = half the partner's width): red on the centre-line and margin assertions in every drawing, and on the nub in the swell concepts. **M3** a square cut at the centre line (`cutSide` with the leg's own normal): red on "equal y" and on the nub (26 vs 21.5 on Bract TextRegular). **M4** the cut kept and the disk still drawn (the `mode === "disk"` branch reached for `tee`): red on the polygon count and the nub. **M5** the leg re-rooted below the bar (`M 320 300`, `i` throws: no interior stroke; with `""`, continuity 0): red either way. **M6** the leg re-rooted on the curve (`M 470 390 L 570 0`): red on the angle. **M7** the sample index dropped from the token (red on the token's shape) |
| b | `test_the_measurement_sees_the_0_4_0_defect` | the measurement of (a), applied to the 0.4.0 `R` skeleton written into the test as a literal, reports a nub ≥ 10 on Bract `text` at mult 1 (measured 14.97) and a disk polygon, so a blind measurement fails here and not silently in (a). **Run in a fresh node process** that installs the literal into `m.G.R` before its first and only draw of `R`: `glyph()` returns `cache[P.key].g[key]` when it exists (lines 902–904), so an in-process swap after any draw of `R` with the same concept and mult reads the new skeleton (review finding F004). This test is a control: it is **green before and after** the fix, and red only when the measurement is broken | the bowl polygon set made to include the leg (nub always 0): red here, green in (a) alone; the lower-edge rule inverted: red; the literal drawn after a warm draw of `R` in the same process (the cache; red here, which is why the fresh process is spelled out) |
| c | `test_an_i_end_is_cut_parallel_to_the_stroke_it_runs_into` | synthetic glyphs installed in-process **before any draw** (each test case under its own concept key, so no case reads another's cache), drawn with the project's first concept at mult 1 and 1.5, **and again through the x-height map at `xh` 400 and 600 and at the italic shear** (review finding F002: the map and the shear change the drawn tangents the cut reads): (1) a level bar `""`/`""` from (100, 340) to (540, 340) and a 54° stroke starting `i` at (320, 340): the record reads `A=tee … ends=tee/… tee=0@<k>/-` with `k` the same in every variant, the cut's two corners (from `runs`) share the bar's drawn `y` and lie `1.24 · w` apart, no terminal polygon; the same with the bar drawn as a ring: `tee=0@<k>/-` and a cut parallel to the ring's tangent there (not level); (2) a 30° bar: the cut is parallel to it within 0.1° and `cutSide`'s clamp is not reached; (3) an `i` start at the bar's END (320, 340 with the bar from 320 to 540): throws "meets another stroke's end"; (4) an `i` start 3 units off the bar: throws "lies on no other stroke's interior"; (5) a stroke at 10° to the bar: throws "nearly parallel" naming the drawn cross product; (5b) a stroke at 20° to the bar whose end is wide enough that the reach would pass the clamp (a stroke at `W` 300 against the clamp arithmetic): throws naming the reach; (5c) a stroke at 16° at `xh` 500 that the map at `xh` 400 turns to 14°: throws at 400 and draws at 500, and the two records differ, which is what the exporter refuses; (6) the same stroke typed `""` draws the 0.4.0 disk and no `tee=` token; a `j` stroke draws a square cut and no token | the `tee=` token dropped from the record (red on 1); the sample index dropped (red on 1); the partner search accepting a stroke end (red on 3); the tolerance widened to 4 units (red on 4); the parallel refusal removed, or read on the unmapped vectors only (red on 5 and 5c); the clamp refusal removed (red on 5b); the cut direction taken from the bar's chord instead of its local tangent (red on the ring case of 1); the rule widened to `""` ends (red on 6) |
| d | `test_the_italic_leg_keeps_its_join_taper` | on the italic `R` of every concept that maps `x`: the leg's width at its root equals `w × 0.7` (the taper kept: the operator's decision, section 11), restated from `tapL = 0.9 · W0` and the taper formula; the roman leg is untapered | the `tee` term dropped from `tapA` (red) |
| e | `test_only_the_r_changed_since_0_4_0` (review finding F005) | exports every group of the three examples twice through the real `export.js`: once with `scripts/gen.js`, once with `gen.js` as committed at `598044b` (`git show 598044b:scripts/gen.js` into a temporary folder beside a copy of `export.js`, the way `tests/baseline_digest.py --repo` builds a checkout), and asserts per master that the glyphs whose `adv`, `polys`, `raw`, `runs`, `keptIdx` or `minw` differ are exactly `{"R"}`, that the glyphs whose record differs are exactly `{"R"}`, that every advance is equal, that the 54-bin left and right profiles recomputed in the test from every glyph's raw polygons are equal for every glyph (`R`'s included: its profile does not move), that the emitted kern list is identical pair for pair and value for value, and that `titles`, `space` and `minStrokeWidth` are equal. The comparison is the one section 4 reports; a committed test is chosen over a one-off script because the baseline's `supersedes` note cites it by name and CI runs it. Cost: ten exports, about a minute (inferred from the scratch runs) | the leg's `""` left in the italic `R` only (red: the italic groups' changed set is empty, not `{"R"}`); a kern pair's value nudged in `export.js` (red on the kern list); the comparison skipping `raw` (green under a change confined to undecimated points: the field list is asserted in the test's own docstring, so this is the one mutation recorded as not catchable by execution) |
| f | `test_the_filled_union_near_the_join_is_the_old_outline_plus_the_leg[file]` (review finding F006) | `tests/r_leg_junction.js` dumps `R`'s polygons for every drawing of (a), with the 0.4.0 polygons drawn by the `598044b` generator of (e); the test unions each set with `pathops.union` and asserts, in the window `y` 150–450 from the stem to past the root, that every vertex of the new union's boundary lies within 0.05 units of the 0.4.0 stem-and-bowl outline or of one of the leg's two side edges (measured worst 0.015), and that between the stem and the point where either construction first touches the bar, above the bar's centre line, the two unions' boundaries coincide both ways within 0.05 (measured 0.000) | **M2** (red: the flush cut's corners sit on the bar's edge and skia keeps them as boundary vertices); **M4** (red: the disk's arc is on the boundary); the window started at the root instead of the stem (green under a step left of it: the window is pinned in the docstring) |

Suite count: `tests/` holds 17 files today (read); this adds one file with six tests, two of them
parametrised five ways, and one node script. Clear `__pycache__` between mutation runs (testing.md
section 7).

## 6. Fixtures that are re-recorded, and the exact claim each one makes afterwards

### 6.1 The compatibility baseline

`test_backward_compat.py` holds the three examples to digests recorded from 0.1.0 (`0fc4314`), per
platform and node major (`darwin/20`, `darwin/22`, `darwin/26`, `linux/20`, `linux/22`; read). This
change moves the export and TTF digests of every group, by design. Excluding `R` from the digests
is not an option: the export digest could drop the glyph, but the decoded-TTF digest covers `glyf`
and `gvar` whole, and a digest that skipped tables would stop proving what it proves now. So the
baseline moves to the fix commit:

1. `tests/fixtures/baseline-0.1.0.json` is replaced by `tests/fixtures/baseline.json` with
   `baseline_rev` = the sha of the commit that carries the generator change, `baseline_version`
   (`"0.5.0"`), and `supersedes` naming `0fc4314`, `0.1.0`, the reason ("the R's leg root; the
   export and TTF digests of every group moved, the manifest digests did not") and the test that
   proves the rest stayed (`tests/test_r_leg_join.py::test_only_the_r_changed_since_0_4_0`, section
   5 e). The 0.1.0 file stays in git history. The manifest digest is expected not to move: it
   excludes `sources_sha256` and the tool versions (read: `tests/baseline_digest.py` lines 20 and
   66), and no per-master figure changes (review finding F007, rejected on that reading).
2. `tests/baseline_digest.py`: `FIXTURE` renamed; the header's commands name the new rev; the guard is
   already parametrised by `--rev`.
3. `tests/test_backward_compat.py`: the literal `0fc4314` in the fixture test, `crafted()`, the
   instructions test and the merge test become the new rev; the module docstring states the promise
   below and names the one departure.
4. `.github/workflows/record-baseline.yml`: the worktree and `--rev` take the new sha; the matrix
   gains `macos-latest` so `darwin/20` and `darwin/22` are recorded without installing older node on
   the author's machine (node 26 only; read: `/opt/homebrew/opt`). `tests/test_ci_workflow.py`'s
   literal assertions (`runs-on: ubuntu-latest`, the worktree line, the `--record` line) follow.
5. Order, because the guard refuses a tree whose scripts differ from the rev and the workflow must
   name a commit that exists (review of the diff, F001): **commit A** (generator, tests, docs, version,
   the fixture with `baseline_rev: "COMMIT_A"`, the workflow and the test literal reading `COMMIT_A`;
   both tests assert a git-sha shape, so A's tree is red on them by design), NOT pushed; then
   `A=$(git rev-parse --short HEAD)`, `sed -i '' "s/COMMIT_A/$A/" tests/fixtures/baseline.json
   tests/test_backward_compat.py .github/workflows/record-baseline.yml`, then
   `.venv/bin/python3 tests/baseline_digest.py --record --rev $A` (re-records `darwin/26` under the
   script-identity guard, same digests as the `--print` entry), the two tests green, **commit B**; then
   push. CI runs on B: `record-baseline` (on `pull_request`, `paths: scripts/gen.js`) records the
   baseline from a worktree at A on ubuntu and macos × node 20 and 22 and uploads `entry-baseline.json`,
   `entry-head.json` and `genre-digests.json` per leg. The compat test on CI is red on every leg until
   **commit C** merges the four entries (`.venv/bin/python3 tests/baseline_digest.py --merge
   entry-baseline.json`, once per downloaded artifact); the genre test is red on the node 20 and 22 legs
   until C adds each leg's `genre-digests.json` content under `by_node_major` in
   `docs/reviews/genres-<date>.md` (review of the diff, F002: the record holds node 26 only, because the
   machine that wrote it could not run the other majors). The PR merges only after C, with A, B and C.

The promise, exactly, for `generator.md` section 11 and the test docstring: a project on 0.1 to 0.4
that copies 0.5's `scripts/` and rebuilds without touching `concepts.js` or `font.json` gets the same
outlines and tables as before **except the glyph `R`**, whose leg root is redrawn (the disk gone,
the end cut level on the bar's centre line; every other point of `R`, its advance and its kerns
unchanged); the three examples' digests are now held to the 0.5.0 record, per platform and node
major, and a later change that moves them is a regression unless its changelog says otherwise.

### 6.2 The genre review record

`tests/test_genres.py` pins a digest of every glyph of every genre recipe to
`docs/reviews/genres-2026-11-16.md` and says the remedy for a stale digest is a new render review,
not an edited digest (read: genres.md section 6, the test's docstring). So:

1. Build the genres page and shoot it as genres.md section 6 says, and read `R` in every recipe at
   1280 px, 2×, plus a confirmation that nothing else on the page moved (only `R` changed, section 4;
   for the recipes themselves, the host's 5,240-drawing comparison of every recipe glyph against 0.4.0).
   The operator's ruling of 2026-11-19 (F009) accepts this targeted re-read in place of a full one.
2. Write `docs/reviews/genres-<date>.md` in the same shape: the ten verdicts (expected unchanged;
   the `reverse`, `clarendon` and `slab` "rendering defects" notes no longer name the `R`'s leg, and
   the `reverse` note names the stem-side lump instead), the new date, and the digests under node
   majors 20, 22 and 26.
3. Point `RECORD` in `tests/test_genres.py` at the new file; update the verdict dates in the
   genres.md table, each recipe's `desc` and `content.genres.json`'s `risk` strings together.

If the operator would rather not spend a review on ten recipes for one glyph, the alternative is to
re-record the digests under the existing date with a note that only `R` changed and the `R` crops
were read; genres.md's own rule forbids that today, so it would need the rule changed in the same
commit. Section 11 asks.

## 7. Docs to update in the same change

- `references/generator.md`: section 2's end-type table gains the row `i` ("a T-join: the stroke
  ends on another stroke's centre line, at an interior point; cut parallel to that stroke there, no
  terminal; the generator refuses an `i` end that meets a stroke's end, lies on no stroke, or runs
  within 14.5° of the stroke it meets; the `R`'s leg"); the joint paragraph gets one sentence
  distinguishing the three meetings (a joint or corner: two ends; a T-join: an end on an interior;
  a hidden join: an end inside a thicker stroke, `""`); section 3's "Join taper" line adds the
  curved `tee` end if the taper is kept; section 5 gains the row `tee` (an outcome of `i`); section
  11's compatibility promise (6.1); section 12 gains the `tee=` token beside `curlsg`, and the
  measured-margins paragraph the leg's 54° against the 14.5° refusal.
- `references/traps.md`: row 36, "The `R` shows a round lump in its counter where the leg leaves the
  bowl" — cause: a hidden-join terminal (`disk`, `0.42 · w` of the joining stroke) on a stroke
  thinner than itself; detection: `tests/test_r_leg_join.py`; guard: the leg's end is a T-join (`i`),
  cut level on the bar's centre line and buried; where it bit: Bract (shipped 2026-11-15, 15–36
  units at the four masters), the genres page (issue #1 item 2, whose `reverse` lump is in fact at
  the bar's stem end and stays open). A second sentence in the row records the rejected flush
  construction, so the next person does not reach for the corner pass.
- `references/genres.md` section 7: the `R` bullet becomes "fixed in 0.5.0" with the numbers, and a
  new bullet records the stem-side lumps of `P`, `B` and `R` in `reverse` (section 0) as open; the
  `reverse` row's cell, the recipe's `desc` and `content.genres.json`'s `risk` are reworded together
  (6.2).
- `references/testing.md`: section 8 gains the four tests and their mutations.
- `CHANGELOG.md`: a `## [0.5.0] — <date>` entry: Fixed (the `R`, with the before/after numbers and
  the statement that no advance, kern or other glyph moved), Added (the `i` end type and the `tee=`
  record token), Changed (the compatibility baseline re-recorded and the promise restated; the
  genres review re-run), and the pointer to this plan.
- `VERSION`, `SKILL.md` (frontmatter `metadata.version` and the "**Version 0.5.0**" line),
  `README.md` badge, `package.json` `version` (the test checks all five).
- `scripts/gen.js`: the header comment's list of end letters (line 35, `s = stem end … '' = join`)
  gains `i`; a one-line comment at the `R` skeleton.
- Issue #1: a comment resolving item 2 for the leg root with the numbers, reattributing the
  `reverse` lump to the bar's stem end on `P`, `B` and `R`, leaving item 1 open.

## 8. Version: 0.5.0, a minor bump

A patch would say "a drop-in with the same output". This change alters every project's `R`, moves
every compatibility digest, re-records the baseline, adds an end-type letter and re-dates the genre
verdicts: behaviour changes with a documented migration, which is what the minor number has marked
here (0.2 added knobs, 0.3 the sparse cap, 0.4 the reusable workflow; read: CHANGELOG). 0.4.1 is
defensible if the operator reads the promise as "same fonts except where a documented defect was
fixed"; section 11 asks, and the recommendation is 0.5.0.

## 9. Order of work

1. Generator (section 1.3), from the scratch prototype's diff; `node --check`; the export of the
   five example groups before and after and the comparison of section 4 (the "before" scripts are a
   copy of `origin/main`'s).
2. Tests of section 5, written first against the unmodified generator: (a) and (f) are red there
   (the defect), (b) is green there and stays green (it is the control that the measurement sees the
   defect), (c) and (d) fail on the missing letter, (e) is green there (nothing has changed yet) and
   must stay green after the fix. Then each mutation through `FONT_DESIGN_R_GEN`, logged (review
   finding F004 corrected the first draft, which had (b) red before the fix).
3. The repo suite: `tests/` green except `test_backward_compat` and the genre staleness test, both
   expected red until step 5; `scripts/smoke.sh --full` steps 1–7.
4. Docs and version (sections 7, 8).
5. The genre review (6.2: a targeted re-read of each recipe's `R`, by the operator's ruling of 2026-11-19) and its record under node 26; commit A (with the `COMMIT_A` placeholder);
   commit B (the placeholder replaced by A's sha, `darwin/26` re-recorded under the guard); push; CI
   runs on B: the compat test and the node 20/22 genre legs stay red until commit C merges the
   recorded entries and digests from the `record-baseline` artifacts (6.1 step 5); then CI is green on
   both OSes and both node majors.
6. Impasse review of the whole diff, both commits, with `r-tjoin.png`, `junc.png` and the export
   comparison as evidence; reconcile; re-review once.
7. Merge to `main`; then section 10.

Serial; nothing parallelises usefully.

## 10. Follow-on: the rollout to hop-safari and to `~/.claude`

hop-safari pins the skill at `tools/font-design` = `4538c4c` (0.3.1; read) and
`~/.claude/skills/font-design` is at `598044b` (0.4.0; read). The site's procedure is
`tools/bract/README.md` "Bumping the skill" (read); with what this change makes each step show:

1. `git -C tools/font-design fetch && git -C tools/font-design checkout <0.5.0 sha>`.
2. `.venv/bin/python3 tools/font-design/scripts/build.py --font tools/bract/font.json --check` fails
   with "manifest DIFFERS" naming `gen.js` in `sources_sha256`. Expected.
3. `git show HEAD:static-pages/fonts/bract/Bract-VF.woff2 > OLD.woff2`; rebuild;
   `.venv/bin/python3 tools/bract/font-diff.py OLD.woff2 static-pages/fonts/bract/Bract-VF.woff2 --locations 400,40 500,40 700,40 400,80 700,80`.
   It exits 1 (no allowance exists for a changed glyph; read: its header), and every line it prints
   must name `R`: `R`'s default outline and every `gvar` tuple; `R` instanced at the five locations.
   It must print nothing else: no `hmtx` or HVAR line (advances unchanged), no GPOS pair (every kern
   unchanged), no shaping difference, no cmap, fvar, avar, STAT, GSUB, gasp, prep, name, hhea, OS/2
   or head line (`xAvgCharWidth` cannot move: no advance did). An unexplained line stops the bump.
   `--allow-glyph-change NAME` for `font-diff.py` would make this exit 0; optional, hop-safari's own
   change.
4. `tests/test_bract_font.py`, then the full suite (`RBENV_VERSION=3.2.8`; read: hop-safari
   CLAUDE.md). `HAIRLINE_FLOORS` hold; the size budget holds (`R` loses 56 decimated points).
5. One design-review crop at 1×: shoot an essay whose H1 sets a capital `R` in Bract and the
   specimen with the skill's `shoot.py` at widths 1280 and 500, scales 1 and 2, and read the `R` at
   the text size (Regular and Medium) and the display size: the counter is clean, the leg leaves
   the bar in a sharp notch, the bowl and bar are as before. Record what was seen in
   `docs/bract-font.md`; the crop stays out of the repo.
6. Commit the pointer, the woff2 and `manifest.json` together with the font-diff summary in the
   message, and a dated section in `docs/bract-font.md` ("The R's leg root, 0.5.0") with the four
   masters' numbers and the statement that no advance, kern, floor or other glyph moved.
7. `~/.claude/skills/font-design`: `git checkout <same sha>` in the submodule, then a `~/.claude`
   commit of the pointer (`git add` and `git commit` as separate calls there; read: the global
   CLAUDE.md).

## 11. Risks and questions for the operator

Risks:
- `cutSide`'s clamp (`3 · w`) and the 14.5° refusal are the T-join's limits; `R` is at 54°. (As planned,
  a skeleton that used `i` at a shallow angle was expected to get a clamped, partly square cut between
  14.5° and about 20°. As built, `teeCut` THROWS instead of drawing: below 14.5°, past the clamp, or
  with the cut crossing the partner's edge or its midpoint outside the partner; the clamp case is
  unreachable, since the 14.5° refusal bounds the reach at 1.87 widths. Nothing is drawn partly square.)
- The genre re-review is a reviewer pass over ten recipes for a one-glyph change; the digest test
  leaves no cheaper honest route (6.2).
- The compatibility baseline moves for the first time, and the recording path (`--repo`, the merge
  refusal, the new macOS leg) is exercised for a non-0.1.0 rev for the first time.
- The italic `R` has never been design-reviewed (read: generator.md section 9); the choice in
  question 1 is made on the scratch picture, not on a page.

Questions, each with the recommendation and **the operator's answer (2026-11-18, after the Impasse
review): every default was taken.**
1. **The italic leg's root: keep the join taper (the leg drawn as 0.4.0 draws it, minus the lump;
   shift ≤ 0.9 units) or drop it (full weight at the root, up to 21 units thicker there)?**
   Recommendation: keep it; the fix then changes nothing visible but the nub. **Answered: keep it**
   (test d pins it).
2. **Version 0.5.0 or 0.4.1?** Recommendation: 0.5.0 (section 8). **Answered: 0.5.0.**
3. **The genre review: a full re-read with a new dated record (the rule as written), or digests
   re-recorded under the old date with the rule amended?** Recommendation: the full re-read.
   **Answered 2026-11-18: the full re-read; ruled again 2026-11-19 (review of the diff, F009): a targeted
   re-read of each recipe's `R` with a new dated record is accepted**, the evidence that the rest of each
   recipe is unchanged being the host's comparison of every glyph of every recipe in
   `templates/concepts.genres.js`, mult 1 and 1.5, roman and italic, 0.4.0's `gen.js` (`598044b`) against
   the fix: 5,240 drawings, only `R` changed (re-run by the implementer after F004–F007, same result).
4. **The stem-side lumps of `P`, `B` and `R` in `reverse` (the bowl's curved end at a stem thinner
   than its disk): fix now by typing those ends `i` too, or record on issue #1 and leave?**
   Recommendation: record and leave; typing them `i` would change `B`, `D`, `P` and `R`'s
   bar-to-stem joins on every face (1.1–2.0 units on Bract Regular, section 3), a second design
   decision. **Answered: record on issue #1 and leave.**
5. **Should the font suite that ships to sites also carry test (a) on the project's own concepts?**
   Recommendation: no for now. **Answered: no.**
6. **Record `darwin/20` and `darwin/22` from a macOS runner (the workflow matrix change) or install
   `node@20` and `node@22` here and log it in `~/log.txt`?** Recommendation: the runner.
   **Answered: the runner.**

## 12. Independent review and what it changed

**Revision history.** The first draft (2026-11-18, same day) proposed the corner construction: the
bowl split into a curve and a bar at the leg's root, the leg's start typed `j`, the joint and corner
pass widened to `j` ends, so that the leg ran out to the bar's far edge and was cut level flush with
it. The operator rejected it the same day after the caller's zoom (`junc.png`): a flush
joint between two outlines is fragile — the cut was placed at the nominal edge while the bar's drawn
edge varies with the swell, leaving the cut 0.28 units proud on Bract TextRegular and up to 3.1 on
`brush` Bold (the first draft's own residual), and the bowl split added a second end-to-end flush
joint with the same fragility; and the corner pass models two ends meeting, not a stroke ending in
another's interior. This draft's T-join (section 1) buries the cut on the centre line, leaves the
bowl whole, and measures 0 residual in all 134 drawings (section 2).

**Independent review** (Impasse, review id `r-leg-plan-independent-review`, 2026-11-18, of revision
2 of this plan). Eight findings; each was checked against `scripts/gen.js` at `598044b` by the host
before the disposition below, and the measurements the accepted ones asked for were made on the
scratch copies the same day (`teediag.js`, `union_check.py`).

| # | Finding | Checked | Disposition and change to the plan |
|---|---|---|---|
| F001 (high) | tests (a) and (c) took "the leg body's first two points" as the cut; the body is `Lp` + reversed `Rp` and may be flipped by area, so points 0 and 1 lie on one edge | read: gen.js 700, 961–972 | accepted: the corners are found from the body's `runs` (the first point of each edge run) and the full cut length `1.24 · w` is asserted (section 5 a, c). The scratch measurement used indices 0 and `2n − 1`, which the flip maps onto each other, so its figures stand |
| F002 (high) | `i` decided on unmapped geometry while `cutSide` skips a cut when the DRAWN cross product is under 0.25 and clamps at the reach; a master could carry a `tee` record with an uncut end | read: gen.js 411–416; measured: drawn `|T × D|` ≥ 0.735, reach ≤ 0.462 w over the 134 drawings | accepted: the T-join computes the drawn cross product and the needed reach per master and throws below 0.25 or past the clamp (section 1.3 item 2); test (c) gains the `xh` 400/600 and italic-shear variants and the clamp and threshold-crossing cases (5b, 5c) |
| F003 (medium) | "the partner is found at distance 0" is false: the bar is sampled every 2.987 units and the root is about 1 unit from the nearest sample; the chosen sample was not recorded | measured: 0.74–1.26 units; sample 314 roman, 318 italic in every drawing, equal across weights for all 67 pairs | accepted: the claim is corrected (sections 1.3, 4); the `tee=` token carries the sample index, so masters that pick neighbours are refused; tests (a) and (c) pin the token and its equality across weights (M7) |
| F004 (medium) | test (b) installed the 0.4.0 `R` in-process, but `glyph()` serves the cache first; and the work order had (b) red before the fix, though it asserts the old skeleton HAS the nub | read: gen.js 902–904 | accepted: (b) runs in a fresh node process that installs the literal before its only draw of `R`, is described as a control that is green before and after, and gains the cache mutation (section 5 b, section 9 step 2) |
| F005 (medium) | after the baseline is re-recorded nothing persistent says the other glyphs were left alone | read: test_backward_compat.py, baseline_digest.py | accepted: test (e) exports every example group with `gen.js` at `598044b` and at HEAD and compares every non-`R` glyph's polygons, advance, 54-bin profiles and the emitted kerns; a test rather than a script because CI runs it and the baseline's `supersedes` note cites it (sections 4, 5 e, 6.1) |
| F006 (medium) | the nub metric is over leg vertices; the visible outline is the filled union, whose boundary includes the crossings of the leg's sides with the bar's edges | measured with skia-pathops on `modE2`: worst boundary vertex off the 0.4.0 stem-and-bowl outline and off the leg's sides 0.015 units; bar top-edge step 0.000, both ways, all 134 drawings | accepted: the measurement is in section 2 with its two pitfalls, and becomes test (f). Harder than stated: comparing a union with a raw polygon reports hidden fold vertices as a 49-unit step, and a window that reaches the root reports the old lump as a step; both are fixed in the check and pinned in its docstring |
| F007 (medium) | the manifest digest would move with the source hashes | read: baseline_digest.py 20, 66: the manifest digest drops `sources_sha256` and `tools`; `--check` is what fails on the source hash | rejected, no change: section 6.1 now states why the manifest digest is expected to hold |
| F008 (medium) | the evidence lives in a session scratch folder nobody else can run | read: this plan's own references | accepted: the measurement and comparison are committed as `tests/r_leg_junction.js` and `tests/test_r_leg_join.py`, every figure here is marked provisional until re-stated from their output (status paragraph), and the record quotes the committed run |

Operator answers (2026-11-18): section 11, every default: keep the italic join taper; 0.5.0; the
full genre re-read; record the `reverse` lumps on issue #1; test (a) stays out of the site-shipped
suite; the macOS runner records `darwin/20` and `darwin/22`.

**Review of the finished diff** (Impasse, review id `r-leg-implementation-independent-review`,
2026-11-19): F001 the commit order (the workflow and the test literal must name an existing commit:
commit A, then B replaces the placeholder and records under the guard, then push; section 6.1 step 5
and section 9 step 5 corrected); F002 the genre record holds node 26 only, so CI's node 20 and 22 legs
stay red until commit C adds their digests from the `record-baseline` artifacts, which now carry
`genre-digests.json`; F003 the mutation run for test e was in `gen.js`, and an exporter defect cancels
out of that comparison (testing.md section 8); F004 the pinned edge (not the pin's reach, a width)
enters the `tee` token as a side letter; F005 the burial check samples the whole cut (the wave case);
F006 a ring partner's outer contour by area, the ring drawn both ways; F007 the partner is the nearest
sampled segment, recorded by index (the mid-gap case); F008 the compat test's exact guarantee stated;
F009 (operator ruling): the targeted `R` re-read accepted, with the host's 5,240-drawing comparison as
the evidence for the rest. Every changed guard was watched red under a mutation chosen as the weakest
change that breaks the property (testing.md section 8).

**Re-review of the finished diff** (Impasse, review id `r-leg-implementation-rereview-independent`,
2026-11-19, five findings, all accepted): R1 the token's side letter was bucketed from the angle with a dead
band, inside which two masters could pin opposite edges and record alike; it now records the edges `clipPast`
pinned (`L`, `R`, `LR`, `=`), and the reviewer's crossing construction reads `R` at mult 1 and `L` at 1.5, which
the exporter refuses. R2 nine probes along the cut could miss a narrow dip; the check is exact (no crossed edge,
midpoint inside), with a narrow-trough fixture that nine probes drew. R3 a reversed hand-written ring CAN be
drawn when the fit is off (`fitSkeleton` returns the skeleton untouched), which the first attempt missed; the
reversed ring runs in that variant and the push-order mutation is red on it. R4 the workflow step piped python
into `tee` under a shell without pipefail; it writes the file first. R5 this plan's status and the shallow-angle
risk were prototype-era text; corrected above. The `R`'s tokens after R1: `1@314L/-` roman, `1@317L/-` italic in
every master; no outline moved.
