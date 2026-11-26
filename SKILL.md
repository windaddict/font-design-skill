---
name: font-design
description: Design, build and ship a custom display typeface for a website as a self-hosted variable web font — a parametric face drawn for the brand, chosen through three rounds of concept pages. Use whenever the operator wants to draw, make or build a custom, unique, bespoke, own or brand typeface or font; wants a headline, display, title or hero font drawn for them rather than chosen from a catalogue; wants their own font instead of a Google Font or a stock face; wants a wordmark or logo-derived letterform, a variable font with weight or optical-size axes, or an italic or new weight for such a face; or asks to "make a font like Bract or Driftwood", to tune, extend or re-review such a face, or to run the concept-page spectrum for a new look. The trigger is the intent to draw or build a face, not the words headline, display or hero alone. Not for recommending, picking or pairing an existing font, including a headline, display or hero font (use frontend-design), for body-text faces, or for CSS-only typography fixes.
license: MIT
compatibility: Needs Node.js 20 or newer, Python 3.10 or newer with a venv made from requirements.txt (fonttools, brotli, skia-pathops, pillow, uharfbuzz, unicodedata2), Google Chrome or Chromium for the screenshots, and a POSIX shell with bash. Supported on macOS and Linux; native Windows is not supported, WSL is. Network access is needed for the independent review (Impasse) and the typeface name check.
metadata:
  version: 0.12.0
---

# font-design

**Version 0.12.0** — the single source of truth is the `VERSION` file at the repo root; this line, the
frontmatter and the README badge are checked against it by `tests/test_versions_and_skill.py`. **Say
this version number when you begin**, so the operator knows which copy answered.

This skill makes a typeface the way Bract (hopsafari.com, 2026-11-15) was made: the nine phases
below, run once in full. The generator and many of the rules come from an earlier face, Driftwood
(movingavg.com, 2026-11-14), which was built before the process was written down, by a static union
pipeline into five CFF files; its lessons and the three bugs found in it later shaped the skill, but
it did not pass through these phases. Both are John Knox's designs (`NOTICE.md`). The shape of the
work is: audit the site,
derive guidelines, pick a design across three rounds of concept pages, plan the build and have the
plan reviewed independently, build with self-checks, review the built font on real pages until a round
finds nothing, have the finished change reviewed independently, ship. The skill runs with little
supervision between gates and stops at every gate.

## Contents

1. Before you start
2. The nine phases (each with its gate)
3. Working with little supervision
4. Publication blockers
5. What the tools are and what each proves
6. Reference index

## 1. Before you start

1. **State the version** (above) and **classify the change**. A site-wide display face is a significant
   change: it touches public pages and is hard to reverse once linked and cached. Follow the full
   order: plan → independent review → build → independent review. A parameter tweak inside an already
   reviewed concept is routine: build, test, one design round.
2. **Check the tools and say which are present.** Run the check, do not assume:
   - `node --version` (≥ 20); the skill's own venv at `<skill dir>/.venv`, made with
     `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` in the skill directory
     (fonttools 4.68.x, brotli, skia-pathops, pillow, uharfbuzz, unicodedata2); Chrome (`$CHROME` or the per-OS default
     `scripts/shoot.py` searches); the Impasse skill (`~/.claude/skills/impasse`); the
     `frontend-design` plugin; and the strongest model the Agent tool offers (named "Fable" in this
     repo's records; use whatever is strongest where you are).
   - **Every Python command in this skill runs on that venv's interpreter, and the command spells it
     out.** Write `.venv/bin/python3 scripts/<tool>.py ...`, never a bare `python` or `python3`, which
     on a Homebrew Mac is a different interpreter without fonttools. No command may depend on a
     variable or a directory set in an earlier Bash call: on most hosts one call does not remember
     the last. "Finding the skill folder" below says how to turn the short form into a command that
     runs from any directory.
   - **Run `.venv/bin/python3 scripts/check-env.py` first.** It lists the platform, Python ≥ 3.10, the four
     requirements at their pinned versions, Node ≥ 20, Chrome and bash as found or missing, prints the exact fix command for
     each missing one and exits 1 if any is missing. (Before the venv exists, run the same script with any
     Python 3: it uses only the standard library and prints the venv command.) macOS and Linux are supported; native Windows is
     not (bash scripts, POSIX venv paths); on Windows run the whole skill inside WSL.
   - **Run `bash scripts/smoke.sh` before the first use of the skill on a machine and after every
     update of the skill**, before starting a project: it builds the three fixtures, runs the suite
     and the mutations, runs the FontBakery gate (skipped, and said so, when FontBakery is not
     installed) and builds the concept pages (`--full` adds the browser steps and the environment check).
   - For anything missing read `references/fallbacks.md` **before** going on; never skip a gate
     silently, and never let the builder's own context be the reviewer.
3. **Ask the opening questions**, in one message, and record the answers verbatim in the plan:
   the goal in the operator's words (this sentence is quoted to every reviewer); which site and
   which pages; the body face it must sit beside; brand sources (mark, colours, materials, history);
   weights and whether an italic is wanted; name candidates; the name-table owner and licence (no
   default — ask every time) and the font's embedding permission, `names.fs_type` (no default: 4,
   Preview & Print, is the usual setting for a proprietary face and 0, installable, for an open one;
   2, Restricted, makes some tools refuse the font; browsers ignore the field for web fonts); the size
   budget; whether the concept pages may be published as claude.ai artifacts; consent to send artifacts to Impasse (a third-party provider); who deploys
   and when. Decide where the project files will live (the convention is `tools/<face>/` in the
   site repo), but create nothing yet: each file is created in the phase that produces its inputs —
   `requirements.json` in phase 2, `concepts.js` in phase 3, `font.json` in
   phase 7, once the plan of phase 6 has settled the masters and axes. **During a project nothing
   is written into the installed skill folder**: scratch files (the plan's export, the charset
   pre-check, measurements) go under the project's `tools/<face>/work/`, which the site's
   `.gitignore` names.

### Finding the skill folder

Every `scripts/`, `references/` and `templates/` path in this file is relative to the folder that
holds this `SKILL.md`, the skill folder. Find its absolute path once per Bash call, by the host:

- **Claude Code:** `${CLAUDE_SKILL_DIR}`, which Claude Code provides for the skill that is running.
  Where it is empty, the install folder `~/.claude/skills/font-design`.
- **Codex:** the absolute path Codex shows in its list of available skills. Use that path, not a
  guessed install folder.
- **Any other host:** the absolute path of the directory holding the `SKILL.md` that was loaded.
  Read it from where the host loaded the file; do not choose among install folders by which exists.

Every command in this file is written in the short form typed from the skill folder,
`.venv/bin/python3 scripts/<tool>.py ...`. To run one from another directory, put the skill folder's
absolute path in front of both `.venv/bin/python3` and `scripts/`, or start the Bash call with
`cd "<skill folder>" &&`; give the project's own files (`font.json`, the site root) as absolute
paths. A site carries no copy of the scripts: a command for a face in a site is typed from the site root as
`<skill folder>/.venv/bin/python3 <skill folder>/scripts/<tool>.py ... --font tools/<face>/font.json`; below, `<skill>`
stands for the skill folder. The contract is `references/face-folder.md`.

## 2. The nine phases

Each phase names its reference file, what it produces and the gate at which the operator decides.
Do not pass a gate on your own.

### Phase 1 — Audit the site first (`references/site-audit.md`)

A font drawn for pages that are about to change is drawn for the wrong pages. Shoot the built site
with `.venv/bin/python3 scripts/shoot.py OUT --serve <static dir> --pages index.html <page>.html --widths 500 1280 1600 --scales 1 2`.
Chrome headless lays out at 500 px minimum, so for the 360 px reading shoot `scripts/narrow.html`,
which `shoot.py` serves at `__fd/` and which reports the inner page's `scrollWidth` against its
`clientWidth` inside an iframe:
`.venv/bin/python3 scripts/shoot.py OUT --serve <static dir> --pages __fd/narrow.html --widths 500 --scales 1 --dump-dom --no-sentinel --query url=/<page>.html --query width=360`.
Read the dumped `.dom.html`: the page passes only when `<html>` carries `data-fd-overflow="false"`
**and** `data-fd-narrow-stage="fonts"` (the reading taken after the web fonts settled; a `"load"`
stage reading was taken before them and does not count). Run the aesthetic pass with the
`frontend-design` plugin when installed; otherwise use the calibration list in `site-audit.md`. List
the "AI tells" (labels that repeat the heading under them, boxed cards that lift on hover, rules as
decoration, two navs or two date formats, repeated or riddling copy, chrome louder than content),
say for each what it changes for the font, and propose which to fix before the font is drawn. Record
the audit with `templates/reviewer-brief-audit.md`. Phase 1 audits and proposes; nothing is fixed
before the gate.

**Gate:** the operator selects which items are fixed before the font and which wait. Then implement
the selected fixes on a branch, each guarded by a test watched to fail, and **commit them as their own
commit** before phase 2 (Bract: hop-safari `2daac34`, before the font's `90a085c`): they are site
design changes the operator judged at this gate, and the concepts are judged on those pages. The
font change itself starts after them and stays uncommitted until phase 9; "commit nothing" in phase
7 means the font change.

### Phase 2 — Guidelines from the site (`references/guidelines.md`)

**Find every element the display face sets before mining.** Give both tools `--family <the display
family in use today>` (`mine-sizes.py <css> --family 'Bodoni Moda'`; `mine-charset.py --html <built
pages dir> --css <css> --family 'Bodoni Moda'`): each rule whose `font-family` names it first gives its
selectors, `@media` blocks included, and the list is printed. A hand-typed `h1,h2,.plate-title` on the
fixture site missed `.frontis-title`, `.wordmark` and a 15.2 px `.num`, which moved the floor from 44.6
to 49.3 units. The limit: a selector that inherits the face from `body` is not found (a site whose
headings and body share one family), and a family set through the `font:` shorthand or a custom
property is not read; then name the selectors by hand from the templates, and add `--selectors` for
any element the family rule misses. Run
`.venv/bin/python3 scripts/mine-sizes.py <css> --family <today's display family> --root 100 150` for the sizes
the face must survive at a 16 px root and a reader's enlarged root, and the hairline floor (one CSS
px at the smallest size is 1000/size units; a hairline should stay at about 0.75 px, `--floor-px`),
and `.venv/bin/python3 scripts/mine-charset.py --html <built pages dir> --css <css> --family <today's display family>`
for the character set of the text those selectors set in the built pages and its traps (no-break
spaces in titles, apostrophes typed as ASCII `'`, `#`, `+`, `*`, accented letters, and the capitals a
`text-transform` rule makes the browser draw, on the selector, on a descendant or on a class inside
the text, which only `--css` can see). What it does not see, so the set is not exact: text set in
the face by an inline style, by script, or by a selector it cannot read (`references/guidelines.md`
section 6 lists them); name those by hand. `--titles <file>` reads one title per line instead of
built pages, and `--json` on either gives the machine-readable form. Write the guidelines: sizes,
floor, the two axes of contrast with the body face, weights, case, charset, precedent lessons.

Create `requirements.json` now from `templates/requirements.example.json`. It is the reviewed
expectation the tests compare the font against, and it changes only with the operator (finding F002
in `docs/plan.md`). Where each field comes from, and when:

| Field | Source | When |
|---|---|---|
| `required_characters`, `titles` | `mine-charset.py --json`: `required_characters` verbatim; the titles from its longest-title report and the site's real titles | now |
| `cmap` | the template's value: the generator's glyph set plus the builder's quote and space glyphs, which is the same for every project; a glyph added in the face's `skeletons.js` is added here too | now, edited only when a glyph is added |
| `names` | the opening questions (section 1, item 3): owner, licence, vendor | now; if the operator has not answered, the field stays as the template's placeholder and phase 7 cannot start (`font.json` `names` is filled from the same answers) |
| `groups.*.axes`, `masters`, `instances`, `avar`, `interpolated_check` | the phase 6 plan | phase 6, before `font.json` exists |
| `groups.*.hairline_floors` | the first `export.js` run of phase 7 (`minStrokeWidth` per master, rounded down), and each master that serves the smallest display size must measure at or above the target `mine-sizes.py` printed (`1000 × 0.75 / smallest px`); a measured minimum below that target is a design finding (thicken `thin`, or move the smallest elements to the body face, gate decision 3), not a floor to record. Bract's 15.2 px numerals read 0.70 px against the 0.75 target and its record carries that as an open item, not a pass. The template's numbers are the fictional Example face's | phase 7, the first export |
| `groups.*.word_space`, `hand_kerns` | the same first export (its word space per master) and the plan's hand pairs | phase 7 |
| `size_budget_bytes`, `fold_units`, `gasp` | the opening questions (budget) and the template's values | now |
| `names.fs_type`, `tables` (`code_page_range1`, `prep_hex`, `mac_names`) | the opening questions (the embedding permission) and the template's values | now |
| `groups.*.vertical_metrics` (`ascender`, `descender`, `line_gap`) | the first build's `vertical metrics written` self-check line, then reviewed: it is the face's `line-height: normal` where a platform reads hhea or typo (win metrics are not covered) | phase 7, the first build |
| `accepted_qa_findings` (`[{id, reason, codes?}]`; `codes` limits the accepted message codes) | the FontBakery gate's first run, each entry read before it is accepted; `[]` until then | phase 7 |

There is no `sizes` key: the sizes live in the guidelines and in `font.json` `review.sizes`.

**Gate:** guidelines written and shown, and three decisions asked explicitly, one question each,
and recorded in the guidelines and `requirements.json` before any concept is drawn:

1. **Each character the generator cannot draw**: fix the content or carry the glyph. Check the
   inventory right then, before asking, from the skill directory:
   `node scripts/export.js --font templates/font.example.json --group roman --requirements <site>/requirements.json <site>/tools/<face>/work/charset-check.json`
   — the template font stands in for the project's `font.json`, which does not exist yet; the
   exporter names every required character without a skeleton and exits non-zero. A character it
   accepts needs no question; a character it refuses is a content fix or a new skeleton
   (`references/generator.md`). **A glyph to carry is drawn before round 1**, because the concept
   pages render the site's real titles and a character no skeleton draws is a gap in every round: it
   goes into the face's skeleton override, `tools/<face>/skeletons.js` (`references/generator.md`,
   "Per-face skeletons"), a project file beside where `font.json` will be, which phase 7 names in
   `font.json` as `"skeletons": "skeletons.js"`. No copy of `scripts/` is patched. The installed skill
   is never edited during a project. A glyph that belongs to everyone (a punctuation mark, a currency
   sign) is a separate change to the skill's own repository, made only on the operator's word, with
   its own tests and review, and reaches this project through the next skill update. Then re-run the
   pre-check with the override applied until it exits 0: copy `templates/font.example.json` to
   `tools/<face>/charset-font.json`, set its `concepts` to the absolute path of the skill's
   `templates/concepts.example.js` and add `"skeletons": "skeletons.js"`, and pass that file as
   `--font`. Build every concept page with `--skeletons tools/<face>/skeletons.js`.
2. **The `opsz` axis ends**, from the smallest and largest display sizes `mine-sizes.py` reports
   (Bract: 40–80 for a 15.2–80 px site, text cut below 40). The neutral example's 24–72 is the
   fixture's range and is wrong for an 80 px site; say which numbers the site's own table gives.
   The ends are CSS px only if the browser maps px to `opsz` one to one, so measure that first, on
   the skill's own fixture font before any project font exists:
   `.venv/bin/python3 scripts/opsz.py <site>/tools/<face>/work/opsz-check --serve examples/neutral/out --font-url /Sampler-VF.woff2 --family Sampler --axis 24 72 --px 24 48 72`
   (`smoke.sh` has built it; Chrome on this machine reads px as `opsz` one to one; Safari and Firefox
   are unmeasured). Phase 8 repeats the measurement on the built font to confirm the ends, it does not
   choose them.
3. **The smallest elements**: do they stay in the display face, or move to the body face? The
   answer sets the hairline floor.

### Phase 3 — Round 1, the spectrum (`references/concept-pipeline.md`)

Create `concepts.js` (`templates/concepts.example.js`) with about six concepts, each a parameter set
named for something the reader can see on the site, ordered closest-to-current first → most organic.
Write the round's content JSON from the `mine-*.py` outputs and the site's real titles, colours and
sizes; start from `scripts/concepts/content.minimal.json` (only the fields round 1 requires, with
sample values) and read `scripts/concepts/content.example.json` for every optional field;
`build-page.js` validates the file and names each missing or malformed field. The neutral example's content (`examples/neutral/content.json`) is sample text
for a fictional site, including its audit section; nothing in it describes a real page. Build the page:
`node scripts/concepts/build-page.js --template round1 --concepts concepts.js --content content.json out/round1.html`,
shoot it at 500 and 1280, and look at the PNGs yourself. Then ask the strongest model, in a fresh
subagent with `templates/reviewer-brief-concepts.md`, to review the page and recommend a shortlist,
saying how to pick. Check two of its claims against the page before repeating them.

**Gate:** the operator picks the shortlist (or asks for a round 1b).

### Phase 4 — Round 2, mock-ups

