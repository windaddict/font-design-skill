# Changelog

All notable changes to this skill. The format follows Keep a Changelog; the version is the `VERSION`
file, repeated in `SKILL.md` and the README badge and checked by the tests.

## [0.1.0] — 2026-11-16

The first version, written for publication. The operator confirmed the rights to relicense both
source generators under MIT on 2026-11-16 (`NOTICE.md`). Everything here was extracted from
two faces John Knox made for the author's own sites:
Driftwood (movingavg.com, static CFF family with an italic, 2026-11-14) and Bract (hopsafari.com, one
variable font with weight and optical-size axes, 2026-11-15). Provenance and licence boundaries are in
`NOTICE.md`; the plan this repo was built from, with its independent review, is `docs/plan.md`.

### Added

- `SKILL.md`: the nine-phase process (audit → guidelines → three concept rounds → plan + independent
  review → build → design-review loop → independent review → ship), the gates, the little-supervision
  rules and the publication blockers.
- `scripts/gen.js`: Bract's generator generalised. Concepts live in a project's `concepts.js`; the
  italic is restored from Driftwood as an opt-in (`params(concept, mult, italic)`): structural italic
  skeletons, shear, narrower set, shorter serifs, sidebearing band, the J rule. New `dropAmt`
  parameter sizes the whole teardrop; `params()` throws on `flareAmt` beside `tear: true`.
- `scripts/export.js`: config-driven (`--font font.json --group`), fails early on a required character
  with no skeleton (`--requirements`), one JSON per group matching `templates/export.schema.json`.
- `scripts/build.py`: one variable pipeline for any number of axes (one-axis builds included) and any
  number of groups (roman and italic as separate files), every Bract self-check, `--check`,
  `--masters` re-checked, `--static DIR` instances with their own checks.
- `scripts/tests/`: the font suite template parametrised on a separate `requirements.json`, the
  site-wiring template, the mutation harness.
- Review tools: `shoot.py` (shot tokens, DOM sentinel and beacon so a 404 page or a fallback font
  cannot pass as evidence), `opsz.py`, `specimen.py`, `narrow.html`, `mine-charset.py`,
  `mine-sizes.py`, `bounds.js`.
- Concept pipeline: `render.js` and the three round templates driven by a content JSON and rendered
  with DOM calls only; `build-page.js`; `?face=` switch and `data-fd-*` self-test for headless runs.
- `references/` (eleven files and two worked examples), `templates/` (configuration, record, plan,
  reviewer briefs, Impasse instructions, two JSON schemas), `examples/` (neutral smoke fixture,
  Bract and Driftwood parameters).
- The repo's own tests: hygiene, versions, schemas, concepts, templates, smoke build of the fixtures.

### Inherited fixes, now in the shipped code or tests

- Driftwood issues: #22 (fold lumps in the Bold: fold pin + fold guard on raw and decimated edges),
  #23 (`quotedblleft` advance), #24 (`flareAmt` dead with teardrops: `dropAmt` + a thrown error).
- Bract's plan review F001–F013, diff review R1–R8 and re-review 1–5: branch-outcome recording with
  partner identity, opsz measurement, the full master rectangle, shared-index decimation per edge run
  with winding and raster checks, `track` kept in advances, quote glyphs re-derived in the test,
  interior hairline measurement, kerning at every reviewed location, measured vertical metrics,
  instancing at every master, `SOURCE_DATE_EPOCH` assigned not defaulted, Chrome exit code and served
  status checked, `--masters` re-checked, the fold detector tested on hand-built edges.
- This repo's plan review F001–F015 (`docs/plan.md` section 13).

### Changed after the final independent review (C1–C13, D2–D13) and a cold dry run (W1–W17), before the first commit

- `shoot.py`: every request path is resolved and must land inside its root, under `/__fd/` and the
  served directory alike (C1); a font 200 counts for a shot only when the request carried that
  shot's cookie token (C4); with `--family` every visible element set in the family is probed for
  a loaded face of its style, an italic element for an italic face, and every character for a
  glyph of its own (C5, W16); the page's own `data-fd-rendered` / `data-fd-error` / `data-fd-font`
  self-test fails the shot (W2). `narrow.html` measures again once the inner fonts settle and
  `smoke.sh` step 10 passes only on that reading (C11).
