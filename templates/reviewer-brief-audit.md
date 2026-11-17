# Brief: audit {{site}} before a display face is drawn for it

<!-- WHAT THIS TEMPLATE IS FOR: the instruction the host gives a FRESH strong-model subagent for
phase 1. The reviewer has no memory of the site or of the host's hypotheses; everything it needs
is in this brief and the files it names. Fill the {{slots}}; do not paste your own conclusions
into it. -->

You are reviewing a website's design before a custom display typeface is drawn for it. You have
not seen this site before, and nobody has told you what is wrong with it. Read-only: change
nothing in the repository.

## The operator's goal, verbatim

> "{{goal sentence, exactly as the operator wrote it}}"

## What to read

- Screenshots: `{{directory}}` — headless Chrome at 500, 1280 and 1600 px ({{list the files and
  which page each is}}). The 360 px reading is `{{narrow results}}` (horizontal overflow measured as
  `scrollWidth` vs `clientWidth` inside a 360 px iframe; screenshots cannot go under 500 px).
- The display sizes read from the stylesheet: `{{file}}` (the JSON from
  `scripts/mine-sizes.py <css> --family <today's display family> --root 100 150 --json`: per selector,
  the size range at a 16 px root and at 150 %, the smallest size and the hairline floor). This is
  read from the CSS, not computed in a browser.
- The stylesheet: `{{path}}`. The templates: `{{glob}}`. The built pages: `{{directory}}`.
- The site's design notes, if any: `{{DESIGN.md or equivalent}}`.
- The body face is {{body face}}; the display face today is {{old face}}, set at {{size range}}.

## What to produce

A report in three parts, in this order.

**1. Design audit, ranked by how noticeable each item is on the page** (not by how easy it is to
fix). For each item: what it looks like; where (page, selector, line); whether you **saw** it in a
screenshot, **computed** it from a style, or **inferred** it from the CSS; the fix; and **what the
item changes for the font** (none; a size; a weight; a role the face must carry by itself). Check
these tells in particular: a label that repeats the heading under it; boxed cards with a hover
lift; rules as decoration; two navs or two date formats; repeated or formulaic copy; headings that
name a mood rather than the thing; arrows appended to links; a label or nav that is the loudest
element on the page; the name twice within a screen; a content column floating on a shadow; a row
of chips; a display face that cannot hold the smallest size it is set at. Say which tells are
absent too.

**2. Guidelines the font concepts must meet**: the axes on which the face must differ from the
body face (at least two of contrast, stress, serif shape, width); the sizes it must survive, from
the stylesheet, and the hairline floor at the smallest (one CSS pixel at size *s* px is 1000/*s*
units; the thinnest stroke should stay at or above about 0.75 px); weights; case; the exact
character set from the real titles, with the NBSP and straight-apostrophe counts; figures.

**3. Concepts**: about six, named for the brand, each as a parameter set for the generator
(`references/generator.md` lists the knobs), ordered closest to the current face first and most
organic last, with the risk of each. Then "prototype first": which to take into round 1, in which
order, and which audit items to fix before the concepts are judged.

## Rules

- Evidence per finding: a screenshot name, a selector, a line, a computed value. A bare
  location is not evidence.
- Say when you are uncertain, and say what would settle it.
- Recommend and say how to pick; do not pick for the operator.
- Do not edit anything. Do not restate the goal sentence back as a finding.
