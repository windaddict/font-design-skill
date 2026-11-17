# Concept pages: how to build and publish rounds 1–3

WHAT IT'S FOR: the three concept rounds of the skill (`references/concept-pipeline.md`) are HTML
pages that render parameter sets straight from `scripts/gen.js` in the browser, so a concept is
judged on real titles at real sizes before any font exists. This folder holds the three templates,
the builder that splices the generator, the concepts and a content JSON into them, and a neutral
sample content file. This README is the operating guide; the design of the rounds is in the
reference.

## Files

| File | What it is |
|---|---|
| `build-page.js` | splices `scripts/gen.js` (module.exports stripped) + `scripts/render.js` into `/*GEN*/`, the project's `concepts.js` into `/*CONCEPTS*/`, and a content JSON into `/*CONTENT*/` (as `<script type="application/json">` with `<` escaped); refuses a template whose placeholder count is not exactly one per marker; parses the assembled script with `new Function` before writing |
| `round1-template.html` | the spectrum: optional audit section, guidelines, "all N side by side" with a text input and a weight select, one full specimen per concept on the site's surfaces, a character row, a recommendation footer |
| `round2-template.html` | the shortlist on three mock pages of a FIXED generic layout (home, article, contents: hop-safari's redesign): a sticky face picker, a glance card per concept, headline slots as `.r[data-t][data-size][data-w][data-min][data-fit][data-lh][data-caps]` whose sizes come from `content.slot_sizes` (required for rounds 2 and 3; a slot left out keeps its hop-safari default and is named on stderr), images only from `img/` |
| `round3-template.html` | the head-to-head: the verdict box (`#verdict`, from the content JSON's `verdict`), a ranking, the two-cut face switching at `DISPLAY_FROM`, `localStorage` memory of the pick, the comparison CSS face |
| `content.example.json` | neutral sample content: titles, chapters, lede, colours, image list, slot sizes, a verdict |

## Run a round

```
node scripts/concepts/build-page.js --template round1 --concepts concepts.js --content content.json out/round1.html
node scripts/concepts/build-page.js --template round2 --concepts concepts.js --content content.json out/round2.html
node scripts/concepts/build-page.js --template round3 --concepts concepts.js --content content.json out/round3.html
```

Then look at it in Chrome before anyone else does (`.venv/bin/python3` is the skill venv's interpreter, run from the skill folder,
`SKILL.md` "Finding the skill folder"; the woff2 the content JSON names must sit beside the page, here at
`out/fonts/Sampler-VF.woff2`):

```
.venv/bin/python3 scripts/shoot.py out/shots --serve out --pages round1.html --widths 500 1280 --family Sampler --font-url /fonts/Sampler-VF.woff2
```

`shoot.py` reads the page's self-test attributes (`data-fd-*`: the glyph count rendered, the
current face, whether the comparison face loaded) from the sentinel beacon, or from the dumped DOM
with `--dump-dom`, and fails the shot on a script error, a zero glyph count or a comparison font
reported missing, so a round that parsed but did not execute is not counted. `--family` and
`--font-url` make the shot prove the comparison face was served and visibly used; without them the
PNG is a picture, not evidence. They apply to a comparison face served as a woff2 (`font_url`); an
installed family has no `FontFace` to prove, so `--family Georgia` fails every probe: shoot that
page without `--family`, with `--dump-dom`, and read the page's own `data-fd-font` (`loaded` means a
face other than the default serif drew the probe string, not that it was Georgia;
`references/concept-pipeline.md` section 4). Switch faces with `--query face=<id>` (`?face=<id>` in
a browser).

## Publish as an artifact

The page is self-contained HTML. When the operator allows it, publish it as a private claude.ai
artifact and give them the link; they click through the faces themselves. Constraints, each
learned on Bract's pages:

- **Images only from `img/` beside the page**, published with it; never a site URL.
- **Comparison web fonts** as local woff2 beside the page or a Google Fonts stylesheet URL. The
  Google Fonts route worked once; whether external stylesheets stay allowed is not verified, so
  re-verify at publish and let the page degrade to Georgia if blocked.
- **Measure after assembly**: `render()` wraps to `el.clientWidth`, so the page draws only once the
  whole DOM is attached. Do not call it earlier.
- **No orphan tiles**: choose tile counts that fill `auto-fill` rows at 500, 1280 and 1600 px.
- **`localStorage`** holds the picked face only.
- The verdict is **data** in the content JSON, written by the host after it has spot-checked the
  reviewer's report; nobody edits the page by hand.
- Content is rendered with `textContent` and `setAttribute`; image paths are validated as
  `img/<name>.(jpg|png|webp)`. The repo's tests feed an adversarial content file (quotes,
  `</script>`, an `<img onerror>`) and require it to render inertly.

Without artifact publishing, open the file locally or serve it; the operator publishes if they want
the link.

## Content JSON

Copy `content.example.json`. Fill `titles` with real titles (the long ones matter: a 70-character
title wrapped at 500 px is a reading the alphabet row cannot give), `surfaces` with the site's
background and foreground colours, `slot_sizes` (rounds 2 and 3: `size`, and `min`, `fit`, `lh` where
the slot fits to width, per named slot) from `scripts/mine-sizes.py`, and the image list from
`img/`. The mock pages' structure is fixed; `slot_sizes` is what makes them the site's sizes. For round 3 add `verdict` (a heading, the ranked list, the risks, how to
pick). Keep the site's own copy out of any template committed to this repository: the templates
carry invented copy only.
