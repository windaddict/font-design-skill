# The site audit: find the tells before drawing a face for the pages

WHAT IT'S FOR: the reference for phase 1. A display face is drawn for the pages as they should be,
not as they are: if a heading sits under a label that repeats it, inside a boxed card, over a
decorative rule, the font never has to carry section identity by itself, and the one that is drawn
will be wrong once those crutches go. So the audit runs first, its fixes land on a branch with a
guard each, and the concept pages of phase 3 are judged on the fixed pages. Read it before the
audit, and read "What each finding changes for the font" when writing the guidelines.

Contents: 1 method · 2 the AI-tells list with instances · 3 the calibration traits · 4 the guard
pattern · 5 fix on a branch first · 6 the 360 px reading · 7 what each finding changes for the
font · 8 recording the audit

## 1. Method

Headless Chrome screenshots at 500, 1280 and 1600 px (and the 360 px reading of section 6), plus
the display sizes read from the stylesheet with `mine-sizes.py --json` (the file the brief names),
plus a read of the stylesheet for what the screenshots cannot show. No tool here collects computed
styles from the browser (`getComputedStyle`); the stylesheet reading stands in for them. Mark each
finding **seen** (in a screenshot), **computed** (only when the host measured it by hand, in
DevTools or a `shoot.py --dump-dom` DOM, and the record says where) or **CSS** (inferred from the
stylesheet). Rank by how
noticeable it is on the page, not by how easy it is to fix. Use the frontend-design plugin for the
aesthetic pass when it is installed; when it is not, section 3 is the calibration list and the
record says the pass was unaided.

The reviewer is a fresh strong-model subagent with `templates/reviewer-brief-audit.md`. Its report
has the shape of hop-safari's `docs/design-review-2026-11-15.md`: a ranked audit, the guidelines,
the concepts, and a "prototype first" recommendation.

## 2. The AI-tells list, with the two precedents' instances

A tell is a treatment that appears whatever the subject, because it is a default rather than a
choice. The two sites' audits found these; check each on yours.

| Tell | What it looks like | hopsafari.com (2026-11-15) | movingavg.com (2026-11-14) |
|---|---|---|---|
| A label that repeats the heading under it | a tracked small-caps eyebrow saying what the H2 says | 14 `.label` spans on the home page: "CONTENTS" over "Four ways in", "KENYA" over "Kenya Safari Guide"; "88" on screen five times above the fold | labels that carry no information; the DESIGN.md rule "labels must carry information" |
| Boxed cards with a hover lift | border + background + `translateY(-3px)` + shadow on hover | four chapter cards, the latest plate, two guide cards with a brass rail, the read-next list; the unboxed grid below them read better | the `.card-hover` pattern retired; "lists over card grids" |
| Rules as decoration | a `border-bottom` on every H2; a rule that fades to transparent | `.prose h2` underlined; the frontispiece rule faded (a 2015 tell) | — |
| Two navs, two date formats | one page with two names; ISO dates beside spelled dates | home nav "Contents · Guides · About · Feed", inner nav "About · Guides · Essays"; `2026-10-16` on the grid, `16 October 2026` on the home page | — |
| Repeated and formulaic copy | the hero lede reused as a blurb; a fact stated three times | "Since August 2010" twice plus "Begun / August 2010"; the lede also the Essays blurb | — |
| Riddling headings | H2s that name a mood, not the thing | "Where the book is open", "Four ways in", "Twelve plates" → "Latest", "Chapters", "A selection" | — |
| Arrows on links | `→` appended to link and button text | none found (0 in the built HTML) | "arrows only on buttons" |
| The loudest element is chrome | a label or nav outranking the content | "READ NEXT" as a 28 px tracked-caps bar between two rules on all 88 essays, because two heading rules outranked the label class | — |
| The name twice in 250 px | wordmark then H1 | defensible on a title page; the eyebrow above it was not | the wordmark now in the display face, part of the logo lockup: confirm wanted |
| The sheet floats on a shadow | a card-on-a-ground shadow under the content column | `.book-page` with a two-layer `box-shadow` (still open) | "no frame on the essay column" |
| Too many chips | a row of tag pills with a count repeated in two rows | 16 `.chip` links, "Food 33" in both rows (still open) | "no tag pills" |
| A display face that cannot hold the small sizes | hairlines under a pixel at 16.8 px | Bodoni Moda at 16.8 px visibly lighter than the body text; at 64 px the hairlines nearly vanished on paper | Fraunces turning up on many other sites: the reason for a custom face |

Not every tell has an instance on both sites; the empty cells are where the second audit did not
look or found nothing.

## 3. The calibration traits

The frontend-design plugin (1.1.1) lists the traits generated design clusters around; use them
as the aesthetic pass when the plugin is absent:

1. a warm cream background (near `#F4F1EA`) with a high-contrast serif display and a terracotta or
   warm-clay accent (often near `#D97757`);
