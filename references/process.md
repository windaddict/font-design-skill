# The process: nine phases, their gates, and who does what

WHAT IT'S FOR: the detailed version of the workflow in `SKILL.md`. For each phase it gives the
inputs, the outputs, the gate (what the operator decides), who does what (the host, a fresh
strong-model reviewer, Impasse, the frontend-design plugin), the questions to ask, time and cost
notes, and the stop rules. It ends with the rules for working with little supervision and the
publication blockers. Read the phase you are entering; read the last two sections before the first
phase.

Contents

0. Before you start
1. Phase 1 — Audit the site
2. Phase 2 — Guidelines from the site
3. Phase 3 — Round 1, the spectrum
4. Phase 4 — Round 2, mock-ups
5. Phase 5 — Round 3, head-to-head
6. Phase 6 — Plan the build
7. Phase 7 — Build
8. Phase 8 — Design-review loop
9. Phase 9 — Ship
10. Working with little supervision
11. Publication blockers
12. Roles in one table

Everything site-specific lives in two files the phases produce: `font.json` (configuration) and
`requirements.json` (reviewed expectations). One face has been made this way in full: Bract
(hopsafari.com, one variable font, two axes, four masters, three review rounds, 2026-11-15).
Driftwood (movingavg.com, 2026-11-14) is the earlier precedent: a static family with an italic,
built before the protocol was written down by a union pipeline into five CFF files. Its lessons and
the three bugs found in it later shaped these phases; it did not pass through them. Both records are
in `references/examples/`.

## 0. Before you start

**Do.** Say the skill version. Classify the change under the operator's process: a site-wide face
is a significant change (it touches public URLs the stylesheet links, and it is a new feature), so
the full plan → review → build → review order applies. Check the tools and state which are present:
`node` (≥ 20), a Python ≥ 3.10 venv with fonttools 4.68.*, brotli, skia-pathops, pillow, uharfbuzz and unicodedata2, Chrome,
Impasse, the frontend-design plugin, the strongest model. For anything missing read
`references/fallbacks.md` and say what the gap costs before starting.

**Ask the operator**, in one message, and record the answers in the plan:

