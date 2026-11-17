# Trigger cases for the `font-design` description

WHAT IT'S FOR: the description in `SKILL.md`'s frontmatter is the only thing that decides whether the
skill is invoked. This records the prompts it was checked against and the result, so a later edit to
the description can be re-checked against the same set (plan section 6, step 8, scaled down from the
skill-creator's description optimiser).

**Method and its limit.** The skill was not installed on the machine when this was run (installation is
a publication step), so the check is a simulation: a fresh Sonnet agent was given the frontmatter
descriptions of `font-design` and five neighbouring skills (`frontend-design`, `impasse`,
`generate-image`, `marketing-skills:image`, `code-review`) and the ten prompts, and asked which one
skill it would invoke first, as Claude Code does from descriptions alone. That is a proxy for the
real triggering decision, not the decision itself. Re-run with the skill installed after publication
and update this file.

| # | Prompt (abridged) | Should trigger | Chose | Hit |
|---|---|---|---|---|
| 1 | "a unique headline font for my site, something nobody else has; body is Newsreader" | yes | font-design | yes |
| 2 | "make us a wordmark face from the logo (a bent tree on a cliff)" | yes | font-design | yes |
| 3 | "replace Playfair Display with something of our own; plate titles are 16.8px" | yes | font-design | yes |
| 4 | "add an italic to Bract; blockquotes need one" | yes | font-design | yes |
| 5 | "our headings use Fraunces like everyone; what would it take to draw our own variable display face?" | yes | font-design | yes |
| 6 | "run the concept-page spectrum again: six directions, closest to what we have first" | yes | font-design | yes |
| 7 | "pick a Google Font for the body text that pairs with Bract" | no | frontend-design | yes |
| 8 | "fix the kerning CSS on the h1 — letter-spacing -0.02em looks cramped on mobile" | no | none | yes |
| 9 | "generate a hero image for the fonts blog post, letterpress type" | no | generate-image | yes |
| 10 | "review my diff that changes the @font-face declarations and the preload tag" | no | code-review | yes |
| 11 | "recommend a hero font for our landing page" | no | not run | — |
| 12 | "what font should my headings use" | no | not run | — |
| 13 | "suggest a display typeface that pairs with Inter" | no | not run | — |
| 14 | "is Playfair a good headline font?" | no | not run | — |

Result (2026-11-15): 10 of 10 on prompts 1–10. The agent called prompts 3, 5 and 10 the closest calls:
3 could read as a plain font swap, 5 is phrased as a question, and 10 sits between `code-review` and
`impasse`. The description was not changed after this run. If a later run misses prompt 3 or 5, add
"replace a stock or Google font with the site's own face" and "what it would take to draw our own
font" to the description.

Prompts 11–14 were added after an independent review of the description (finding D10, 2026-11-15):
each names a headline, display or hero font with no intent to draw or build one, so each is a
should-not-trigger case for `frontend-design`. The description was tightened for them (the trigger
is the intent to draw or build a face, and the "Not for" clause now names headline, display and hero
fonts to be recommended, picked or paired). **The simulation has not been run on prompts 11–14, and
has not been re-run on prompts 1–10 since that edit**: the "Chose" and "Hit" cells of 11–14 say so
(an earlier version of this table showed results for them that no run had produced; independent
re-review, docs F006), and the results for 1–10 are from the pre-edit description. Both are filled in
when the simulation is re-run with the tightened description, and the real check is the installed
skill after publication.
