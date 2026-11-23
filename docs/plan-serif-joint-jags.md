# Plan: clean serif brackets, corners, the G's chin and the italic r's arm (0.10.0)

WHAT IT'S FOR: the implementation plan for the request "fix the jagged joints in the italic w, G and r that
`scripts/gen.js` draws, and any other glyph with the same cause". It records what each jag is, which are
defects of the generator and which of a skeleton, the exact edits, the tests that must fail first, and who can
verify each piece. Written 2026-11-22 on branch `feature/serif-joint-jags`, from `main` at the 0.9.0 merge.

All paths are relative to the repository root. The request's evidence (renders and three Node scripts) is in the
main checkout's `.claude/requests/serif-joint-jags/`, outside this worktree. The shipped Driftwood concept is
`tools/driftwood/concepts.js` in the movingavg-website repository; it equals `examples/driftwood/concepts.js`
plus `headSink: 0.6`.

**Markers.** **(read)** = checked against the named file. **(measured)** = run here on 2026-11-22 with node 26
against the unmodified `scripts/gen.js` and against a patched copy kept in the session scratch folder, outside
the repository. Those copies are not available to the implementer; every figure below is restated by the new
tests. **(inferred)** = not verified; the implementer must check before relying on it.

**As built (2026-11-22).** Everything in sections 0.1 to 0.5 and "Code to be changed" was built as written, character for
character, and the nine tests of `tests/test_serif_joints.py` and the one of `tests/test_joint_spacing.py` are the ones the plan
describes. Departures and findings, each also recorded where named:

- **The compatibility baseline** (follow-up, 2026-11-22): commit 1dc3856 replaced the placeholder `COMMIT_A` with 6302b8a in the fixture, the
  test literal and the `record-baseline` workflow, and recorded `darwin/26` with `tests/baseline_digest.py --record`. The two
  tests that were red by design are green (`tests/test_backward_compat.py` and `tests/test_ci_workflow.py`: 28 passed). The `linux`
  and the node 20 and 22 entries still wait for the `record-baseline` workflow.
- **The genre review record** is `docs/reviews/genres-2026-11-22.md`. The round-1 page sets all nine letters (`G M Z z 2 4 5 7 e`) in
  each recipe's specimen line, so none had to be left unread. They were read at Regular only, at specimen size, with the Didone's
  and the Clarendon's `G` and `M` enlarged. Two files outside the plan's list carry the verdict dates and
  `tests/test_genres.py` holds them equal to the table in `references/genres.md`: `scripts/concepts/content.genres.json` and
  `templates/concepts.genres.js` changed from 2026-11-19 to 2026-11-22. Only node 26 is recorded; the node 20 and 22 digests wait
  for the workflow (`genre-review-acceptance`).
- **An equivalent mutation, retired (follow-up, 2026-11-22).** `headsink-zero-on` is removed from `scripts/tests/mutate.py`; the reason
  and the measurement are in `references/testing.md` section 11; the guards are LEVEL-END and HEAD-END-FLAT.
- **The kern bound (follow-up, 2026-11-22).** The operator chose a bound over holding the `G`'s left profile; `tests/test_joint_spacing.py`
  holds a roman pair with `G` on the right within 0.05 units and every other refused pair exactly.

  **The kern guarantee, exactly.** Of the kern pairs a font ships, the ones 0.10.0 changes are, in a roman group, pairs with `G` on the left and, in an italic group, pairs that contain `G` or `r`. Before rounding, a roman pair with `G` on the right and another glyph on the left also moves: it reads the `G`'s left profile, and the redrawn bowl's sample points shift that profile. On the three examples 639 such pairs move (Bract 207, Driftwood 147, neutral 285), by 0.0364 units at most, and `tests/test_joint_spacing.py` holds each of them under 0.05 units. `export.js` rounds an automatic kern to a whole unit (`Math.round`) and `build.py` writes that whole number, so a move this small changes a shipped value only where it crosses a rounding boundary, and then by 1 unit. On the three examples it changes none: the one pair that crosses, the Driftwood roman Bold's `ú` before `G` (-21.5065 to -21.4970, which round to -22 and -21), is outside Driftwood's `kerning.set`, so it is never written to the font. Every other automatic kern is the value 0.9.0 computes, to 1e-9 units. This is measured on the three examples and is not a claim about another face: `update-check.py` reports the kern values that change before a site adopts 0.10.0.
- **The watches** W1 to W10 and the spacing recipe (W11) were run as written and are logged in `references/testing.md`
  section 11. W5 did not survive (the plan allowed that it might). The watches of `tests-since-revision` were run in the follow-up and are logged in `references/testing.md` section 11.
- **Not changed or not run here:** the tag `v0.10.0` and the CI run on the branch (`release-acceptance`), the
  operator's look at the redrawn `G` and `r` (`design-acceptance`), and the `Releases` line of the CHANGELOG.

## 0. Findings

### 0.1 Italic w: the bracket leaves the stroke (generator defect; the operator's direction is confirmed)

`strokePolys` picks the serif routine with `serifKind(TU)`: `|TU[0]| > 0.1` gives `diagSerifPoly`, otherwise
`serifPoly` (read, `scripts/gen.js` lines 656 to 661). `serifPoly` puts every bracket point on the plumb lines
`x - w/2` and `x + w/2` (read, lines 580 to 617). A stroke that leans by less than 0.1 therefore gets brackets
that do not follow its edge. The comment in `diagSerifPoly`, "every italic stem is slanted, so all italic
serifs come through here", is false for such a stroke.

Every serif end whose stroke leans but takes the `head` or `foot` kind, enumerated over all 131 keys of `G`
(with `GI` in the italic), every serif concept of the three example concept files, roman and italic at 10
degrees, mult 1, 1.3, 1.5 and 1.65 (measured):

| Glyph and end | Kind | Drawn lean (x per unit of y) | Where |
|---|---|---|---|
| italic `w`, `GI.w` stroke 0, start | lowercase head | 0.085 to 0.126 | 8 of the 12 serif example concepts: bract `text`, `display`, `foil`, `burin`, `field`, `burin2`, `burinD`; driftwood `driftwood`. In `blind`, `cone` and neutral `text`, `display` the same end is `diag` |
| italic `W`, `GI.W` stroke 0, start | symmetric head | 0.034 to 0.115 | all 12 |
| roman `M`, `G.M` stroke 0 start and stroke 3 end | foot | 0.025 to 0.034 | all 12 |

Nothing else. The w is not the only one. An italic slanted by less than 5.7 degrees would put every stem in
this list; no shipped group has one.

How far a bracket tip stands outside its stroke body, concepts as shipped (measured; the request's figures for
the w were 6.8, 7.9 and 9.1):

| | mult 1 | mult 1.3 | mult 1.65 |
|---|---|---|---|
| driftwood italic `w` (with and without `headSink` 0.6) | 6.8 | 7.9 | 9.0 |
| driftwood italic `W` | 2.8 | 3.7 | 4.6 |
| neutral `text` italic `W` | 5.3 | 7.2 | 9.5 |
| driftwood roman `M` | 2.3 | 2.6 | 3.0 |
| bract `text` roman `M` | 2.6 | 3.1 | 3.7 |

