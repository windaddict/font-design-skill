# Plan: `headSink`, a stem end that sinks under a lowercase head serif (skill 0.9.0)

WHAT IT'S FOR: the plan for one opt-in concept parameter in `scripts/gen.js`. It says what changes, what
each test asserts and how each test is proved, and who can verify each work item. Every path is relative to the
repository root. Every number marked "measured" came from a command run on 2026-11-21 against a throwaway copy of
`scripts/` outside the repository; nothing in the repository was edited to get it.

Terms used below, each defined once:

- **Stem end**: the end of a stroke body polygon, the segment between the last point of its left edge and the
  last point of its right edge. Its role: it is what must stay hidden inside the serif.
- **Wedge**: the 15-point polygon `serifPoly()` draws for a lowercase head serif (bracketed or blended). Its top
  edge runs from `(x + w/2, y + 0.18·h)` down to `(x − L + 0.5·h, y − 0.2·h)`.
- **Poke**: how far the stem end stands above the wedge's top edge, in font units, measured on a vertical line.
  A positive poke is the defect.
- **Sink**: moving the stem end down to the line `y − headSink × h`, where `y` is the end's centre-line height and
  `h = SW × serifH` is the serif height `serifPoly()` uses (`SW = W0 × (W/W0)^serifGrow`).
- **Spacing profile**: the per-bin leftmost and rightmost polygon point that `glyph()` reads to set sidebearings
  and that `kern()` reads to set kerns (`references/generator.md`, section 8).
- **Watch**: a mutation applied once to a copy of the scripts, with the named test run against the copy, to see
  the test fail. The repository records watches in `references/testing.md`.

## 0. Findings that shaped the plan

Read these first. Four of them change what the request asked for, and each is a decision a reviewer can
challenge.

### 0.1 The defect, measured