2. a near-black background with a single acid-green or vermilion accent;
3. a broadsheet layout with hairline rules, zero border-radius and dense columns;
4. the SaaS-card kit: identical rounded cards, one radius on everything, the same soft grey shadow
   under each, gradient washes as decoration;
5. template chrome whatever the subject: a tracked ALL-CAPS eyebrow above every heading; meta
   strings joined with middle dots; labels built as "WORD — fragment"; tinted near-black standing in
   for black; a monospace face for small data labels; a `→` appended to link and button text.

The plugin's typographic tells: accenting one word of a headline in italic, bold or a colour;
all caps for labels; labels above content that add nothing. Its rule for structure: outlines,
borders, numbering, eyebrows and dividers encode information or go. All of these are legitimate
for some briefs; the point is that they appear regardless of subject.

## 4. The guard pattern

Each audit fix ships with a test, in the shape of hop-safari's `tests/test_design_audit.py`: a
module docstring that names the review and lists the problems it found and why no test noticed
them ("every page still rendered"), then one test per fix over the **built** pages:

- every page carries the same navigation (parametrised over the pages; a second test asserts the
  page list is not empty, so an empty glob cannot pass);
- the hidden heading is hidden on every essay, **and** the hiding class actually hides (the rule
  exists in the stylesheet with the properties that hide);
- no label sits directly over a heading (the tell, as a DOM shape);
- the contents and tag pages spell out every date (a regex over the built HTML for ISO dates);
- the home page items are not boxed cards (a source check on the stylesheet, stated as such,
  because a test can read CSS but cannot render it).

Write what the test checks, not what it is for, in its name; put the incident in the docstring;
watch each one fail. Describe the shape, do not copy hop-safari's file: its selectors are that
site's.

## 5. Fix on a branch first

Apply the fixes that change what the font must do (the eyebrows, the boxes, the rules, the second
nav) on a branch before round 1, each with its guard, so the concept pages show headings standing
alone. Bract's audit asked for items 1, 2, 4 and 5 fixed first and the concepts were judged on
those pages; the fixes merged in their own commit (hop-safari `2daac34`) before the font's
(`90a085c`), which is the rule (`SKILL.md` phase 1 gate): the audit fixes are the operator's own
decision at this gate and are committed as their own change; the font change that phase 9 reviews
and commits as one starts after them. Items that do not change the font (the chips, the shadow)
can wait, and the audit record lists them as open with their status.

## 6. The 360 px reading

Headless Chrome will not lay out under 500 px (trap 7). For the phone reading, use
`scripts/narrow.html`: a wrapper page with a 360 px-wide iframe around the target page; it measures
`scrollWidth` against `clientWidth` **inside** the iframe to detect horizontal overflow, after
checking that the inner page was served 200 and none of its faces failed (it reads no computed
styles; `SKILL.md` phase 1 has the command). Screenshots stay at 500 px and above (plan finding F007). Bract's audit
measured all six pages this way: `scrollWidth` never exceeded `clientWidth`. This reading is of the
pages in the face being replaced; it is repeated on every page with the wired font in every round of
phase 8 (`references/review-loop.md` section 2), because a wider face overflows a title that fit. Note also that
headless Chrome's virtual-time budget can expire before large images arrive, so a photograph
showing as alt text in a capture is not by itself a site defect.

## 7. What each finding changes for the font

The audit is not an end in itself; each item has a font consequence, and the brief should say it.

| Finding | Font consequence |
|---|---|
| Eyebrows removed | each H2 stands alone, so the display face must carry section identity by itself at 25–35 px; the label face shrinks to nav, buttons and chips |
| Boxes removed | the chapter names (17.6–27 px Bold) become the only structure, so **the Bold at 18 px matters** |
| Rules removed | an H2 must read as a heading without a rule, so the Bold needs a clear step from the Regular (Driftwood used ×1.65 pen width; Bract ×1.5 with `thinGrow` and `serifGrow`) |
| Riddling H2s renamed | shorter, plainer headings; no long balanced wrapped headlines except essay titles up to 70 characters |
| "READ NEXT" bar | none if hidden; if kept, a quiet 20–24 px weight |
| The small titles cannot be held by the current face | **the hardest constraint**: the hairline floor at the smallest size (references/guidelines.md), and a decision whether those elements stay in the display face or move to the body face |
| Dates and nav unified | none if dates leave the label face for the body face |
| The wordmark | the same face in tracked caps at 24–30 px Bold on a dark surface: design for it |

## 8. Recording the audit

The record is a numbered table of items with a status column (fixed in commit X; partly fixed,
with what is open; open), kept in the site repo's `docs/` as hop-safari's
`design-review-2026-11-15.md` is, followed by the ranked audit with its seen/computed/CSS marks,
the guidelines, and the concepts. Status is checked after the font ships, not before: Bract's
audit had 10 items; after the deploy, 5 were fixed, 2 partly, 3 open.
