# Changelog

All notable changes to this skill. The format follows Keep a Changelog; the version is the `VERSION`
file, repeated in `SKILL.md` and the README badge and checked by the tests.

## [0.4.0] — 2026-11-18

A site runs the platform shots through the skill's own workflow instead of a copy of it. The site keeps a short
caller pinned to a skill commit; the run happens in the site's repository, checks out the site's pages and fonts
there and the skill's scripts at the pinned commit, and is billed to the site. Nothing of the site enters this
repository. Planned by Fable and reviewed before code by an independent cross-provider reviewer (Impasse, 5
findings, all accepted: consumer details kept out of this repository, the weight rule's width and italic/oblique
limits, the specimen's `requirements.json` path, one test mutation Bash could not fail, GitHub Enterprise Server).
The finished diff was reviewed the same way (5 findings, all accepted and fixed: oblique angles, `font-synthesis`,
a consumer named in a test docstring, the leg filter's substring match, one README sentence). One re-review of the fixes
found three more, all accepted: the two limits above, now stated, and a test that read the probe's own answer
instead of the face Chrome chose.

### Changed
- **`.github/workflows/platform-shots-reusable.yml`** (new, `on: workflow_call`) holds the six legs (Windows,
  macOS and Ubuntu runners × Chrome and Playwright's Firefox) and the compare job: the only copy of them. Inputs
  `serve`, `family`, `font_urls`, `pages` (required), `font_json`, `scales`, `browsers`, `oses`, `build`,
  `run_tool_tests`; every value reaches a script through `env:`, never `${{ }}` inside `run:`.
- **The scripts come from the pinned commit, or the leg refuses.** Each job first requires `job.workflow_sha` to
  be a full 40-hex SHA, checks out `job.workflow_repository` at it, and verifies `git rev-parse HEAD` equals it;
  it never falls back to a branch. GitHub Enterprise Server, which has no `job.workflow_*` context, is not
  supported.
- **`templates/platform-shots.yml` is now a caller** (`workflow_dispatch`, one job `uses:` the reusable workflow
  at a full commit SHA, `with:` the inputs). `FD_SCRIPTS` is gone: a site keeps no copy of `scripts/`. A site
  that copied the 0.3 template keeps working; its copy is its own.
- **The skill's own `platform-shots.yml` calls the reusable workflow locally** (`uses: ./…`) on pull requests that
  touch the tools, with the neutral fixture and `run_tool_tests: true`, so a pull request runs its own scripts.
- **The probe's weight rule follows the browser's font matching** (`shoot.py` item 6). It used to require a face
  whose declared range covers the computed weight, which failed a static family of 400/500/700 asked for 600,
  although Chrome draws the 700 file without synthesis (measured 2026-11-18 on a live site's static faces).
  `pickFace()` now applies CSS Fonts 4 § 5.2 to the loaded faces of the element's style, italic and oblique kept
  apart. **Exact guarantee:** the visible text in the family is drawn by a loaded face of the right style that the
  browser's weight matching selects without synthesising bold; it does not check that the selected weight is the
  one the design intended (a 500 request with 400 and 700 files draws Regular and passes), and it models faces of
  normal width and one oblique angle only. It reads the faces' load state and the computed style, not the face
  that painted the element, so text that `font-display: optional` left in the fallback is not detected (the
  screenshot is the check there). An italic element needs a face declared italic: CSS would fall back to an
  oblique face, and the probe fails that on purpose (`no-italic-face`). New failing verdicts: `synthetic-bold` (a request of 600 or more
  whose selected face is below 600, with weight synthesis allowed), `lighter-face` (the same with
  `font-synthesis` turning weight synthesis off, so the lighter face is drawn as is), `unmodelled-stretch` (a
  loaded face of the family with a non-normal `font-stretch`) and `unmodelled-style` (an oblique element whose
  loaded oblique faces declare more than one angle).
  `no-weight-face` is removed. Each probed element carries `data-fd-probe-weight`, the weight selected.

### Fixed
- **The shot server's listen backlog is 128, not 5.** Several browsers at once (`--jobs`, default 3) each open a
  burst of connections; on macOS a full backlog refused the extra ones, so a font request never reached the
  server, the browser drew the fallback, and the shot failed as `font=missing` or `no-italic-face` with nothing in
  the response log. Measured 2026-11-18 on a 12-shot site at `--jobs 6`: three of three runs failed so at 5, five of
  five clean at 128; at the default `--jobs 3`, one shot in fifteen. It failed shots, never passed one wrongly.

- **The leg filter matches whole words.** The `browsers` and `oses` inputs were tested with `contains()`,
  which on a string is a substring test; a shell step now matches exact words and fails the leg on an unknown
  or empty one.

### Removed
- The copy template's `FD_SCRIPTS` slot and the `requirements-platform.txt` fallback install; the reusable
  workflow installs `playwright==1.64.1` by name, held equal to `requirements-platform.txt` by a test.

## [0.3.1] — 2026-11-18

Lets a site build its face from the skill's scripts instead of a private copy of them. hopsafari.com is the
first site to do this: it carries the skill as a pinned submodule and keeps Bract's definition in its own
repository.

### Added
- **`kerning.sparse_cap`** in `font.json`: an integer ≤ 0 or `null`, default −50 (the 0.2 behaviour, so
  every recorded digest in `tests/test_backward_compat.py` is unchanged). `null` switches the sparse-glyph
  cap of trap 34 off, for a face whose kerning was reviewed without it (Bract: `.|Y` −149 at Bold). `kern()`
  takes the cap as a fourth argument and keys its cache on it; `export.js` refuses any other value before
  drawing; the schema, `templates/font.example.json` and the font suite's `restate_kern` carry it.
  `layWord()` (the concept-page preview layout, through `render.js`) takes it as `opt.sparseCap`.

### Fixed
- **The manifest's `file` entry is relative to `font.json`'s directory even when the woff2 lies outside it**
  (`../../static/F-VF.woff2`). It used to be recorded absolute, so the manifest named one clone's home
  directory and `--check` failed in any other clone. Only a file on another Windows drive is still absolute.
- **`--out-dir` keeps a group's `file` inside DIR.** A `file` with `..` steps (`../../static/F-VF.woff2`) escaped
  DIR by them; under `--out-dir` only its name is kept now, the same rule as the `manifest` key.

The Impasse review of this release (4 findings: `layWord` ignoring the cap, an over-broad pair-count claim in
`examples/bract/README.md`, and two test gaps, a numeric cap and `--out-dir` portability) is reconciled in the
pull request. The three code fixes each have a test watched red under its mutation; the README correction is prose
and has no test. A re-review of the fixes found that keeping only the name lets two groups collide under
`--out-dir`; `build.py` now refuses any config in which two groups would write one file.

## [0.3.0] — 2026-11-17

The cross-platform rendering check (`docs/plan-platform-shots.md`), planned by Fable, reviewed before code by an
independent cross-provider reviewer (15 findings, all reconciled in the plan's section 14; the operator ruled the
Firefox leg in), and built by five agents in parallel. It answers the question every font record carried as
"not checked on Windows": how the face draws under DirectWrite/ClearType, and on macOS and Linux, in Chrome and
Firefox. **What a result proves:** how headless Chrome and Playwright's Firefox drew the face on GitHub-hosted
Windows Server, macOS and Ubuntu runners, as each leg's `meta*.json` records them; not a reader's laptop (display,
scaling and ClearType tuning differ), not Safari, not phones. It is a record line, not a publication blocker.

**Acceptance run:** platform-shots run 44238569295 on the neutral fixture (Sampler), commit 4b7085d: all six legs
verified, 6 legs accepted, 208 row images, 0 rows mismatched, missing, below the capture or refused. At 16.8 px
Windows Chrome 156 drew ClearType with colour fringes, Windows Firefox 157 drew greyscale, Linux Chrome 158 drew
subpixel, both macOS browsers drew greyscale, and no stroke broke up in any leg. Earlier runs on the same pull
request found the faults fixed in this release: Git Bash path rewriting and cp1252 on Windows, a relative screenshot
path Chrome on Windows would not write, Chrome's command line on Windows measuring the page 16 px narrower than it
captured, Firefox's 1/16 px font sizes, and the sentinel starting before an external stylesheet had loaded.

### Added
- **`templates/platform-shots.yml`**: a manually started GitHub Actions workflow a site copies into
  `.github/workflows/`. Three OSes × two browsers; each leg shoots the review specimen (6000 CSS px tall, so
  every row is captured) and the site's named pages with the full `shoot.py` proofs; one job then compares the
  legs. Slots in `env:` (`FD_SCRIPTS`, `FD_SERVE`, `FD_BUILD`, `FD_FAMILY`, `FD_FONT_URLS`, `FD_PAGES`,
  `FD_FONT_JSON`, `FD_SCALES`); an empty `FD_FONT_JSON` gives pages-only legs, for a face the skill did not build.
  Free on a public repository; about $0.40 a run on a private one (GitHub's per-minute prices read 2026-11-17,
  jobs rounded up to whole minutes; macOS is most of it).
- **`scripts/compare-shots.py`**: one PNG per row stacking every leg's crop at `--zoom` (nearest-neighbour, so
  subpixel colour stays visible), labels from each leg's meta (OS, browser from the user agent, scale, Windows
  ClearType from `FontSmoothingType`), an ink figure measured against the crop's own background, and `compare.md`
  with the smallest sizes first. Rows pair across legs by key and by text, size, weight and style; a leg without
  its record is refused and the others are still compared.
- **`scripts/shoot_playwright.py`** and `requirements-platform.txt` (`playwright==1.64.1`, optional): `shoot.py
  --browser firefox` drives Firefox through Playwright against the same server, tokens, cookie and sentinel proofs
  as Chrome. Without Playwright it exits 3, `SKIPPED, NOT PASSED`. On macOS Firefox could not open its profile
  under `~/Library/Application Support/Firefox`; `launch_env()` points `CFFIXED_USER_HOME` at a reused folder
  (the cause inferred from that workaround, not traced). `check-env.py` reports Playwright as optional.
- **`shoot.py --launcher playwright`**: Chrome driven by Playwright (the Chrome binary `shoot.py` found). The platform
  workflow uses it on every leg: on a Windows runner Chrome's command line laid the page out at 1264 px for a 1280 px
  shot, so its row boxes were cropped from the wrong place (run 44227825840). A rows file measured on a page more than
  2 px wider or narrower than its shot now fails the shot in `shoot.py` and is refused by `compare-shots.py`.
- `compare-shots.py` pairs font sizes that agree to 1/16 px: Firefox reports 16.8125px where Chrome says 16.8px, and
  run 44227825840 dropped every such row as a mismatch; all legs' sizes must lie within 1/16 px of each other.
- From the Impasse review of that change: Chrome through Playwright keeps its sandbox and `--disable-gpu`, as the
  command line does; `--rows` needs `--family` and `--font-url`; `compare-shots.py` refuses a PNG whose size is not
  the shot its rows file describes; the Chrome legs run the Playwright Chrome test natively.
- The sentinel starts at `load`, not `DOMContentLoaded`. It is injected before the page's stylesheets, and Chrome
  through Playwright reached `DOMContentLoaded` before an external stylesheet had declared the family, so it reported
  the font missing and only then fetched it (run 44236884579, every Chrome leg's `index.html`).
- **`shoot.py`**: `--rows` (each `data-fd-row` and probed element's viewport box, written to `<stem>.rows.json`
  only after every proof passed; a scrolled shot is refused), `--meta FILE` (platform, browser user agent, Windows
  font-smoothing registry values, every verified shot, the failures), fractional `--scales` (`@1.25x`), repeatable
  `--font-url`, `--browser`. Windows teardown: `taskkill /T /F` before the parent is killed, a bounded wait for
  stdout EOF, and a profile folder whose failed cleanup is a logged departure, not a crash.
- **`specimen.py`**: every family row carries a unique `data-fd-row` key; a duplicate key refuses the page.
- **`.github/workflows/platform-shots.yml`**: the template filled for the neutral fixture, run on pull requests
  that touch these tools: the release proof that they run on Windows and macOS.

### Designed, not built
- **WebKit.** Playwright's WebKit is not Safari, and the macOS runner bills the most; a `safaridriver` leg is the
  better future item (plan section 2.4).

### Changed
- The "not checked on Windows" wording in `SKILL.md`, `references/` and the record template becomes a two-way
  record line: the run's result, or "not checked" with the claim it limits. Traps row 21 records the one
  Driftwood observation (2026-11-17).

### Added (folded in from the unreleased lint work)
- **JavaScript and shell lint** (issue #3). A `lint` CI job runs ESLint 10.14.0 (pinned, through npx; `eslint.config.js`, correctness rules only)
  over `scripts/*.js` and `scripts/concepts/*.js`, and shellcheck over `scripts/smoke.sh`, as `npm run lint:js` and `npm run lint:sh`. Both
  pass the 0.2.0 tree unchanged. Detail and guards: `references/testing.md` section 8.

### Fixed
- From the Impasse review of the finished diff: `compare-shots.py` reads a Windows leg's `leg\x.png` path on the
  Linux compare job, and refuses a meta or rows file of the wrong JSON shape instead of crashing; `shoot.py` fails a
  font path when any response for it was not 200 (one 200 among them passed before); the specimen shot fails a row
  below its capture (`--require-captured`) instead of leaving it out; the skill's workflow also runs when
  `specimen.html.tmpl` changes.
- On Windows, `shoot.py` now gives Chrome an absolute `--screenshot` path; Chrome there wrote nothing for a
  relative one. `build.py` reads and writes its files as UTF-8, not the Windows default cp1252.
- `package.json` said 0.1.0 in the 0.2.0 release. `test_version_is_the_same_everywhere` now checks it too.

## [0.2.0] — 2026-11-16

Five changes from the font research review (`docs/plan-0.2.md`, items 3, 4, 9, 2 and 10), planned by Fable,
reviewed before code by an independent cross-provider reviewer (14 findings, all reconciled in the plan's
section 12), and built by three agents in parallel. **Every new parameter defaults to the 0.1 behaviour**, and
the three examples build to the same fonts as 0.1.0: `tests/test_backward_compat.py` holds the export and the
decoded TTF to digests recorded from the 0.1.0 code (it does not hash the woff2 bytes, which depend on the
brotli build; on this machine the rebuilt woff2 files were also byte-identical to 0.1.0's by `cmp`). One
default did change, as a fix: an unset `cut` is now 0 rad, where 0.1 drew non-finite outlines (see Fixed); no
0.1 example left `cut` unset.

### Added

- **Optical corrections in the pen model** (item 3): `hzThin` (level strokes thinned, weighted by cos²θ),
  `roundGain` (curves thickened, weighted per sample by local curvature: a ring fully, an open curve by
  min(1, κ·2.5·W0)) and `diagThin` (diagonals thinned, weighted by sin²2θ); all default 1 (off). The width
  law is now one function, `penWidth()`, used by the stroke samples, the corner reach and the vertical fit,
  so a thinned bar still lands on its line, and a round top lands at the line plus `overshoot` whatever
  `roundGain` is. `params()` refuses `hzThin` or `diagThin` outside (0.5, 1.5), `roundGain` outside
  (0.8, 1.25), and non-numbers. Tests: `test_optical_corrections_change_only_the_strokes_they_name` (one
  variant per knob plus one with all three whose expectation restates the full product) and
  `test_the_optical_knobs_refuse_values_outside_their_ranges`; 14 `optical-*` mutations, all red.
- **`xh`, the x-height of the lowercase** (item 4): 400–600, default 500. A piecewise-linear y map inside
  `fitSkeleton()` for every lowercase key except the apostrophe: the body scales to `xh`, the band to the
  ascender scales to 740, descenders and ascenders stay. Flat and round targets follow the map; the dot rule
  reads the unmapped dot position; the spacing and kerning bands follow `xh`. **Every geometry-dependent
  decision** (curved, teardrop side, curl, vertical, serif kind, corners and joints, the beak side) **is
  taken on the skeleton fitted at `xh` 500**, so `xh` cannot flip a branch record: measured over 16,768
  glyph comparisons at `xh` 400 and 600, none flipped. Four tests, 11 `xh-*` mutations, all red.
- **`serifBracket`** (item 4): 0–1, default 1. Blends every serif between the 0.1 bracketed form (1, the old
  code unchanged) and an unbracketed slab (0) with the same point count (26, 15 and 26 for the three serif
  constructions), so a bracket can interpolate between masters. Two tests, 4 `bracket-*` mutations.
- **`joints`** (item 9): `joints: true` gives a concept whose `s` end is not `serif` the joint and corner
  pass a serif concept always had: level or plumb ends where two strokes meet (`V W A M N 1 4 v w`) and
  squared corners. Default off. Test `test_joints_opt_in_cuts_a_sans_joint_level`.
- **`crotch`** (item 9): 0–0.5, default 0 (refused outside 0–0.6). At an acute joint (`V A W M N v w 1 4 5`)
  the edge on the partner's side thins by `crotch` over the last 1.1·W0 with the teardrop's smoothstep; the
  outer edge keeps its line and the hairline floor never sees it. The acute outcome is recorded in every
  open stroke's branch record. Test `test_crotch_thins_only_the_inner_edge_of_an_acute_joint`; six
  `crotch-*` mutations.
- **`references/genres.md` and `templates/concepts.genres.js`** (item 2): a genre table (Didone, fat face,
  Scotch roman, Clarendon, Egyptian slab, grotesque, geometric, reverse contrast, optical sizes) with what
  defines each, the parameters that reach it and whether the generator reaches it today, plus ten recipes
  and seven genres it cannot reach (Tuscan, Art Deco, a circular `O`, a single-storey roman `a`, a spurred
  `G`, the pointed apex, expansion contrast). **Each recipe was rendered and read by a fresh strong-model reviewer
  on 2026-11-16**, and each verdict is dated in the table: reaches (`scotch`, `slab`, the optical-size pair),
  partly (`didone`, `grot`, `reverse`), no (`fatface`, `clarendon`, `geometric`). One reading, not a panel.
  `scripts/concepts/content.genres.json` is the genres page's content; `tests/test_genres.py` (6 tests) holds
  recipes, table and content together. `concepts.example.js` gains `slab` and `grot`.
- **`scripts/diff.py`** (item 10): the per-round visual diff. It renders the titles at every review size and
  every named instance of every group from a previous and a current build (instanced with
  `varLib.instancer`, through the one-instruction `fpgm` so FreeType does not autohint, laid out with raqm so
  GPOS kerning applies) and writes `diff.md`, `diff.json` and a before/after/diff PNG per changed render.
  It proves what FreeType drew on one machine, not a browser render. 7 tests in `tests/test_diff.py`, 13
  by-hand mutations, all red; `smoke.sh` step 2b checks a build against its own copy reports no change.
- **A junction row in the specimen**: `1 4 5 v w A M N V W AVAWMNW vwvwv` in the Bold at the smallest review
  size (`y` and `k` are not in it: their strokes cross, they do not end on each other). The proof rows go
  from five to six, and all six still lie inside the default 2400 px shot.
- **`tests/test_backward_compat.py`**, with `tests/baseline_digest.py` and `tests/fixtures/baseline-0.1.0.json`:
  the three examples must build to digests recorded from the unmodified 0.1.0 code (the export without branch
  records, the woff2 decompressed to a TTF, the manifest without source hashes, tool versions, woff2 figures
  and the absolute output path), keyed by Node major version (20 and 22 agree; 26 differs by V8 arithmetic).

### Fixed

- `params()` now sets `cut` to 0 when a concept leaves it unset, as `generator.md` section 4 always said. Before,
  a concept with `cut` or `taper` ends and no `cut` angle drew non-finite coordinates in `C E G S T a c e g s t y 1 2 3 &`:
  Chrome dropped whole words while the concept page's self-test counted them drawn, and `export.js` wrote about 2,900
  `null` coordinates and exited 0, so `build.py` died later with an unrelated `TypeError`. The three examples all set
  `cut`, so 0.1.0 never drew the case; the genre render review was the first to. Now `export.js` refuses non-finite
  coordinates (exit 1, naming master and glyph), `render.js` sets `data-fd-error` on a NaN or Infinity path so
  `shoot.py` fails the shot, and `tests/test_genres.py` checks every recipe's glyphs are finite; each guard watched red.

### Changed

- With an optical knob set, the hairline is no longer `W × thin`: it is the smallest stroke the export
  reports, so a concept that adds a knob re-reads the export and re-pins its floors.
- The branch record gains a `crotch=a/b` token (text only).
- Phase 3 names each round-1 concept's genre and covers at least three (`process.md`, `concept-pipeline.md`,
  the concepts brief); phase 8 keeps each round's `out/` and gives the reviewer `diff.md`.

### Fixed before release, from the independent review of the finished diff (15 findings)

- Two geometry decisions still read the drawn skeleton, not the `xh`-500 one: the beak gate (a stroke 0.45 units
  off level at `xh` 500 was 0.54 at 600) and the pairing of stroke ends (1.8 units apart at 500, 2.16 at 600). Both
  read the unmapped skeleton now. The test that should have caught them used only the project's own glyphs, which
  sit far from every threshold, so both mutations were green against it. `test_no_decision_reads_a_mapped_coordinate`
  draws 500 synthetic glyphs placed on the thresholds, in five concepts, at `xh` 500, 400 and 600, and requires every
  decision to be reached; `generator.md` section 12 lists every decision and what it reads.
- `roundGain` gives a ring its exact overshoot; an open curve (`c e s`) lands within `(W/2)(roundGain − 1)` of it,
  measured, documented and asserted.
- `diff.py` counts a render as changed when the title's advance moves by more than 0.02 CSS px, not only when ink
  moves; refuses a group with no `instances`; sizes its canvas from both builds' ink so nothing outside the line box
  is clipped; and its `share` figures and order are now asserted.
- The genre table's parameter column, the recipes, and the page content are held to one source by tests; the build
  command written in `concepts.genres.js` named the wrong content file and is now run by a test; smoke step 8b
  checks that each of the ten recipes drew, not only that something did.
- `docs/reviews/genres-2026-11-16.md` records the render review's verdicts and a digest of each recipe's outlines
  (by Node major; 20, 22 and 26 agree). A recipe or generator change that moves a reviewed recipe's outlines fails
  "the genre verdict for <id> is stale", which enforces the sentence in `genres.md` that said so.
- Test gaps closed: the optical range test carries its own case list (it never sent `null` for two knobs); the joints
  test runs the shipped `"": "disk"` mapping; `test_the_0_1_woff2_bytes_are_unchanged_for_the_recorded_brotli` adds a
  raw-byte check keyed by Node major and brotli version, beside the decoded-font digests.

### Fixed before release, from the re-review (8 findings)

- The curl's spiral direction was decided on the drawn cross product while the curl itself was decided on the
  unmapped one, and the branch record did not encode it, so `xh` could flip a curl's handedness unseen. It is
  decided on the unmapped value now and recorded as `curlsg=a/b`. **This is the one token 0.2 adds to a 0.1
  branch record**, and only a curl end writes it: two masters of a 0.1 curl project that spiral opposite ways,
  which interpolate to nonsense, are now refused instead of built.
- The `crotch=a/b` token was written on every open stroke, so a 0.1 project whose masters fell on opposite sides of
  the new acute-angle test would have been refused although nothing is thinned. It is written only when `crotch`
  is set (`test_an_unset_crotch_leaves_the_0_1_branch_record`).
- The open-curve overshoot bound is `(W/2) × f(0) × hzThin × |roundGain − 1|`; the first form was signed and left
  out `hzThin`, and `roundGain` 1.05 with `hzThin` 1.4 broke it (4.49 against 3.75). The test covers that case.
- `diff.py` compares an advance change with its 0.02 px tolerance before rounding (a change of 0.0204 rounded to
  0.020 and was reported unchanged).
- The genre table's rows that describe a recipe relative to another must name every difference: two were
  undisclosed (`fatface` `xs 0.98`, `geometric` `track 4`). The review record's digests include the Medium
  (mult 1.25) the reviewed page showed, added after the review from a generator whose mult 1 and 1.5 digests match
  the review-time record.

### Fixed, found by the first CI run

- The compatibility fixture was keyed by Node major only. On Linux the neutral digests matched and the Bract and
  Driftwood ones recorded on macOS under the same Node did not: the generator's floating-point output depends on the
  operating system as well as on V8. The fixture is now keyed by platform and Node major (`darwin/26`, `linux/22`);
  an unrecorded one fails with the instructions to record it, and the promise that a 0.1 project rebuilds to the same
  fonts is stated per platform and Node major. The `record-baseline` workflow records the 0.1.0 code on Linux (Node
  20 and 22) beside the branch's own digests, by hand or on a pull request that changes the generator, and
  `tests/baseline_digest.py --merge` merges an entry and refuses one without a baseline revision.
- The built bytes depended on whether `uharfbuzz` was installed (fontTools serialises GPOS and GSUB with HarfBuzz's
  repacker when it is; blocking it changed every example's TTF digest). FontBakery installs it, so CI and this
  machine had it and a build from `requirements.txt` alone did not: the first Linux record was made without it
  and could not match CI. `requirements.txt` now pins `uharfbuzz` and `unicodedata2` (which fontTools also uses
  when present), `check-env.py` checks both, and the Linux digests were re-recorded with them.
- The genres page named Georgia as its comparison face, an installed family a Linux runner does not have, so the
  page's own probe failed both shots in CI. Its comparison face is now the built neutral Sampler beside the page, and
  smoke step 8b proves it was drawn (`--family Sampler`).
- The macOS CI job lacked libfribidi, which Pillow's raqm layout engine loads at run time, so `diff.py` refused. CI
  installs it before pip and asserts `features.check('raqm')`; `check-env.py` reports raqm as a required piece with
  the fix per OS (`brew install fribidi`, `apt install libfribidi0`).
- `scripts/shoot.py` kept waiting for Chrome after the shot was done. `test_hostile_text_is_inert_in_chrome` timed out
  ("Chrome took over 300s") in 10 of 14 macOS CI jobs and 4 of 22 Linux ones, on 0.2 and, by the same mechanism, on
  0.1 (whose single CI run was lucky). The hostile pages serialise to 96–124 MB of SVG path data; Chrome writes the
  screenshot and the whole DOM in ~12 s on the runner, then stalls in its own teardown (on macOS its 10-second
  shutdown watchdog logs "Teardown watchdog expired; recording dump and terminating." and `_exit`s with 2, and the
  helpers it leaves behind hold stdout open), and `subprocess.run` waited for the pipe to close. `run_chrome()` now
  reads stdout as it arrives; once the PNG exists and the DOM ends in `</html>` Chrome has `EXIT_GRACE` (20 s) to exit,
  after which its process group is killed, and an exit 2 that follows a complete shot with the watchdog's line on stderr
  is accepted (any other non-zero exit still fails: a dead renderer leaves a complete DOM of an error page); both
  departures are printed. An incomplete DOM still fails as before. `tests/test_shoot.py` runs a fake Chrome through all four cases;
  the two "keep" cases were red on the old code with the exact CI messages.
- The frequent half of the same failure is not the teardown: asked for a screenshot of such a page under
  `--virtual-time-budget`, Chrome 156/157 on the macOS runners stalled BEFORE taking it in about half of all attempts
  (every process idle, no PNG, no DOM, until the timeout: 7 of 12 and 8 of 12 in two probes; `sudo sample` stacks of
  every process show only run loops, and release Chrome carries no symbols), and never stalled in 24 probes without
  `--screenshot` or without the budget. The cause inside Chrome is not identified. `shoot.py --dom-only` takes no
  screenshot and returns the DOM alone (png None), and the hostile test uses it; the review shots keep both flags
  unchanged (their pages are a tenth of the size and have never stalled).

### Known issues

- Butt-ended curves draw a hooked flag with a notch at the top terminal of `a` and on `f r j y`, and the
  reverse-contrast `R` has a bump at the bowl and leg join. Not fixed in 0.2 (`references/genres.md` section 7).

### Designed, not built

- **`apex`**, a pointed apex that passes the line by a few units. `params()` refuses it, so a concept cannot
  carry a parameter that does nothing. `references/generator.md` section 13 holds the construction and the
  arithmetic for `A`, `V`, `N` and `M`. It waits because one value cannot serve `A` and `M`: the Bold `M`'s
  crotch would reach y = 26.1, closing the letter. A fix needs thinner diagonals or new skeletons.

### Findings, kept because they are about how the work was done

- Places where the build measured the plan wrong: the `c`'s curvature weight at its leftmost sample
  (≈ 0.6, not 1); unmapped points recovered by inverting the map (flipped 103 records on an all-curl concept;
  replaced by fitting at `xh` 500); an absolute tolerance on the `o` top that failed on unmodified code; an
  `o|o` kern that is 0 at every `xh`; a test outline shift that FreeType undoes unless the `lsb` moves too;
  `content.minimal.json` cannot serve the genres page; the first apex construction drew a 208-unit flat, not
  a point (found by the plan review).
- Mutations that survived the plan's own assertions, each fixed in the test: a corner or fit giving a
  straight bar the round gain; a corner counted as a joint; "every joint is acute" (no obtuse joint was in
  the identical list); a curl-decision change (no example uses a curl end, so the branch test now draws a
  curl-end variant of each master); a manifest digest that moved with the absolute output path.
- The neutral example's italic `w` decides its serif kind with a margin of 0.0028 (0.1028 against 0.1): a
  fragility present in 0.1.0, recorded in `generator.md` section 12.
- FreeType autohints the shipped fonts as they are; `prep` does not prevent it (deleting it changes nothing;
  adding a one-instruction `fpgm` changes the `B` at 16 px by 212 grey levels). Measured twice.

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
