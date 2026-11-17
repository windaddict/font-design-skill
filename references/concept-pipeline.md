# The concept pipeline: three rounds of interactive pages before any font exists

WHAT IT'S FOR: the reference for phases 3–5. A concept is a parameter set, and the only honest way
to judge one is on the site's real titles at the site's real sizes on the site's surfaces, before
the cost of a build. The pipeline renders concepts in the browser straight from `scripts/gen.js`
(through `scripts/render.js`), in three pages of increasing commitment: the spectrum, the
mock-ups, the head-to-head. Read it when you build a round's page, when a page misbehaves as a
published artifact, and when the operator has to pick.

Contents: 1 the three rounds · 2 how the content JSON drives a page · 3 the face switch and the
DOM self-test · 4 artifact constraints · 5 how verdicts get into the page · 6 how the operator
picks · 7 the name check · 8 building a page

## 1. The three rounds

| Round | Page | Shows | Who judges | Gate |
|---|---|---|---|---|
| 1, the spectrum | `round1-template.html` | an optional audit section; the guidelines; "all N side by side" with a text input and a weight select; one full specimen per concept on the site's surfaces (real titles at real sizes, the smallest in Medium); a character row; a recommendation footer | the strongest model, with `templates/reviewer-brief-concepts.md`: a shortlist, how to pick, the risks | the operator picks the shortlist, or asks for a round 1b |
| 2, the mock-ups | `round2-template.html` | the shortlist set into mock-ups of the redesigned pages (after the audit's fixes), with a sticky face picker and a glance card per concept; headline slots carry the site's sizes and weights | the reviewer plus the frontend-design plugin when installed; the reviewer revises the leading concept (Bract: Medium for the small titles, serifs that grow with weight, heavier hairlines) | the operator names the finalists |
| 3, the head-to-head | `round3-template.html` | the finalists on the mock pages with the picker; a verdict box and a ranking; a two-cut face that switches at `DISPLAY_FROM`; the comparison face (the one the site uses today) as a CSS face | the reviewer ranks and says how to pick; targeted fixes are sketched here (Bract's display cut "D2": stems 8 % heavier, hairlines thinner, serifs longer) before any build | the operator chooses the design and the **name** |

Round 1 is wide on purpose: about six concepts named for the brand, **closest to the face in use
first, most organic last**, so the operator sees the range before the recommendation. Bract's six
ran from Foil (a Scotch roman, vertical stress) through Burin (engraved captions) to Bine (curling
terminals); Driftwood's four from Driftwood (wedge serifs, teardrops) to Windswept (sheared, bent,
cut ends). Driftwood needed two earlier rounds of **styled existing fonts** before the operator's
reaction ("they have become common") reframed the job as drawing one; start at the generated round.

## 2. How the content JSON drives a page

`scripts/concepts/build-page.js` splices four things into a template:

```
/*GEN*/        scripts/gen.js with its module.exports stripped, plus scripts/render.js
/*CONCEPTS*/   the project's concepts.js (leaves the global CONCEPTS)
/*CONTENT*/    a content JSON, embedded as <script type="application/json"> with "<" escaped
```

The content JSON carries the titles, the chapters or sections, a lede, the colours (CSS variables
for the site's surfaces), the image list, the sizes and weights per headline slot, and for round 3
the `verdict`. `scripts/concepts/content.example.json` is a neutral sample. The builder refuses a
template whose placeholder count is not exactly one per marker, and parses the assembled script
with `new Function` before writing, so a syntax error fails the build rather than the page.

Round 2 and 3 mock pages mark each headline slot with data attributes the page script reads:
`.r[data-t][data-size][data-w][data-min][data-fit][data-lh][data-caps]` (the text, the CSS size,
the weight, the minimum size, a fit rule, the line height, caps). Measured on Bract's round 3
template: 33 `data-t` slots, 32 `data-size`, 28 `data-w`, 11 `data-min`, 10 `data-fit`, 7
`data-lh`, 5 `data-caps`, 7 `data-face` cards, 3 `data-pick`.

Templates build the DOM with `textContent` and `setAttribute`, never `innerHTML` from content
(review finding F009 of the skill plan: Bract's `esc()` did not escape quotes). Image paths are
validated as `img/<name>.(jpg|png|webp)`. An adversarial content fixture (quotes, `</script>`, an
`<img onerror>`) must render inertly; the repo's tests run it.

## 3. The face switch and the DOM self-test

The picker sets the current face; `?face=<id>` in the URL selects one on load, and the choice is
remembered in `localStorage` so the operator's pick survives a reload. A **two-cut** entry (Bract's
`burinos`) is one picker item that resolves to the text cut below `DISPLAY_FROM` (40 px) and the
display cut at or above it, so the operator sees the optical-size idea before it is an axis. The
comparison face is a CSS font, redrawn on `document.fonts.ready`. The mock pages of rounds 2 and 3
are a fixed layout (a home page with a frontispiece, latest plate, chapters, selection and guides;
an article; a contents page: the shape of hop-safari's redesign), and only their headline sizes
follow the site: `content.slot_sizes` names each slot (`article_title`, `section_heading`,
`plate_title`, ...; the list and the four fields `size`, `min`, `fit`, `lh` are in
`content.example.json`), filled from `mine-sizes.py`; the block is required for rounds 2 and 3
(content without it fails the build), every slot it leaves out keeps the template's hop-safari
default and is named on stderr by `build-page.js`, and a name the builder does not know fails the
build. The face is judged on the site's real pages in phase 8.

`render(el, text, P, sizePx, opt)` wraps the text to `el.clientWidth` and writes one SVG path per
slot, **after the whole page is assembled** (`redraw()` at the end; an earlier version measured
before attachment and clipped every title). It returns the glyph count, and the page sums the
counts into DOM attributes (`data-fd-*`: the rendered glyph count, the current face, whether the
comparison face loaded) that `shoot.py` reads from the dumped DOM, so the smoke run proves a round
**executed** in Chrome, not merely parsed (review finding F001 of the skill plan: the first
templates called a `render()` that the shipped generator did not have). The attribute names are
`data-fd-round`, `data-fd-face`, `data-fd-rendered`, `data-fd-font` and `data-fd-error`, set on
`<html>` by the three templates and read by `scripts/shoot.py` and the smoke run.

## 4. Artifact constraints

The pages are self-contained HTML and can be published as private claude.ai artifacts so the
operator can click through them (Bract's three rounds were). The constraints, all learned the
hard way (trap 23):

- **Images only from files published with the artifact**: `img/` beside the page, never an
  absolute site URL.
- **Comparison web fonts** as local woff2 beside the page or a Google Fonts stylesheet URL. The
  Google Fonts route worked in the Bract session; whether external stylesheets stay allowed is
  inferred, not verified, so **re-verify at publish** and let the page degrade to Georgia if
  blocked.
- **The comparison face is the face the site uses today**, in every round: in round 1 no file of
  the new face exists, so the content JSON's `comparison` names the current display face (an
  installed family, or a woff2 beside the page as `font_url`), and the sketches are judged against
  what they would replace. `scripts/concepts/content.minimal.json` starts that way. The neutral
  example's `content.json` is the one exception: it is a finished sample, so its comparison row is
  the built fixture font, which is what the smoke run's shots prove loaded.
- **What a shot of the comparison face proves depends on how it is served.** A woff2 beside the
  page (`font_url`) is evidence-grade: shoot with `--family <its family> --font-url /<its path>`
  and the sentinel proves it was served 200 and a loaded `FontFace` drew every visible element.
  An installed family (Georgia on a Mac) has no `FontFace` to prove, so `--family Georgia` fails
  every probe (`102 of 102 probed element(s) are not drawn by 'Georgia'`): shoot such a page
  **without** `--family` and with `--dump-dom`, and read the page's own `data-fd-font` on the
  dumped `<html>`. The page sets it to `loaded` only when `document.fonts.check` accepts the
  family and a probe string measures a different width in `<family>, serif` than in `serif`; the
  exact guarantee is that a face other than Chrome's default serif drew the probe on the machine
  that shot it, not that it was that family (an alias would pass). Say in the record that the
  comparison row is this weaker reading, or serve the current face as a woff2 when the site ships
  one.
- **Measure after assembly** (section 3).
- **No orphan tiles**: choose tile counts that fill `auto-fill` rows at 500, 1280 and 1600 px, or a
  half-empty last row reads as a layout bug.
- **`localStorage`** for the picked face only; nothing else persists.
- Without artifact publishing, open the file locally or serve it (`shoot.py --serve`); the
  operator publishes if they want the link (references/fallbacks.md).

## 5. How verdicts get into the page

The reviewer's verdict is **data in the content JSON** (`verdict`: a heading, the ranked list, the
risks, how to pick), rendered into the `#verdict` box of round 3 and the recommendation footer of
round 1. It is written by the host from the reviewer's report after the host has spot-checked it;
the reviewer never edits the page. Keep verdict prose out of any public copy of the pipeline: the
examples in this repo carry parameters and numbers only.

## 6. How the operator picks

The page is the operator's instrument, not the reviewer's. Give them: the page link or file, the
reviewer's ranking **and its reasons**, the one-line recommendation, and the question in the form
"I recommend X; shall I take X into the build?" so a bare yes has one referent. Record the pick and
the operator's words in the plan. Bract's sequence: the reviewer suggested prototyping four; the
operator asked to compare the revised leader with two others; the reviewer ranked them; the
operator chose, then renamed.

## 7. The name check

Before any file carries the name, the host searches for it, before the phase 5 gate: `WebSearch`
when the tool is available (else the operator's browser) for `"<name>" font` and `"<name>" typeface`,
then Google Fonts, MyFonts, Fontspring, Adobe Fonts and Monotype. Every hit and every search run go
into the plan, and the operator chooses the name knowing them; no hit is not proof the name is free,
and the plan says so. Bract's sketches were called Burin; Monotype sells a Burin, so the operator
renamed the face before the first file existed.

## 8. Building a page

```
node scripts/concepts/build-page.js --template round1 --concepts concepts.js --content content.json out/round1.html
node scripts/concepts/build-page.js --template round2 --concepts concepts.js --content content.json out/round2.html
node scripts/concepts/build-page.js --template round3 --concepts concepts.js --content content.json out/round3.html
.venv/bin/python3 scripts/shoot.py out/shots --serve out --pages round1.html --widths 500 1280 --family <comparison family> --font-url /fonts/<its file>.woff2
```

The flags above are the script's own (`--template`, `--concepts`, `--content`, `--gen`, `--render`,
then the output path); `scripts/concepts/README.md` has the same lines.