`serifPoly()`'s lowercase head draws a top edge that slopes down to the left. The stem under it ends flat at `y`.
Measured poke at the stem's left edge with no `headSink`, on the `driftwood` concept of
`examples/driftwood/concepts.js` (W 88, serifH 0.4, serifLen 0.64): 2.81 units at mult 1, 4.11 at mult 1.65 (the
example's Bold master). The request said about 3 units.

It reaches 28 stroke ends in the roman glyph set: `b d g h i j k l m n p r u` (`u` has two), the ligature `fi`,
and the accented `ú í ù ì û î ü ï ñ`. The request's list omitted `g`.

It is larger in other concepts the repository ships: 16.8 units on `examples/bract/concepts.js` `blind` and
`templates/concepts.example.js` `anvil` (serifH 0.85), 22.0 on `templates/concepts.genres.js` `clarendon` at mult
1.65. The poke is `h × (0.38·t − 0.18)` with `t = w / (w + SW·serifLen − 0.5·h)` while the stem's left edge meets
the straight part of the top edge, so it grows with `serifH`.

### 0.2 Decision: the range is 0 to 0.7, not the suggested 0 to 1.5

The request suggested 0 to 1.5. This plan uses 0 to 0.7, bounds allowed, for two measured reasons.

1. Depth has no visual effect past the point where the stem end is hidden. The deepest poke the wedge geometry
   can produce is `0.65·h` (the wedge's top at its far left point), so 0.7 buries every case.
2. Above 0.7 the stem end can leave the serif. The lower edge of the lowercase head over the stem is at
   `y − h × (1 + 0.8 × serifBracket)`. With `serifBracket: 0` that is `y − h`. Measured: at `headSink` 0.7 the stem
   end keeps `0.3·h` of overlap at every `serifBracket` (0, 0.5 and 1). At `headSink` 1.2 with `serifBracket: 0` the
   stem would end `0.2·h` below the slab, a visible gap, with no error.

A range of 0 to 1.5 would need a second rule tying the limit to `serifBracket`. That rule breaks the font suite's
existing fixtures: `SLAB_FIXTURE` in `scripts/tests/test_font.py` copies the project's first concept and sets
`serifBracket: 0`, so a project with `headSink` 0.9 would fail an unrelated test. One range that is safe at every
bracket avoids both problems.

### 0.3 Decision: spacing is measured on the body before the sink

The prototype moves spacing. The spacing profile reads polygon points, and the wedge has no points along its long
right edge. Once the stem's points leave the bins between `y − headSink·h` and `y`, those bins read as a notch on
the right side, although no ink moved there.

Measured with the prototype's pin on the `driftwood` concept at `headSink` 0.6: the advances of `g i j u fi` and
eight accented letters shrink by 0.3 to 2.0 units, and 1,410 automatic kern values change at mult 1 (1,496 at
mult 1.5), most by 2 to 3.5 units.

This plan keeps the body polygon as it was before the sink (`prof` on the stroke's item) and `glyph()` measures the
profile on it. Measured with that change, for all 27 serif concepts the repository ships, roman and italic, at mult 1 and
1.65: every advance, every profile bin and the kern of every pair of single-character keys is exactly what the
concept gives with no `headSink`. The same run showed the absent key drawing exactly what the unchanged
`scripts/gen.js` draws, glyph for glyph.

The alternative is to accept the moved spacing. It was rejected because the feature is an outline repair, and the
follow-up (a shipped face adopting `headSink`) would otherwise have to re-review its spacing.

### 0.4 Decision: only the end's own run of points is pinned

The prototype pins every point of the stroke that lies above the line. A stroke that starts at a head serif and
rises above it elsewhere would be flattened along its whole upper part. No shipped skeleton has such a stroke
(measured: at most 8 points per edge are pinned, all at the end), but a face's own `skeletons` file can add one.

This plan walks each edge from the end inward and stops at the first point at or below the line.

### 0.5 Decision: the blended head (`serifBracket` other than 1) gets the same treatment

The request asked for a decision. The blended branch needs it, and gets it from the same code.

- It has the defect. Its two top anchors are `mix((x + w/2, y + 0.18·h), (x + w/2, y), b)` and
  `mix((x − L + 0.5·h, y − 0.2·h), (x − L, y), b)`, so the slope scales with the bracket `b`. Measured on the
  `driftwood` concept with `serifBracket: 0.5`: a poke of 1.10 units at mult 1 and 1.81 at mult 1.65. At
  `serifBracket: 0` the top is level at `y` and the poke is 0.00.
- The sink moves the stem in `strokePolys()`, not the serif polygon in `serifPoly()`. It therefore applies to
  whichever branch draws the wedge, with one definition of the depth.
- At `serifBracket: 0` there is nothing to bury. The sink is harmless there because of the range in 0.2 (measured
  overlap `0.4·h` at `headSink` 0.6).

### 0.6 Decision: no refusal for a concept with no serif end

`params()` refuses a dead knob in two places (`flareAmt` with `tear`, `dropAmt` without it). A refusal for
`headSink` on a concept that maps no end to `serif` was tried and dropped. Measured: with it, three existing font
suite tests fail on a face whose first concept sets `headSink`, because their fixtures copy that concept and set
every end to `butt`. `serifLen`, `serifH` and `serifBracket` are also unused by such a concept without a refusal,
so `headSink` follows them.

### 0.7 Other facts a builder needs

- **The sink applies wherever the lowercase wedge is drawn, including in an italic.** Italic stems normally take
  the diagonal serif, whose top is level. The exception is the italic `w` of narrow concepts, whose first stroke
  takes the `head` kind (`references/generator.md`, section 12). Measured: the Driftwood example's italic `w`
  changes with `headSink`, and nothing else in the italic does.
- **The sink is not written into the branch record (`g.sig`).** Whether it applies reads the end's mode, the
  reference tangent `TU` and the glyph key, which are the same in every master. How many points it pins differs
  between weights, like the fold pin's reach. Point counts and edge runs do not change.
- **The decimated outline of a sunk glyph keeps a different set of points** (`keptIdx`), because decimation runs on
  the sunk polygon. That is expected and is not a compatibility defect: one kept set is still shared by all masters.
- **A T-join (`i`) rooted in the sunk part of a stem is refused** by the existing burial check, loudly. No shipped
  skeleton has one.

### 0.8 The suite cannot pass in this checkout today, for two reasons unrelated to `headSink`

Measured: `.venv/bin/python3 -m pytest -q` on the untouched tree gave 16 failed, 680 passed, 30 skipped in 22 minutes
17 seconds.

1. **15 failures need the neutral example built.** `examples/neutral/out/` is build output that git ignores, so a
   fresh checkout has none. `scripts/smoke.sh` step 2 builds it before step 7 runs the repo tests. The fix is a
   command, not a code change (section "Verification", "Suite prerequisites").
2. **1 failure is a defect in the hygiene walk.** In a linked git worktree `.git` is a file that holds the path of
   the main checkout. `tests/conftest.py` `tree_files()` skips a directory named `.git` and not a file, so
   `tests/test_hygiene.py::test_no_forbidden_string_anywhere_in_the_tree` reports `.git: line 1`.

The second one blocks any run of the suite in a linked worktree, including this workflow's own final run. Work
items `hygiene-git-pointer-test` and `hygiene-git-pointer-skip` fix it. They are a prerequisite of the run, not part
of `headSink`; a reviewer who wants them out of this change should say so, and the run then needs a checkout whose
`.git` is a directory.

The hygiene walk also reads this plan file, so the plan holds no machine path.

## Code to be changed

### `scripts/gen.js` (work item `gen-head-sink`)

Four edits. The text below is authoritative: the mutations in `scripts/tests/mutate.py` quote it, and
`mutate.py` refuses a mutation whose text does not match exactly once. Keep the ES5 style of the file (`var`,
`function`): `scripts/concepts/build-page.js` splices this file into a page that a browser runs.

**1. `params()`: the range check.** Insert directly after the `serifBracket` check and before the `apex` check.
`P.headSink` is not given a default: `var P = Object.assign({}, concept)` already carries the key when it is set,
and an absent key leaves `P` exactly as today.

```js
  if (concept.headSink !== undefined && !(typeof concept.headSink === "number" && concept.headSink >= 0 && concept.headSink <= 0.7)) {
    throw new Error("params: concept " + concept.id + " sets headSink to " + JSON.stringify(concept.headSink) + "; it must be a number from 0 to 0.7 (references/generator.md, section 4)");
  }
```

**2. `serifKind(TU)`: one function for the serif kind.** Insert above `clipPast()`. Replace the inline expression
in the terminal loop of `strokePolys()` with `var kind = serifKind(TU);`. The expression is unchanged, so the
value is.

```js
/* The serif a serif-mode end takes, from the end's outward tangent on the reference skeleton: "diag" on a slanted stem, "foot" or
   "head" on a plumb one (pointing down or up), "ball" on anything flatter. One function, so the head sink in strokePolys() and the
   terminal drawn for the same end cannot disagree about which ends carry a head. */
function serifKind(TU) {
  return Math.abs(TU[1]) > 0.5 && Math.abs(TU[0]) > 0.1 ? "diag" : Math.abs(TU[1]) > 0.5 ? (TU[1] < 0 ? "foot" : "head") : "ball";
}
```

**3. `strokePolys()`: the sink.** Replace the two lines `var poly = Lp.concat(Rp.slice().reverse());` and
`out.push({ pts: poly, runs: [[0, n - 1], [n, 2 * n - 1]] });` with the block below. It runs after the loop that
makes the cuts, so `e[1]` is the end's final mode: an end that became a `joint` or a `corner` draws no serif and is
not sunk. The prototype tested the mode from before that loop.

```js
  // headSink: a lowercase head serif's top edge slopes down to the left while the stem under it ends flat, so the stem's top-left
  // corner showed above the wedge. The run of points at that end of each edge that lies above `line` is pinned down to it, inside the
  // wedge. Only the end's own run is walked, so a stroke that rises above the line elsewhere keeps its shape, and the count of points
  // is unchanged, so masters stay compatible. `unsunk` is the body as it was: glyph() measures the spacing profile on it, because the
  // profile reads polygon points and the wedge has none along its long right edge, so the sunk body would read as a notch and move
  // advances and kerns although no ink moved on either side.
  var unsunk = null;
  if (P.headSink > 0 && !UPPERISH.test(ch)) {
    ends.forEach(function (e) {
      var k = e[0], sg = e[2], TU = pu === pts ? [Ts[k][0] * sg, Ts[k][1] * sg] : [tang(k)[0] * sg, tang(k)[1] * sg];
      if (e[1] !== "serif" || serifKind(TU) !== "head") return;
      var SW = (P.W0 || P.W) * (P.serifGrow ? Math.pow(P.W / (P.W0 || P.W), P.serifGrow) : 1), line = pts[k][1] - P.headSink * SW * P.serifH;
      if (!unsunk) unsunk = Lp.concat(Rp.slice().reverse());
      [Lp, Rp].forEach(function (E) { for (var j = k; j >= 0 && j < n && E[j][1] > line; j -= sg) E[j] = [E[j][0], line]; });
    });
  }
  var poly = Lp.concat(Rp.slice().reverse()), body = { pts: poly, runs: [[0, n - 1], [n, 2 * n - 1]] };
  if (unsunk) body.prof = unsunk;
  out.push(body);
```

**4. `glyph()`: the profile reads `prof`.** Four small edits in the orientation and profile block.

- `var polys = [], runs = [];` becomes `var polys = [], runs = [], profs = [];` with a comment: `profs` is what the
  spacing profile reads, the drawn polygon unless a head sink kept the unsunk body.
- In the ring branch, after `runs.push(o.runs, inn.runs);` add `profs.push(o.pts, inn.pts);`.
- In the other branch, after `runs.push(f.runs);` add `profs.push(it.prof || f.pts);`.
- The loop that fills `minX`, `maxX`, `Lb` and `Rb` iterates `profs` instead of `polys`.

With no `headSink`, `profs` holds the same arrays as `polys` in the same order, so the arithmetic is the same.

Also update the header comment of `scripts/gen.js`: add item 9 to the numbered list, "The head sink (0.9.0)", two
lines saying what it does and that an absent key runs none of it.

Measured with exactly this text in a copy of the tree: `tests/baseline_digest.py --print --repo <copy>` gives the
recorded `darwin/26` digests for all five example groups (`judge` returns `ok`).

## Code to be written

- `tests/head_sink_probe.js` (work item `head-sink-tests`): the Node half of `tests/test_head_sink.py`. WHAT IT'S
  FOR: it draws glyphs with the generator under test and prints what it drew, so every assertion stays in Python.
  It takes the path of a `gen.js`, a concepts file and one JSON argument naming concept ids, styles, multipliers,
  `headSink` values (`"undef"` for an absent key), the key set (`"lower"` for every key that is not `UPPERISH`, or
  `"all"`), optional parameter overrides and kern pairs. Per glyph it prints `adv`, `L`, `R`, `sig`, the point count of
  each polygon, the edge runs, a sha256 of the polygons, and for each stem end under a lowercase head the two
  corner points and the 15 wedge points (found as section "New automated tests" describes).
  It must load a fresh copy of the generator for each concept and style (`delete require.cache[...]`, then
  `require` again). The generator's glyph cache is never freed: measured, one process that drew 27 concepts without
  the reload ran out of a 4 GB heap, and with the reload it used 1.3 GB and took 2.5 seconds.
  A glyph that throws must end the probe with a non-zero exit, never be skipped.
- No new script, schema or template.

## New automated tests

Levels are named per test. "Generator" means the test calls `scripts/gen.js` through Node. "Pipeline" means it
runs `scripts/export.js` and `scripts/build.py`. "Whole tool" means it runs the font suite as a site would.

### The measure, shared by every test below

The request asks for a test that measures a stem's top against the wedge's top edge at the stem's left edge. The
measure is built from the generator's output only, never from its formulas.

1. **Find the stem ends.** A stroke body is a polygon with two edge runs. The bodies of a glyph, in order, pair
   with the glyph's `sig` entries that start with `open`, in order. A body has a lowercase head at end A (or B) when
   its `sig` holds ` serifA=head` (or ` serifB=head`) and the glyph is not `upper`.
2. **Find the corners.** With `runs = [[a0, a1], [b0, b1]]`, `n = a1 − a0 + 1` and `flipped = (a0 != 0)`:
   `L(j) = flipped ? poly[a1 − j] : poly[a0 + j]` and `R(j) = flipped ? poly[b0 + j] : poly[b1 − j]`. End A's
   corners are `L(0)` and `R(0)`; end B's are `L(n − 1)` and `R(n − 1)`. This is the `bodies()` helper of
   `JOINTS_FIXTURE` in `scripts/tests/test_font.py`.
3. **Find the wedge.** The first polygon after the body with one edge run and 15 points whose x range holds the
   mean x of the two corners.
4. **Measure.** The stem end is the segment between the two corners. At 21 x positions from 0.1 % to 99.9 % of
   the way from the left corner to the right, take `stem_y(x)` on that segment and the highest and lowest crossing
   of the wedge's boundary with the vertical line at `x`. `poke = max(stem_y − wedge_top)`,
   `left_poke = stem_y − wedge_top` at the first position, `cover = min(stem_y − wedge_bottom)`.
5. **Restate the depth.** `h = W0 × mult^serifGrow × serifH` from the concept's own numbers (`serifGrow` 0 when
   unset). The centre-line height of an end is the mean y of its two corners with no `headSink`.

### Work item `head-sink-tests` (kind test-new, proof red-green)

Files: `tests/test_head_sink.py`, `tests/head_sink_probe.js`, `scripts/tests/test_font.py`.

`tests/test_head_sink.py` opens with a WHAT IT'S FOR docstring and reads
`SCRIPTS = pathlib.Path(os.environ.get("FONT_DESIGN_HS_SCRIPTS", REPO / "scripts"))`, the pattern of
`tests/test_skeleton_overrides.py`. The variable names another `scripts/` folder, a copy that carries one
mutation, for the watches in section "Verification". Unset, the tests run the real scripts.

The four tests of `tests/test_head_sink.py` are the red-green tests. Each fails first on the assertion named
below, and every assertion before it passes on the 0.8.0 generator, which ignores the key.

**a. `test_headsink_buries_the_stem_corner_on_the_driftwood_example`** (generator level; the request's
adversarial fixture). The `driftwood` concept of `examples/driftwood/concepts.js`, unchanged, roman at the
multipliers of the example's roman masters (1 and 1.65) and italic at its italic masters' (1 and 1.3), every key,
`headSink` absent, 0 and 0.6. Assertions in order:

1. Control. With no `headSink`, the roman glyphs with a lowercase head include `b d h i j k l m n p r u`, and every
   such end has `left_poke > 1` (measured 2.81 and 4.11). Message: `the fixture cannot observe the defect`.
2. **First failure before the feature.** At 0.6 every roman end has `poke <= 0.01`. Message starts
   `HEADSINK-POKE: with headSink 0.6 the stem of` and gives the glyph, the multiplier and the figure.
   **Expected failure marker: `HEADSINK-POKE`.**
3. At 0.6 both corners of every roman end sit at the end's centre-line height minus `0.6 × h` (21.12 units), within
   1e-6.
4. At 0.6 every end has `cover >= 0.25 × h`: the stem end is still inside the wedge.
5. Reach. In each style, the glyphs whose polygons differ between absent and 0.6 are exactly the glyphs that have
   a lowercase head (found from `sig`, not typed in; in the italic that set is `{w}`). Within them, every polygon
   that differs is a body with a lowercase head. Message starts `HEADSINK-REACH`.
6. In both styles and at every multiplier, each glyph's point counts, edge runs and `sig` are equal between absent
   and 0.6, and so are `adv`, `L` and `R`, and the automatic kern of every ordered pair over
   `a` to `z`, `A H O T V W` and `. , - '`. Message starts `HEADSINK-SPACING`.
7. `headSink: 0` gives the polygons and advances of the absent key for every glyph in both styles. Message starts
   `HEADSINK-ZERO`.

**b. `test_headsink_buries_the_stem_end_in_every_serif_concept_the_repo_ships`** (generator level; the blended
branch, `serifGrow`, the italic `w`). Every concept that maps an end to `serif` in `examples/*/concepts.js`,
`templates/concepts.example.js` and `templates/concepts.genres.js` (27 today), roman and italic, lowercase keys,
mult 1.65, `headSink` absent and 0.6. One probe process, generator reloaded per concept and style. Assertions in
order:

1. At least 20 such concepts were found and at least 20 have a roman lowercase head (a guard against a sweep that
   silently shrinks).
2. **First failure before the feature.** No end has `poke > 0.01` at 0.6. Message starts
   `HEADSINK-SWEEP:` followed by the count and the first five (file, concept, style, glyph, figure).
   **Expected failure marker: `HEADSINK-SWEEP`.**
3. Every end has `cover >= 0.25 × h` at 0.6, the four `serifBracket: 0` concepts included.
4. Every end's two corners sit at its centre-line height minus `0.6 × h` within 1e-6, with `h` restated with the
   concept's `serifGrow` (Bract's concepts use 0.35, `clarendon` 0.6). This is the assertion that a depth without
   `serifGrow` fails.
5. The partial bracket, which no shipped concept has. The `driftwood` concept with `serifBracket: 0.5`: with no
   `headSink` every roman end has `left_poke > 0.5` (measured 1.10 and 1.81), and at 0.6 none has `poke > 0.01`.
   With `serifBracket: 0`: with no `headSink` every `|poke| <= 0.01` (the top is level), and at 0.6
   `cover >= 0.25 × h`.

**c. `test_a_face_that_sets_headsink_builds_with_its_spacing_unchanged`** (pipeline and whole-tool level; follows
the parameter from `concepts.js` to the woff2). Two copies of `examples/driftwood/` (`font.json`, `concepts.js`,
`requirements.json`) in a temporary folder: `plain`, and `sunk`, where the text `serifLen: 0.64, serifH: 0.4,`
(asserted to occur once) gains ` headSink: 0.6,`. Each is built with
`build.py --font <face>/font.json --requirements <face>/requirements.json --keep-masters <face>/keep/export.json`,
so the fonts land in `<face>/out`. Measured: about 5 seconds per build. Assertions in order:

1. Both builds exit 0. The sunk build therefore passed the exporter's compatibility and fold checks and the
   builder's self-checks.
2. **First failure before the feature.** In the sunk export, for every roman master and the glyphs `n i l b`, and
   for every italic master and `w`: the measure on the undecimated polygons (`raw`, with `runs` and `sig`) gives
   `poke <= 0.11` (`raw` is rounded to 0.1). Message starts `HEADSINK-BUILD: the exported`.
   **Expected failure marker: `HEADSINK-BUILD`.**
3. For the same glyphs the decimated polygon that ships (`polys`) has the same highest point as `raw` on the sunk
   body, within 0.11: decimation kept the sunk end.
4. Between the two exports, per group and master: every advance is equal, the kern lists are equal, `titles` and
   `space` are equal, and the glyphs whose `polys` or `raw` differ are exactly the glyphs with a lowercase head
   (from the plain export's `sig`). Message starts `HEADSINK-EXPORT`.
5. Between the two fonts of each group, read with fontTools: `hmtx` metrics are equal, the `GPOS` table bytes are
   equal, and the roman `glyf` bytes differ.
6. The font suite passes on the sunk face:
   `pytest scripts/tests/test_font.py -q -p no:cacheprovider --font <sunk>/font.json --requirements <sunk>/requirements.json --static-dir none --scripts=<SCRIPTS>`
   exits 0. Measured: 20 seconds. This is the check that found the problem in 0.6.

**d. `test_the_font_suites_headsink_tests_pass_on_two_examples`** (whole-tool level). For `examples/neutral` and
`examples/driftwood` it runs
`pytest scripts/tests/test_font.py -q -p no:cacheprovider --font <ex>/font.json --requirements <ex>/requirements.json --static-dir none --scripts=<SCRIPTS> -k headsink`
and asserts exit 0 and `2 passed` in the output. Neither font-suite test needs a built font. Message starts
`HEADSINK-SUITE: the font suite's headSink tests did not both pass on` and appends the last 2,000 characters of
the output. **Expected failure marker: `HEADSINK-SUITE`.** This test is what puts the two font-suite tests below
into the suite command, so the red and green runs see them.

**The two font-suite tests**, added to `scripts/tests/test_font.py` after
`test_serifbracket_outside_zero_to_one_is_refused`, under a comment line `# --- headSink (0.9.0) ---`. They run
on any project's concepts file, so they use a synthetic concept, the way `SLAB_FIXTURE` does. They are written in
this work item so that test d is red for the right reason. They are proved by the mutation harness (work item
`mutate-head-sink`), not by the workflow's red run.

`HEADSINK_FIXTURE`, authoritative in what it draws:

```js
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
// the project's first concept made into the adversarial case: a tall, short serif whose top edge falls well below the stem's flat
// end, bracketed, growing with weight, upright except `l`, which leans 0.045 (wonk) so one corner of its end stands above the
// centre line; whatever headSink the project sets is removed and set per run
const base = Object.assign({}, concepts[0], { serifLen: 0.5, serifH: 0.85, serifBracket: 1, serifGrow: 0.35, shear: 0, bend: 0, wonk: "l" });
base.ends = Object.assign({}, base.ends, { s: "serif" });
delete base.headSink;
// a stroke that starts at a head serif, runs down, turns and rises 140 units above its own start: only the end's run may be pinned
m.G["ĸ"] = [m.S("M 90 500 L 90 100 C 90 -40 300 -40 300 100 L 300 640", "s", "j")];
const res = { W0: base.W, serifH: base.serifH, serifGrow: base.serifGrow, runs: {} };
for (const mult of [1, 1.5]) for (const hs of ["undef", 0, 0.6]) {
  const c = Object.assign({}, base, { id: "hs" + hs });
  if (hs !== "undef") c.headSink = hs;
  const P = m.params(c, mult), r = { glyphs: {}, kern: {} };
  for (const k of ["n", "i", "j", "u", "l", "I", "H", "o", "ĸ"]) { const g = m.glyph(k, P); r.glyphs[k] = { adv: g.adv, polys: g.polys, runs: g.runs, sig: g.sig, L: g.L, R: g.R, upper: g.upper }; }
  for (const pair of ["ij", "ni", "ll", "ui"]) r.kern[pair] = m.kern(m.glyph(pair[0], P), m.glyph(pair[1], P), P);
  res.runs[mult + "/" + hs] = r;
}
console.log(JSON.stringify(res));
```

Measured with this fixture on the neutral, Driftwood, Bract and genres concept files: the smallest poke with no
`headSink` is 11 to 15 units, so the control holds on every project tried.

`test_headsink_sinks_the_stem_end_under_a_lowercase_head_serif(cfg)` (generator level). For mult 1, then 1.5,
in this order. The quoted phrase is a fixed part of each message; the mutations expect these phrases.

| # | Assertion | Fixed phrase in the message |
|---|---|---|
| 1 | every one of `n i j u l` and the test glyph has a lowercase head end in its record | `no stem end with a lowercase head serif` |
| 2 | control: with no `headSink`, `left_poke > 1` on `n i j u` | `the fixture cannot observe the defect` |
| 3 | at 0.6, `poke <= 0.01` on every head end | `pokes out above the wedge` |
| 4 | at 0.6, both corners at the centre-line height minus `0.6 × h`, within 1e-6, `h = W0 × mult^0.35 × 0.85` | `of the serif height` |
| 5 | at 0.6, `cover >= 0.25 × h` | `has left the serif` |
| 6 | point counts, edge runs and `sig` equal between absent and 0.6 for all nine glyphs | `changed a point count, an edge run or a branch record` |
| 7 | `I`, `H` and `o` have no polygon that differs; in the others only bodies with a head differ | `which has no lowercase head serif` (for `I H o`); `moved a polygon that is not a stem under a head serif` |
| 8 | `adv`, `L`, `R` equal for all nine glyphs; the four kerns equal | `headSink changed the advance of`; `changed the spacing profile of`; `changed the kern of` |
| 9 | on the test glyph, no body point higher than its head end's centre line plus 1 differs between absent and 0.6 (94 such points, measured) | `away from its serifed end` |
| 10 | the `0` run equals the absent run: polygons and advance, all nine glyphs | `headSink 0 is not the outline with no key set` |

`test_headsink_outside_its_range_is_refused(cfg)` (generator level), shaped like
`test_serifbracket_outside_zero_to_one_is_refused`. `params()` on the project's first concept with `headSink` set
to `-0.01`, `0.71`, `"0.6"`, `null`, `true` and `NaN` throws a message that names `headSink`; `0`, `0.6` and `0.7`
are accepted. Message for a value not refused: `headSink <value>: params() did not refuse it by name`.

### Work item `hygiene-git-pointer-test` (kind test-new, proof red-green)

File: `tests/test_hygiene.py`.

**`test_the_tree_walk_leaves_out_a_git_pointer_file`** (unit level). In a temporary folder it writes `.git` as a
file holding `gitdir: ` and a made-up absolute path, a file `a.md`, and a folder `sub/` holding another `.git`
file and `b.md`. It points `conftest.REPO` at the folder with `monkeypatch.setattr` and calls
`conftest.tree_files()`. It asserts the names returned are exactly `a.md` and `sub/b.md`. Message starts
`HYGIENE-GIT-POINTER: tree_files() returned`. **Expected failure marker: `HYGIENE-GIT-POINTER`.** Before the fix
the walk returns both `.git` files, so the test fails on this assertion in any checkout, not only in a worktree.

### The red-green tests and their markers, in one place

These five are the tests a manifest lists. The two font-suite tests are not listed: the suite command does not
collect `scripts/tests/`, so the final run would report them missing. Test d runs them.

| Test id as the runner prints it | Work item | Expected failure marker |
|---|---|---|
| `tests/test_head_sink.py::test_headsink_buries_the_stem_corner_on_the_driftwood_example` | `head-sink-tests` | `HEADSINK-POKE` |
| `tests/test_head_sink.py::test_headsink_buries_the_stem_end_in_every_serif_concept_the_repo_ships` | `head-sink-tests` | `HEADSINK-SWEEP` |
| `tests/test_head_sink.py::test_a_face_that_sets_headsink_builds_with_its_spacing_unchanged` | `head-sink-tests` | `HEADSINK-BUILD` |
| `tests/test_head_sink.py::test_the_font_suites_headsink_tests_pass_on_two_examples` | `head-sink-tests` | `HEADSINK-SUITE` |
| `tests/test_hygiene.py::test_the_tree_walk_leaves_out_a_git_pointer_file` | `hygiene-git-pointer-test` | `HYGIENE-GIT-POINTER` |

Each marker appears in one assertion message of its test and in no other. The other message prefixes named above
(`HEADSINK-REACH`, `HEADSINK-SPACING`, `HEADSINK-ZERO`, `HEADSINK-EXPORT`) belong to later assertions, which the
watches of section "Verification" prove.

### Tests considered and left out

- A test that compares every glyph with the 0.8.0 generator read from git. It would add a second recorded baseline
  to move at the next change of font output. `tests/test_backward_compat.py` already holds the byte-identity of
  the three examples and runs in the suite; section "Verification" adds a watch that shows it sees a default that
  is not off.
- A refusal test for a T-join rooted in the sunk part of a stem. The existing burial check does the refusing and
  has its own tests.

## Automated tests to be changed

- `tests/conftest.py` (work item `hygiene-git-pointer-skip`): in `tree_files()`, skip a file named `.git` the way
  `.DS_Store` is skipped, with a comment: in a linked worktree or a submodule `.git` is a file that holds the path
  of the git directory; git never tracks it, so it cannot be published, like the `.git` folder in `SKIP_DIRS`.
  Nothing else about the walk changes: untracked files and the `.claude` folder are still read.
- `scripts/tests/mutate.py` (work item `mutate-head-sink`): seven mutations, added after the `bracket-range-removed`
  entry. None rebuilds (`rebuild` unset): the tests they name run the generator directly.

  Each entry: the name, the test it names, the exact text to replace in `scripts/gen.js` (one match), the
  replacement, and the `expect` text. Three of them replace the same line, the one that opens the sink.

  1. `headsink-ignored: the sink never runs` (sinks). Replace

         if (P.headSink > 0 && !UPPERISH.test(ch)) {

     with `if (false) {`. Expect `pokes out above the wedge`.
  2. `headsink-zero-on: headSink 0 sinks too` (sinks). Replace the same line with

         if (P.headSink >= 0 && !UPPERISH.test(ch)) {

     Expect `headSink 0 is not the outline with no key set`.
  3. `headsink-capitals: the capital test is dropped` (sinks). Replace the same line with `if (P.headSink > 0) {`.
     Expect `which has no lowercase head serif`.
  4. `headsink-global: every point above the line is pinned` (sinks). Replace

         for (var j = k; j >= 0 && j < n && E[j][1] > line; j -= sg) E[j] = [E[j][0], line];

     with

         for (var j = 0; j < n; j++) if (E[j][1] > line) E[j] = [E[j][0], line];

     Expect `away from its serifed end`.
  5. `headsink-spacing: the spacing profile reads the sunk body` (sinks). Replace

         profs.push(it.prof || f.pts);

     with `profs.push(f.pts);`. Expect `headSink changed the advance of`.
  6. `headsink-no-serifgrow: the depth ignores serifGrow` (sinks). Replace

         line = pts[k][1] - P.headSink * SW * P.serifH;

     with

         line = pts[k][1] - P.headSink * (P.W0 || P.W) * P.serifH;

     Expect `of the serif height`.
  7. `headsink-range-removed: params() accepts any headSink` (refused). Replace the whole first line of edit 1,
     from `if (concept.headSink !== undefined` through `<= 0.7)) {`, with `if (false) {`. Expect
     `did not refuse it by name`.

  "sinks" is `test_headsink_sinks_the_stem_end_under_a_lowercase_head_serif`; "refused" is
  `test_headsink_outside_its_range_is_refused`. The replaced text keeps the indentation it has in the file. Each
  mutation was applied to a copy of the generator carrying the text of section "Code to be changed". A script
  that computes the quantities of the ten assertions, on the neutral example's first concept, showed the named
  quantity break and the earlier ones hold: the `i` advance moves by −1.94 under `headsink-spacing`, 94 of 94 arm
  points move under `headsink-global`, `I` and `H` change under `headsink-capitals`, the depth is off by 7.8 units
  at mult 1.5 under `headsink-no-serifgrow`, and only `l` differs under `headsink-zero-on`. The tests themselves do
  not exist yet, so the harness run of work item `mutate-head-sink` is the proof, not this measurement.
- `tests/test_backward_compat.py` and `tests/fixtures/baseline.json`: **no change.** `BASELINE_REV` stays `c5b4abb`
  and no digest is re-recorded. A digest that differs after this change is a defect in the change.
- `tests/test_genres.py`, `tests/test_schemas_and_concepts.py`, `tests/test_weight_decisions.py`,
  `tests/test_mutate_harness.py`: no change. No recipe sets `headSink`, concepts have no JSON schema, and the
  harness's verdict logic is untouched.

## Documentation to be updated

- `references/generator.md` (work item `docs-head-sink`). Every statement is checked against the code as built.
  - Section 3, after the fold pin sentence: the head sink runs next, on the same edges, and the profile is taken
    from the body before it.
  - Section 4, a table row after `serifBracket`:
    `headSink` | 0–0.7 (refused outside, bounds allowed; a string, `null`, a boolean and `NaN` are refused); default
    0, off | sinks a stem end under a lowercase head serif by `headSink × h` (`h = SW × serifH`, so `serifGrow` is
    included): the run of points at that end of each edge above `y − headSink × h` is pinned to that line, point
    count unchanged | what it repairs and by how much (`h × (0.38·t − 0.18)`, with the measured figures of 0.1);
    0.2 buries the poke when `serifLen >= 0.5 × serifH`, 0.6 buries it in every concept this repository ships;
    why 0.7 is the limit; applies to bracketed and blended heads; capitals, feet, diagonal serifs and ends that
    became a joint are untouched; no effect when no end maps to `serif`; advances, profiles and kerns are those of
    the concept without it.
  - Section 5, the `serif` row: one clause naming `headSink` for the lowercase wedge.
  - Section 8: one paragraph. The exact guarantee: with `headSink` set, the spacing profile is measured on each
    stem body as it was before the sink, so advances and kerns equal the concept's without it. It is not a claim
    that the profile follows the sunk outline.
  - Section 9: the italic `w` of a narrow concept is the one italic end that takes the wedge and therefore the
    sink.
  - Section 11: add `headSink` that is not a number from 0 to 0.7 to the list of what `params()` refuses.
  - Section 12: add the head sink to the list of what reads drawn coordinates and is not in the record, with the
    reason from 0.7.
- `references/testing.md` (work item `docs-head-sink`).
  - The list of font-suite test names near the top, and the section 2 table: two rows, with the seven mutation
    names.
  - Section 5: the harness count after this change, as `mutate.py` prints it in the smoke run (127 if the current
    set is the 120 that section records; state the printed figure, not this estimate).
  - A new section 10, "The headSink guards (0.9.0)", added to the contents list: the four repo tests, the watches
    of section "Verification" with their dates and outcomes, the measured figures of 0.1 and 0.3, and one recorded
    limit: no shipped concept maps the empty end letter to `serif`, so no input reaches the difference between an
    end's mode before and after the joint pass.
- `references/traps.md` (work item `docs-head-sink`): row 39 under a new "One more, met in 0.9.0" heading. Symptom:
  the stem's top-left corner shows above a lowercase head serif (2.8 to 4.1 units on the Driftwood example, up to
  22 on a tall serif). Cause: the wedge's top slopes and the stem ends flat. Guard: `headSink`, with the tests
  named. Where: Driftwood.
- `CHANGELOG.md` (work item `release-0-9-0`): `## [0.9.0] — <the date it lands>` above the 0.8.0 entry. Its first
  line is `Font output: unchanged. No concept this repository ships sets headSink, and with the key absent every
  example rebuilds to the recorded digests (tests/test_backward_compat.py). A face that sets headSink builds
  differently under 0.9.0 than under 0.8.0, which ignored the key.` Then an "Added" entry for the parameter that
  states the range, the spacing guarantee and the decisions of 0.2 to 0.6, and a "Fixed" entry for the hygiene
  walk. Add the row `| v0.9.0 | the merge commit of the release branch | tagged after the merge |` to the
  Releases table.
- `SKILL.md` (frontmatter `version:` and the `**Version 0.9.0**` line), `README.md` (the badge),
  `package.json` (`version`), `VERSION`: 0.9.0. `tests/test_versions_and_skill.py` holds all five together.
- `docs/plan-head-sink.md` (work item `release-0-9-0`): a copy of this plan, as the repository keeps each
  feature's plan. This file has no machine path, so the copy needs no scrubbing.
- No change: `references/genres.md`, `references/guidelines.md`, `templates/concepts.example.js`,
  `templates/concepts.genres.js`. Checked: none names the stem end under a head serif, and no recipe gains the key,
  so no recipe's output moves.
- **Not changed in this run, reported for the operator:** `CLAUDE.md`. Its layer 2 line gives a test count from
  2026-11-20 and no duration, and it does not say that layer 2 needs the neutral example built. The figures to add
  are in 0.8.

## Work items

| id | title | kind | files | verifiable_by |
|---|---|---|---|---|
| `hygiene-git-pointer-test` | A test that the hygiene walk leaves out a git pointer file | test-new | tests/test_hygiene.py | agent |
| `head-sink-tests` | Tests that headSink buries the stem end under a lowercase head serif and moves nothing else | test-new | tests/test_head_sink.py, tests/head_sink_probe.js, scripts/tests/test_font.py | agent |
| `hygiene-git-pointer-skip` | The hygiene walk skips a file named .git so the suite can pass in a linked worktree | test-change | tests/conftest.py | agent |
| `gen-head-sink` | The headSink parameter in the generator with its range check, the sink and the spacing profile on the unsunk body | code-change | scripts/gen.js | agent |
| `mutate-head-sink` | Seven harness mutations that turn the font suite's headSink tests red | test-change | scripts/tests/mutate.py | agent |
| `docs-head-sink` | Documentation of headSink in the generator reference, the testing reference and the traps list | doc-change | references/generator.md, references/testing.md, references/traps.md | agent |
| `release-0-9-0` | Release 0.9.0 with the version lines, the CHANGELOG entry and the plan copy | code-change | VERSION, CHANGELOG.md, SKILL.md, README.md, package.json, docs/plan-head-sink.md | agent |
| `head-sink-render-review` | A person confirms on a rendering that the sunk heads read as one shape at three weights | live-acceptance | | operator |
| `release-ci-and-tag` | The operator runs CI on the branch, merges, and tags v0.9.0 | live-acceptance | | operator |

## Verification

### Suite prerequisites (do these before any run of the whole suite)

1. Build the neutral example, which 15 repo tests read and git ignores:
   `.venv/bin/python3 scripts/build.py --font examples/neutral/font.json --static examples/neutral/out/static`.
   Run it again after the last edit to `scripts/gen.js` and after the `VERSION` bump, so the manifest matches the
   scripts. `scripts/smoke.sh` step 2 runs this same command, so a completed smoke run leaves it done.
2. Work item `hygiene-git-pointer-skip` must be in place, or the hygiene test fails on the worktree's `.git` file.

With both done the suite command is `.venv/bin/python3 -m pytest -q`. It took 22 minutes 17 seconds on this
machine on 2026-11-21.

### Per work item

| id | verifier | proof | How it is verified |
|---|---|---|---|
| `hygiene-git-pointer-test` | agent | red-green | Red: `.venv/bin/python3 -m pytest tests/test_hygiene.py -q -k git_pointer` fails with `HYGIENE-GIT-POINTER` before `hygiene-git-pointer-skip`. Green after it. |
| `head-sink-tests` | agent | red-green | Red: `.venv/bin/python3 -m pytest tests/test_head_sink.py -q` on the unchanged `scripts/gen.js` fails all four tests, each on its marker: `HEADSINK-POKE`, `HEADSINK-SWEEP`, `HEADSINK-BUILD`, `HEADSINK-SUITE`. Green after `gen-head-sink`. The two font-suite tests are proved by `mutate-head-sink`. |
| `hygiene-git-pointer-skip` | agent | n/a | `.venv/bin/python3 -m pytest tests/test_hygiene.py -q` passes all five tests in this worktree. Before the change the first test fails with `.git: line 1`. |
| `gen-head-sink` | agent | n/a | (1) `npm run check` exits 0. (2) `.venv/bin/python3 -m pytest tests/test_head_sink.py tests/test_backward_compat.py -q` passes: the new behaviour, and the recorded digests of all five example groups with the key absent. (3) The font suite passes on both examples after their builds (smoke steps 4 and 4a, run under `release-0-9-0`). (4) The watches below. (5) `npm run lint:js` when the machine can reach the npm registry; otherwise say so, and the CI lint job of `release-ci-and-tag` covers it. |
| `mutate-head-sink` | agent | n/a | After prerequisite 1: `.venv/bin/python3 scripts/tests/mutate.py --font examples/neutral/font.json --requirements examples/neutral/requirements.json --static-dir examples/neutral/out/static --only headsink` prints `7 mutations, 7 RED, 0 skipped, 0 problem(s)` and exits 0. A mutation that prints GREEN or UNPROVEN is a finding about the test or the mutation: report it, do not reword the `expect`. Then `git status --short scripts/` shows nothing: the harness restored `scripts/gen.js`. |
| `docs-head-sink` | agent | n/a | `.venv/bin/python3 -m pytest tests/test_docs_commands.py tests/test_hygiene.py tests/test_versions_and_skill.py -q` passes. Every figure quoted in the docs is one the builder measured with the built code; a figure copied from this plan is re-measured first. |
| `release-0-9-0` | agent | n/a | (1) `.venv/bin/python3 -m pytest tests/test_versions_and_skill.py tests/test_hygiene.py -q` passes. (2) `bash scripts/smoke.sh --full --out out/smoke` exits 0. This is the repository's rule for a `VERSION` bump and for a change to `scripts/gen.js`. It runs every fixture build, the font suite on two faces, every mutation, the Chrome steps and the repo tests. CI takes 60 to 81 minutes for steps 1 to 7 alone, so run it in the background with its output in a file under `out/`, and report the last line of each step. `scripts/check-env.py` found all 12 required tools on this machine on 2026-11-21, Chrome included. If the run cannot finish, report that as a blocker with the step it reached; do not report the item done. (3) `git status --short` shows only the files this plan names. |
| `head-sink-render-review` | operator | n/a | Accepts `gen-head-sink`. Requires Chrome to render a page, and a person's judgment of the picture. See below. |
| `release-ci-and-tag` | operator | n/a | Accepts `release-0-9-0`. Requires GitHub credentials for the repository, and the merge. See below. |

### Watches (run under `gen-head-sink`, recorded in `references/testing.md` section 10)

The workflow's red run proves only the first failing assertion of each test. The repository's rule
(`references/testing.md`, section 1) is that every guard is seen failing. The harness covers the font-suite
tests. These four watches cover the later assertions of the repo tests and the existing compatibility test.

For each: copy `scripts/`, `templates/` and `VERSION` into a new folder outside the repository, apply the one edit
to the copy's `scripts/gen.js` (assert one match), run the command, confirm the named test fails with the named
text, and delete the copy. Never edit the repository's `scripts/gen.js` for a watch.

| Watch | Edit (text as in the mutation table) | Command | Must fail with |
|---|---|---|---|
| W1 | `headsink-capitals` | `FONT_DESIGN_HS_SCRIPTS=<copy>/scripts .venv/bin/python3 -m pytest tests/test_head_sink.py -q -k driftwood_example` | `HEADSINK-REACH` |
| W2 | `headsink-spacing` | the same command, then again with `-k builds_with_its_spacing` | `HEADSINK-SPACING`, then `HEADSINK-EXPORT` |
| W3 | `headsink-no-serifgrow` | the same variable, `-k every_serif_concept` | the depth assertion of test b (its item 4), naming a concept that sets `serifGrow` |
| W4 | default not off: after `  var P = Object.assign({}, concept);` insert the line `  if (P.headSink === undefined) P.headSink = 0.6;` | also copy `examples/*/font.json`, `concepts.js`, `requirements.json` and `titles.txt` into the copy; run `.venv/bin/python3 tests/baseline_digest.py --print --repo <copy> --out <copy>/entry.json`; compare `entry["record"]["digests"]` with the fixture through `baseline_digest.judge(load_fixture(), entry["key"], ...)` | `judge` returns `differs`, naming `bract/roman` and `driftwood/roman`. The same comparison on an unedited copy returns `ok`. Measured on 2026-11-21 with an equivalent edit: `differs` on bract/roman, driftwood/roman and driftwood/italic. |

A watch that does not fail is a finding about the test. Report it in the result and in section 10; do not
weaken the edit to make it fail.

One difference has no watch: reading an end's mode from before the joint pass instead of after it. No concept in
the repository maps the empty end letter to `serif`, so no input reaches it. Section 10 records that.

### Operator items

**`head-sink-render-review`** (accepts `gen-head-sink`). What it needs: Chrome, and a person who looks. The builder
prepares the page, then hands the review to the person. The neutral example's `content.json` cannot be used as it
is: it names the concept ids `text` and `display` (the `concepts`, `shortlist`, `faces` and other per-concept keys),
and `scripts/concepts/build-page.js` reports `names no concept` for an id the concepts file lacks. The Driftwood
example has no content file, and its concept ids are `driftwood`, `tideline`, `dune` and `windswept`. Builder steps:

1. Copy `examples/driftwood/concepts.js` to `out/head-sink/concepts.js` and add `headSink: 0.6` to the `driftwood`
   concept.
2. Copy `examples/neutral/content.json` to `out/head-sink/content.json` and rename every concept id in it to a
   Driftwood id: `text` becomes `driftwood` and `display` becomes `tideline`, in the `concepts` object, the
   `shortlist`, the descriptions keyed by concept, and every `faces`, `cuts` and `ranking` reference. Then run
   `grep -n '"text"\|"display"' out/head-sink/content.json` and check that each remaining hit is a field name, not
   a concept id. Drop any entry that names a concept with no counterpart rather than leaving a stale id.
3. Build the page:
   `node scripts/concepts/build-page.js --template round1 --concepts out/head-sink/concepts.js --content out/head-sink/content.json out/head-sink/round1.html`.
   It must exit 0 with no `names no concept` line. If it does not, the builder fixes the content file and reruns
   it. The builder does not hand the review to the person until this build has exited 0.

Person's steps: open `out/head-sink/round1.html`. Look at `n m r b d h i u` at Regular, Medium and Bold. Accept when
the head and the stem read as one shape with no step at the top left, and nothing else looks different from the
request's `before.png` and `after.png`. The tests measure the geometry; they cannot judge the picture.

**`release-ci-and-tag`** (accepts `release-0-9-0`). What it needs: GitHub credentials for
`windaddict/font-design-skill`, and the merge. Steps: `gh workflow run ci.yml --ref <branch>` and read the result
of every job (CI does not run on push); merge; tag `v0.9.0` on the first `main` commit that carries `VERSION`
0.9.0 and push the tag, as `CLAUDE.md` "Version discipline" requires.

### Out of scope, named in the request

`movingavg-website` sets `headSink: 0.6` in `tools/driftwood/concepts.js` and adopts 0.9.0 in a later run. This
plan's test c shows what that adoption changes on the example: the outlines of the 23 roman glyphs with a
lowercase head and the italic `w`, and no advance or kern.