- `specimen.py`: a font URL is allow-listed, never escaped (C2); the italic rows carry
  `data-fd-probe="italic"`; labels on a dark surface take its foreground; a character the built
  font's cmap lacks refuses the page unless `--allow-missing` (W16). The C2 test's `--font-url` cases
  first ran against the hostile comparison face, so a mutation that opened either branch of the
  allow-list stayed green. They now run against a clean config, and each branch mutation turns them red.
- `gen.js`: the glyph cache is keyed by every parameter at full precision (C3); a sparse glyph
  (hyphen, period) is capped at −50 in the automatic kern (W17, trap 34).
- `build.py`: `requirements.json` is a build input (beside `font.json`, `--requirements`, or an
  explicit `--no-requirements` recorded in the manifest) so the required-character check runs on
  every build (C6); under `--masters` the fold measure and the minimum interior stroke width are
  recomputed from the polygons and held against the stated figures (C7); paths in `font.json`,
  `--out-dir` and `--static` resolve relative to `font.json`'s directory (W6); the masters JSON is
  written to a temporary directory unless `--keep-masters` (W5); one `SELF-CHECK ok:` line per check.
- `scripts/tests/mutate.py`: RED only when the mutation applied, the rebuild succeeded and changed
  an artefact (or refused with the declared text) and the named tests failed on the expected
  assertion; otherwise UNPROVEN (C8). `test_font.py` pins the word space per master from
  `requirements.json` (C9). `conftest.py` finds the scripts beside its folder, or through
  `--scripts` / `FD_SCRIPTS` (W1). `test_site_wiring.py.tmpl` reads selector lists, both quote
  styles, nested `@media`, non-`clamp()` sizes and a shared `font-synthesis` rule, and makes the
  old-face slots optional (W12).
- `mine-charset.py` reads the same selector grammar as `mine-sizes.py` (W8);
  `scripts/concepts/content.minimal.json` is the round-1 starting content, with the current face as
  the comparison (W2, W10); `build-page.js` names each missing field.