1. The goal, in their words, as one sentence (Bract: "a readable and unique font that complements
   the design and branding"). This sentence goes verbatim into every reviewer brief.
2. Which site and which pages; the body face; where the brand comes from (a mark, materials, a
   history).
3. Weights, and whether an italic is wanted.
4. Name candidates (checked for collisions before any file exists).
5. Name-table owner and licence text: **no defaults**, asked every time.
6. The size budget (both precedents: 100 KB).
7. May the concept pages be published as private artifacts?
8. Consent to send the plan and the diff to a third-party model through Impasse.
9. Who deploys, and whether time or cost is constrained (the review loop is the expensive part).

**Project files.** Decide where they will live (the convention is `tools/<face>/` in the site repo)
and create nothing yet. Each file is created in the phase that produces its inputs:
`requirements.json` in phase 2, `concepts.js` in phase 3, `font.json` and the copy of `scripts/` in
phase 7, after the plan of phase 6 has settled the masters and axes.

**Stop rule.** No consent to Impasse and no agreed substitute: stop before phase 6.

## 1. Phase 1 — Audit the site

**Inputs.** The built pages, the stylesheet, Chrome. **Reference:** `references/site-audit.md`;
the frontend-design plugin when installed.

**Do.** Screenshots at 500, 1280 and 1600 px with `shoot.py`, and the 360 px iframe reading through
`scripts/narrow.html` (`shoot.py OUT --serve <static dir> --pages __fd/narrow.html --widths 500 --scales 1 --dump-dom --no-sentinel --query url=/<page>.html --query width=360`;
the page passes only when the dumped `<html>` carries `data-fd-overflow="false"` with
`data-fd-narrow-stage="fonts"`, the reading taken after the web fonts settled); the display sizes
read from the stylesheet (`scripts/mine-sizes.py <css> --family <today's display family> --root 100 150 --json`,
saved to a file the brief names; no tool here writes a computed-styles report from the browser, so
the brief asks for this stylesheet reading instead); a fresh reviewer with
`templates/reviewer-brief-audit.md` returns the ranked audit with seen/computed/CSS marks and what
each item changes for the font. The host spot-checks two items itself and **proposes** which items
to fix before the font (typically the ones that change what the font must do: labels over headings,
boxed cards, decorative rules, a second nav). Nothing is fixed before the gate.

**Outputs.** The audit record (a numbered table with status; the ranked list; the proposal) in the
site's `docs/`.

**Gate.** The operator selects which items are fixed before the font, and which wait.

**After the gate.** Implement the selected fixes **on a branch**, each with a guard in the shape of
a design-audit test, watched to fail, and commit them as their own commit (Bract: hop-safari
`2daac34`, before the font's `90a085c`): they are site design changes the operator judged at this
gate, outside the font change that phase 9 reviews. That branch is the set of pages the concepts are
judged on from phase 3.

**Cost.** One reviewer context; the fixes are routine CSS and template edits. Bract: 10 items, 4
fixed first.

## 2. Phase 2 — Guidelines from the site

**Inputs.** The stylesheet, the built pages. **Reference:** `references/guidelines.md`.

**Do.** Find every selector the display face sets with `--family <today's display family>` on both
tools (every rule whose `font-family` names it first, `@media` included; the list is printed; a
face inherited from `body`, a `font:` shorthand or a custom property is not seen, and then the
selectors are named by hand from the templates and added with `--selectors`). Run
`scripts/mine-sizes.py <css> --family ... --root 100 150` for the display selectors' size ranges at a
16 px root and at a 150 % root; run `scripts/mine-charset.py --html <built pages> --css <css> --family ...`
for the character set of the text those selectors set in the built pages, the NBSP and
straight-apostrophe counts, the capitals a `text-transform` rule makes the browser draw (on the
selector, a descendant or a class inside the text), and the `charset` block; what it cannot see
(an inline style, script-set text, a selector it cannot read) is named by hand, so the set is
checked, not exact. Write: the sizes the face must survive; the hairline floor (`1000 × 0.75 /
smallest px` units, the target every master serving the smallest size must measure at or above at
the first export; a measured minimum below it is a design finding, not a floor to record); the two
contrast axes against the body face; the weights; the case; the charset with its traps; the
precedent lessons. Create `requirements.json` here, from `templates/requirements.example.json`: now it takes
`required_characters` and `titles` from `mine-charset.py --json`, `cmap` from the template (the
generator's glyph set plus the builder's quotes and spaces, the same for every project), `names`
from the opening questions and `size_budget_bytes` from the budget answer; `axes`, `masters`,
`instances`, `avar` and `interpolated_check` come from the phase 6 plan; `hairline_floors` and
`word_space` from the first `export.js` run of phase 7 (the template's floors are the fictional
Example face's). `SKILL.md` phase 2 has the table. This is the file's first version.

**Outputs.** The "Guidelines" section of the audit record; the first `requirements.json`.

**Gate.** Guidelines written and shown, and three decisions asked explicitly, one question each,
and recorded in the guidelines and `requirements.json` before phase 3 draws a concept:

1. **Each character the generator cannot draw**: fix the content, carry the glyph (a new
   skeleton), or both. Check the inventory before asking, from the skill directory, with the
   template font standing in for the project's `font.json` (which phase 7 creates):
   `node scripts/export.js --font templates/font.example.json --group roman --requirements <site>/requirements.json <site>/tools/<face>/work/charset-check.json`
   — the exporter names every required character without a skeleton and exits non-zero. Bract: fix
   the asterisk H2 as content, carry `#` and `+`, and draw U+0027 as the curly apostrophe. A glyph
   to carry is drawn before round 1 (`SKILL.md` phase 2 gate, item 1), in the face's skeleton
   override `tools/<face>/skeletons.js` (`references/generator.md`, "Per-face skeletons"), with the
   concept pages built with `--skeletons` and the pre-check re-run with the override applied. The installed skill is not edited during a project: a glyph that belongs to
   everyone (a punctuation mark, a currency sign) is a separate change to the skill's own repository,
   on the operator's word, with its own tests and review.
2. **The `opsz` axis ends**, from the smallest and largest display sizes `mine-sizes.py` reports
   (Bract: 40–80 for a 15.2–80 px site, the text cut serving everything under 40). The neutral
   example's 24–72 is the fixture's range; for an 80 px site it is wrong. Measure the browser's
   px-to-`opsz` mapping first, on the fixture font `smoke.sh` built (`opsz.py` on
   `examples/neutral/out`, `SKILL.md` has the line); phase 8 confirms it on the built font.
3. **The smallest elements**: do they stay in the display face, or move to the body face? The
   answer sets the hairline floor (Bract: 15.2 px numerals and 16.8 px titles stayed, floor ≈ 45
   units; moving them would have relaxed it to about 24 px).

## 3. Phase 3 — Round 1, the spectrum

**Inputs.** The guidelines, the fixed pages, the brand sources. **Reference:**
`references/concept-pipeline.md`, `references/generator.md`, `references/genres.md`.

**Do.** Name each round-1 concept's genre from `references/genres.md` beside its brand name, and cover at
least three genres; the table says which genres the generator reaches and which it cannot. Create `concepts.js` (`templates/concepts.example.js` is the shape) with about six
concepts named for the brand, each a parameter set, closest to the face in use first and most
organic last. Build
the round-1 page with `scripts/concepts/build-page.js` from a content JSON of real titles, the
site's surfaces and sizes. Publish it as an artifact if allowed. A fresh reviewer with
`templates/reviewer-brief-concepts.md` recommends a shortlist and says how to pick. The host opens
the page and checks two of the reviewer's claims against it.

**Outputs.** `concepts.js`, the round-1 page, the reviewer's ranked recommendation.

**Gate.** The operator picks the shortlist, or asks for a round 1b with new or revised concepts.

**Cost.** A reviewer context; the page builds in seconds. Say that each further round costs the
same again.

## 4. Phase 4 — Round 2, mock-ups

**Do.** The shortlist set into mock-ups of the redesigned pages (the branch from phase 1) with a
face picker; the reviewer, with the frontend-design plugin when installed, judges on the mock pages
and revises the leading concept (Bract: a Medium for the small titles, serifs that grow with weight,
slightly heavier hairlines). Revisions are parameter changes in `concepts.js`, recorded with the
reason.

**Outputs.** The round-2 page; the revised concepts.

**Gate.** The operator names the finalists.

## 5. Phase 5 — Round 3, head-to-head

**Do.** The finalists on the mock pages with the picker; the reviewer's verdict and ranking
rendered in the page; targeted fixes sketched before any build (an optical-size cut: Bract's second
display sketch made the stems 8 % heavier after the first changed nothing visible). The two-cut
switch at `DISPLAY_FROM` shows the optical-size idea before it is an axis.

**Outputs.** The round-3 page; the chosen concept's parameters; the name.

**Gate.** The operator chooses the design **and the name**. Before the gate the host searches the
name (`WebSearch` when available, else the operator's browser: `"<name>" font`, `"<name>" typeface`,
then Google Fonts, MyFonts, Fontspring, Adobe Fonts, Monotype) and puts every search and hit in the
plan; no hit is not proof the name is free, and the plan says so (Burin → Bract).

## 6. Phase 6 — Plan the build

**Inputs.** The chosen parameters, the guidelines, `requirements.json`, the stylesheet.
**Reference:** `references/variable-font-build.md`, `references/traps.md`, `templates/plan.md`.

**Do.** The strong model writes the plan in the template's shape: the success criterion in the
operator's words; axes, masters (a full rectangle), instances, `avar`; the hairline table per size;
the CSS and template changes; the tests with their mutations; the review loop; the risks and
questions. Its measured figures (incompatible glyphs, points per master before decimation) come
from an export of the planned masters run now from a scratch `font.json` in the project, at
`tools/<face>/work/plan-check.json` (`templates/font.example.json` copied, `concepts` pointed at the
project's `concepts.js`, the planned masters and axes written in; `work/` is scratch, not committed,
and nothing is written into the installed skill); the project's `font.json` is created in phase 7 from the
reviewed plan. The host **writes its own view first** (a numbered list, kept out of the instruction),
then sends Impasse the plan **with** the generator, the precedent build and the site's stylesheet
in the artifact, because a relational claim needs both sides. Verify every finding against the
code; a rejection needs contradicting evidence, not judgment. Amend the plan. Record every finding,
its check and its change in "Independent review and what it changed". Bract's plan review: 13
findings, all accepted, four masters instead of three among the changes.

**Gate.** The operator answers the plan's questions. A deadlock between the host and the reviewer
is the operator's to settle.

**Cost.** One Impasse run (minutes; consent-gated); the plan is the longest single document.

## 7. Phase 7 — Build

**Inputs.** The amended plan. **Reference:** `references/variable-font-build.md`,
`references/testing.md`, `references/generator.md`.

**Do.** Copy `scripts/` into the site's `tools/<face>/`, after `smoke.sh` has finished (its mutation
step edits the scripts in place and restores them by digest, so a copy taken mid-run carries a
mutated file), and check the copy with `diff -r <skill dir>/scripts tools/<face>/scripts` (no
output: the face's own letters are in `tools/<face>/skeletons.js`, outside the copy). Create `font.json` there from `templates/font.example.json` with the plan's masters, axes
and floors, plus `"skeletons": "skeletons.js"` when the face has an override, and finish `requirements.json`. Paths written inside `font.json` (`out_dir`, `concepts`,
a group's `file`) resolve relative to the `font.json`'s directory; the manifest lands at
`<out_dir>/manifest.json` unless the `manifest` key moves it; every path given on the command line
(`--static`, `--out-dir`, `--masters`, `--requirements`, `export.js`'s output, `pytest --static-dir`,
`mutate.py --static-dir`) resolves relative to the working directory, as the shell that typed it
expects, and under `--out-dir` the manifest goes into that directory whatever the `manifest` key
says. `export.js --requirements` first, per group: this explicit export is only the pre-check
(it names any character without a skeleton), and its JSON is not committed. Then `build.py`, which
runs the export itself into a temporary directory and prints a `SELF-CHECK ok:` line per check;
read every one. Three of them decide things outside the font's drawing and are read twice: the
`vertical metrics written` line (hhea and OS/2 typo carry the same ascender and descender with a line
gap of 0, win covers every glyph; the `line-height: normal` it prints is what an element with no
explicit line height gets where the platform reads hhea or typo, which now agree (a platform that reads the win
metrics is not covered), and it can differ from what a live site had, so the numbers
are reviewed and pinned in `requirements.json` `vertical_metrics`), the `fsType` line (the operator's
`names.fs_type`, which a config cannot omit) and the STAT line (axis values for every named instance). Get the woff2 to the served path: point `out_dir` at the site's font folder (Bract:
`static-pages/fonts/bract/`, the manifest kept beside the tool) or copy each group's woff2 there
after every build; the file the stylesheet names must be the file the manifest hashes. Wire the
stylesheet (one `@font-face` with the weight range, `font-optical-sizing: auto`, weight 500 on the
small titles, no `letter-spacing` on display rules) and the preload in every template. Run the
font suite where the copy put it (`tools/<face>/scripts/tests`, which needs the scripts beside
it) with `--font`, `--requirements` and `--static-dir` (`none` when no statics ship), and fill
`test_site_wiring.py.tmpl` into the site's own tests directory. Run
`scripts/tests/mutate.py` with the same `--static-dir` (`none` skips the static mutations and says
so; every expected text is derived from the project's own `requirements.json`) and **watch every
guard fail**; choose the weakest mutation; record survivors as findings and fix the tests, not the
log. **Commit nothing yet**: the commit is phase
9's last step, after the independent review and its fixes, so the review covers everything that
ships.

**Outputs.** The font, the manifest, the wired site, the green suite, the mutation log — all
uncommitted.

Then the FontBakery gate, `scripts/fontbakery-gate.py --font font.json --requirements requirements.json`:
it builds each group's variable TTF into a temporary folder and runs `fontbakery check-universal` on it.
Every FAIL, ERROR or FATAL must be fixed or listed in `requirements.json` `accepted_qa_findings` with
the reason (a required key; `[]` when nothing is accepted) and, where the check could fail another way later, the
message `codes` accepted (a failure with another code then blocks). The match is on the code, not the message
text: a new failure that reuses an accepted code passes and shows only in the printed messages, so read them on
every run (operator decision, 2026-11-16; text matching would break on FontBakery upgrades). A report whose summary counts more failures than
its sections hold, a FontBakery exit code other than 0 or 1, and a missing report all fail the gate. The first run on a face finds what the
suite never pinned, because the suite holds what the project decided and FontBakery holds what the
format expects. The neutral example accepts five, each with its reason in `requirements.json`: `case_mapping` (the
generator draws seven lowercase accented letters, ì î ò ù û ā š, without capitals); `opentype/STAT/ital_axis`
(no `ital` axis in STAT, not written by the build); `opentype/varfont/family_axis_ranges` and
`varfont/consistent_axes` (the fixture's italic has one axis beside the roman's two); and
`family/vertical_metrics` (the roman and italic extents differ by a unit and each group is built alone). The
two files go through one FontBakery run, because family checks need the pair. An exit of 3 means FontBakery is not
installed (`requirements-dev.txt`); the gate was SKIPPED, NOT PASSED, and phase 7 does not pass without
it unless the operator waives it in writing. A deliberate non-zero `fs_type` is accepted under a vendor
profile (`--profile googlefonts`, id `googlefonts/fstype`) with the licence as the reason.

**Gate.** Suite green, every mutation red, `build.py --check` byte-identical, the FontBakery gate
passed or waived in writing.

**Stop rule.** A self-check that fails for a design reason (a hairline under the floor, a fold) goes
back to the concept, not to the budget.

## 8. Phase 8 — Design-review loop (≤ 6 rounds)

**Reference:** `references/review-loop.md`.

Keep each round's `out/` (`cp -R` to `work/round-N/`) and run `scripts/diff.py` against it after the
next build; give the reviewer `diff.md`, so "what changed" arrives as pictures, not as the host's summary.

**Do.** build → `specimen.py --font font.json --requirements requirements.json --font-url /fonts/<file> <site root>/review/specimen.html`
→ `shoot.py OUT --serve <site root> --pages ... --family <Family> --font-url /fonts/<file>` (pages ×
widths × 1×/2×, plus `--root 150`; a shot without `--family` and `--font-url` is a picture, not
evidence). Serve the built site root and write the specimen under it, so the root-relative font URL
resolves to the woff2 the pages load (the specimen opens with the proof rows of `references/review-loop.md`
section 3); `opsz.py OUT --serve <site root> --font-url /fonts/<file> --family <Family> --axis <min> <max> --px <sizes>`
confirms on the built font the `opsz` the browser applies at each size (the ends were chosen at
the phase 2 gate from the same measurement on the fixture font) → the 360 px reading **on every
page with the wired font** (`shoot.py OUT --serve <site root> --pages __fd/narrow.html --widths 500 --scales 1 --dump-dom --no-sentinel --query url=/<page>.html --query width=360 --query family=<Family>`
per page; every page must carry `data-fd-overflow="false"` at `data-fd-narrow-stage="fonts"`,
which `narrow.html` writes only for an inner page served 200 with no failed face and a loaded face
of the family, and `error` otherwise; phase 1 measured the old face, and a wider face overflows a
title that fit, `smoke.sh` step 11 shows it on the fixture site) → a **fresh** reviewer with `templates/reviewer-brief-design-round.md` and the goal
sentence verbatim → ranked findings naming their crops, an overflow ranked first → changes → the host
spot-checks two crops and runs one mutation of its own → suite green → next round. After the round
that would end the loop (or round 6), and at any round the operator asks for, ask the operator to make
the platform run once for the face (`references/review-loop.md` section 2, a caller of the skill's reusable workflow: `gh workflow run platform-shots.yml`,
then `gh run download -n platform-shots-compare`) and read `compare.md` top-down, "Refused" and
"Mismatched" first, then the smallest sizes. A stroke that breaks up at 1× on a real page in any leg is a
1× finding; one that reads lighter but whole goes in the record. A round that changes `thin`, the floors
or the smallest sizes re-runs it.

**Gate.** Stop when a round reports nothing visible at 1× on a real page and the suite is green; or
at round 6 when what remains is visible only at 2× or in the specimen, recorded as open items for
the operator. **At round 6 with a defect still visible at 1× on a real page, stop before phase 9 and
ask the operator**: revise the design (back to phase 5 or 6) or leave the face unshipped. That
defect is publication blocker 5 (section 11); the round limit does not turn it into an open item.
The operator may cap the rounds earlier; say the cost before round 1.

**Cost.** The expensive part of the skill: each round is a full shoot and a long reviewer context.
Bract: three rounds.

## 9. Phase 9 — Ship

**Reference:** `templates/font-record.md`, `templates/impasse-diff-instruction.txt`.

**Do.** Nothing of the font change has been committed yet. First write the record from
`templates/font-record.md`, the tool README and the site's CLAUDE.md section, so the review covers
them. Then stage the whole change (`git add -A -- <every path of the change>`: new files are most of
it, and an unstaged `git diff` leaves untracked files out) and, host view first, have Impasse review
**`git diff --cached`**, docs and tests included (the regenerated pages excluded except samples).
Verify each finding; fix; `git add` the fixes; **one re-review** of the staged diff with the
re-review instruction naming the previous findings; fix its findings without a third review. After
material fixes rerun the affected tests and smoke steps, say so, and note the post-review fixes in
the record. **Then commit everything together** in one commit: the woff2, the manifest, the sources
(`font.json`, `requirements.json`, `concepts.js`, the copied `scripts/`), the stylesheet and
templates, the tests and the docs. **Deploy only on the operator's word.** Live checks: the font
served 200, the preload present, a headless shot of the live page with `--family` and `--font-url`.

The record's Windows line has two forms (`templates/font-record.md`): the platform run's id, date, browsers
and what the smallest rows showed, or "not checked on Windows" with the claim it limits. The platform run is
not a publication blocker and is not in section 11's list.

**Gate.** The operator says deploy. Bract's diff review: 8 findings; re-review: 5; all fixed.

## 10. Working with little supervision

**Decide alone:** parameter changes inside the reviewed concept during the loop; which mutation to
run; test and documentation wording; the order of work; which audit items change what the font
must do (then report it).

**Ask:** the shortlist, the finalists, the design, the name (after the host's own name search, phase
5); the name-table owner and licence (asked in the opening questions, written into
`requirements.json` `names` in phase 2 and `font.json` `names` in phase 7; unanswered by phase 7, the
build waits), and the embedding permission `names.fs_type` (4 for a proprietary face, 0 for an open
one; no default, the build refuses a config without it); which
audit items to fix first; content traps; the size budget; anything irreversible (deleting the old
face's files, deploying); any Impasse deadlock; whether to proceed when a tool is missing; capping
the review rounds.

**Report:** findings ranked by visibility at 1× on a real page, each naming its crop; parameters
and numbers, not reviewer prose; what was verified and how ("measured with `opsz.py`", "read in
`build.py`"), and what was not. A subagent result is a lead until the host has opened the source.
Every departure from the plan is logged in the plan's review section or the record's "What failed".
Questions end with one action so a bare yes has one referent: options, recommendation, question.

## 11. Publication blockers

The face does not ship, and the skill repo itself does not publish, while any of these holds
(review finding F015 of the skill plan):

1. A failed self-check or test.
2. Browser evidence missing: no round of the loop has a Chrome shot of the font on a real page at
   1× taken with `--family` and `--font-url` (a shot without them is a picture, not evidence).
   Missing browser evidence blocks publication unless the operator waives it in writing; the waiver
   is recorded in the font record and stated in the shipped docs, and nothing else lifts this item.
   `SKILL.md` section 4 and `references/fallbacks.md` ("No Chrome") say the same.
3. A required character missing from the font (`export.js --requirements` or the coverage test).
4. Licence or rights unconfirmed: the name-table owner and licence not answered; for this repo, the
   operator's confirmation that both source generators may be relicensed (`NOTICE.md`).
5. A defect visible at 1× on a real page in the last round — including the sixth; the round limit
   sends the question to the operator (phase 8), it does not lift the blocker.
6. A page that overflows at 360 px with the wired font (`narrow.html`, the `fonts`-stage reading),
   or a shipped build with no such reading on every page.

After material post-review fixes, rerun the affected tests and smoke steps and record that they
were rerun; a fix after the review is not covered by the review.

## 12. Roles in one table

| Who | Does | Never does |
|---|---|---|
| The host (the session running the skill) | runs the tools, writes `font.json`, `concepts.js`, the plan and the record; forms its own view before every review; verifies every finding; spot-checks two crops per round; runs the mutations | reviews its own build in its own context; pastes its conclusions into a reviewer's instruction |
| A fresh strong-model reviewer (a new subagent each time) | the audit, the concept rounds, each design round, from a brief template with the goal sentence verbatim | edits anything; sees the previous round's findings |
| Impasse (a different provider's model) | the plan review and the diff review and re-review, from the instruction templates, with both sides of every relational claim in the artifact | runs without consent; is replaced silently by a same-provider review |
| The frontend-design plugin | the aesthetic pass of the audit and round 2 | decides anything alone |
| The operator | every gate; the goal sentence; the name; the licence; deploy | — |