Two smaller defects share the cause. The leaning end is cut square to the stroke, not level, so one corner of
the roman `M`'s feet hangs below the baseline: 1.04 to 1.90 units on the Driftwood example, 1.23 to 2.24 on
Bract `text` (measured). And the `headSink` pin moves points straight down, which takes a leaning stroke's
corner off its own edge by `lean x drop`: 1.8 to 1.9 units on the Driftwood example's w, 2.5 to 3.4 on Bract `text`'s (measured).

**Direction, confirmed.** `serifPoly`'s head and foot brackets, in the bracketed branches and in the
`serifBracket` blend branches, end on the stroke's own edge: the straight line through the end's corner along
the end's direction, as `diagSerifPoly`'s `onEdge` does. A leaning head or foot end is cut level, as a `diag`
end already is. The `headSink` pin moves along that edge. On an exactly plumb stem all three are the expressions
0.9.0 evaluates, so the output is the same bytes.

Exact guarantee after the fix: a bracket tip lies on the straight edge line of its end. With `swell` set, a
stroke narrows away from its end, so the drawn edge falls inside that line by 1.3 to 2.6 units at the bracket's
height on every upright stem of the shipped example concepts today (measured), and the leaning ends join them:
driftwood italic `w` 1.4, 1.8, 2.4; `W` 0.9, 1.2, 1.5; roman `M` 0.9, 1.2, 1.5. Removing the swell's share
would move every upright serif in every face and is not part of this change.

### 0.2 Italic G

| | What it is | Cause | Class | Fix |
|---|---|---|---|---|
| (a) the crossbar's end crosses the stem's edge | the bar's right end is cut plumb; the stem it meets is slanted | the corner pass cuts a level stroke with `Dc = [0, 1]` whatever the partner's direction (read, line 885) | generator | 0.3 |
| (b) step and notch at the stem's foot | `G.G` draws bowl and stem as one path that arrives at 45 degrees and turns plumb in one sample. The pen width is a function of direction, so it jumps from about 0.50 W to 0.85 W there. The outside gets two straight segments (turns of 18.7, 30.5 and 35.5 degrees on consecutive points at the Medium italic), the inside a fold that the fold pin holds for five samples and then releases in one 24.8 unit step (turns of 111 and 89 degrees) | a corner inside one stroke, which the stroker has no construction for | skeleton | 0.4 |
| (c) bump on the inner contour before the terminal | a smooth inflection, not a kink: no point of the inner edge within `1.1 x W0` of the terminal turns by more than 3.4 degrees | the teardrop law. The stroke thickens as it turns towards its terminal (the nib), then the inner edge thins by `0.28 x dropAmt/0.55` over `1.1 x W0`. That neck is the teardrop | the pen model, by design | not changed, 0.6 |
| (d) kink in the outer bottom curve | the fit lifts the round extreme `(370, -10)` and its control `(470, -10)` by `hwRound - overshoot`: 14.3 units at the Driftwood Regular, 21.5 at the Medium, 30 at the Bold. The next control `(560, 20)` stays, so at the Medium it is below the lifted extreme and the centre line runs flat, then dips: 0.01 units at the Medium italic, 0.83 at the Driftwood Bold, 0.51 at the neutral Bold (measured). The outer edge turns 3.6 degrees at the joint at the Medium italic and 4.1 at the Bold | a control drawn closer to a round extreme than the fit moves the extreme | skeleton | 0.4 |

(b) and (d) are in the roman `G` too: `GI` has no `G`, so the italic is the roman skeleton slanted. Measured on
all 268 drawings of the five concept files (roman and italic, four multipliers), the largest three-sample turn
on the bowl's edges is never under 78 degrees.

### 0.3 The corner cut, and every glyph that has it

At a corner (two stroke ends within 2 units, one steep and one shallow) the steep stroke runs out to the
partner's far edge and is cut level. That is exact, because every shallow partner in the tables is level. The
shallow stroke runs out to the partner's far edge and is cut plumb. That is exact only when the partner is
plumb. How far a cut corner of the shallow stroke stands outside the partner's body, on the shipped example
concepts (bract `text`, `display`; driftwood; neutral `text`, `display`) as shipped, all four multipliers
(measured, worst case per glyph):

| | 0.9.0 | after |
|---|---|---|
| roman `Z` 24.3, `z` 26.2, `2` 25.1, `4` 22.9, `7` 15.4, `5` 3.6, `e` 1.9 | as listed | 1.6 or less |
| roman `E F G L [ ] fl` (plumb partner) | 1.6 | 1.6 |
| italic `z` 41.7, `2` 27.5, `Z` 26.8, `4` 25.7, `7` 19.9, `5` 10.2, `E F G L [ ] fl` and `È É Ê Ë` 6.3 to 6.5 | as listed | 1.6 or less |

The 1.6 that remains is the swell again (trap 36: two outlines that meet edge to edge sit `swell/2` of a width
proud of each other). So the same defect is a 24 unit tooth on the roman `Z` of every shipped face.

