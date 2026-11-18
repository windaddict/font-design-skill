# Guidelines from the site: what the face must survive before anyone draws it

WHAT IT'S FOR: the reference for phase 2. The guidelines turn the site's stylesheet and content into
the constraints every concept is judged against: the sizes, the hairline floor, the axes on which
the face must differ from the body face, the weights, the case, the character set (checked, with what
the miner cannot see named by hand), and the
lessons the two precedents paid for. Read it before running `scripts/mine-sizes.py` and
`scripts/mine-charset.py`, and keep the output as the "Guidelines" section of the audit record and
the `requirements.json` of phase 7.

Contents: 1 sizes · 2 the hairline floor · 3 contrast axes · 4 weights · 5 case · 6 the exact
character set · 7 precedent lessons · 8 the output

## 1. The sizes the face must survive

`.venv/bin/python3 scripts/mine-sizes.py STYLESHEET --selectors h1,h2,.plate-title --root 100 150` reads the
`clamp()`, `rem` and `px` font-size rules for the display selectors (a comma list of tags and
`.classes`) and reports each selector's size range at every `--root` value, given as a percentage of
16 px (100 is the default root; 150 is the enlarged-root reading). `--floor-px` sets the thinnest
stroke in CSS px the floor is computed for (default 0.75); `--json` gives the machine-readable form.
The result is a table like Bract's:

| Element | Size | Weight |
|---|---|---|
| chapter numerals | 15.2 px | 500 |
| grid titles (88 of them), read-next titles | 16.8 px | 500 |
| H3 | 17.6–27 px | 700 |
| H2 | 25.6–35.2 px | 700 |
| wordmark, caps tracked .06em | 24–30 px | 700 |
| essay H1 | 32–48 px | 400 |
| contents and tag H1 | 38.4–64 px | 400 |
| frontispiece | 48–80 px | 400 |

