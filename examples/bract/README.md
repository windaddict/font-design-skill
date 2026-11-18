# Bract (hopsafari.com): parameters and configuration

WHAT IT'S FOR: the first face made with this process, as a `font.json` and `concepts.js` the skill
can build, so a reader can see a real configuration beside the neutral one and reproduce the
generator's outlines for the shipped design. **Parameters only**, MIT like the rest of the repo: the
shipped woff2 is not here and may not be added; it is licensed for use on hopsafari.com only. The
name table in `font.json` is neutral — family "Bract Example", `{{operator}}` placeholders for the
owner strings, vendor id `EXMP` — because the name Bract identifies the site's face and is not
licensed for reuse as a font name (`NOTICE.md`). The full worked example, with the audit, the
rounds, the reviews, the mutations and the open items, is `references/examples/bract.md`.

Files: `font.json` (one roman group, two axes wght 400–700 × opsz 40–80, four masters, `avar` user
500 → design 580, the floors 41 / 50 / 32 / 40, the kern set and hand pairs, five public page titles
as character-set illustrations) and `concepts.js` (the two shipped cuts `text` and `display`; the
six round-1 concepts Foil, Burin, Blind, Field, Cone, Bine; and the round-3 revisions `burin2` and
`burinD`). There is no `requirements.json`: the shipped site's reviewed expectations live in its
own test file, and this example is not run through the test suite.

## Build

```
node scripts/export.js --font examples/bract/font.json --group roman out/bract-roman.json
.venv/bin/python3 scripts/build.py --font examples/bract/font.json --no-requirements
```

`--no-requirements` because this example carries no `requirements.json` (the site's reviewed
expectations live in its own test file); `build.py` otherwise refuses to build without the
required-character check, and the manifest records `requirements: null`.

The output is `out/BractExample-VF.woff2`, a font of this repository's generator under the neutral
name table above; fill in the owner strings and the licence before using it for anything. It is not
the shipped file. **What shipped, as history:** `Bract-VF.woff2` (86,580 bytes, 2026-11-15) carried
copyright John Knox, manufacturer Hop Safari, vendor id `HOPS` and the licence "Licensed for use on
hopsafari.com only" — the site's name table, not what this file builds. It was built from the
site's own copy of the generator before the italic
was restored and `dropAmt` added, and `flareAmt 0.28` was dropped from the two cuts here because the
generator now refuses it beside `tear: true`; the teardrop keeps its default `dropAmt` 0.55, so the
outlines are the same.

**The kerning is not the same on sparse pairs.** This example keeps the skill's default
`kerning.sparse_cap` (−50), so at each of the five reviewed locations 103 to 144 of the 4,100 kern values
(pairs with a period, hyphen, dash, colon or quote) sit at −50 where the shipped font has more (`.|Y` −102 at
Regular, `endash|five` −170 at Bold). The site's own `font.json` sets `sparse_cap: null` and reproduces the
shipped kerning. This file is not changed to match, because it is one of the five backward-compatibility
groups (`tests/fixtures/baseline-0.1.0.json`). For Bract the two settings emit the same 4,100 pairs (measured):
every pair the −50 cap touches still reaches the threshold of 12. That is a fact about these two values, not
about the parameter. A cap closer to zero than the threshold, 0 for instance, takes sparse pairs out of the list.

## Outcome and status

Shipped as hopsafari.com's display face on 2026-11-15 (site commit `90a085c`) after three
design-review rounds, an Impasse plan review (13 findings) and a diff review with one re-review
(8 + 5 findings), all accepted. Exported with this repository's generator: 131 glyphs per master,
4,100 kern pairs, 156,184 → 28,547 points per master at eps 1, minimum interior strokes 41.6 /
51.0 / 32.8 / 40.2 units (TextRegular / TextBold / DisplayRegular / DisplayBold), 0 folded edges,
worst decimated excursion 7.83 (`ç`, DisplayBold). The shipped record's figures were 155,042 →
28,457 points and 41.61 / 50.99 / 32.78 / 40.16; the point difference is exactly the `™` glyph this
generator carries and Bract did not (1,142 raw, 90 decimated points, measured); the stroke minima
are the same numbers rounded. The (700, 80) master is built and self-checked,
not visually reviewed for use. Open items are in the worked example.