Fix: the shallow stroke is cut along its partner's drawn end direction. Exact when the partner is straight.
Limit, stated: when the partner is a curve (`2`, where the bar meets the bowl's end; `e`, where the bar meets
the bowl's start), the cut follows the partner's tangent at its end and the partner's edge curves away from it.
`2` goes from 12.5 to 51.2 units down to 1.6 or less in every example concept. `e` improves or holds in every
example concept except bract `blind` at mult 1.5 and 1.65, where it goes from 4.9 to 6.2 and from 5.5 to 7.7
(measured). `blind` is a round-1 concept that did not ship.

### 0.4 The skeleton changes

`G.G` stroke 0 (roman and italic):

    old  M 610 570 C 560 655 480 710 380 710 C 200 710 80 560 80 350 C 80 140 200 -10 370 -10 C 470 -10 560 20 610 70 L 610 330
    new  M 610 570 C 560 655 480 710 380 710 C 200 710 80 560 80 350 C 80 140 200 -10 370 -10 C 500 -10 610 60 610 180 L 610 330

The bowl now runs into the stem plumb, so the path has no corner, and the control next to the extreme sits 70
units above it, clear of the fit's lift on every example master (30 at most). Measured on the 14 example masters
(roman and italic): the largest three-sample turn on the bowl's edges falls from 42.8 to 119.7 degrees down to
12.0 or less; the centre line no longer falls after its lowest point (0.00 on all 14); the turn at the bottom
joint is 2.5 degrees or less (Driftwood: 3.6 and 4.1 down to 1.5 and 1.8; the neutral example rises from 0.7 to
1.4 up to 1.3 to 2.5, still under every other joint of the letter).

Two alternatives were drawn and rejected. A separate stem with a square foot and the bowl joining it as a
hidden join keeps a spur, but the join's disk shows 3 to 5 units below the foot on the near-monoline concepts
(`dune`, `grot` at mult 1.5), and a T-join there is refused because its cut does not fit inside the stem. A
rounder chin (`C 470 -10 610 60 610 220`) measures a little smoother (9.9 degrees) and moves kerns further.

`GI.r` stroke 1 (italic only; the roman `G.r` is not touched):

    old  M 90 380 C 140 470 210 510 290 510 C 330 510 360 500 380 480
    new  M 90 380 C 140 470 210 510 290 510 C 330 510 362 470 382 450

The cause of r (b) and (c) is the cause of G (d). The fit lowers the arm's extreme `(290, 510)` and
`(330, 510)` by `hwRound - overshoot` (24.3, 31.5, 40 units on the Driftwood Regular, Medium, Bold) and leaves
the control `(360, 500)` and the terminal `(380, 480)` where they are. At the Medium the extreme's centre line
is at 478.5, below the terminal, so the centre line humps up over the control and turns 70 degrees in its last
50 units. The hump is the dip in the top edge (b). The turn is tighter than the stroke is thick there, so the
underside folds and the fold pin leaves a notch (c). The new arm ends 30 units lower with the same end
direction. Measured on the four italic example masters (driftwood 1 and 1.3, neutral `text` 1 and 1.5): the
largest three-sample turn on the underside falls from 50.3, 56.7, 115.4, 54.1 to 15.1, 11.3, 15.1, 25.2 degrees
and on the top edge from 24.8, 29.0, 19.8, 34.2 to 7.8, 10.1, 5.9, 9.0. The terminal hangs 30 units lower: a
design change the operator must look at (section "Verification", `design-acceptance`).

### 0.5 What the two redraws do to spacing

The generator fixes of 0.1 and 0.3 move no advance and no kern (0.7). The two redraws move real ink, so they do
(measured through `export.js` on the five example groups, 0.9.0 against the patched copy):

- Roman groups: the advance of `G` falls by 2 to 3 units. 66 to 80 kern pairs per master change, every one with
  `G` on the left. The largest: `G|A` from -84 to -126 on Bract `TextRegular`, -74 to -122 on `TextBold`, -77 to
  -123 on `DisplayBold`; -63 to -107 on the neutral `TextRegular`. The old value was held up by the corner that
  stuck out at the lower right; without it the automatic kern pulls the `A`'s foot under the chin.
- Italic groups: `G` and `r` advances move by 1 to 2 units. 159 to 191 pairs per master change, every one
  containing `G` or `r`; the largest 57 to 123 units (`r|7`, `r|1`, `r|?`). The old arm's teardrop stood above
  the x-height, which the pair measure read as a distant left edge for a capital or a figure.

These are the consequence of removing G (b), G (d), r (b) and r (c) in the shared tables. A site sees them in
`update-check.py`'s report before it adopts 0.10.0, and can pin a pair in `kerning.hand`.

### 0.6 Two items this plan does not change, and why

- **G (c), the bump before the teardrop.** It is the teardrop's neck, a parameter (`dropAmt`), present on every
  teardrop terminal of both shipped faces, roman and italic. Changing the law would move every terminal of
  Bract and Driftwood. If the operator wants a shallower neck on Driftwood, that is `dropAmt` in the site's
  concept, in the adoption step's design round.
- **r (a), the serif's right bracket above the arm.** Not a construction error. `diagSerifPoly` gives an italic
  stem's head a right half that reaches `1.15 x 0.6 x SW x serifLen` (39 units on Driftwood), and on `n`, `m`,
  `r`, `p` and `ñ` the arch leaves the stem inside that half. It is the italic form of trap 37 (the notch
  where the head serif meets the arch), for which this repository already ruled that "no edit of the shared
  table suits every face", and whose guard is the face's own `skeletons.js` (an arch that starts at the serif's
  corner; `tests/fixtures/skeletons/bract-shoulder.js` is the roman precedent). A generator rule that drops the
  right half where an arch leaves was prototyped: it removes the nub and leaves the roman-style notch of trap
  37 in its place (about 35 units on the Driftwood Medium italic), so it trades one for the other. This run
  records the italic case in `references/traps.md` row 37; the override for Driftwood's italic `n m r p`
  belongs to the adoption step in movingavg-website, which the request puts out of scope.

Also found and not changed: with `swell` and `wob` off, a `diag` serif on a CURVED stroke end (italic `y`,
and the italic capitals `A`, `M`, `N`) has bracket tips up to 7.0, 2.3, 1.5 and 0.7 units outside the body,
because the bracket follows the end's tangent and the stroke curves away. A different cause; the new guard
bounds it so it cannot grow unseen. The inner shoulder of the italic `n` shows a pinned fold at the Medium; that
is trap 37's neighbourhood and has its own probe (`tests/skeleton_probe.js shoulder`).

### 0.7 Spacing is measured on the 0.9.0 end constructions

Without care the corner fix moves advances a great deal in the italic, by accident of the measure: an italic
group reads sidebearings from the 20 unit bins between the baseline and the x-height or cap line only, a
bar's corner is one of the few points in its bin, and the slanted cut moves it. Measured without the measure
below: the italic `Z` loses 47 units of advance at mult 1.3 and the italic `z` 57 at mult 1.5.

So, as `headSink` does with `unsunk`: wherever 0.10.0 cuts an end differently from 0.9.0 (a slanted corner cut,
a level cut on a leaning serif end, a bracket on a leaning edge), the polygon carries `prof`, the same polygon
as 0.9.0 cut it, and `glyph()` reads the spacing profile from `prof`. Exact guarantee: for every glyph except
`G` and the italic `r`, the advance, the two 54-bin profiles and every kern are the values 0.9.0 computes; the
ink differs from the profile by the corner triangle or the bracket sliver that moved (up to the figures in 0.1
and 0.3).

## 1. Decision on the version

0.10.0, not 0.9.1. The change redraws two skeletons and moves kerns, which is more than a fix.

`Font output: changes:` on every face. Measured through `export.js` and `build.py` on the three examples, which
all still build with every self-check passing (folds, hairline floors, master compatibility, raster budgets):

| Group | Outlines that change, every master | Advances | Branch records | Kern pairs |
|---|---|---|---|---|
| neutral/roman, bract/roman, driftwood/roman | `2 4 5 7 G M Z e z è é ê ë` | `G` | `G` | 66 to 80, all `G` on the left |
| neutral/italic | `2 4 5 7 E F G L W Z [ ] fl r z È É Ê Ë` | `G`, `r` | `G`, `r` | 176 to 191, all containing `G` or `r` |
| driftwood/italic | the same and `w` | `G`, `r` | `G`, `r` | 159 to 169, all containing `G` or `r` |

Every other glyph of every master exports the same JSON (polygons, raw polygons, runs, kept indices, minimum
width, record, advance). `space` and `minStrokeWidth` do not move. This table is the proof the request asks for
that upright stems are untouched; `tests/test_serif_joints.py::test_only_the_named_glyphs_changed_since_0_9_0`
holds it (a whole-font `build.py --check` cannot, because the listed glyphs change every font file).

