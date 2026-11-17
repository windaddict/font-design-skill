# Brief: judge round {{1 | 2 | 3}} of the concept pages for {{site}}

<!-- WHAT THIS TEMPLATE IS FOR: the instruction the host gives a FRESH strong-model subagent for
phases 3–5. One brief per round; the reviewer has not seen the previous round's verdict. Fill the
{{slots}}; give it the page and the parameters, not your opinion of them. -->

You are judging typeface concepts for a website, rendered in the browser from a parametric
generator before any font file exists. You have not seen the earlier rounds. Read-only.

## The operator's goal, verbatim

> "{{goal sentence, exactly as the operator wrote it}}"

The tests, in order: readable at every size the site uses ({{sizes}}); unique, not mistakable for
{{old face}}, {{body face}} or a stock face; complements {{the brand sources}}.

## What to read

- The page: `{{path or artifact link}}` ({{round 1: the spectrum, all concepts side by side plus
  one full specimen each | round 2: the shortlist on mock-ups of the redesigned pages, with the
  face picker | round 3: the finalists head to head, with the picker and the two-cut switch at
  {{DISPLAY_FROM}} px}}). Use `?face=<id>` to select a face; the picker remembers the choice.
- Screenshots of the page at 500 and 1280 px, 1× and 2×: `{{directory}}`.
- The concepts and their parameters: `{{concepts.js}}`; the knobs are explained in
  `references/generator.md`.
- The guidelines from the audit: `{{file}}` (the sizes, the hairline floor of {{N}} units at
  {{smallest px}}, the character set with its traps).
- {{Round 2 and 3: the audit items already fixed on the mock pages.}}
- {{Round 2 and 3: what changed in the leading concept since the last round, as parameters and
  numbers: e.g. "serifGrow added at 0.6; Medium ×1.3 for the small titles".}}

## What to produce

**Findings ranked by visibility at 1× on the page at the sizes the site uses**, then at 2×, then
in the specimen rows only. In round 1 that page shows the site's real titles at its sizes; in
rounds 2 and 3 it is the mock pages (a fixed layout set at the site's sizes, not the site's pages:
the face is judged on the real pages in phase 8, so say "on the mock" and never "on a real page").
Each finding names the concept, the element (a title, the wordmark, an H2), the size, and the crop
or the `?face=` view where it is seen, and says what it would change for the concept (a parameter,
a skeleton, a cut).

Then, for this round:

- **Round 1**: a shortlist (three or four) with one sentence each on why; which concepts to drop and
  why; **how to pick** among the shortlist (what to look at, at which size); the risk of each.
- **Round 2**: the leading concept and the revisions it needs, as parameters; which finalists to
  carry; whether a Medium or a second cut is needed and at which size.
- **Round 3**: a ranking with reasons; the one recommendation; the targeted fixes to sketch before
  a build (an optical-size cut, a skeleton change); and **how to pick** if the operator disagrees.

## Rules

- Judge on the real titles at the real sizes on the real surfaces, not on the alphabet row. The
  smallest size on the page decides more than the largest.
- Evidence per finding: the view and the size. Say when you are uncertain and what would settle it.
- Recommend and say how to pick; the operator picks.
- Do not edit the page or the concepts. Do not describe the page's own verdict box as your finding.