Two things follow from the table alone. The smallest size sets the hairline floor (section 2). The
fluid sizes that cross the optical-size axis (Bract's two H1s crossing 40 px) decide the widths the
review loop must shoot (667 and 889 px for Bract), and whether one cut can serve the whole range:
Bract's spans 15.2–80 px, and hairlines that engrave at 80 px break up at 17 px, so it got a text
cut and a display cut on one `opsz` axis.

## 2. The hairline floor

One CSS pixel at size *s* px is `1000 / s` font units. A stroke under about 0.75 px breaks up or
greys out at 1×, so the floor for the Regular's thinnest stroke is

```
floor_units ≈ 1000 × 0.75 / smallest_px
```

Bract: 16.8 px → one px = 60 units → floor ≈ 45 units. A Didone hairline (12–20 units) is what
failed on the site; Driftwood's Regular hairline was recorded at 48 units and flagged as a Windows
risk in its record (its concept's `W 88 × thin 0.36` is 32 nominal; this repo's exporter measures
30.5 as the interior minimum, so treat the 48 as the record's figure, not a measurement made here).

Set the floor per master, from the exporter's measured minimum interior stroke rounded down, and
fix it in `requirements.json`: Bract's floors were 41 / 50 / 32 / 40 for TextRegular / TextBold /
DisplayRegular / DisplayBold (nominal 42.2 / 51.7 / 33.3 / 40.8, less the 3 % swell's half). The
Bold floors are not `1.5×` the Regular's: with `thinGrow 0.5` hairlines grow as `1.5^0.5`. The
measured minimum is not the target: each master that serves the smallest display size (the text
masters, and the Medium interpolated between them) must measure at or above the target above, or
the reading is a design finding (thicken `thin`, or move the smallest elements) and not a floor to
record. Bract's 15.2 px numerals in Medium read 0.70 px against the 0.75 target; the record carries
that as an open item (Windows rendering of the 0.70-0.78 px hairlines), not as a pass. The floor
relaxes if the audit moves the smallest elements to the body face (Bract's would have gone to
about 24 px, and the face could have been thinner); say which decision was taken.

What the floor does not settle: Windows rendering of sub-pixel strokes (trap 21). It is not checked
unless the platform run was made, and then only as headless Chrome and Playwright's Firefox on a
GitHub-hosted Windows Server runner (`references/review-loop.md` sections 2 and 9). Mitigate with `gasp`
and Medium at the smallest sizes, and say so.

## 3. Contrast with the body face on at least two axes

A display face that differs from the body face on none of contrast, stress, serif shape or width
reads as the same face at a different size. Name the body face's position on each (Newsreader: a
text serif with moderate contrast, slightly oblique stress, bracketed serifs, teardrop terminals;
IBM Plex Sans: a mechanical grotesque) and require each concept to move **at least two**: much
higher or much lower contrast; vertical stress (`nib 0`) or a steep angle; hairline, slab or no
serifs; wide or condensed. The spectrum of round 1 is built along these axes.

`references/genres.md` is the vocabulary for these axes (Didone, Scotch roman, Clarendon, slab,
grotesque, geometric, reverse contrast, optical sizes), with a parameter set for each and a plain
statement of what the generator cannot reach. Name the genre of each concept from it.

**Set the three optical knobs (`hzThin`, `roundGain`, `diagThin`) whenever a concept's `thin` is above
about 0.7**, because contrast no longer supplies the correction by accident: a high-contrast pen already draws
level strokes thinner than stems, which is most of what `hzThin` asks for, and a near-monoline pen
does not. Re-read
`minStrokeWidth` after setting them and re-pin the hairline floors (`generator.md` section 3).

Note the sister-site trap: a pen-drawn humanist roman is what Driftwood already is, so on hopsafari
the Field concept was flagged as "sharing a hand" with the sister site and shown only to anchor the
organic end.

## 4. Weights

A Regular and a Bold that is **a clear step**, because after the audit nothing but weight marks an
H2 (Driftwood ×1.65 pen width; Bract ×1.5 with `thinGrow` so the contrast survives). A Medium for
the smallest titles when the Regular cannot hold them (Bract's 15.2–16.8 px elements are Medium,
`W × 1.3`, reached through `avar`). Review the Medium at the smallest size in round 1: it is an
interpolation, and the generator is not linear in weight (references/generator.md section 6).

## 5. Case

Count the all-caps titles (Bract: 0 of 93). If titles are Title Case and only the wordmark, buttons
and nav are caps, design the lowercase first and the capitals for one tracked word. Caps tracked
at .06em on a dark surface at 24–30 px Bold is a separate reading in the review.

## 6. The character set, and what "exact" does not cover

`.venv/bin/python3 scripts/mine-charset.py --html DIR --css CSS --family 'Bodoni Moda'` scans every `.html` under
`DIR` for the characters the display selectors set, the selectors found in `CSS` as every rule whose
`font-family` names the family first (`--selectors` adds to or replaces that list; without `--family`
it defaults to `h1,h2,h3`); `--titles FILE` reads one title per line instead of built pages, for a
site not yet built. It reports: the character inventory, the **NBSP count**, the **straight
apostrophe count**, `#` `+` `*`, accented letters, the longest title, and the `charset` block for
`font.json`; `--json` gives the machine-readable form.

What the set is. The characters in the source text of the matched elements, plus, with `--css`,
the characters a `text-transform` rule makes the browser draw inside that text, whether the rule is
on the mined selector, on a descendant (`.display span { text-transform: uppercase }`) or on a
class an element inside it carries (`.caps`): `uppercase` adds the capitals of every letter that
text holds (a `.wordmark` set in `text-transform: uppercase` draws `HARBOUR REVIEW` from `Harbour
Review`), `lowercase` the small letters, `capitalize` the capitals of every letter (over-inclusive:
word starts cannot be told apart without a layout). The source characters stay in the set, so a
transform only makes it stricter. Without `--css` a transform is invisible and the output says
`text-transform: not read: no --css`; a transform rule whose selector the tool cannot read is named
in the output as `not read: <selector>`. What the set is NOT, so it is checked rather than exact:
text set in the face by an inline style, by script, or by a selector the tool cannot read (`>`,
`+`, `~`, pseudo-classes, attributes) is not seen; name those by hand from the templates and add
their characters. The font's coverage test in the site (`test_site_wiring.py.tmpl` guard g) reads
the source text the same way and has the same limit.
The no-break space is kept in `required_characters` (beside a plain space) whenever a title carries
it, because `nbsp_to_space` maps it to the space glyph and the suite checks that mapping.

The two traps it exists for, with Bract's counts:

- **83 of 93 titles carried U+00A0** before the last word (a widow guard in the content). A font
  that does not map NBSP lets that one space fall back to the body face. `charset.nbsp_to_space`.
- **55 of 56 apostrophes were typed as ASCII `'`**, and the site's builder does not smarten quotes.
  A font whose U+0027 is a straight tick shows a typewriter mark in every "Don't" (Driftwood's
  first lesson). `charset.ascii_apostrophe_curly`: U+0027 draws the curly form and the tick stays
  unmapped.

Then the content surprises: `#` ("The Dessert Project #4"), `+` ("Google+ SXSW Photowalk"), and a
literal `*` from an H2 written as `**Update**`. Each is an operator decision (fix the content,
carry the glyph, or both); `export.js --requirements` refuses a build whose required characters
have no skeleton (references/generator.md section 10). Figures: decide tabular or old-style if plate
numbers or dates move into the display face (neither shipped face has old-style figures).

## 7. Precedent lessons

Design rules that are not bugs but recurred, from Driftwood's record and Bract's rounds:

- **No gesture on frequent letters.** Driftwood's back-leaning n/h/m read as an error, not as
  character; a gesture on the most frequent letters costs too much legibility. Save gestures for
  rare letters.
- **Terminals from the stroke's own edges, never a shape dropped on the end.** A shape placed on
  top of a stroke meets its edges at an angle and leaves a notch or a spur; Driftwood's pebbles
  failed twice before the teardrop was built from the edges with a smoothstep swell.
- **A corner-rounding pass is invisible at real sizes.** Driftwood's wear pass added 38 % more
  points and changed nothing a reader could see.
- **Leaf dots read as accents.** Cone was crisp at 16.8 px but its leaf-shaped dot read as an
  accent at every size ("Guídes").
- **Judge on real titles at real sizes**, the long ones (70 characters) wrapped at 500 px.
  Specimen alphabets hide most real problems.
- **Weak at 48–80 px is a cut problem, not a concept problem.** Burin's weak point was presence at
  large sizes; the first display sketch only thinned hairlines and lengthened serifs and changed
  nothing visible; the second made the stems 8 % heavier as well.
- **Review an italic on real words that use its structural overrides** — a, e, f, k, v, w, y and
  the other letters `GI` in `scripts/gen.js` redraws (d, h, i, l, m, n, r, u and the f-ligatures) —
  and on `x`, which has no override because Driftwood's cursive italic `x` read as a Greek chi in
  running words and was replaced by a slanted roman `x`. Read words, not an alphabet row. In the
  same reading, check that the exit strokes do not collide at the tightest kerned pairs, and that
  the italic serifs, cut to 60 % of the roman's length (`diagSerifPoly`), still read at the smallest
  size the site sets the italic (Driftwood: 17.6 px). The design-round brief carries this as its own
  row.

## 8. The output

A "Guidelines" section in the audit record (the shape of hop-safari's
`docs/design-review-2026-11-15.md` section 2), and the first draft of `requirements.json`: the
required characters, the sizes, the floors (to be measured and fixed at the first export, against
the target of section 2), the weights and the titles the kerning test will lay. Show it to the
operator. The gate is "guidelines written and shown, and three decisions asked explicitly, one
question each, and recorded in the guidelines and `requirements.json`": each character the
generator cannot draw (fix the content or carry the glyph), the `opsz` axis ends, and whether the
smallest elements stay in the display face; `SKILL.md` phase 2 states the three in full.