## Code to be changed

One file, `scripts/gen.js`, in three work items that must land in this order. Keep the quoted new lines
character for character: `scripts/tests/mutate.py` and the watches in "Verification" replace them by exact
string.

### `gen-serif-edge`

1. `serifBlend(x, y, w, L, h, sy, b)` becomes `serifBlend(x, y, ed, L, h, sy, b)`. In its `A`, `S` and `C`
   arrays every point written `[x - w / 2, y + sy * h * K]` becomes `ed(-1, sy * h * K)` and every
   `[x + w / 2, y + sy * h * K]` becomes `ed(1, sy * h * K)` (six points in `A` and `S`, two in `C`; `K` is 1.7,
   1 or 0.55 as written today).
2. In `serifPoly`, after `var b = P.serifBracket;`, add

       var lean = T[0] / T[1], hw = w / 2 / Math.abs(T[1]);
       function ed(side, dy) { return [x + side * hw + lean * dy, y + dy]; }

   and pass `ed` to `serifBlend` in place of `w`. Then replace every edge point of the function the same way:
   a point at `x - w / 2` becomes `ed(-1, dy)` and one at `x + w / 2` becomes `ed(1, dy)`, with `dy` the
   point's own offset from `y` (`h * 1.7`, `h * 0.55`, `-h * 1.7`, `-h * 0.55`, `-h * 1.8`, `h * 0.18`,
   `-h * 0.8`, `-h * 1.9`, and in the blended lowercase head `-h` and `0`). There are 21 such points: 7 in the
   blended lowercase head (`A[0]`, `A[1]`, `A[4]`, `S[0]`, `S[1]`, `S[4]`, and `c2`'s first argument), 5 in the
   foot, 5 in the symmetric head, 4 in the lowercase head. Points at `x - L`, `x + L` and their neighbours do
   not change. On a plumb stem `T` is exactly `[0, 1]` or `[0, -1]`, so `hw` is `w / 2` and `lean * dy` is a
   zero: the same bytes.
3. In `strokePolys`, wrap the first `ends.forEach(...)` (the end cuts) in
   `function cutEnds(ends, Lp, Rp, legacy)` that returns whether any end differs from its 0.9.0 construction,
   and call it as

       var L0 = Lp.slice(), R0 = Rp.slice(), legacyBody = null;
       if (cutEnds(ends, Lp, Rp, false)) { cutEnds([[0, modeA, -1], [n - 1, modeB, 1]], L0, R0, true); legacyBody = L0.concat(R0.slice().reverse()); }

   Inside it, the level cut's condition becomes

       var leanS = mode === "serif" && e[1] !== "joint" && Math.abs(TU[0]) <= 0.1 && Math.abs(TU[1]) > 0.5 && T[0] !== 0;
       if (leanS) differs = true;
       if ((mode === "serif" && Math.abs(TU[0]) > 0.1 || e[1] === "joint" || leanS && !legacy) && Math.abs(TU[1]) > 0.5) {

   The line `if (pd && vert) e[1] = "joint";` stays as it is (a mutation names it). The second call runs on
   copies of the uncut edges with a fresh ends list, so the first call's `e[1]` outcomes are not read back; a
   `tee` end is cut again by the same `teeCut` on the same input, which gives the same result.
4. The head sink: `if (!unsunk) unsunk = legacyBody || Lp.concat(Rp.slice().reverse());`, then

       var leanK = Ts[k][0] / Ts[k][1];
       [Lp, Rp].forEach(function (E) { for (var j = k; j >= 0 && j < n && E[j][1] > line; j -= sg) E[j] = [E[j][0] + (line - E[j][1]) * leanK, line]; });

   and `if (unsunk || legacyBody) body.prof = unsunk || legacyBody;`.
5. Where the serif terminal is pushed, the `head`/`foot` branch becomes

       else if (kind !== "ball") {
         var sp = { pts: serifPoly(p, T, w, P, UPPERISH.test(ch)) };
         if (T[0] !== 0) sp.prof = serifPoly(p, [0, T[1] < 0 ? -1 : 1], w, P, UPPERISH.test(ch));
         out.push(sp);
       }

6. Comments, in the same change: the header's ORIGIN list gains item 10 (0.10.0: brackets on the stroke's own
   edge, the level cut on a leaning serif end, the corner cut along the partner, spacing read from the 0.9.0
   constructions); `diagSerifPoly`'s first comment says which italic ends do NOT come through it (a stroke
   whose reference lean is 0.1 or less: the `w` of a narrow concept, the `W`); `serifKind`'s comment says
   "plumb or leaning by 0.1 or less"; the head-sink comment says the pin moves along the edge and what `prof`
   now holds.

### `gen-corner-cut`

In the corner branch inside `cutEnds`:

    var slant = !vert && pd[0] !== 0;
    if (slant) differs = true;
    var Dc = vert ? [1, 0] : slant && !legacy ? [pd[0], pd[1]] : [0, 1], at = ...   // `at` unchanged

and the branch's comment says: the shallow stroke is cut along its partner's drawn direction (exact for a
straight partner, the tangent at the end for a curved one), the steep stroke level. With a plumb partner
`pd[0]` is exactly 0 and the 0.9.0 expression runs.

### `skeleton-g-and-italic-r`

Line 108 and line 202 of `scripts/gen.js`: the two strings of section 0.4. Nothing else in the tables.

## Code to be written

No new source file. `tests/joint_changes.py`, `tests/joint_probe.js` and `tests/joint_spacing_probe.js` are
test support and are listed under "New automated tests".

## New automated tests

All run `scripts/gen.js` through node and read what it drew; none reads its source. `FONT_DESIGN_JOINT_SCRIPTS`
names another `scripts/` folder (a scratch copy carrying one mutation), as `FONT_DESIGN_HS_SCRIPTS` does for
`tests/test_head_sink.py`. Load `tests/conftest.py` by path, as that file does.

### Support files

- `tests/joint_changes.py`: the sets of section 1 as data, imported by the new tests and by the two changed
  ones. `GEN_0_9_0 = "dae7a54"` (the last commit that changed `scripts/gen.js` before this change; read from
  `git log`). `OUTLINES[(example, group)]`, `ADVANCES["roman"] = {"G"}`, `ADVANCES["italic"] = {"G", "r"}`,
  `RECORDS` the same two sets, and `kern_pair_allowed(group_is_italic, a, b)`: roman, `a == "G"`; italic, `G` or
  `r` is one of the two.
