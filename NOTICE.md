# NOTICE: provenance, and what the MIT licence does and does not cover

WHAT IT'S FOR: this repository publishes code that was first written for two private websites,
and it publishes the parameters of two typefaces that are not themselves public, and the parameters of
a third face, Tiki Terminal, whose font is open. This file records
where each part came from, what licence it carries here, and what is deliberately **not** in the
repository, so a reader can tell the open code from the two sites' property. It answers review
finding F010 of the skill's plan.

## Code

| Part | Derived from | Author | Licence here |
|---|---|---|---|
| `scripts/gen.js` (the generator: skeletons, pen model, serifs, terminals, fit, spacing, kerning, the italic) | John Knox's Driftwood generator, movingavg.com, `tools/driftwood/driftwood-gen.js` at commit `67a4e5b` (2026-11-14), as forked and fixed for Bract, hopsafari.com, `tools/bract/gen.js` at commit `90a085c` (2026-11-15), then generalised here (concepts externalised, `dropAmt`, the italic restored) | John Knox | MIT (see `LICENSE`) |
| `scripts/export.js`, `scripts/build.py`, `scripts/bounds.js`, `scripts/shoot.py`, `scripts/opsz.py`, `scripts/specimen.py`, `scripts/tests/*` | the Bract exporter, builder, review tools and test suite (hopsafari.com, `90a085c`), with the Driftwood exporter and builder (movingavg.com, `67a4e5b`) as the earlier form | John Knox | MIT |
| `scripts/render.js`, `scripts/concepts/*` | the Bract concept pages (hopsafari.com, 2026-11-15), neutralised: the templates carry invented copy and `content.example.json` | John Knox | MIT |
| `references/`, `templates/`, `SKILL.md`, `README.md` | written for this repository from the two sites' records | John Knox | MIT |

The author is John M. P. Knox, founder of Moving Average Inc. ([movingavg.com](https://www.movingavg.com)),
an advisory firm for CEOs and founders of B2B SaaS and MedTech companies.

All forked code is the author's own; no third-party code is included. Both source repositories
are private. **Relicensing**: the Driftwood generator lives in a company repository (Moving Average
Inc.'s movingavg.com site), and the Bract fork in a personal one. Publication of this repository
waited on the operator's written confirmation that they hold the rights to relicense both
generators under MIT. That confirmation is recorded here:

> Rights confirmation: given by John M. P. Knox on 2026-11-16, who holds the rights to both
> generators, the Driftwood generator as founder of Moving Average Inc. and the Bract fork as
> its author, and releases both under MIT in this repository.

## What is not here, and is not MIT

- **The fonts.** No `.woff2`, `.ttf` or `.otf` of any face, Tiki Terminal's included, is in this
  repository, and none may be added. Bract is licensed for use on hopsafari.com only; Driftwood MA is
  proprietary to Moving Average Inc.; a font built from the Tiki Terminal parameters is under the SIL Open
  Font License 1.1, not MIT (see below). The repository's tests fail if a font binary is tracked.
- **The sites' content.** No essay text, photograph, photograph title or built page from either
  site. `examples/bract/font.json` and `examples/driftwood/font.json` quote a few **public page
  titles** as character-set illustrations (the `titles` arrays), with the sites' owner's permission
  (plan decision 2 of 2026-11-15); nothing else of the sites' content appears.
- **Reviewer prose.** The verdicts written by the design reviewers into the two sites' private
  concept pages and review notes are paraphrased in `references/examples/`, never quoted.
- **Reference fonts.** Bodoni Moda, Newsreader, Fraunces and IBM Plex Sans (the faces the two
  sites compared against or replaced) are not shipped; the specimen takes comparison faces as local
  paths or URLs the user supplies.

## What the examples are

`examples/bract/` and `examples/driftwood/` carry **parameters and configuration only**: the
concept parameter sets (six round-1 concepts and the two shipped cuts for Bract; four concepts for
Driftwood) and a `font.json` for each. They are part of this repository and **MIT like the rest of
it**. Their name tables are neutral: the families are "Bract Example" and "Driftwood Example", the
copyright, manufacturer and designer strings are `{{operator}}` placeholders, the vendor id is
`EXMP` and the licence string is a placeholder for whatever licence the builder chooses. Building
them with this repository's scripts produces fonts of this repository's generator under those
neutral strings; those builds are not the shipped fonts, and the Driftwood example in particular is
a re-expression (variable, overlapping contours) of a design that shipped as unioned CFF statics.

**The names are the exception.** "Bract" and "Driftwood MA" identify the two sites' shipped faces
and are not licensed for reuse as font names: a font built from these parameters may carry any
family name except those two. The example READMEs and `references/examples/` describe the shipped
fonts' real name tables (copyright, maker, licence) as history — what shipped on the sites, not
what these files build.

**Tiki Terminal** (`examples/tiki-terminal/`) is the exception to "neutral": the face is the skill's own
open example, so its name table is real. The family is "Tiki Terminal", the copyright, manufacturer and
designer strings are John M. P. Knox, the vendor id is `JMPK`, and the licence string and name ID 13 say the
SIL Open Font License, Version 1.1. Its parameters (`concepts.js`, `skeletons.js`, `font.json`,
`requirements.json`, `content.json`) are MIT like the rest of the repository. A font built from them is
under the OFL 1.1 and travels with `examples/tiki-terminal/OFL.txt`; no Reserved Font Name is declared.
The name was searched for and no typeface of that name was found; no hit is not proof that it is free.
The font itself is not tracked, like every other face.

## Third-party tools

The scripts call fontTools, brotli, skia-pathops and Pillow (Python), Node, and a Chrome or
Chromium binary on the user's machine. None is vendored. Their licences are their own.