- Repo tests added: `tests/test_shoot.py` (the server and sentinel, in real Chrome where found),
  `tests/test_copy_into_site.py` (W1), `tests/test_site_wiring_template.py` (W12),
  `tests/test_docs_commands.py` (every documented command's flags against the parser, W3), the C3
  cache test and the hostile-content pages opened in Chrome (C10). `ruff` is pinned (C13).
  `pytest.ini` limits a bare `pytest` to `tests/`.
- CI: a `chrome` job on Linux installs a stable Chrome and runs `smoke.sh --full` from step 6 and
  the browser tests (C12). **It has not been executed**: the workflow has never run on GitHub, and
  this machine cannot run it; its first push is its first run.
- Skill text: project files are created in the phases that produce their inputs (D2); phase 1
  audits and proposes, fixes follow the gate (D3); the phase 2 gate asks the content-trap, `opsz`
  and smallest-element decisions explicitly (D4, W9); nothing is committed before phase 9's review
  (D5); a defect visible at 1× at round six stops before phase 9 (D6); one rule for missing browser
  evidence, in `SKILL.md`, `process.md` and `fallbacks.md` (D7); `--family` and `--font-url` on
  every evidence shot (D8); `testing.md` says which expectations are pinned and which are
  consistency checks against a fresh export (D9); the trigger description requires the intent to
  draw or build a face (D10); Bract is the full-process example and Driftwood the precedent (D11);
  the example name tables are neutral and MIT, the names Bract and Driftwood MA reserved (D12);
  the italic review row (D13); `$FD_PY` for every Python command (W4); `narrow.html`'s command
  and settled-fonts rule in phase 1 (W7); the served root and the specimen's place in phase 8
  (W11); `extra-glyphs.js` as the convention for site glyph additions (W13); when to run
  `smoke.sh` (W14); what the neutral example is and is not (W15).

### Changed after the second cold dry run (findings 1–16), before the first commit

A fresh-context agent followed `SKILL.md` on `examples/neutral` with `tests/fixtures/site-sample` as
the site, with no statics, and reported it not runnable end to end unsupervised. Each finding was
verified against the files before it was fixed; every new or changed guard was watched failing under
the weakest mutation that breaks it, restored by copy and checked by digest (the mutations are named
in the tests' docstrings).

- `scripts/tests/mutate.py` (1, 2): `--static-dir none` is the conftest's word, skips the three static
  mutations with `SKIPPED | name | reason` and exits 0 (the first harness read it as a path, built
  statics into the served font folder during the static-overlap mutation and died in a
  `FileNotFoundError`); with no flag and no `<out_dir>/static` the run is refused naming both ways
  out. Every `expect` text is derived from the project's `requirements.json` (`required-F002` names
  the project's own digits; the floor mutations the project's floor less one; the win-metrics
  constants are halves, not the precedent's 940/300; `floor-F002b` cuts every concept's `thin` by a
  regular expression instead of matching the neutral fixture's `0.6`), and a mutation the project
  cannot exercise is `SKIPPED`, never silently green. The summary line counts the skips.
  `tests/test_copy_into_site.py` runs both cases in a site.
- The 360 px reading is a phase-8 requirement (3): every page, every round, with the wired font
  (`SKILL.md` phase 8, `process.md`, `review-loop.md` sections 1–3 and 7, `site-audit.md` section
  6), publication blocker 6, and `smoke.sh` step 11, which wires Sampler into a copy of the fixture
  site and requires the `fonts`-stage reading on both pages with the index's overflow REPORTED (the
  NBSP-joined frontispiece title fits in Georgia and reads 384 px against 360 in Sampler) and the
  essay passing.
- `build.py --static` and `--out-dir` are documented as resolving from `font.json`'s directory, which
  is what the code does (4); under `--out-dir` the manifest goes into that directory whatever the
  `manifest` key says (15), with a test in `tests/test_copy_into_site.py`.
- `SKILL.md` phase 2 has a table of where each `requirements.json` field comes from and when (5):
  `required_characters` and `titles` from `mine-charset.py`, `cmap` from the template, `names` from
  the opening questions, the axes from the phase 6 plan, the floors and word spaces from the first
  export of phase 7. There is no `sizes` key.
- The audit brief's "computed styles" slot is the `mine-sizes.py --json` output, read from the CSS
  (6); no tool here reads computed styles from the browser, and the docs say so.
- The round-2/3 mock sizes come from `content.slot_sizes` (7): seventeen named slots with `size`,
  `min`, `fit`, `lh`, validated by `build-page.js` (an unknown slot or field fails the build),
  documented in `content.example.json`, with a Chrome test reading the rendered `data-size`. The
  mock structure stays fixed and the docs say the face is judged on the real pages in phase 8.
- An installed comparison family has its evidence path stated (8): shoot without `--family`, read
  the page's own `data-fd-font` from the dumped DOM, and what that proves (a face other than the
  default serif drew the probe) and does not (that it was that family).
- `test_site_wiring.py.tmpl` (9): `static_config` empty skips f with the reason, and the stylesheet
  is refused as the config by name (its `url()` names woff2 whatever the host serves); e skips,
  saying so, outside a git work tree; the font-synthesis guard takes a `font_synthesis` slot
  (`adopted` / `declined`) instead of a pytest marker that failed as shipped and warned. Guard p's
  scope is stated: display-cut selectors only; a tracked wordmark in the text cut keeps its
  letter-spacing (16). `tests/test_site_wiring_template.py` runs a third style and the stylesheet case.
- `mine-sizes.py --family NAME` and `mine-charset.py --css FILE --family NAME` find every selector
  whose rule sets the family first, `@media` included (16; a hand-typed list had missed
  `.frontis-title`, `.wordmark` and a 15.2 px `.num`, moving the floor from 44.6 to 49.3 units);
  `mine-charset.py --css` adds the characters a `text-transform` makes the browser draw and says when
  it could not read one (10); U+00A0 stays in `required_characters` beside the space, and the two
  example templates carry it (11).
- `$FD_PY` in every documented command (12): six lines in `variable-font-build.md` and one in
  `concept-pipeline.md` ran a bare `python3`; `tests/test_docs_commands.py` now fails on any bare
  `python3` command in the docs (the earlier test checked flags, not interpreters). It also refuses
  `python3.12` and an absolute system interpreter path: its first pattern missed both, found by a host
  mutation. `smoke.sh` honours
  `$FD_PY` first (13).
- Copy `scripts/` into a site only after `smoke.sh` has finished, then `diff -r` the copy (14):
  `SKILL.md` phase 7, `process.md`, `testing.md` section 7.