- `tests/joint_probe.js`, `node tests/joint_probe.js <mode> <scripts dir> <spec json>`, prints JSON. Shared
  rules: a stroke's polygons are its body (the one polygon with two edge runs) and the one-run polygons after
  it up to the next body; a serif end's polygon is the 15- or 26-point polygon of that group whose nearest
  vertex is closest to the midpoint of the end's two corners; the end's corners are `body[0]` and
  `body[2n-1]` (start) or `body[n-1]` and `body[n]` (end), `n` half the body's length; a polygon's bracket tips
  are its first and last vertex (reversal for orientation keeps them first and last). The probe throws when the
  count of open-stroke records and of bodies differ.
  - `serifs`: for every serif concept (`ends.s === "serif"`) of the given concept files, with `swell: 0`,
    `wob: 0` and any keys of the spec's `extra` merged in, roman and italic 10 degrees, mult 1, 1.3, 1.5, 1.65,
    every key of `G`: one row per end whose record says `serifA=` or `serifB=` `head`, `foot` or `diag`, with
    the kind, `out` (the larger distance of the two tips outside the body polygon, 0 when inside), `lean` (x
    drift per unit of y between the end's midpoint and the midpoint 12 samples in), `tilt` (the y difference of
    the end's two corners), `straight` (whether the skeleton segment at that end is an `L`: the glyph's
    skeleton is `GI[key]` in the italic when it exists, else `G[key]`), `lowestY` of the body.
    Why the swell is off: it bends a straight stroke's edges by 1.3 to 4.3 units at the bracket's height, which
    would hide the `M`'s 2 units; with it off a straight stroke's edges are straight lines and the measure is
    exact (measured over the 12 serif example concepts: 0.00 on 2,352 plumb heads and 2,640 plumb feet, on 0.9.0 and on the patched copy).
  - `sink`: the same sweep with `headSink: 0.6` against the same concept without the key: per lowercase head
    end, `sinkOut`, the largest distance of a point of the sunk body's end run (the points that differ from
    the unsunk body) outside the unsunk body polygon.
  - `corners`: with `swell: 0`, `wob: 0`, every concept with `ends.s === "serif"` or `joints === true`: one row
    per end whose record outcome is `corner` and whose stroke is shallow at that end (the end's midpoint and
    the midpoint 5 samples in differ more in x than in y), with `tooth` (the larger distance of its two corners
    outside the nearest other body) and `partnerCurved` (the skeleton segment of the partner's end is a `C`).
  - `edges`: for a named glyph and stroke index, every master of every group of an example `font.json`: per
    body edge the largest absolute sum of three consecutive turning angles in degrees, over the points from
    sample 3 to sample n-4 with repeated points skipped (`w3`); for the `G`, also `centreFall` (the largest
    fall in y of the centre line, the midpoints of the two edges, after the sample at the bottom joint, which
    is the sum of the first three `sampleCounts` of `G.G[0].d`) and `jointTurn` (the largest single turn of the
    outer edge within 12 samples of that joint).
- `tests/joint_spacing_probe.js`, `node tests/joint_spacing_probe.js <gen under test> <0.9.0 gen> <font.json>`:
  for every master of every group, every glyph the charset exports: the unrounded `adv`, `L` and `R` of
  `glyph()` from both generators, and for every pair of exported keys the unrounded `kern()`; prints the keys
  and pairs that differ.

### Item `tests-joint-geometry` (red-green): `tests/test_serif_joints.py`

Each test must fail on today's code at the named marker, which is the first assertion about the new behaviour.
The assertions before it are coverage checks that pass today (at least so many rows were measured, the named
glyph is among them), so a probe that measures nothing cannot pass.

| Test | Level | First assertion it fails on, 0.9.0 | Then |
|---|---|---|---|
| `test_no_head_or_foot_bracket_tip_stands_outside_its_stroke` | crosses `strokePolys`, `serifPoly`, `glyph()`; every glyph of every example concept | `BRACKET-TIP`: with the swell off, every `head` or `foot` end has `out <= 0.05`. Today: the italic `w` up to 14.7, `W` up to 18.2, the roman `M` up to 5.6 | every `diag` end with `straight` true has `out <= 0.05`; the ends with `straight` false are exactly the italic `y`, `A`, `M`, `N` and have `out <= 7.5`; the same with `extra` `{headSink: 0.6}` and with `{serifBracket: 0.5}` |
| `test_a_leaning_serif_end_is_cut_level` | the same | `LEVEL-END`: every `head` or `foot` end with `lean != 0` has `tilt <= 1e-6`, and the roman `M`'s `lowestY >= -1e-6`. Today, on the Driftwood example, the `M` tilts by 2.0 to 3.7, the italic `W` by 2.9 to 7.9 and the italic `w` by 7.3 to 16.1, and the `M` hangs 1.04 to 2.24 below the baseline | rows exist for the roman `M`, the italic `W` and, in the Driftwood example, the italic `w` |
| `test_the_head_sink_moves_a_leaning_stem_end_along_its_own_edge` | the same, `headSink` set | `SINK-ON-EDGE`: every lowercase head end has `sinkOut <= 0.01`. Today, with the concepts as shipped, the italic `w` reads 1.8 to 1.9 on the Driftwood example and 2.5 to 3.4 on Bract `text`. After the fix the figure with the swell off is expected to be 0 (not measured with the swell off: if it is above 0.01, find the reason before changing the bound) | plumb ends read 0 with the swell off (with it on they read 0.4 to 0.7, the swell's share, which is why the probe turns it off) |
| `test_a_corner_bar_ends_on_the_far_edge_of_the_stroke_it_meets` | crosses two strokes of one glyph | `CORNER-TOOTH`: with the swell off, every row with `partnerCurved` false has `tooth <= 0.05`. Today the roman `Z` 49.2, `z` 82.8, `4` 44.4, `7` 32.6 and every italic corner 12.1 or more | the rows with `partnerCurved` true are exactly `2 e è é ê ë`, with `2 <= 1.5` and the `e` family `<= 8.0`; with the concepts as shipped, every corner of every master of the three example `font.json` files has `tooth <= 2.0` |
| `test_the_g_bowl_runs_into_its_stem_without_a_step` | the whole glyph through `fitSkeleton`, `strokePolys`; every example master | `G-STEP`: `w3 <= 25` on both edges of the `G`'s bowl. Today 42.8 to 119.7 | |
| `test_the_g_bottom_curve_does_not_dip_or_kink_at_its_lowest_point` | the same | `G-BOTTOM`: `centreFall <= 0.005` and `jointTurn <= 3.0`. Today 0.83 and 4.1 on the Driftwood Bold, 0.51 on the neutral `TextBold` | |
| `test_the_italic_r_arm_underside_runs_into_its_terminal_without_a_notch` | the same, italic masters | `R-ARM-UNDER`: `w3 <= 35` on the underside (the edge with the lower y at the arm's joint sample). Today 50.3 to 115.4 | |
| `test_the_italic_r_arm_top_edge_has_no_dip` | the same | `R-ARM-TOP`: `w3 <= 15` on the top edge. Today 19.8 to 34.2 | |
| `test_only_the_named_glyphs_changed_since_0_9_0` | the software as a whole up to the export: `export.js` on every group of the three examples, the 0.9.0 generator (`git show dae7a54:scripts/gen.js` beside this tree's `export.js`, as `tests/test_r_leg_join.py` does for 0.4.0) against the one under test | `SCOPE-OUTLINES`: per master, the glyphs whose `polys`, `raw`, `runs`, `keptIdx` or `minw` differ are exactly `OUTLINES[(example, group)]`. Today the set is empty: "outlines changed on [], expected [...]" | records differ on exactly `RECORDS`; advances differ on a subset of `ADVANCES`; every changed kern pair satisfies `kern_pair_allowed`; `space` and `minStrokeWidth` are equal; every title without a `G` (and, italic, without an `r`) keeps its width |

`expected_failure` for the manifest is the marker in the third column, which appears in that assertion's
message and in no other assertion of the same test.

### Item `tests-spacing-frozen` (proof: mutation): `tests/test_joint_spacing.py`

`test_no_advance_profile_or_kern_moved_outside_g_and_the_italic_r` (follows the data from `strokePolys`'
`prof` through `glyph()`'s profile to `kern()`): for the three example `font.json` files,
`tests/joint_spacing_probe.js` reports no glyph outside `ADVANCES` whose unrounded `adv`, `L` or `R` differs
from the 0.9.0 generator's, and no pair that fails `kern_pair_allowed` whose unrounded kern differs. Marker
`SPACING-FROZEN`. It pins behaviour that already holds (today nothing differs), so a red run cannot prove it;
the recipe is in "Verification". After the build it is the guard for section 0.7 at full precision, which the
export test above sees only after rounding.

## Automated tests to be changed

### Item `tests-since-revision`

Two older tests state "nothing but X changed since an earlier release" by comparing an old generator with this
tree. They stay, with 0.10.0's declared changes taken out through `tests/joint_changes.py`, so they still hold
every other glyph.

- `tests/test_r_leg_join.py::test_only_the_r_changed_since_0_4_0`: expected outlines `{R}` and
  `OUTLINES[(example, group)]`; expected records `{R}` and `RECORDS`; advances a subset of `ADVANCES`; the
  profile comparison (recomputed from `raw`) only on glyphs outside the outline set; kern pairs through
  `kern_pair_allowed`; titles as in the new scope test. Docstring and the module header say so.
- `tests/test_weight_decisions.py::test_only_the_italic_opening_quotes_changed_since_0_5_0`: the export
  comparison becomes "equal after dropping the glyphs of `OUTLINES`, the kern pairs `kern_pair_allowed`
  admits and the titles that contain `G` or `r`" (apply `bd.export_digest` to the two reduced exports); the
  record comparison skips `RECORDS`; a roman group's "TTF digest identical" becomes "every glyph outside the
  set has the same compiled `glyf` record and the same `gvar` variations, and `hmtx` differs on `G` at most";
  in an italic group the glyph and `gvar` comparisons skip the set, `hmtx` differs on the two opening quotes
  and on `G` and `r` at most, the opening quotes' advances still equal the rule, and "GPOS identical" is
  dropped (kerns are held by the new scope test). The list of tables allowed to differ is whatever the build
  shows; start from `{glyf, gvar, hmtx, HVAR, GPOS, OS/2, head, hhea, maxp}` (inferred) and state the final
  list in the docstring. Characters map to glyph names through the font's cmap; `fl` is the ligature glyph
  (inferred: `f_l`).
- `tests/test_weight_decisions.py::test_a_mixed_concept_group_without_a_mult_1_master_per_concept_exports_as_0_5_0_did`:
  the same reduction before `bd.export_digest`; records may differ on `RECORDS["roman"]` only.

Each changed guard is watched red again under the mutation its docstring already names (for the first, the
`R`'s leg `i` back to `""` through `FONT_DESIGN_R_GEN`), and the result goes in `references/testing.md`.

### Item `mutate-strings`: `scripts/tests/mutate.py`

Two mutations replace text this change rewrites; a replacement that matches nothing is UNPROVEN.

- `bracket-count`: the old string becomes `"function serifBlend(x, y, ed, L, h, sy, b) {\n"` and the inserted
  line returns `[ed(-1, sy * h), [x - L, y + sy * h], [x - L, y], [x + L, y], [x + L, y + sy * h], ed(1, sy * h)]`.
- `headsink-global`: the old string is the new sink loop of `gen-serif-edge` step 4 and the replacement is
  `for (var j = 0; j < n; j++) if (E[j][1] > line) E[j] = [E[j][0] + (line - E[j][1]) * leanK, line];`.

No mutation is added: the new tests are repository tests, not font-suite tests.

### Item `baseline-rebase`

The compatibility baseline (`tests/test_backward_compat.py`) holds every example to the digests of commit
`c5b4abb`. This change moves the export and TTF digests of all five groups by design, so the baseline moves to
the commit that carries it, by the two-commit order of `docs/plan-r-leg.md` section 6.1. A build agent does not
commit, so it prepares the placeholder state and the operator finishes it (`baseline-record`).

- `tests/fixtures/baseline.json`: `baseline_rev` `"COMMIT_A"`, `baseline_version` `"0.10.0"`, `supersedes`
  `{baseline_rev: "c5b4abb", baseline_version: "0.7.0", why: ...}` naming this change and
  `tests/test_serif_joints.py::test_only_the_named_glyphs_changed_since_0_9_0` as the proof that nothing else
  moved; `by_platform_node` holds one entry, `darwin/26`, from `.venv/bin/python3 tests/baseline_digest.py --print`
  on the finished tree. The other four entries are removed: they describe 0.7.0's output.
- `tests/test_backward_compat.py`: `BASELINE_REV = "COMMIT_A"`; the module docstring gains the 0.10.0 step.
- `tests/baseline_digest.py`: the header's history sentence gains the 0.10.0 step.
- `.github/workflows/record-baseline.yml`: the two `c5b4abb` become `COMMIT_A`.

Known red after this item, by design, until `baseline-record`:
`tests/test_backward_compat.py::test_the_baseline_fixture_exists_and_covers_every_example_group` on
"BASELINE_REV is 'COMMIT_A', not a git sha", and the `record-baseline` test of `tests/test_ci_workflow.py` on
the same shape check. `test_the_0_1_examples_export_and_build_to_the_recorded_digests` must be green on this
machine.

## Documentation to be updated

### Item `genre-review-record`

`tests/test_genres.py::test_a_verdict_is_stale_when_the_recipe_outlines_change` goes red with the generator
change (every recipe's roman `2 4 5 7 G M Z e z` move). The rule in `references/genres.md` section 6 is a new
reading and a new record, not an edited digest.

- `docs/reviews/genres-2026-11-22.md` (named for the day of the reading; rename if it is done later): what was
  rendered (the three commands of `references/genres.md` section 6), what was read, the verdict table, and the
  `json digests` block with `by_node_major` holding node 26 from `current_digests()`. The reading is targeted,
  as on 2026-11-19: for each of the ten recipes, the roman `G`, `M`, `Z`, `z`, `2`, `4`, `5`, `7` and `e`
  where the page sets them, and nothing else, because nothing else changed by measurement. If the page does
  not set one of them (inferred: the round-1 template may not), say so in the record instead of drawing it some
  other way.
- `references/genres.md`: the verdict table's dates and the "Status of the review" paragraph.
- `tests/test_genres.py`: `RECORD` and the docstrings that name the record file.

### Item `version-bump`

`VERSION` 0.10.0; `package.json`; `SKILL.md` (frontmatter and the body line); the `README.md` badge;
`CHANGELOG.md`: a `## [0.10.0]` entry dated the day it lands, with the line
`Font output: changes: ...` built from the table of section 1 (the glyph lists per group, `G` and the italic
`r` redrawn with their advances and kerns, no other advance or kern moved, the `blind` limit of 0.3), a Fixed
section (the four fixes), a Changed section (the `G` and the italic `r` skeletons, with the `G|A` figures of
0.5), and what was looked at and not changed (0.6). The `## Releases` list gains the tag line when the tag
exists.

### Item `docs-generator-traps-testing`

- `references/generator.md`: section 2 (the joint paragraph: the shallow stroke of a corner is cut along its
  partner; exact for a straight partner); section 5 (`serif` row: brackets on the stroke's own edge, the level
  cut on a leaning end; `corner` row); section 7 (a new paragraph: a control or an end drawn nearer a round
  extreme than `hwRound - overshoot` folds the centre line back, with the `G` and italic `r` figures, and the
  rule for a new skeleton or a per-face override); section 8 (spacing is read from `prof`, what `prof` holds
  since 0.10.0, the exact guarantee of 0.7); section 9 (replace "Every italic stem is slanted, so every italic
  stem serif comes through `diagSerifPoly`" with the true statement and the table of 0.1; the last bullet about
  the `w` follows).
- `references/traps.md`: after row 39, "Four more, met in 0.10.0" with rows 40 to 43 in the table's five
  columns: the bracket off a leaning stroke; the corner tooth; a corner inside one stroke (the `G`); an end
  nearer a round extreme than the fit's travel (the `G`'s control, the italic `r`'s arm). Row 37 gains the
  italic form (the serif's right half standing where the arch leaves, 0.6) and that the guard is the same
  per-face override.
- `references/testing.md`: a new section 11, "The joint guards (0.10.0)", in the form of section 10: the table
  of tests and first assertions, the watches of "Verification" with the figure each fired on, as run.
- `docs/plan-serif-joint-jags.md`: this plan, with an "As built" paragraph for every departure. It must pass
  `tests/test_hygiene.py`: repository-relative paths only.
- `CLAUDE.md`: the test count and date in layer 2.

## Work items

| id | title | kind | files | verifiable_by |
|---|---|---|---|---|
| `tests-joint-geometry` | Write the geometry tests that fail on 0.9.0 for each joint defect and for the release's scope. | test-new | tests/joint_changes.py, tests/joint_probe.js, tests/test_serif_joints.py | agent |
| `tests-spacing-frozen` | Write the test that pins every advance, spacing profile and kern outside G and the italic r to 0.9.0's values. | test-new | tests/joint_spacing_probe.js, tests/test_joint_spacing.py | agent |
| `gen-serif-edge` | Put serifPoly's brackets on the stroke's own edge, cut a leaning serif end level, and move the head sink along the edge. | code-change | scripts/gen.js | agent |
| `gen-corner-cut` | Cut the shallow stroke of a corner along its partner's direction instead of plumb. | code-change | scripts/gen.js | agent |
| `skeleton-g-and-italic-r` | Redraw the G so the bowl runs into the stem without a corner, and the italic r's arm so it clears the fit. | code-change | scripts/gen.js | agent |
| `tests-since-revision` | Take 0.10.0's declared changes out of the two tests that compare this tree with 0.4.0 and 0.5.0. | test-change | tests/test_r_leg_join.py, tests/test_weight_decisions.py | agent |
| `mutate-strings` | Update the two font-suite mutations whose target text this change rewrites. | test-change | scripts/tests/mutate.py | agent |
| `version-bump` | Bump the version to 0.10.0 and write the changelog entry with its font-output line. | code-change | VERSION, package.json, SKILL.md, README.md, CHANGELOG.md | agent |
| `baseline-rebase` | Move the compatibility baseline to this change with the commit placeholder and this machine's digests. | test-change | tests/fixtures/baseline.json, tests/test_backward_compat.py, tests/baseline_digest.py, .github/workflows/record-baseline.yml | agent |
| `genre-review-record` | Re-read the genre recipes' changed glyphs and write the new review record with node 26 digests. | doc-change | docs/reviews/genres-2026-11-22.md, references/genres.md, tests/test_genres.py | agent |
| `docs-generator-traps-testing` | Update the generator reference, the traps list, the testing log, the released plan and the test count, then run the full smoke check last. | doc-change | references/generator.md, references/traps.md, references/testing.md, docs/plan-serif-joint-jags.md, CLAUDE.md | agent |
| `design-acceptance` | The operator looks at the redrawn G, the italic r and the changed joints and accepts or rejects each. | live-acceptance | | operator |
| `baseline-record` | The operator commits, records the baseline under the script guard and merges the entries CI records. | live-acceptance | | operator |
| `genre-review-acceptance` | The operator rules on the targeted genre re-read and adds the node 20 and 22 digests from CI. | live-acceptance | | operator |
| `release-acceptance` | The operator runs CI by hand on the branch, merges, and tags v0.10.0. | live-acceptance | | operator |

Order: the two test items; `gen-serif-edge`, `gen-corner-cut`, `skeleton-g-and-italic-r`;
`tests-since-revision`, `mutate-strings`; `version-bump`; `baseline-rebase` and `genre-review-record` (both
need the final generator); `docs-generator-traps-testing`, whose verification ends with the full
`bash scripts/smoke.sh --full` run, so that run comes after `baseline-rebase` and `genre-review-record`.

## Verification

Layers are those of `CLAUDE.md`. The change touches what draws a glyph, so layer 4 applies, and it is a
release, so `--full`.

### Per work item

- **`tests-joint-geometry`, agent.** Red first: `.venv/bin/python3 -m pytest tests/test_serif_joints.py -q`
  on the unmodified generator, nine tests failed, each on its marker (table above). Green after the three code
  items. `ruff check tests/` and `npm run lint:js` pass.
- **`tests-spacing-frozen`, agent, proof by mutation.** The test passes when written. Recipe, on the tree
  before the feature: in `scripts/gen.js`, in `glyph()`, the one line that begins
  `var W0 = P.W0 || P.W, T = 30 + 0.36 * W0` : replace `T = 30 + 0.36 * W0` with `T = 31 + 0.36 * W0`. No
  rebuild; the test runs node on the file. Run
  `.venv/bin/python3 -m pytest tests/test_joint_spacing.py -q`: it must fail on `SPACING-FROZEN` (the
  sidebearings that are not at their floor of 8 grow by 1, so advances move). Restore the file by digest; the test is green. `mutation_files`: `scripts/gen.js`.
- **`gen-serif-edge`, agent.** The three tests marked `BRACKET-TIP`, `LEVEL-END`, `SINK-ON-EDGE` green;
  `tests/test_head_sink.py` green (the stem top stays under the wedge's top edge on the leaning `w`: its
  `poke` measure covers the italic `w` of the Driftwood example); the scope test now reports exactly
  roman `M`, italic `W` (and `w` in driftwood/italic) as changed, so it is still red on `SCOPE-OUTLINES`
  until the other two code items land. Watches, each on a copy of `scripts/` outside the repository named by
  `FONT_DESIGN_JOINT_SCRIPTS`, each expected red on the marker, logged in `references/testing.md` section 11:
  W1 `var lean = T[0] / T[1], hw = w / 2 / Math.abs(T[1]);` to `var lean = 0, hw = w / 2;` (`BRACKET-TIP`);
  W2 `leanS && !legacy` to `false` (`LEVEL-END`); W3 the sink loop back to `E[j] = [E[j][0], line]`
  (`SINK-ON-EDGE`); W4 `if (unsunk || legacyBody) body.prof = unsunk || legacyBody;` to
  `if (unsunk) body.prof = unsunk;` (`SPACING-FROZEN`); W5 the `sp.prof` line removed (`SPACING-FROZEN`, on the
  roman `M`'s unrounded advance; if it survives, say so in the log and the pull request, and strengthen the
  test).
- **`gen-corner-cut`, agent.** `CORNER-TOOTH` green. Watches: W6 `slant && !legacy ? [pd[0], pd[1]] : [0, 1]`
  to `[0, 1]` (`CORNER-TOOTH`); W7 `if (slant) differs = true;` removed (`SPACING-FROZEN`: the italic `Z`'s
  advance).
- **`skeleton-g-and-italic-r`, agent.** `G-STEP`, `G-BOTTOM`, `R-ARM-UNDER`, `R-ARM-TOP` and the scope test
  green; all three examples build (`scripts/smoke.sh` steps 1 and 2). Watches: W8 the old `G.G` string
  (`G-STEP`); W9 the `G`'s control `610 60` to `560 20` with the rest new (`G-BOTTOM`); W10 the old `GI.r`
  string (`R-ARM-UNDER`). Whether the new shapes are right is not this item's check; see `design-acceptance`.
- **`tests-since-revision`, agent.** `.venv/bin/python3 -m pytest tests/test_r_leg_join.py tests/test_weight_decisions.py -q`
  green; each changed test watched red under its own documented mutation and logged.
- **`mutate-strings`, agent.** `.venv/bin/python3 scripts/tests/mutate.py --font examples/neutral/font.json --requirements examples/neutral/requirements.json --static-dir examples/neutral/out/static --only bracket --only headsink`
  after `build.py --static`: every listed mutation RED, none UNPROVEN. `tests/test_mutate_harness.py` green.
- **`version-bump`, agent.** `tests/test_versions_and_skill.py`, `tests/test_docs_commands.py`,
  `tests/test_hygiene.py` green. Nothing more runs here: the full smoke run waits for `baseline-rebase` and
  `genre-review-record`, because until they land two other tests are red that this item cannot fix
  (`test_the_0_1_examples_export_and_build_to_the_recorded_digests`, whose baseline still holds 0.7.0's digests,
  and `tests/test_genres.py::test_a_verdict_is_stale_when_the_recipe_outlines_change`), and the two
  `COMMIT_A` tests named under `baseline-rebase` do not exist yet.
- **`baseline-rebase`, agent.** `test_the_0_1_examples_export_and_build_to_the_recorded_digests` green on this
  machine; the two named tests red on the placeholder and on nothing else.
- **`genre-review-record`, agent.** `.venv/bin/python3 -m pytest tests/test_genres.py -q` green under node 26.
  The reading needs headless Chrome through `scripts/shoot.py`, which the repository's Chrome tests use on
  this machine.
- **`docs-generator-traps-testing`, agent.** `tests/test_docs_commands.py`, `tests/test_hygiene.py`,
  `tests/test_versions_and_skill.py` green; every figure in the new text is one a test or a logged watch
  printed. This item runs last, so it also owns the full run: layer 4, `bash scripts/smoke.sh --full`, in the
  background, only after every other item has landed (`baseline-rebase` and `genre-review-record` included).
  CI takes 60 to 81 minutes for steps 1 to 7; no local time is recorded, so record the measured time in
  `CLAUDE.md`. Expected red in step 7 are exactly the two tests named under `baseline-rebase`
  (`test_the_baseline_fixture_exists_and_covers_every_example_group` and the `record-baseline` test of
  `tests/test_ci_workflow.py`), both on the `COMMIT_A` shape check; any other red is a defect to fix, not to
  list. `test_the_0_1_examples_export_and_build_to_the_recorded_digests` and `tests/test_genres.py` must be
  green by then.

### Operator items, and what each needs

- **`design-acceptance`** (accepts `skeleton-g-and-italic-r`), operator. Needs a person's judgment. Build
  the Driftwood example and draw, before and after, at the Regular, Medium and Bold: the italic `G`, `r`, `w`,
  `W`, `Z`, `z`, `E`; the roman `G`, `M`, `Z`, `2`, `4`, `7`; and the words `GABF`, `GA`, `ro`, `re`, `r7` for
  the kerns of 0.5 (`scripts/diff.py` with the 0.9.0 build as `--before` renders the titles and lists every
  value that moved). Three decisions: the round chin of the `G`; the lower terminal of the italic `r`; leaving
  G (c) and r (a) as 0.6 describes. A rejected redraw is reverted by its one string and its tests.
- **`baseline-record`** (accepts `baseline-rebase`), operator. Needs a commit and GitHub Actions. Commit A (the
  change with the placeholder); `sed` the placeholder to A's short sha in the three files;
  `.venv/bin/python3 tests/baseline_digest.py --record --rev <A>`; commit B; push; the `record-baseline`
  workflow records `linux/20`, `linux/22`, `darwin/20`, `darwin/22` from a worktree at A;
  `tests/baseline_digest.py --merge` each artifact; commit C.
- **`genre-review-acceptance`** (accepts `genre-review-record`), operator. Needs a ruling that the targeted
  re-read is enough (as ruled for 0.5.0), and the node 20 and 22 `genre-digests.json` from the same workflow
  run added under `by_node_major`.
- **`release-acceptance`** (accepts `version-bump`), operator. Needs GitHub credentials:
  `gh workflow run ci.yml --ref feature/serif-joint-jags` (layer 5), the merge, the tag `v0.10.0` on the first
  `main` commit that carries it. Adoption in movingavg-website and hop-safari is a separate step per site.

### Risks the reviewer should weigh

- The kern moves of 0.5 reach a shipped title (`G|A` in Bract). They follow from the `G`'s new shape, and the
  only way to avoid them is not to redraw the `G`.
- `prof` now stands in for three more end constructions. The profile and the ink differ at those ends by
  design; section 0.7 states by how much.
- The corner cut is the partner's tangent on a curved partner: one unshipped concept's `e` gets 1.3 to 2.2
  units worse at mult 1.5 and above.
- The thresholds of the edge tests (`w3`) sit between measured before and after values with at least 10
  degrees on each side, except the italic `r`'s underside on the neutral Bold (25.2 against 35).