Set the shortlist into mock-ups (`--template round2`), with the sticky face picker and the comparison
face. The mocks are a fixed generic layout (a home page, an article, a contents page, the shape of
hop-safari's redesign); their headline sizes come from `content.slot_sizes`, filled from
`mine-sizes.py`, which rounds 2 and 3 require (the build refuses content without it), and every slot
left out keeps the template's hop-safari default and is named on stderr by `build-page.js`. The
operator judges the face on the site's real pages in phase 8, not here. Reviewer and `frontend-design` judge; the
reviewer revises the leading concept (Bract's Medium for small titles and `serifGrow` came from here).

**Gate:** the operator names the finalists.

### Phase 5 — Round 3, head-to-head

Finalists on the mock pages (`--template round3`), the reviewer's verdict and ranking published in
the page's verdict box (content `verdict`), targeted fixes sketched before committing to a build
(an optical-size cut, a second weight). **Check the candidate name against existing typefaces before
any file exists** (Burin was taken; the face became Bract): the host does it, before this gate, with
a web search (`WebSearch` when the tool is available, else the operator's browser) for
`"<name>" font` and `"<name>" typeface` and a look at Google Fonts, MyFonts and the foundries
`references/concept-pipeline.md` section 7 names; every hit and the searches run go into the plan,
and the operator chooses the name knowing them. No hit is not proof the name is free; say so.

**Gate:** the operator chooses the design and the name.

### Phase 6 — Plan the build (`references/variable-font-build.md`, `templates/plan.md`)

The strongest model writes the plan: masters, axes, floors, cmap decisions, tests with their
mutations, docs to update. Mark every claim (read / measured / inferred). The plan's measured
figures (incompatible glyphs, points per master) come from an export of the planned masters run
now, from a scratch `font.json` that lives in the project, not in the installed skill (copy
`templates/font.example.json` to `tools/<face>/work/plan-check.json`, point its `concepts` at
`../concepts.js`, write the planned masters and axes, and run
`node scripts/export.js --font <site>/tools/<face>/work/plan-check.json --group roman <site>/tools/<face>/work/plan-roman.json`);
`work/` is scratch and is not committed. The project's `font.json` is still created in phase 7 from
the reviewed plan. **Write your own view of
the plan first**, then run Impasse on it with `templates/impasse-plan-instruction.txt`, with the
generator, the builder and the site's stylesheet in the artifact (a relational claim needs both
sides). Verify every finding against the code before accepting it; a rejection needs contradicting
evidence. Amend the plan and fill its "Independent review and what it changed" section. Deadlocks go
to the operator.

**Gate:** the operator answers the plan's questions.

### Phase 7 — Build (`references/variable-font-build.md`, `references/testing.md`)

Every command in steps 1 to 7 is typed from the site root.

1. Create the face folder, `tools/<face>/` in the site (`references/face-folder.md`); the scripts stay in the
   skill and nothing is copied. Run the suite and the mutation step **after `smoke.sh` has finished**, never
   while it runs: the mutation step edits `gen.js`, `export.js` and `build.py` in place and restores them by
   digest. The face's own letters live in `tools/<face>/skeletons.js` (the phase 2
   gate, item 1). Create `font.json` there from `templates/font.example.json` with the plan's masters, axes
   and floors, and, when the face has an override, `"skeletons": "skeletons.js"`; the build log's
   `skeletons skeletons.js: overrides ...` line names every key it changed. **Path rule:** paths written inside `font.json` (`out_dir`, `concepts`, a group's
   `file`) resolve relative to the `font.json`'s own directory, and the manifest lands at
   `<out_dir>/manifest.json` unless the `manifest` key moves it (relative to `out_dir`); every path
   given on the command line (`--static`, `--out-dir`, `--masters`, `--requirements`, `export.js`'s
   output, `pytest --static-dir`, `mutate.py --static-dir`) resolves relative to the working
   directory, as the shell that typed it expects, so one spelling names one folder in every tool;
   under `--out-dir` the manifest goes into that directory whatever the `manifest` key says. Then the charset pre-check,
   per group (an italic is a second group and a second file):
   `node <skill>/scripts/export.js --font tools/<face>/font.json --group roman --requirements tools/<face>/requirements.json tools/<face>/work/roman-check.json`.
   This explicit export is **only** the `--requirements` pre-check: it names any required character
   without a skeleton and refuses masters whose point structure or branch record differ. `build.py`
   runs the export itself, into a temporary directory, so no masters JSON lands in the committed
   `out_dir`; do not commit `work/roman-check.json` either.
2. `<skill>/.venv/bin/python3 <skill>/scripts/build.py --font tools/<face>/font.json` — read every `SELF-CHECK ok:` line; a refused build
   writes nothing. The build also writes the tables a web font needs and the format expects:
   `OS/2.fsType` from `names.fs_type` (a config without it is refused), hhea and OS/2 typo metrics equal
   with a line gap of 0 and `USE_TYPO_METRICS` set, STAT axis values for every named instance, the
   smart-dropout `prep` program beside `gasp`, no Macintosh name records and the Latin 1 code-page bit.
   The `vertical metrics written` line prints the metrics and the `line-height: normal` they give;
   **that can change the line height of any element on a live site that uses `line-height: normal`, so
   review the numbers and pin them in `requirements.json` `vertical_metrics`** (`references/variable-font-build.md`
   section 6). `--static tools/<face>/out/static` (from the site root) adds static instances for
   renderers without variable-font support.
3. Get the woff2 to the served path. Either point `out_dir` at the site's font folder so every
   build writes the roman and the italic woff2 straight to where the stylesheet names them (Bract
   served its woff2 from `static-pages/fonts/bract/` and kept `manifest.json` beside the tool; here
   the `manifest` key does that), or keep `out_dir: out` and copy each group's woff2 into the font
   folder after every build. The
   file the stylesheet names must be the file the manifest hashes. Then wire the CSS and templates
   (`@font-face` with the weight range, `font-optical-sizing: auto`, preload with `crossorigin`
   before the stylesheet, `font-weight: 500` where the guidelines say, no `letter-spacing` on a cut
   that carries its own `track`).
4. The font suite stays in the skill and runs from it against the face folder, typed from the site root:
   `<skill>/.venv/bin/python3 -m pytest <skill>/scripts/tests/test_font.py -q --font tools/<face>/font.json --requirements tools/<face>/requirements.json --static-dir tools/<face>/out/static`
   (`--static-dir none` when no statics ship; a site that keeps the tests elsewhere passes
   `--scripts=<skill>/scripts`, with the equals sign). Fill `scripts/tests/test_site_wiring.py.tmpl`
   into the site's own tests directory; its header says how it reads the stylesheet. Two of its guards
   are optional and skip, with the reason printed, while their slot is empty: a fallback face
   with the vertical metrics held to the font (`fallback_family`; the guard does not hold the horizontal match, `size-adjust`
   against the real fallback widths, which only the script's arithmetic and a screenshot of the swap cover; `.venv/bin/python3 scripts/fallback-metrics.py --font font.json --location opsz=<the
   headline size>` prints the `size-adjust` and the three overrides from the built font and each
   fallback font file) and `text-wrap: balance` declared on the listed display selectors (`balance_selectors`; the cascade
   is not computed, so a later rule on another selector that overrides it is not seen).
5. **Watch every guard fail**: `<skill>/.venv/bin/python3 <skill>/scripts/tests/mutate.py --font tools/<face>/font.json --requirements tools/<face>/requirements.json --static-dir none`
   runs every mutation (`--only NAME` for a subset, `--list` to see them; `--static-dir DIR` when
   statics were built, `--static-dir none` when none ship, which skips the static mutations and
   prints `SKIPPED` with the reason; with neither, a missing `<out_dir>/static` refuses the run). Every
   expectation it checks is derived from the project's `requirements.json`, and a mutation the project
   cannot exercise (no digit in its titles, no `opsz` axis) is `SKIPPED`, never silently green. Choose
   the weakest mutation that breaks the property, not the one your fix already handles. A mutation
   that stays GREEN is a finding about the test: record it and fix the test.
6. `<skill>/.venv/bin/python3 <skill>/scripts/build.py --font tools/<face>/font.json --check` must report byte-identical.
7. **The FontBakery gate:** `<skill>/.venv/bin/python3 <skill>/scripts/fontbakery-gate.py --font tools/<face>/font.json --requirements tools/<face>/requirements.json`
   builds each group's variable TTF into a temporary folder, runs `fontbakery check-universal` on it
   and exits 1 on any FAIL, ERROR or FATAL whose check id is not in `requirements.json`
   `accepted_qa_findings` (each `{id, reason}`, a required key, `[]` when nothing is accepted). The
   first run on a new face lists what FontBakery finds that the suite never pinned; read each finding,
   fix it, or accept it with its reason. Exit 3 means FontBakery is not installed
   (`requirements-dev.txt`): the gate was SKIPPED, NOT PASSED. A deliberate non-zero `fs_type` is
   accepted under a vendor profile's check (`--profile googlefonts`, id `googlefonts/fstype`).

Commit nothing yet. The commit comes in phase 9, after the independent review of the whole change
and its fixes, so that the review covers everything that ships.

**Gate:** suite green, every mutation RED, `--check` identical, the FontBakery gate passed (or waived in writing by the operator).

### Phase 8 — Design-review loop, at most six rounds (`references/review-loop.md`)

Each round: build → `.venv/bin/python3 scripts/specimen.py --font font.json --requirements requirements.json --font-url /fonts/<file> <site root>/review/specimen.html`
(`--italic-url` for the italic group) → `.venv/bin/python3 scripts/shoot.py OUT --serve <site root> --pages <page>.html review/specimen.html --widths 500 667 889 1280 1600 --scales 1 2 --family <Family> --font-url /fonts/<file>`,
then the same with `--root 150` for a reader's enlarged default (a shot without `--family` and
`--font-url` is a picture, not evidence) → a **fresh** reviewer (new subagent context,
`templates/reviewer-brief-design-round.md`, the operator's goal sentence verbatim, the crops) →
findings ranked by visibility at 1× on a real page → changes → **you spot-check two crops yourself and
run one mutation of your own** → next round. From round 2, copy `out/` to `work/round-N/` before each
build and run `scripts/diff.py` against it; the reviewer brief names its `diff.md`. **Serve the built site root** (Bract: `static-pages/`),
and write the specimen under that same root, so the root-relative `/fonts/<file>` the stylesheet and
the specimen use resolves to the same woff2 the pages load; keep the specimen out of the commit.
The specimen's FIRST section holds the proof rows the reviewer reads in every round (a default review shot is 2400 CSS px tall and the rest of the specimen is longer; the page records `data-fd-proof-bottom` and `smoke.sh` step 9 checks it is within the capture): spacing control
strings (each lowercase letter between `nn` and `oo`, each capital between `HH` and `OO`, each figure
between `00` and `11`, each punctuation mark after `r`, `f` and `y`) and a legibility row,
`Il1 O0 B8 rn m cl d`, at the smallest review size. They hold only characters the font maps. Uneven
rhythm in the control strings is reported before any kern finding.
`.venv/bin/python3 scripts/opsz.py OUT --serve <site root> --font-url /fonts/<file> --family <Family> --axis <min> <max> --px <the site's sizes>`
confirms, on the built font, which `opsz` the browser applies at each size: the ends were chosen at
the phase 2 gate from the same measurement on the fixture font, and a reading here that disagrees
with them is a finding for the plan, never an assumption to keep.

**Required in every round, on every page: the 360 px reading with the wired font.** Phase 1 measured
the pages in the old face; a title that fit in Georgia overflows in a wider face (the fixture site's
NBSP-joined frontispiece title at 48 px reads 384 px against 360 in Sampler, `smoke.sh` step 11
proves it). Run, per page,
`.venv/bin/python3 scripts/shoot.py OUT --serve <site root> --pages __fd/narrow.html --widths 500 --scales 1 --dump-dom --no-sentinel --query url=/<page>.html --query width=360 --query family=<Family>`
and read the dumped `.dom.html`: every page must carry `data-fd-overflow="false"` at
`data-fd-narrow-stage="fonts"`, which `narrow.html` writes only when the inner page was served 200
(`data-fd-narrow-inner-http`), none of its faces failed (`data-fd-narrow-fonts-failed="0"`) and a
face of the family loaded (`data-fd-narrow-family="loaded"`); otherwise it writes
`data-fd-overflow="error"` with the reason, since a 404 page and a page without its font both lay
out narrow. An overflow is a finding ranked above anything visible at 1× (it is
visible on every phone), fixed in the CSS or the content, not left as an open item; a page that
overflows at the last round is a publication blocker (section 4, last item).

**Stop** when a round reports nothing visible at 1× on a real page and the suite is green; or at round
six, when what remains is visible only at 2× or in the specimen, recorded as open items. **At round
six with a defect still visible at 1× on a real page, stop before phase 9 and ask the operator**:
revise the design (back to the concept or the plan) or leave the face unshipped. Such a defect is a
publication blocker (section 4); the round limit does not turn it into an open item. A screenshot
proves what one renderer on one machine drew; say so in the record.

**The platform run, once per face** (`references/review-loop.md` sections 2, 7 and 9): after the round that would end the loop (or round six), or when the operator asks,
ask the operator to run the site's `platform-shots.yml`, a short caller of the skill's reusable workflow pinned to a skill commit (`templates/platform-shots.yml`; the site keeps no copy of the scripts) (`gh workflow run platform-shots.yml`, then `gh run download -n platform-shots-compare`; the first dispatch needs the file on the default branch). It shoots the specimen and the pages in headless Chrome and Playwright's Firefox on GitHub-hosted Windows Server, macOS and Ubuntu runners, and `scripts/compare-shots.py` stacks each row from every leg.
Read `compare.md`'s "Refused" and "Mismatched" lists first, then the smallest sizes. A stroke that breaks up at 1× on a real page in any leg is a 1× finding; one that reads lighter but whole goes in the record. Re-run it when `thin`, the floors or the smallest sizes change. It is not a publication blocker.

### Phase 9 — Ship

Nothing of the font change has been committed yet. In this order:

1. **Write the docs first**: the record from `templates/font-record.md`, the tool README and the
   site's CLAUDE.md section, so the review covers them.
2. **Stage the whole change and review the staged diff.** New files are most of a font change
   (`tools/<face>/`, the woff2, the manifest, the tests) and an unstaged `git diff` leaves untracked
   files out, so run `git add -A -- <every path of the change>` and give Impasse
   `git diff --cached` (docs and tests included, the regenerated pages excluded except samples) with
   `templates/impasse-diff-instruction.txt`. Verify each finding; fix; `git add` the fixes; one
   re-review of `git diff --cached` again; fix its findings without a third review. After any
   material fix, rerun the affected tests and smoke steps (finding F015) and update the record's
   "what changed after the review" line.
3. **Then commit everything together** in one commit: the woff2, the manifest, the sources
   (`font.json`, `requirements.json`, `concepts.js`, `skeletons.js` when there is one), the stylesheet and
   templates, the tests and the docs.

Deploy only on the operator's word, then check live: the font served 200, the preload present, one
headless shot of the live page with `--family` and `--font-url`.

### Later: a new skill version under a shipped face

`manifest.json` records `skill_version`. When `VERSION` of the installed skill differs, run, from the site root,
`<skill>/.venv/bin/python3 <skill>/scripts/update-check.py work/update --font tools/<face>/font.json` and read `update.md`.
It changes nothing in the face folder. The operator approves by running the `build.py` line it prints; commit the woff2 and manifest.

## 3. Working with little supervision

Decide alone: parameter changes inside the chosen concept; skeleton fixes a review round asked for;
which mutation to run; test and doc wording; the order of work inside a phase.

Ask: the shortlist, the finalists, the name, the licence and owner strings, anything that deletes or
overwrites authored content, every deploy, every Impasse deadlock, any gate.

Report: findings ranked by visibility at 1× on a real page, each naming its crop; numbers with the
command that produced them; a subagent's or reviewer's claim as a lead until you opened the source
yourself; every departure from the expected path logged in the record, never swallowed. Say what was
not verified in the same sentence as the claim it limits: Safari, phones and real displays always;
Windows and Firefox unless the platform run was made, and then only as a GitHub-hosted runner's headless Chrome and Playwright's Firefox.

Cost: six rounds with a fresh strong-model reviewer each is the expensive part. Say so at the start
and let the operator cap the rounds.

## 4. Publication blockers

Do not ship while any of these holds (finding F015):

- a self-check or a test fails, or a mutation stays green and is unexplained;
- browser evidence is missing for the shipped build: no shot of a real page at 1× taken with
  `--family` and `--font-url`, or a shot that failed the sentinel (page or font not served 200, face
  not used). A shot without `--family` and `--font-url` is a picture, not evidence. Missing browser
  evidence blocks publication unless the operator waives it in writing; the waiver is recorded in the
  font record and stated in the shipped docs, and nothing else lifts this item.
  `references/fallbacks.md` ("No Chrome") and `references/process.md` section 11 say the same;
- a required character has no glyph (the exporter's `--requirements` check);
- the FontBakery gate fails, or was skipped (not installed) and the operator has not waived it in writing;
- the licence or the name-table owner is unconfirmed, or the rights to the design sources are;
- a defect is visible at 1× on a real page;
- a page overflows at 360 px with the wired font (`narrow.html`, the `fonts`-stage reading), or no
  such reading exists for the shipped build.

## 5. What the tools are and what each proves

| Tool | Does | Exact guarantee |
|---|---|---|
| `scripts/gen.js` | Centre-line skeletons stroked by a broad-nib model into overlapping polygons; `params(concept, mult, italic)`; refuses dead knobs (`flareAmt` with `tear`); `applySkeletons(fn, name)` applies a face's override once, rebuilds the accented letters from overridden bases, refuses a malformed one | Same point count per segment in every master (pinned sampling); branch outcomes recorded; folds pinned. An override is validated as data (paths, end letters, dots, rings, mappable keys), not as a design |
| `scripts/export.js` | Draws every master of a group, checks compatibility, decimates with shared indices, measures hairlines and folds, emits one kern list; applies `font.json`'s `skeletons` file first (one stderr line names what it changed) and records its name and sha256 | Compatible = same contour count, point count per contour and branch record. Not a proof that corresponding points are the same feature |
| `scripts/check-env.py` | The platform (native Windows is MISSING; WSL passes), Python ≥ 3.10, the four requirements at the versions `requirements.txt` names (`==4.68.*` handled; an older install is MISSING with the pip command), Node ≥ 20, Chrome (through `shoot.py`'s own `find_chrome()`), bash: found or missing, with the fix command; optional FontBakery and Playwright | Exit 1 when a required piece is missing. Reports what this process sees (this interpreter's imports, `node` and `bash` on PATH, the Chrome file); the network is not tested |
| `scripts/build.py` | Masters → one variable TTF/WOFF2 per group + `manifest.json`; needs `requirements.json` beside `font.json` (or `--requirements`; `--no-requirements` is recorded in the manifest); `--check`, `--static`, `--masters` (re-checked: an export drawn with another skeleton override, or none, refused; folds and the minimum stroke width recomputed from the polygons, each master's `W`, `thin` and `track` read back from `gen.js` through node and held against the JSON, one record per polygon in every list); writes `OS/2.fsType` from `names.fs_type` (required, no default), hhea = typo metrics with a line gap of 0, win = every glyph's extent, `USE_TYPO_METRICS`, STAT axis values for every named instance, a smart-dropout `prep` beside `gasp`, no Macintosh names, the Latin 1 code-page bit; refuses an interpreter older than 3.10 or without fontTools, naming the venv command; one `SELF-CHECK ok:` line per check | Every self-check fails the build; rasters are FreeType via Pillow on this machine, not CoreText or DirectWrite; the advances, kern values, word space, title widths and branch records are still the JSON's, held by the font suite against a fresh export; the table properties above are held by the suite against `requirements.json`, not by this file |
| `scripts/tests/test_font.py` | The site's font guards, parametrised on `requirements.json` | Reviewed values (cmap, axes, instances, `avar`, floors, hand pairs, word space, names, `fs_type`, line metrics, STAT values, the `prep` bytes, the code-page bit, Macintosh names, budget, fold units) come from `requirements.json`; outlines, every kern pair (no GPOS pair the exporter did not emit, and at least one live automatic pair per master) and the title widths are consistency checks against a fresh export, which share any defect in `gen.js` (`references/testing.md` section 2) |
| `scripts/tests/mutate.py` | Applies each named mutation, rebuilds when it is a build input, runs the named tests, restores by digest; `--static-dir none` skips the static mutations; every expected text is derived from the project's `requirements.json` | RED only when the mutation applied, the rebuild exited 0 and changed an artefact (or refused with the declared text) and every named test FAILED on its own expected assertion text (read from that test's failure section, not from the run as a whole); a mutation the project cannot exercise is SKIPPED with the reason; anything else is UNPROVEN or GREEN, both findings about the test, and the run exits non-zero |
| `scripts/fontbakery-gate.py` | Builds each group's variable TTF to a temp folder, runs `fontbakery check-universal` (or `--profile`), fails on any FAIL/ERROR/FATAL not in `requirements.json` `accepted_qa_findings` | The community's format checks at the pinned FontBakery version found nothing outside the accepted list in the TTF (the woff2's uncompressed twin); not proof the font is good, and `--skip-network` leaves the network checks out; exit 3 = not installed, SKIPPED, NOT PASSED |
| `scripts/fallback-metrics.py` | The CSS `size-adjust` and three overrides for a `local()` fallback face (Georgia, Times New Roman, Arial, or any `--fallback NAME=PATH`), from the built font and the fallback's file | The arithmetic on advances and hhea metrics at one `--location`, kerning excluded and the visitor's copy of the fallback not seen: a starting point to confirm with a screenshot of the swap |
| `scripts/shoot.py` | Self-terminating server + headless Chrome (found through `$CHROME`, the macOS app, the Windows install paths, then PATH names); shot tokens; DOM sentinel + beacon (recorded only from the Chrome that carries the shot's cookie); `--family` and `--font-url` (repeatable) name what each shot must prove; `--scales` takes fractions (1.25); `--browser firefox` shoots through `scripts/shoot_playwright.py`; `--rows` (which needs `--family` and `--font-url`) writes `<png>.rows.json` (each marked row's viewport box, text and computed style), and `--require-captured` fails a shot with a row below the capture; `--meta FILE` records platform, browser, Windows font smoothing, verified shots and failures | A PNG is evidence only if the page was served 200 for that shot, every named font path it requested was served 200 and at least one was requested, the named face was used (a loaded `FontFace` of the family and of the element's style that the browser's weight matching selects without synthesising bold or drawing a lighter face, read from load state and computed style, not from the painted pixels; an italic needs a face declared italic, not an oblique stand-in; on an element `checkVisibility()` and the document bounds count as visible), Chrome exited 0 (Firefox: Playwright returned a PNG and raised nothing); a rows file is written only beside a verified PNG; the page under test is trusted to be the operator's own (its script could send the beacon itself); a shot without `--family` and `--font-url` is a picture, not evidence, and so is a shot of an installed family, which has no `FontFace` to prove |
| `scripts/shoot_playwright.py` | The Playwright launcher behind `shoot.py --browser firefox` (Playwright's own Firefox) and `--launcher playwright` (the Chrome `shoot.py` found, driven by Playwright, which lays the page out at exactly the shot's width; Chrome's command line on Windows does not): it opens the shot's tokenised URL at the same viewport and scale; optional (`requirements-platform.txt`, `playwright==1.64.1`); without it `shoot.py` exits 3, SKIPPED, NOT PASSED. WebKit is designed, not built | The proofs are `shoot.py`'s server records, as for Chrome; Playwright's Firefox build, not the Firefox a reader installs |
| `scripts/compare-shots.py` | One PNG per row from several `shoot.py --rows --meta` legs (one OS and one browser each): the row cropped from every leg, zoomed nearest-neighbour, labelled from the meta, stacked; `compare.md` (smallest sizes first), `compare.json` (`.venv/bin/python3 scripts/compare-shots.py OUT LEG_DIR LEG_DIR --min-legs 2`) | Pairs a row only when its key, text and computed style match in every accepted leg; refuses a leg without meta, a PNG without rows, a file of the wrong JSON shape, a scrolled shot, a shot laid out at another width and a PNG whose size is not the shot its rows describe, and compares the rest; exit 1 below `--min-legs`, exit 0 at or above it even when some shots failed (the workflow fails the run on a failed leg separately). It shows, it does not judge; the ink share is a hint, the PNG the evidence; a runner is not a reader's machine (`references/review-loop.md` section 9) |
| `scripts/opsz.py` + `opsz.html` | Which `opsz` the browser applies under `font-optical-sizing: auto` | Chrome headless on this machine; Safari and Firefox unmeasured |
| `scripts/diff.py` | What changed between two builds, by value (tables, outlines, metrics, HarfBuzz kerning of two-character strings) and by render at every review size and named instance: `diff.md`, `diff.json`, a PNG per changed render. `--before`/`--after` hold each group's file under its file name; no `--after` means the shipped files (`.venv/bin/python3 scripts/diff.py OUT --font font.json --before DIR`) | Renders: FreeType through Pillow with the `fpgm` that stops autohinting, on one machine, not a browser. Values: the listed tables and two-character shaping, not contextual features or longer strings |
| `scripts/fetch-version.py` | The skill's code at a released version in a folder: `git archive` of tag `v<version>`, else the GitHub tag archive; moved into place only after its `VERSION` matches; refuses 0.6.0 | The tree at the tag as the remote serves it, not a signature; version 0.6.0 names two sources and is refused |
| `scripts/update-check.py` | Whether the installed skill changes a shipped face: drift check, rebuild into a temporary folder, `update.md` and `update.json` (exit 0 same, 3 differs, 1 error) | The drift check proves the shipped files match `manifest.json`, not that the recorded version built them; attribution to the update is reported as unverified; it never writes into the face folder |
| `scripts/specimen.py` | The review specimen from `font.json`: real titles, sizes, surfaces, comparison faces, spacing control strings and the legibility row (only characters the font maps); italic rows marked `data-fd-probe="italic"`; refuses a page that shows a character the built font's cmap lacks (`--allow-missing` writes it with a footer note) | What it shows is what one renderer drew; the charset check covers the family's own rows, only when the font file is found |
| `scripts/narrow.html` | 360 px overflow check inside an iframe, measured at the inner load event and again once the inner fonts settled, after a HEAD request for the inner page's status, a count of failed faces and (with `?family=`) a loaded face of the family | `scrollWidth` vs `clientWidth` of a page served 200 with every face loaded; only a `data-fd-narrow-stage="fonts"` reading counts, and a 404, a failed face or a missing family reads `error`, never `false` |
| `scripts/mine-sizes.py`, `scripts/mine-charset.py` | Sizes and floor from the CSS; the character set of the text the display selectors set in the built pages, with its traps; `--family` finds every selector whose rule sets the family first; `mine-charset.py --css` adds the characters any `text-transform` rule makes the browser draw inside that text (the selector's own rule, a descendant's or a class's) | Reads `clamp()`, `rem`, `px` rules and the named or found selectors, `@media` included; a family inherited from `body`, a `font:` shorthand or a custom property is not seen; text set by an inline style, by script or by a selector the tool cannot read is not seen, so the set is not exact; without `--css` a `text-transform` is not seen, and a transform rule it cannot read is named in the output |
| `scripts/concepts/build-page.js` + three templates | Rounds 1–3 pages from `concepts.js` + a content JSON; `?face=` switch; `data-fd-*` self-test; `--skeletons` splices the face's override after `gen.js` (applied at build time first, `data-fd-skeletons` set in the browser); the round-2/3 mock slot sizes from `content.slot_sizes`, required for those rounds, every slot left at the default named on stderr | Content is embedded as JSON and rendered with DOM calls; images only from `img/` beside the page; the mock pages' structure (home, article, contents) is fixed and only their sizes follow the content |
| `scripts/bounds.js` | Vertical extents of glyphs from the generator | Alignment check only |

## 6. Reference index

- `references/face-folder.md` — the face-folder contract: what a site keeps, the working directory of every command, the version record, `update-check.py`, `fetch-version.py`, the migration note.
- `references/process.md` — the nine phases in detail: inputs, outputs, gates, who does what, stop rules.
- `references/site-audit.md` — the AI-tells list, the calibration traits, the guard pattern, the 360 px method.
- `references/guidelines.md` — sizes, the hairline floor, contrast axes, weights, charset traps, precedent lessons.
- `references/generator.md` — skeleton grammar, every parameter with range and interactions, the italic, adding a glyph.
- `references/variable-font-build.md` — masters, avar, opsz, decimation, the self-check table with exact guarantees, `font.json` key by key, `--static`.
- `references/traps.md` — 38 traps: symptom, cause, detection, the guard that ships, where it bit.
- `references/review-loop.md` — the round protocol, the checklist, the fresh-reviewer rule, the stop rule.
- `references/genres.md` — which typeface genres the generator reaches (a candidate recipe each, in `templates/concepts.genres.js`), which it cannot, and the limit of each; read it at phase 3.
- `references/concept-pipeline.md` — rounds 1–3, the content JSON, artifact constraints, the name check.
- `references/testing.md` — every test with its mutation; choosing the weakest mutation; the survivors and why.
- `references/fallbacks.md` — when the strongest model, Impasse, Codex, frontend-design, Chrome, Playwright or artifacts are absent.
- `references/examples/bract.md` — the full-process worked example; `references/examples/driftwood.md` — the earlier precedent (static union pipeline, five CFF files) whose lessons and bugs shaped the skill.
- `templates/` — `font.example.json`, `requirements.example.json`, `concepts.example.js`, `font-record.md`, `plan.md`, the three reviewer briefs, the two Impasse instructions, the two schemas, `platform-shots.yml` (the caller a site copies; the legs live in the skill's `.github/workflows/platform-shots-reusable.yml`).
- `examples/neutral/` — the smoke fixture ("Sampler": roman with two axes, italic with one). It is a finished sample with two concepts for speed, its floors and `opsz` ends are the fixture's rather than measured from a site, and its content JSON is sample text, audit section included; a real run writes about six round-1 concepts and sets its floors from its own measurements. `examples/bract/`, `examples/driftwood/` — the two faces' parameters and configuration under neutral name tables ("Bract Example", "Driftwood Example"), MIT like the rest of the repo, no font files; the Driftwood example also carries a `requirements.json`, so the font suite runs on it as a second face (`smoke.sh` step 4a).
- `docs/plan.md` — the plan this repo was built from, with its independent review (F001–F015).
- `scripts/smoke.sh` — the pre-publish run: build the three fixtures, run the suites and mutations, build and shoot the concept pages.