- The name search is the host's, before the phase 5 gate, with the searches and hits in the plan;
  the owner and licence strings are asked in the opening questions and written into
  `requirements.json` in phase 2 and `font.json` in phase 7 (16).

### Changed after the independent re-review (2026-11-16)

A cross-provider re-review of the whole repository returned 37 findings in three pieces (the
generator, exporter, builder, font suite and harness; the review tools, concept builder, templates,
repo tests and CI; the documentation). Each was verified against the files before anything changed:
a code defect was reproduced first, a doc defect quoted; every new or changed guard was watched
failing under the weakest mutation that breaks it and restored. Findings the re-review got wrong,
and the ones accepted as stated limits, are in the host's report, not here.

- `scripts/build.py`: the `--masters` path reads each master's `W`, `thin` and `track` back from
  `gen.js` through node and refuses a JSON that differs, and the stroke-width recomputation takes
  its `W` from there, since `W` sets the interior reach (code-a F002; a tripled `W` had built);
  every glyph's `raw`, `runs`, `polys` and `keptIdx` lists must have one record per polygon, and
  every zip over them is strict (code-a F003; a `keptIdx` list one record short had built with that
  polygon's checks skipped); under `--out-dir` the manifest's `file` entries name the woff2 where it
  was written (code-a F009). **Path rule reversed** (docs F007): every command-line path (`--static`,
  `--out-dir`, and the other tools' options) resolves from the working directory, as a shell does;
  only paths written inside `font.json` resolve from its directory. The README's own build and test
  lines had named two different static folders under the old rule; `tests/test_neutral_readme_commands.py`
  runs them as written.
- `scripts/gen.js`: `undefined` and `null` serialise differently in the glyph-cache key (code-a
  F001: `dropAmt: null` drew the default's glyphs).
- `scripts/tests/test_font.py`: no GPOS pair the exporter did not emit, and at least one live
  automatic pair per master (code-a F005, F004: the automatic values stay unpinned, said so); the
  two `--masters` refusals above have tests. `scripts/tests/mutate.py`: every expected text is held
  against the failure section of the test it belongs to, with `expect` as a dict for a mutation
  naming several tests (code-a F008), and `tests/test_mutate_harness.py` on the pure judgement; the
  `F013` mutation shifts the last master's outlines by 3 units, so it reaches its test on a
  two-master group (code-a F007: the old form was refused by the gvar self-check, UNPROVEN); a
  project with no roman group or one named instance lists and runs (code-a F006). The set is 48.
- `scripts/shoot.py`: a beacon is recorded only from the Chrome carrying that shot's cookie, and the
  remaining trust assumption (the page is the operator's own; its script could send the beacon) is
  stated in the header (code-b F001; a host mutation accepting any `.inner` cookie survived the first
  test, which now also sends another shot's inner-page cookie); `</` is escaped in the sentinel's literals (code-b F002);
  visible means `checkVisibility()` with opacity and visibility counted, a box, and a box inside the
  document, with the limits stated (code-b F003); a face must cover the element's weight, verdict
  `no-weight-face` (code-b F004). `scripts/narrow.html`: the fonts-stage reading is written only
  for an inner page served 200 (HEAD), with no failed face and, with `?family=`, a loaded face of
  the family; otherwise `data-fd-overflow="error"` with the facts in three attributes (code-b F005,
  docs F015); the documented command passes `--query family=<Family>`.
- `scripts/mine-charset.py`: every `text-transform` rule in the stylesheet is matched against the
  elements inside the display text, descendants and classes included, and an unreadable rule is
  named (code-b F006). `scripts/concepts/build-page.js`: `slot_sizes` is required for rounds 2 and
  3 and every slot left at the default is named on stderr (code-b F007); `examples/neutral/content.json`
  carries the block. `scripts/tests/test_site_wiring.py.tmpl`: guard s requires every selector set
  in the face to be listed as display or text-cut (new slot `text_cut_selectors`; code-b F008) and
  guard a2 requires the italic src to be an italic font (code-b F009). CI: the matrix job runs
  `smoke.sh` steps 1-7, so every fixture builds and every mutation runs (code-b F010), with
  `tests/test_ci_workflow.py` reading the line; the workflow has still never run on GitHub.
- Docs: the version is stated as unpublished (docs F001; the rights line in `NOTICE.md` is the
  operator's); the phase 2 gate's three decisions in `guidelines.md` (F002); the audit fixes are
  their own commit before the font change, in `SKILL.md`, `process.md` and `site-audit.md` (F003);
  the round-six rule in `review-loop.md` (F004); one sentence for the browser-evidence waiver in
  `SKILL.md`, `process.md`, `fallbacks.md` and `review-loop.md` (F005); the trigger table's unrun
  cases say so (F006); the hairline floor is held against the site target, with Bract's 0.70 px
  named as the open item it is (F008); the `opsz` ends are measured on the fixture font before the
  phase 2 decision and confirmed in phase 8 (F009); the plan's measured figures come from a scratch
  export (F010); a glyph to carry is drawn before round 1, with `build-page.js --gen` (F011);
  `site-audit.md` no longer asks for computed styles no tool collects (F012); phase 9 writes the
  record and docs first, then reviews `git diff --cached` with the change staged (F013, F014);
  `font.example.json` says what it needs to build (F016); the concept brief ranks on the mock, not
  "a real page", in rounds 2 and 3 (F017); the character set is described as checked, not exact,
  with what it cannot see (F018).

### Changed after the research reviews (2026-11-16)

Two read-only reviews (skill packaging and cross-platform use; font design and technology, with
FontBakery run on the neutral fixture) produced a list; these eight items from it are built. Nothing
else from their later lists is.

- **Packaging.** The `SKILL.md` description is 1,019 characters, under the 1,024 the hosts enforce (it
  was 1,223; the process clause moved to the body, the trigger and non-trigger cues stayed), and a test
  holds the limit. The frontmatter gains `license: MIT` and a `compatibility:` line (Node 20, Python 3.10,
  Chrome, bash, macOS and Linux, WSL, network for the independent review and the name check). The
  instruction to set `FD_PY` once is gone: a Bash call on most hosts does not remember the last, so every
  command spells `.venv/bin/python3`, and a new section, "Finding the skill folder", says how to find the
  folder on Claude Code (`${CLAUDE_SKILL_DIR}`), Codex (the path it shows) and any other host (the
  directory of the loaded `SKILL.md`). `tests/test_docs_commands.py` refuses `$FD_PY` in a document and
  keeps its bare-`python3` guard.
- **Environment check.** `scripts/check-env.py` reports Python >= 3.10, the four requirements, Node >= 20,
  Chrome (through `shoot.py`'s own `find_chrome()`, imported) and bash, each with its fix command, and exits
  1 when one is missing. `build.py` refuses Python older than 3.10 and a missing fontTools with the venv
  command in the message instead of a traceback.
- **No edits to the installed skill during a project.** The plan's scratch `font.json`, the charset
  pre-check and the `opsz` measurement go under the project's `tools/<face>/work/`. A glyph that belongs to
  everyone is a separate, operator-gated change to the skill repository, never an edit of the installed copy.
  `SKILL.md`, `process.md`, `generator.md`, `plan.md` agree.
- **Platforms.** README and `SKILL.md` say macOS and Linux are supported, native Windows is not, WSL is.
  `shoot.py` also looks for Chrome in Program Files, Program Files (x86) and LocalAppData; a test fixes the
  order (`$CHROME`, the macOS app, those three, PATH names).
- **Font table defaults in `build.py`** (each found by FontBakery on the fixture, 6 FAIL and 1 ERROR before,
  1 FAIL after):
  - `OS/2.fsType` comes from `names.fs_type`, a required key with no default (it was fontTools' 4). The
    neutral example and the template say 0; the Bract and Driftwood configurations say 4, the usual setting for
    a proprietary face. 2 (Restricted) makes some tools refuse the font; browsers ignore the field.
  - **Line height can change on a live site.** hhea and OS/2 typo now carry the same ascender and descender
    with a line gap of 0, and `USE_TYPO_METRICS` stays set; win is still the measured extent. With no
    `typo_metrics` key both are the measured extent, so macOS is unchanged and Windows and Chrome (which read
    typo) move from the old typo set (760/-240 plus a gap of 200, 1.2 em) to it (the neutral roman: 1.212 em).
    With a `typo_metrics` override both platforms take it: the Bract example, whose override is 760/-240,
    goes from 1.23 em to 1 em on macOS for any element left at `line-height: normal`. `typo_metrics.line_gap`
    must be 0. The build prints `vertical metrics written: ...` and the `line-height: normal` they give;
    `requirements.json` pins them per group (`vertical_metrics`). See `variable-font-build.md` section 6.
  - STAT has axis values for every named instance (weights by standard name, the default elidable, the
    elided fallback the style); statics drop STAT, whose name IDs their rewritten name table would not hold.
  - A smart-dropout `prep` program (7 bytes) beside `gasp`, `maxp.maxStackElements` raised to count it.
  - No Macintosh name records; `ulCodePageRange1` has the Latin 1 bit.
  - Self-check lines for each; `requirements.json` gains `names.fs_type`, `groups.*.vertical_metrics` and
    `tables`; `test_font.py` gains five tests that read them (plus the static instances' checks); the
    mutation harness gains 20 mutations (and the gasp one is reworked). `build.py --check` stays byte-identical across two builds.
- **FontBakery gate.** `scripts/fontbakery-gate.py` builds each group's TTF into a temporary folder, runs
  `fontbakery check-universal` (pinned `fontbakery==1.1.0` in `requirements-dev.txt`) and fails on any
  FAIL, ERROR or FATAL not listed in `requirements.json` `accepted_qa_findings` (`[{id, reason}]`, a required
  key). It is phase 7's gate in `SKILL.md` and `process.md` and step 4b of `smoke.sh`, which skips it, loudly,
  when FontBakery is not installed (exit 3, SKIPPED, NOT PASSED). The roman and italic TTFs go through one
  FontBakery run (family checks need the pair, and the TTF carries the woff2's name because FontBakery reads the
  style from it). Fixed on the neutral example: code pages, `fvar`/STAT, Mac names, hhea against typo, smart
  dropout, and the ERROR in `name/family_and_style_max_length` that STAT without values caused. Five findings
  remain, each accepted in `requirements.json` with its reason: `case_mapping` (the generator draws seven
  lowercase accented letters, ì î ò ù û ā š, without capitals), `opentype/STAT/ital_axis` (no `ital` axis in
  STAT), `opentype/varfont/family_axis_ranges` and `varfont/consistent_axes` (the fixture's italic has one axis
  beside the roman's two) and `family/vertical_metrics` (957 against 956 units, each group being built alone). A deliberate non-zero `fs_type` is accepted under a vendor profile's `googlefonts/fstype`.
- **Specimen proof rows.** `specimen.py` opens with (fix round 2: they were last, beyond the 2400 px a default shot captures) spacing control strings (each lowercase between `nn` and
  `oo`, each capital between `HH` and `OO`, each figure between `00` and `11`, each punctuation mark after
  `r`, `f` and `y`) and the legibility row `Il1 O0 B8 rn m cl d` at the smallest review size, both built only
  from characters the font maps. The review checklist and the reviewer brief ask for spacing before kerning
  and for the legibility reading.
- **Site wiring.** Two optional guards in `test_site_wiring.py.tmpl`: a metric-matched fallback face
  (`fallback_family`) and `text-wrap: balance` on the display headings (`balance_selectors`); each skips with
  its reason while its slot is empty. `scripts/fallback-metrics.py` prints the `size-adjust` and the three
  overrides from the built font and a fallback font file. Measured once in Chrome on this Mac (the neutral
  roman against Georgia at 40 px): web font 521.0 x 48.0 px, bare Georgia 493.3 x 46.0, matched fallback
  530.1 x 48.0.
- **Survivors found while writing the guards** (testing.md section 8): a dead `removeNames` call in the
  builder (mutation GREEN, line deleted), a gasp mutation blocked by the new gasp self-check, two mutations
  that left a syntax error, a stack-order check that survived `in`, an equivalent WARN mutation, and stale
  bytecode after a same-size swap.
- **Not done, by decision:** an `ital` axis in STAT and family-wide vertical metrics (both accepted FontBakery findings above) and the later items in the two reports (genre vocabulary, optical-correction
  knobs, x-height and unbracketed serifs, class kerning, `unicode-range`, a Codex or Cursor installer, the
  trigger evaluation run). Python 3.10 and 3.11 are claimed by the guard and `compatibility`, but CI runs
  3.12 only.

#### Fix round after the first review of this section

- Tests now observe the specimen's proof rows (four spacing kinds, the legibility row at the smallest size and its
  weight, no character the cmap lacks) and `smoke.sh` step 9 greps for them.
- `check-env.py` also refuses native Windows, compares installed versions with `requirements.txt` (a system
  Python's fonttools 4.60.2 is no longer "found" against `==4.68.*`), and quotes the skill path in its fix command.
- `fallback-metrics.py`, `specimen.py`, `shoot.py` and `opsz.py` give the same interpreter and install message as
  `build.py` when fontTools or Pillow cannot be imported.
- `fontbakery-gate.py`: a check id reported for two files takes the worst result (a test pins WARN against FAIL in
  both orders); `build.py`'s `fs_type` validity check has executed refusals for a missing, boolean, string, 6 and 16
  value; the gate's build test no longer needs `examples/neutral/out` to exist.
- STAT limits written down in `variable-font-build.md`: `opsz` values are named by number, and the italic's STAT
  has no `ital` axis.

#### Fix round 2 after the cross-provider review

- FontBakery gate: a stale report is removed before a run and an exit code other than 0 or 1 fails (cited to
  `fontbakery/cli.py`); a summary claiming more FAIL, ERROR or FATAL results than the sections hold blocks; an
  accepted entry may list `codes`, so a new failure of an accepted check blocks (the neutral example lists the real
  ones).
- `names.fs_type` bit 9 (bitmap-only embedding) is refused: the build writes no bitmaps. Designer (name ID 9) is
  checked by the build and the font suite, with mutations.
- Mutation harness: the italic derivation works for a project whose only group is italic; `static-weight` forces a
  class no static has.
- `check-env.py`: a missing `requirements.txt` or an unreadable version is MISSING, the submodules the tools use are
  imported, a fontbakery that raises on import is reported, not a crash.
- `shoot.py`: a Chrome that is a file but not executable is refused in discovery, and a launch failure is a clear
  error. The specimen's proof rows are now its first section, with `data-fd-proof-bottom` proving them inside the
  captured height at 500 and 1280 wide (a Chrome test and `smoke.sh` step 9).
- Site-wiring template: font URLs with a query or fragment are checked; the `text-wrap` guard states that it does not
  compute the cascade; the fallback guard is no longer called "metric-matched" without its limit. `test_docs_commands.py`
  reads flags from `add_argument` calls, not from any text. Doc fixes: `--group roman` on `--masters` and `--ttf`,
  `SOURCE_DATE_EPOCH` wording, the `line-height: normal` claim.

#### Fix round 3 (last)

- Phase 7 no longer contradicts phase 3: when phase 3 already copied `scripts/` to carry a glyph, do not copy again and the
  `diff -r` shows only the recorded `gen.js` patch and `extra-glyphs.js`. Under WSL the Windows Chrome paths are not
  searched: install Chrome or Chromium in the Linux distribution.
- `check-env.py`: `find_spec` separates "fontbakery not installed" from "installed but raises ImportError", and the fix
  command uses an absolute, quoted requirements path.
- Tests: every documented flag must appear in the script's own `--help`; fragment-only and query-only font URLs; the
  proof-row Chrome test measures with its own injected script; the gate's summary check with non-empty sections and a
  process killed by a signal; the static designer record (name ID 9) in the build and the font suite.
- The build's STAT self-check now verifies the standard weight names, the single elidable default and the fallback
  name (mutations with it cut, and `-refused` mutations proving it refuses).

### Known limits

- The italic path is pipeline-tested on the neutral and Driftwood fixtures (compatibility, folds,
  hairlines, gvar, instancing, metadata) but has not been design-reviewed in any shipped font since
  Driftwood 1.000, which was static and unioned.
- Raster self-check budgets are per machine (FreeType in the Pillow wheel); CI on two operating
  systems uploads each manifest so a difference is visible.
- The CI `chrome` job (Linux Chrome through `shoot.py`, `opsz.py` and the specimen) is written and
  has never run; until its first run on GitHub the browser steps are proven only by
  `scripts/smoke.sh --full` on the author's Mac.
- The round-1 comparison row of the neutral example shows the built fixture font itself; a real
  round 1 compares against the site's current face (`content.minimal.json`).
- Statics from `--static` keep overlapping contours and are for modern renderers.
