# Plan: `font-design-skill` (skill name `font-design`), a public MIT Claude Code skill for designing and shipping a custom display typeface

Status of this document: a plan, written 2026-11-15 before any file exists, for independent review (Impasse) and then implementation. Markers: **(read)** = checked against the named file; **(measured)** = run or counted here; **(inferred)** = not verified, the implementer must check. Everything about Bract and Driftwood below was read from the files in the two site repositories on the day; nothing was taken from memory. Machine-specific paths were scrubbed before publication (section 12); source files are named by their path inside each site repository.

---

## 0. What was verified, and what the sources say (so the review can check me)

| Claim | Where | Status |
|---|---|---|
| Bract `gen.js` has: pinned sampling (`sampleCounts` from the unfitted skeleton), fold pin in `strokePolys`, `serifGrow`, `thinGrow` in `params()`, partner ids in the branch signature (`joins=0b/-`), ring closing twin dropped at source (`pts.pop()`), `#`/`+`/`*` skeletons, `module.exports` with `layWord` and `UPPERISH` | hop-safari `tools/bract/gen.js` lines 224–236, 454–460, 322, 608–616, 636–641, 655, 152–156, 779 | (read) |
| Bract `gen.js` **still carries** the non-Bract terminal modes: `cut`, `taper`, `curl`, `butt` (falls through), `disk`, `exit`, `pebble`, `leaf` dots, `wob`, `shear`, `bend`, `wonk` | lines 260–267, 289–312, 471–474, 501–505, 521–530, 648 | (read) — so the Bract generator can still draw all six round-1 concepts |
| Bract `gen.js` **removed the italic**: no `GI`/`GI_CAPS`, `params(concept, mult)` has no `italic` argument, `xf` has no italic shear | lines 24–25, 260–267, 608–616 | (read) |
| Issue #24 (`flareAmt` dead when `tear` is on) is **not fixed in Bract**; `endMod` still has `mode === "flare" && !P.tear` | gen.js line 308; Driftwood line 347 | (read) — Bract only documents it |
| Issues #22 (fold lumps) and #23 (`quotedblleft` advance) are fixed in Bract | gen.js 454–460 + export.js 33–86 fold guard; build.py 161–169 | (read) |
| Driftwood `driftwood-gen.js` has no fold pin (grep for the pin comment returns nothing), unions with skia-pathops, writes CFF statics, keeps the `wear` pass opt-in, builds Regular/Medium/Bold/Italic/MediumItalic | movingavg-website `tools/driftwood/{driftwood-gen.js,build.py,export.js}` | (read) |
| Driftwood italic = `GI` (lowercase structural overrides incl. `exitStem`), `GI_CAPS` (A T W M R K V U N J Y), `params(concept, mult, italic)` setting `P.italic = tan(10°)`, `xf` shear + 0.95 narrowing, serif length ×0.6 for italic, a sidebearing band (`cMin/cMax`) so hooks overhang, `J` descender rule, extra italic kern pairs in export.js, slanted tick in build.py | driftwood-gen.js 131–195, 300–304, 361, 392, 617–620, 677–683, 691; export.js 32–40; build.py 93 | (read) |
| The 48 Bract guards and their mutations; two survived first time (fold guard returning 0 on unequal-length decimated runs; partner-identity mutation that could not fire because no end has two partners) and were rewritten; the mutation log shows two more survivors fixed during the run (`i`: needed three edits to fire; `overlap`: the raster self-check refused the build first, so the budgets had to be lifted too) | hop-safari `tests/test_bract_font.py`; commit `90a085c` message; the build session's mutation log and harness (reproduced in `references/testing.md`) | (read) |
| Impasse plan review: 13 findings F001–F013, all accepted; diff review: 8 findings (quotedblleft advance; fold guard measured raw only and skipped the first segment; shoot.py ignored Chrome's exit code; master-reproduction test skipped builder-made quote glyphs; branch signature recorded presence not identity; `SOURCE_DATE_EPOCH` setdefault; `bounds.js` wrong module; plan called (700,80) reviewed); re-review: 5 findings (`--masters` bypassed the checks; a 404/fallback-font screenshot passed as evidence; docs again said Bold cannot exceed 35.2px; fold test trusted the exporter's metric; reproducibility test didn't catch setdefault) | hop-safari `docs/plan-display-font.md` §10; the build session's Impasse run records (instructions generalised into `templates/impasse-*-instruction.txt`) | (read) |
| Concept pipeline: round 1 `page-template.html` + `build-page.js` (splices `gen-src.js` + `hop-concepts.js` into `/*GEN*/`, parses the result with `new Function`); round 2 `r2-template.html` adds `/*COLOURS*/`, sticky face picker over mock-ups of three redesigned pages with `img/*.jpg`; round 3 `r3-template.html` adds the "What Fable says" verdict box, `data-face` cards, `burinos` two-cut face switching at `DISPLAY_FROM = 40`, `localStorage` for the picked face. `render()` wraps to `el.clientWidth`, so specs are collected and drawn only after the whole page is assembled (`redraw()` at the end; `document.fonts.ready` redraws the CSS comparison face) | the build session's concept-page sources; hop-safari `tools/bract/concepts/r3-template.html` 315–423; the sketch generator's `render()` | (read) |
| Comparison faces in the artifacts load from Google Fonts (`fonts.googleapis.com`), images from `img/` relative paths | r3 page external refs (measured: only googleapis/gstatic) | (read) |
| Toolchain on the author's Mac: node v26.13.1; Python 3.12.16 with fonttools 4.68.0, brotli 1.2.1, skia-pathops 0.9.2, pillow 12.3.0; Chrome 157 at the macOS application path; `codex` 0.167.2 and `claude` CLIs installed; `frontend-design` plugin 1.1.1 installed; Impasse 0.5.0 installed as a skill; the system Python is 3.9.6; the repo directory did not yet exist; `gh` logged in as windaddict | (measured) |
| Skill-creator guidance: frontmatter `name` + pushy `description` carrying all "when to use"; SKILL.md < 500 lines; `scripts/`, `references/`, `assets/`; reference large files with a TOC; imperative voice; explain why | the installed skill-creator skill's `SKILL.md` | (read) |
| Impasse protocol: host forms its own view first, sends evidence not conclusions, verifies each finding, a rejection needs contradicting evidence, same-provider fallback carries an independence notice, never silently downgrade, consent-gated | the installed Impasse skill's `SKILL.md` | (read) |
| Operator conventions: watch every guard fail, choose the weakest mutation, prefer executing to source regexes, test the shipped thing, a subagent result is a lead until verified, log departures, plan → review → build → review | the operator's global and repo-directory instruction files ("Tests"; "How we work") | (read) |

---

## 1. Decisions (with reasons)

### 1.1 Generator: ship Bract's `gen.js`, generalised, with the italic restored from Driftwood

**Decision.** The shipped `scripts/gen.js` is Bract's generator (every fix listed above) with three changes:

1. **Concepts externalised.** `CONCEPTS` leaves the file; `gen.js` exports a `load(conceptsPath)` or the caller passes concept objects. A project keeps its concepts in `concepts.js` (JavaScript, because angles are written `12 * DEG`). `gen.js` keeps the `DEG` constant exported.
2. **Italic restored** as an opt-in: `GI`, `GI_CAPS`, `exitStem`, `params(concept, mult, italic)`, the italic shear and 0.95 narrowing in `xf`, the ×0.6 italic serif length in `serifPoly`/`diagSerifPoly`, the italic sidebearing band and the `J` rule in `glyph()`, the italic `T −6` spacing term. Ported from `driftwood-gen.js` lines 131–195, 300–304, 361, 392, 617–620, 677–691 **(read)**; the port must preserve pinned sampling (`sampleCounts` runs on the italic skeleton too) and the branch signature. The Bract accented-letter builders already exist; the italic accented builders (Driftwood 235–242) come with them.
3. **Issue #24 fixed properly**: a new concept parameter `dropAmt` (default 0.55, the constant now at gen.js line 437) sets the teardrop swell, and `params()` **throws** if a concept sets `flareAmt` with `tear: true` ("flareAmt has no effect with teardrop terminals; set dropAmt"). A test mutates `dropAmt` and asserts outlines change; another asserts the throw. (The Bract and Driftwood example concepts in `examples/` therefore drop their dead `flareAmt` values, with a note.)

**Why not roman-only.** The operator asked for everything learned from both faces; Driftwood shipped an italic and the code is proven in production; the port is about 120 lines of tested code; without it the skill cannot reproduce one of its two worked examples, and a headline face for a site with blockquotes needs one. **Why opt-in**: italic skeletons differ in structure from roman (single-storey `a`, exit stems), so roman and italic can never share one variable file (no `ital` axis); the italic is a **second variable font** (`Family-Italic-VF.woff2`) whose own masters are compatible with each other under pinned sampling. **Gate:** if the italic path fails the end-to-end smoke run (§6) in a way that needs more than a day, cut it from v0.1.0 to "ported, not wired" and say so in CHANGELOG and README — a decision at the gate, not an omission.

**Caveat to document:** the italic path will be *pipeline-tested* (compat, folds, hairlines, gvar, instancing) by the smoke run but **not design-reviewed** in any shipped font since Driftwood 1.000 (which was static, unioned, unpinned).

### 1.2 Builder: one variable pipeline; statics come from the instancer, not from a union

**Decision.** `scripts/build.py` is Bract's: N masters → `FontBuilder(isTTF=True)` → `varLib.build` → woff2 with `gvar`, `avar`, `fvar`, `gasp`, GPOS kern, GSUB liga, name table, measured vertical metrics, overlapping contours with `OVERLAP_SIMPLE`, all self-checks. It gains `--static OUT_DIR`, which writes static TTF/woff2 instances at each named instance via `fontTools.varLib.instancer` (overlaps retained; flag kept). Driftwood's skia-pathops union + CFF static path is **not** shipped as a build mode.

**Why.** The union produces master-dependent contour structure (plan §1.1, measured: 80 of 128 glyphs incompatible), and it is the thing that turned Bold folds into lumps (#22). One pipeline means one set of self-checks to keep honest. skia-pathops stays as a **measuring instrument** in the raster seam check only. A project that wants statics (older browsers, email, print) gets them from the same reviewed variable font, so what was reviewed is what ships.

### 1.3 Axes are configuration, not code

`wght` range and `avar` map, `opsz` range (or no `opsz`), master grid, named instances, hairline floors per master, size budget, raster budgets, cmap decisions (NBSP→space, U+0027→quoteright), kern set, F010 titles, `SOURCE_DATE_EPOCH`, name-table strings, output paths all move into a per-project `font.json`. `build.py`/`export.js` read it; nothing site-specific remains in the scripts. A one-axis (wght only) build must work: the neutral example uses two axes to exercise the full rectangle, the Driftwood example file shows wght-only roman + wght-only italic.

### 1.4 The repo is the skill directory

Like the Impasse skill (its repo *is* the skill dir, `SKILL.md` at root, `VERSION`, `CHANGELOG.md`, `tests/`, `.github/workflows/ci.yml`) **(read)**. Install = `git clone` into the user's Claude skills directory as `font-design`.

---

## 2. Repo layout and what each file contains

```
font-design-skill/                      → github.com/windaddict/font-design-skill
├── SKILL.md                            the skill (≤ 500 lines; frontmatter + phased workflow + gates)
├── README.md                           human-facing: what, install, requirements, how a run goes, screenshots policy, credits
├── LICENSE                             MIT, "Copyright (c) 2026 John Knox"
├── CHANGELOG.md                        Keep-a-Changelog; 0.1.0 entry lists the inherited fixes (#22 #23 #24, F001–F013, diff R1–R8, re-review 1–5)
├── VERSION                             0.1.0  (SKILL.md frontmatter `metadata.version` and the README badge are tested against it)
├── .gitignore                          .venv/ out/ __pycache__/ *.woff2 *.ttf *.otf *.png (except examples/*/README images: none) .DS_Store
├── .github/workflows/ci.yml            §7
├── requirements.txt                    fonttools==4.68.* brotli skia-pathops pillow pytest
├── package.json                        { "engines": { "node": ">=18" } } — no npm deps; documents the node requirement
├── scripts/
│   ├── gen.js                          the generator (§1.1). Header: WHAT IT'S FOR, origin (Driftwood 67a4e5b → Bract 90a085c, both John Knox), MIT
│   ├── export.js                       masters → one JSON: draw, compat check (points + branch sig), shared-index RDP per edge run, fold guard (raw+decimated), min interior stroke, kern pair list identical across masters, title widths. Reads font.json + concepts.js. Exits non-zero on any incompatibility. `--eps`, `--group roman|italic`
│   ├── build.py                        JSON → variable TTF/WOFF2 + manifest.json; self-checks that fail the build; `--check`; `--static DIR`; `--ttf`; `--masters JSON` (re-checked, never trusted); `--font font.json`
│   ├── bounds.js                       glyph vertical extents (GEN env var honoured; default ./gen.js — the R7 fix)
│   ├── mine-charset.py                 scans built HTML (or a text file of titles) for the characters and the elements the display face sets; reports NBSP count, straight-apostrophe count, `#`/`+`/`*`, accented letters, longest title; emits the `charset` block for font.json
│   ├── mine-sizes.py                   reads a stylesheet's `clamp()`/`rem` font-size rules for the display selectors and reports the size range per selector at 16px and at `--root N%` roots; computes the hairline floor in units for the smallest size ("one CSS px = 1000/size units")
│   ├── shoot.py                        self-terminating http.server + headless Chrome at widths × scales; Chrome located via `$CHROME`, then per-OS defaults (macOS app path, `google-chrome`, `chromium`); fails a shot unless the page and the font were served 200 and Chrome exited 0; `--root N`; `--serve DIR --font-url PATH` instead of hard-coded site paths; minimum width 500 enforced with a message
│   ├── opsz.py + opsz.html             which `opsz` the browser applies under `font-optical-sizing: auto` at given px (row-compare); family/url/title parameterised by query string
│   ├── specimen.py + specimen.html.tmpl renders the review specimen from font.json: real titles at the project's sizes, weights as the site uses them, surfaces (background colours from font.json), comparison faces (optional local woff2 paths or Google Fonts URL), the opsz crossing rows, intermediate instances, kerning row, NBSP-wrap row, quotes/new-glyph row
│   ├── concepts/
│   │   ├── build-page.js               splices gen.js (module.exports stripped) + concepts.js + a content JSON into a template at /*GEN*/, /*CONCEPTS*/, /*CONTENT*/; parses the script with `new Function`; refuses if a placeholder count ≠ 1
│   │   ├── round1-template.html        the spectrum page: audit section (optional), guidelines, "all N side by side" lineup with text input + weight select, one full specimen per concept (surfaces from content JSON), character row, recommendation footer. Neutral copy; CSS variables for the site's colours
│   │   ├── round2-template.html        shortlist on mock-ups: sticky face picker, glance cards per concept, mock pages built from the content JSON (headline slots as `.r[data-t][data-size][data-w][data-min][data-fit][data-lh][data-caps]`), images only from `img/` beside the page
│   │   ├── round3-template.html        head-to-head: adds the verdict box (`#verdict`, filled from content JSON `verdict` field), ranking, two-cut face (`DISPLAY_FROM`), `localStorage` memory, comparison CSS face
│   │   ├── content.example.json        neutral sample content (titles, chapters, lede, colours, image list)
│   │   └── README.md                   how to run each round, publish as an artifact, the constraints (§4.5)
│   └── tests/
│       ├── test_font.py                the font test-suite TEMPLATE (parametrised on font.json; the g–w tests of Bract generalised; §5)
│       ├── test_site_wiring.py.tmpl    the a–f, n–r site tests as a template with `{{ }}` slots (css path, templates glob, preload tag, display selectors), copied into the site repo
│       ├── mutate.py                   mutation harness template: exact-string replacements asserted to match once, pristine copies restored by copyfile, pycache cleared, "RED/GREEN" log, `--only`
│       └── conftest.py                 fixtures: `font` (TTFont of the built woff2), `export` (fresh node export), `cfg` (font.json)
├── templates/
│   ├── font.example.json               every key documented inline (JSON with a sibling `font.schema.json`)
│   ├── concepts.example.js             six-concept spectrum skeleton with the knobs annotated
│   ├── font-record.md                  the record template (bract-font.md's shape: why, how chosen, generator, the variable font, self-checks with exact guarantees, review rounds, what failed, open items)
│   ├── plan.md                         the build-plan template (plan-display-font.md's shape incl. an empty §"Independent review and what it changed")
│   ├── reviewer-brief-audit.md         the site-audit brief (AI tells; what each finding changes for the font)
│   ├── reviewer-brief-concepts.md      the concept judge brief (rounds 1–3; must name how to pick, rank, risks)
│   ├── reviewer-brief-design-round.md  the per-round design-review brief (checklist; rank by visibility at 1× on a real page; name the crop)
│   ├── impasse-plan-instruction.txt    the lens for the plan review (the build session's Impasse instruction, generalised)
│   └── impasse-diff-instruction.txt    the lens for the diff review and the re-review (instr.txt/instr2.txt, generalised)
├── references/
│   ├── process.md                      the nine phases in detail: inputs, outputs, gate, operator questions, who does what (host / strong-model reviewer / Impasse / frontend-design), time budget, stop rules
│   ├── site-audit.md                   AI tells with the hop-safari and movingavg instances as examples; the guard pattern (tests/test_design_audit.py shape); "fix on a branch first" rule
│   ├── guidelines.md                   deriving sizes, the hairline floor, contrast axes vs the body face, weights, case, charset traps, precedent lessons
│   ├── generator.md                    skeleton grammar (S/D/ring, end types s t u x j ''), every parameter with range, effect and interaction (W, nib, thin, thinGrow, pow, xs, swell, wob, track, ends, flareLen, flareAmt, dropAmt, taperLen, cut, serifLen, serifH, serifGrow, dot, leaf, overshoot, beak, tear, pebble, shear, bend, wonk, italic), fit rules, spacing & kerning model, what interpolates linearly and what does not (serifGrow, teardrop, Medium)
│   ├── variable-font-build.md          masters as a full rectangle, avar for the reviewed Medium, opsz semantics and measurement, decimation with shared indices per edge run, the self-check table with EXACT guarantees and what they do not prove (FreeType ≠ CoreText/DirectWrite), reproducibility, size budget, `--static`
│   ├── traps.md                        the checklist (§3), each item: symptom, cause, detection, guard, where it bit
│   ├── review-loop.md                  the round protocol, the checklist, the fresh-reviewer rule, host spot-checks and one mutation per round, stop rule, enlarged-root check, what a screenshot proves
│   ├── concept-pipeline.md             rounds 1–3, artifact constraints, how verdicts get into the page, how the operator picks
│   ├── testing.md                      the suite template explained test by test with its mutation; choosing the weakest mutation; the survivors and why; running mutate.py; site-wiring tests
│   ├── fallbacks.md                    when Fable / Impasse / frontend-design / Chrome / Codex are absent (§8)
│   └── examples/
│       ├── bract.md                    worked example: brief, audit, guidelines, six concepts (parameters), rounds, two cuts, four masters, floors, what failed, review rounds, open items
│       └── driftwood.md                worked example: brief, three rounds, four generated concepts, static family with italic, what failed, the three bugs found later and their fixes
├── examples/
│   ├── neutral/                        the smoke sample (§6): font.json, concepts.js ("Sampler" family, a concept unlike Bract and Driftwood), content.json for round 1, titles.txt
│   ├── bract/                          font.json + concepts.js carrying the Bract text/display parameters (and the six round-1 + round-3 concept parameter sets), README: outcome, NO font files
│   └── driftwood/                      font.json + concepts.js with Driftwood/Tideline/Dune/Windswept parameters, README: outcome, NO font files
└── tests/                              the REPO's own tests (§7): hygiene, frontmatter/VERSION, smoke
```

Why `scripts/tests/` and `tests/` both exist: `scripts/tests/` is what the skill copies into a *site* repo; `tests/` tests the skill itself.

---

## 3. The trap checklist (`references/traps.md`), each with the guard that ships

Each row is "symptom → cause → guard in the shipped code or the suite". All verified in the Bract sources unless marked.

1. **varLib skips incompatible glyphs with a warning and ships them frozen** → structural pre-check in `export.js` (point counts + branch signature incl. partner ids) and `build.py` (`endPtsOfContours` per master); `gvar` test; F013 instancing test (±2 units) at every master.
2. **FreeType autohints a TrueType font with no `fpgm`, snapping glyphs a pixel** (209-level false diffs) → one-instruction `fpgm` in the throwaway raster fonts.
3. **`TTGlyphPen` drops a rounded closing point that lands on the first one, in one master only** → glyphs built verbatim with `Glyph()`/`GlyphCoordinates`; the ring's repeated start point dropped at the source identically in every master.
4. **A fold guard that returns 0 on unequal-length edge runs** → `throw`/`check` on unequal runs; fixture test feeds hand-built edges (clean, first-segment fold, decimated-only fold).
5. **Quote glyphs made in the builder escape every generator test** → cmap pinned to a declared set; quote test re-derives all six from the exported apostrophe at every master, advances exact (#23).
6. **`opsz` units are a browser decision** → `opsz.py` measures; axis endpoints set from the measurement; Safari/Firefox marked unmeasured; `font-optical-sizing: auto` stated in CSS.
7. **Chrome headless lays out at ≥ 500 px** → `shoot.py` refuses narrower widths with a message; 500 is the phone reading.
8. **A reader's enlarged root font size moves rem-sized Bold into opsz territory** → draw the full master rectangle (F003); `shoot.py --root 150`; the record states the region is built, self-checked, not reviewed, if that is the truth.
9. **Wordmark wraps at narrow widths** → `white-space: nowrap` + a 500/667 reading in round 3 of the review.
10. **Straight `'` and NBSP in real titles** → `mine-charset.py` counts them; cmap U+0027→quoteright (tick unmapped), U+00A0→space; tests h, i.
11. **`flareAmt` is dead with `tear: true`** → `dropAmt` + throw (§1.1).
12. **Hairline floors measured on parameters miss the swell and terminals** → floors measured on interior samples (beyond `max(tearL, tapL)`), per master; floors fixed in the test file, not read from the manifest.
13. **Mutations that cannot fire** → `testing.md` lists the three shapes seen here: a mutation blocked by an earlier self-check (overlap flag: lift the raster budgets too), a mutation masked by another mapping (apostrophe: three edits needed), a mutation of a property that no input exercises (partner identity: no end has two partners; mutate the *recording* instead). Rule: ask "what is the weakest change that makes this assertion false, and is it the defect the test is named for?"
14. **`SOURCE_DATE_EPOCH` via `setdefault` makes the bytes depend on who ran the build** → assigned unconditionally; the reproducibility test passes a foreign value in `env`.
15. **A screenshot of a 404 page or a Georgia fallback passes as evidence** → `shoot.py` records every (path, status) and fails the shot unless page and font were both 200 and Chrome exited 0 and the PNG exists (stale PNGs deleted first).
16. **`--masters JSON` trusted** → `load_masters` re-checks signatures and recomputes the fold measure in Python.
17. **Bold reads as another family**: serifs scaled with W (Clarendon) → `serifGrow` (0.35 for Bract; 0.6 was wrong); hairlines scaled with W → `thinGrow` 0.5. **Interpolated Medium ≠ generated Medium** (nonlinear terms) → review Medium at the smallest size in round 1.
18. **Union for shipping keeps folded loops as lumps** (#22) → ship overlaps; union only as a check.
19. **Kerning that does not interpolate** → identical pair list in every master (zeros included); `track` lives in advances, not kerning (F005); word-space pairs; ligature glyphs in the kern set.
20. **Vertical metrics copied from a precedent clip accented capitals** (À reached 947 vs win 940 in the F012 mutation) → measured from every glyph of every master.
21. **Windows drops sub-pixel strokes** → `gasp` 0xFFFF→0x000F; Medium at the smallest sizes; unverifiable from a Mac — say so.
22. **Decimation across a contour's seam or flipping a winding** → RDP per edge run with endpoints kept, ≥ 3 points, signed-area sign checked, raster before/after ≤ budget.
23. **claude.ai artifact CSP**: images only from files published with the artifact (`img/` beside the page); comparison web fonts from Google Fonts worked in the session **(read: the pages reference googleapis)** but must be re-verified at publish; **measure widths after the page is assembled** (an earlier version measured before attachment and clipped every title); **grids must not leave orphan tiles** (choose tile counts that fill `auto-fill` rows at 500/1280/1600).
24. **Name collisions** → check the candidate name against existing typefaces before any file exists (Burin → Bract).
25. **Content traps the charset mine surfaces** (a literal `**Update**`) → fix content or carry the glyph; decide with the operator.
26. **Hard-coded interpreter and Chrome paths** (`.venv/bin/python3`, the macOS app path) → `sys.executable`; `$CHROME` + per-OS search.
27. **CSS `letter-spacing` doubles a display cut's own `track`** → remove it on display rules; test q.
28. **Faux bold/italic** when a requested weight/style is outside the file → recommend `font-synthesis: none` (host view item 9; **(inferred)** not implemented in Bract — list as a recommendation, not a precedent).
29. **Preload needs `crossorigin` even same-origin**, and must precede the stylesheet → test r.
30. **Design lessons** that are not bugs but recur: no gesture on frequent letters (Driftwood's back-lean); terminals from the stroke's own edges, never a shape dropped on the end; a corner-rounding pass is invisible at real sizes; leaf dots read as accents; judge on real titles at real sizes, long ones wrapped at 500 px.
31. **Pillow/FreeType raster budgets are per-machine** → the manifest records what each build measured; CI on two OSes reports differences rather than hiding them (§7).

---

## 4. `SKILL.md` design

### 4.1 Frontmatter

```yaml
---
name: font-design
description: Design, build and ship a custom display typeface for a website as a self-hosted variable web font — a generated, parametric face drawn for the brand, reviewed on the site's real titles at real sizes, with self-checks and mutation-tested guards. Use whenever the operator wants a custom, unique, bespoke or brand typeface, a headline/display/title font, their own font instead of a Google Font, a wordmark face, a logo-derived letterform, or asks to "make a font like Bract/Driftwood"; also when they ask to tune, extend (italic, new glyphs, a weight) or re-review a face built this way. Not for picking an existing font (use frontend-design) or for body text faces.
metadata:
  version: 0.1.0
---
```

### 4.2 Body (≤ 500 lines; imperative; each phase names its reference file and its gate)

1. **Before you start** — say the skill version; classify the change per the operator's process (a site-wide face is a significant change: plan → review → build → review); check tools (`node`, Python ≥ 3.11 venv with the four packages, Chrome, Impasse, frontend-design, the strongest model) and state which are present; read `references/fallbacks.md` for anything missing; ask the operator the opening questions (goal sentence in their words; which site/pages; the body face; brand sources; weights and italic; name candidates; name-table owner and licence; size budget; may concept pages be published as artifacts; consent to send artifacts to Impasse; who deploys).
2. **Phase 1 — Audit the site first** (`site-audit.md`; use `frontend-design` when installed for the aesthetic pass): headless screenshots at 360/500/1280/1600; the AI-tells list; fix the items that change what the font must do, on a branch, each fix guarded; record the audit (template). Gate: operator approves which items are fixed before the font.
3. **Phase 2 — Guidelines from the site** (`guidelines.md`): run `mine-sizes.py` and `mine-charset.py`; write the sizes the face must survive, the hairline floor (units = 1000 × 1 px / smallest size, floor ≈ 0.75 px), contrast axes vs the body face, weights, case, exact charset, precedent lessons. Gate: guidelines written and shown.
4. **Phase 3 — Round 1, the spectrum** (`concept-pipeline.md`): ~6 concepts named for the brand, each a parameter set, closest-to-current first → most organic; render on real titles at real sizes on the site's surfaces; the strongest model reviews and recommends a shortlist and says how to pick. Gate: operator picks the shortlist (or asks for a round 1b).
5. **Phase 4 — Round 2, mock-ups**: shortlist set into mock-ups of the redesigned pages with a face picker; reviewer + frontend-design judge; reviewer revises the leading concept (e.g. Medium for small titles, serifGrow). Gate: operator names the finalists.
6. **Phase 5 — Round 3, head-to-head**: finalists on the mock pages with the picker; verdict and ranking published in the page; targeted fixes sketched (optical-size cut) before committing. Gate: operator chooses the design and the **name** (check collisions).
7. **Phase 6 — Plan the build** (`variable-font-build.md`, `templates/plan.md`): strong model writes the plan; **host forms its own view first**, then Impasse reviews the plan with the generator, precedent build and the site CSS in the artifact (relational claims need both sides); verify every finding against code; amend; record §"review and what it changed". Gate: operator answers the plan's questions.
8. **Phase 7 — Build**: copy `scripts/` into `tools/<face>/`; write `font.json` and `concepts.js`; export, build, read the self-check output; wire CSS/templates; copy and fill the test templates; **watch every guard fail** with `mutate.py`, choose the weakest mutation, record survivors as findings. Gate: suite green, `--check` byte-identical.
9. **Phase 8 — Design-review loop (≤ 6 rounds)** (`review-loop.md`): build → `specimen.py` → `shoot.py` (pages × widths × 1×/2×, plus `--root 150`) → a **fresh** reviewer each round (new subagent context, the brief template, the operator's goal sentence verbatim, the crops) → ranked findings → changes → the host spot-checks two crops itself and runs one mutation of its own → next round. Stop when a round reports nothing visible at 1× on a real page and the suite is green; or at round 6 with remaining items as open items.
10. **Phase 9 — Ship**: Impasse reviews the finished diff (docs and tests included); fix; one re-review; fix its findings without a third review; write the record (`templates/font-record.md`), README, CLAUDE.md; commit (woff2 + manifest + sources together); deploy only on the operator's word; live checks (font served 200, preload, a headless shot of the live page).
11. **Working with little supervision** — a short section: what to decide alone (parameter changes inside the reviewed concept, test mutations, doc wording), what to ask (shortlist, finalists, name, licence, deploy, anything irreversible, any Impasse deadlock), how to report (findings ranked by visibility at 1× on a real page; "a subagent result is a lead until verified"; every departure logged).
12. **Reference index** — one line per file in `references/` saying when to read it.

---

## 5. The test-suite template (`scripts/tests/test_font.py`) and its mutations

Parametrised on `font.json` (masters, floors, axes, instances, cmap decisions, titles). Generalised from Bract's g–w and the review additions **(read: test_bract_font.py)**:

| Test | Asserts | Named mutation |
|---|---|---|
| covers every display character | HTMLParser over built pages for the display selectors (or `titles.txt`) → all in cmap | put `ž` in a built H1 |
| cmap is exactly the declared set | set equality with font.json `charset` | drop U+2018 from the cmap, rebuild |
| NBSP is space; ASCII apostrophe is curly and ≠ tick | cmap + outline inequality | map U+0027 to `quotesingle` **and** disable the two self-checks (three edits; record why) |
| axes and instances | fvar == font.json | opsz max 72 |
| every contoured glyph varies | gvar entry | delete `o`'s gvar with the self-check off |
| each master location reproduces its exported outlines (F013) | ±2 units, advances exact | build one master from another's outlines |
| quote glyphs follow the apostrophe at every master | re-derived in the test | restore Driftwood's `quotedblleft` advance |
| Medium is the reviewed weight (avar) | 0.333→0.6 | drop the map |
| kerning and advances at every reviewed location (F005/F010) | hand pairs, every pair, word space, title widths; (500,40) within a unit of the mix | zero display kerns; drop `2*track` from space |
| hairlines clear the floor (F009) | manifest ≥ floor, export ≥ floor, equal; gasp present | lower the manifest to 40; drop gasp |
| no edge folds back | exporter figures ≤ thresholds | (fixture) hand-built folds, first segment and decimated-only |
| under budget | woff2 ≤ budget | `--eps 0` with the budget lifted |
| no glyph exceeds win metrics (F012) | every master | return the precedent's constants |
| glyphs declare overlaps | flag on every contoured glyph | clear the flag, disable the flag check **and** lift the raster budgets |
| manifest matches the shipped bytes and sources | sha256 | edit a comment in gen.js |
| name table | family/copyright/licence/vendor from font.json | rename the family |
| build is reproducible | `--check` with a foreign `SOURCE_DATE_EPOCH`, `sys.executable` | `Math.random()` in an advance |
| **new:** `dropAmt` changes outlines; `flareAmt`+`tear` throws | export twice | revert the throw |
| **new (italic group, if wired):** italic masters compatible and instanced; `post.italicAngle`, `fsSelection` italic bit; slanted tick | same checks over the second file | build italic from roman JSON |

`test_site_wiring.py.tmpl` carries a–f, n–r (stylesheet declares one variable face with a weight range; every url has a file; nothing names the old face; old files gone; shipped fonts tracked; served by the static config; fluid sizes inside the opsz axis; small titles Medium; no letter-spacing on display rules; preload in every template and page). These are site tests and live in the site repo.

`mutate.py` template: pristine copies by `copyfile`, exact-string replacements asserted to match once, `__pycache__` cleared, RED/GREEN log, restores and re-greens after each. `testing.md` documents the survivors from Bract verbatim as worked examples.

---

## 6. Testing the skill before publishing (on this Mac)

`scripts/smoke.sh` (also the manual pre-publish run):

1. `python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt` (Python 3.12 is at `/opt/homebrew/bin/python3.12` **(measured)**; system 3.9 is not used).
2. `node scripts/export.js --font examples/neutral/font.json out/masters.json` — the **"Sampler"** face: a concept unlike both precedents (proposal: upright low-contrast bracketed serif, `nib 0`, `thin 0.6`, `pow 1.2`, `W 100`, `serifLen 0.5`, `serifH 0.6`, `beak true`, `tear false` with `flareAmt 0.2` so the flare path is exercised too, `serifGrow 0.4`, `thinGrow 0.6`), four masters (wght 400/700 × opsz 24/72) so the full-rectangle path, avar, and opsz are all exercised; plus the italic group if wired.
3. `.venv/bin/python3 scripts/build.py --font examples/neutral/font.json --masters out/masters.json --static out/static` — all self-checks must pass; manifest written to `out/`.
4. `.venv/bin/python3 -m pytest scripts/tests/test_font.py --font examples/neutral/font.json` green, then `scripts/tests/mutate.py --font … --all` must report every mutation RED and restored.
5. `node scripts/concepts/build-page.js --template round1 --concepts examples/neutral/concepts.js --content examples/neutral/content.json out/round1.html` — parses; then `shoot.py --serve out --pages round1.html --widths 500 1280` renders it in Chrome; open the PNGs and look.
6. `specimen.py` + `shoot.py` on the built woff2 at the sample's sizes; `opsz.py --px 24 48 72` must report an unambiguous mapping.
7. `build.py --check` byte-identical on a second run; `--static` instances load in fontTools.
8. Skill-triggering check (skill-creator's description optimisation, scaled down): 6 prompts that should trigger (e.g. "I want a unique headline font for my site", "make us a wordmark face from the logo", "replace Playfair with something of our own") and 4 that should not ("pick a Google Font for the body", "fix the kerning CSS") — run with the skill present and record hits/misses in `tests/trigger-cases.md`; adjust the description.
9. Dry-run SKILL.md end to end against the neutral example in a fresh session, following only the skill, no memory of this session (the operator or a subagent): note every place it had to guess.

---

## 7. CI (`.github/workflows/ci.yml`)

Matrix `ubuntu-latest` and `macos-latest`, Node 22, Python 3.12:

- `ruff check scripts/ tests/`; `node --check` on every `.js`.
- `pytest tests/` — the repo's own tests: (a) hygiene: no home-directory paths, session scratch paths or temp-directory names, personal email addresses or session links anywhere in the tree, and no `.woff2`/`.ttf`/`.jpg`/`.png` files; (b) `VERSION` == frontmatter `metadata.version` == README badge; (c) SKILL.md ≤ 500 lines and every `references/*.md` it names exists; (d) every reference file > 300 lines has a TOC; (e) `font.schema.json` validates the three example `font.json`s; (f) `concepts.example.js` and the three `examples/*/concepts.js` load and every concept passes `params()` (which also exercises the `flareAmt`+`tear` throw on a negative fixture).
- Build the neutral sample end to end (steps 2–4 of §6, no Chrome) **with raster checks on** — Pillow wheels bundle FreeType on both OSes **(inferred: standard for manylinux/macOS wheels; verify on first run)**; the manifest's measured raster diffs are uploaded as an artifact so a Linux-vs-macOS difference is visible. If Linux exceeds a budget, the fix is a per-OS note and a raised sample budget *with the measured number recorded*, never a disabled check.
- **No Chrome in CI** for v0.1.0: `shoot.py`/`opsz.py`/specimen rendering are local-only (`smoke.sh --full`). Reason: the browser evidence is about CoreText on the reviewer's machine anyway; a Linux Chrome would add a third rasteriser without a reviewer to read it. Open question §10.

---

## 8. Fallbacks (`references/fallbacks.md`)

- **No Fable / strongest model:** use the strongest model the Agent tool offers; if none above the host, run the review in a **fresh subagent context** of the host model and label every verdict "same-model review — breadth, not independence". Never let the builder's own context be the reviewer.
- **No Impasse:** do not skip the gate silently. Offer three options and ask: install Impasse; a fresh-context host review with the Impasse reviewer stance pasted from `templates/impasse-*-instruction.txt` and labelled as same-provider; or proceed with the operator's explicit "skip the independent review" recorded in the plan's review section. (This mirrors the operator's standing rule: "If Impasse cannot run — stop and ask.")
- **Impasse present but no Codex:** Impasse's own ladder applies (same-provider with disclosure); surface the `independence_notice`.
- **No frontend-design plugin:** `site-audit.md` carries the calibration list (the plugin's five generic-design traits plus the hop-safari/movingavg tells) so the audit still runs; say the aesthetic pass was unaided.
- **No Chrome:** render the specimen with Pillow/FreeType (`specimen.py --raster`) and state that it proves FreeType rendering only; the design review cannot stop on "no defect at 1× on a real page" without a browser — the loop ends as "not browser-reviewed", an open item.
- **No claude.ai artifact publishing:** the concept pages are self-contained HTML; open them locally or serve them; the operator publishes if they want the artifact.
- **Linux host:** Chrome via `$CHROME`/`google-chrome`; everything else identical; raster budgets may differ (trap 31).

---

## 9. Portability and publication checklist

**Portability.** No absolute paths (`HERE`-relative, `--font` paths); Chrome discovered; `sys.executable`; `SOURCE_DATE_EPOCH` from font.json; node ≥ 18 (uses `Object.fromEntries`, optional chaining — **(inferred)**: confirm with `node --check` under 18 in CI if cheap, else document 20+); Python ≥ 3.11 (f-strings with `=`, `removesuffix`); fonttools pinned `4.68.*` (varLib/instancer behaviour the checks were calibrated on), brotli, skia-pathops, pillow unpinned minors; macOS vs Linux: Chrome path, FreeType build (budgets), `python3.12` location; no `/Applications` outside the Chrome search list.

**Before `gh repo create windaddict/font-design-skill --public`:**
1. `grep -rn` for the author's home path, the session scratch and temp-directory names, the session id, personal and company email addresses and session links → zero hits (`tests/test_hygiene.py` holds the list, built from pieces so it does not match itself).
2. No site content beyond what the operator allowed: no `img/*.jpg`, no built HTML from either site, no `.woff2`/`.ttf` from either face, no Fable verdict prose copied from the private concept pages (the worked examples paraphrase and quote parameters/numbers only; a few public titles like "Hop Safari" are fine as examples of NBSP/apostrophe traps — ask the operator, §10).
3. The round-1/2/3 templates carry **neutral** sample copy and `content.example.json`; the hop-safari copy stays out.
4. Licence headers on `gen.js`, `export.js`, `build.py`, `shoot.py`, templates: "Copyright 2026 John Knox. MIT. Derived from the author's Driftwood (movingavg.com, commit 67a4e5b, 2026-11-14) and Bract (hopsafari.com, commit 90a085c, 2026-11-15) generators." `LICENSE` MIT with "John Knox" (not Moving Average Inc., per the operator).
5. The Impasse instruction templates contain no site names.
6. `README.md` screenshots policy: the repo ships **no screenshots** (none would be neutral and the review PNGs are not tracked); the README explains how to produce them. If the operator wants one hero image later, it must be of the neutral Sampler face.
7. `CHANGELOG.md` 0.1.0 and `VERSION` agree; CI green on both OSes; `smoke.sh --full` run on this Mac with its log pasted into the PR/commit message.
8. The repo's `.github` has no workflow secrets; Impasse consent is never committed (`.gitignore` as Impasse's).

---

## 10. Order of work and parallelism

0. **Operator decisions** (§11 questions) and this plan through Impasse (host view written first; artifact = this plan + `gen.js`, `export.js`, `build.py`, `test_bract_font.py`, Driftwood `driftwood-gen.js`/`build.py`, the r3 template — both sides of every relational claim). Amend; record in the plan's review section.
1. **Scaffold** (serial, ~1 h): repo, LICENSE, VERSION, CHANGELOG stub, .gitignore, requirements, CI skeleton, `font.schema.json`, `font.example.json`.
2. **Three parallel streams** (non-overlapping outputs; the JSON contract between export and build is Bract's current shape, frozen at step 1):
   - **A. Generator + exporter**: generalise `gen.js` (concepts out, `dropAmt`, throw), port the italic, `export.js` reads font.json/concepts.js and `--group`; `bounds.js`.
   - **B. Builder + test templates**: `build.py` reads font.json, `--static`, `--font`; `test_font.py`, `test_site_wiring.py.tmpl`, `mutate.py`, `conftest.py`.
   - **C. Review and concept tooling**: `shoot.py` (Chrome discovery, `--serve`), `opsz.py`/`.html` parameterised, `specimen.py` + template, the three concept templates neutralised + `build-page.js` + `content.example.json`, `mine-charset.py`, `mine-sizes.py`.
   - **D (parallel with A–C, docs):** `references/*.md` drafts and the `templates/*.md` briefs from the records read today; `generator.md`'s parameter table is re-verified against the final `gen.js` at step 4.
3. **Neutral example + smoke** (after A, B, C): `examples/neutral/`, `smoke.sh`, fix what breaks; **italic gate** decided here.
4. **Worked examples** (`examples/bract`, `examples/driftwood`, `references/examples/*.md`) and `SKILL.md` (after 2D and 3, so pointers are real).
5. **Repo tests + CI** green on both OSes; trigger-case check; dry run of SKILL.md.
6. **Impasse reviews the finished tree** (the whole repo is the diff; docs and tests included); fix; one re-review; fix without a third review.
7. **Publication checklist (§9)**, commit, `gh repo create --public`, add the row to the operator's repo-directory instruction file (his convention), optional clone into the user's Claude skills directory as `font-design`.

Docs to write: `SKILL.md`, `README.md`, `CHANGELOG.md`, the eleven `references/*.md`, the nine `templates/*`, `scripts/concepts/README.md`, three `examples/*/README.md`.

---

## 11. Risks and open questions for the operator

**Risks**
- **Italic scope** (§1.1): the port is tested code but has never run under pinned sampling or the fold pin; it may surface new incompatibilities (e.g. `exitStem` curves with the Bold pen folding). Mitigated by the gate; worst case v0.1.0 ships roman-only with the italic tables present and documented as unwired.
- **Pillow/FreeType budgets differ on Linux** → CI may be red on first run for a non-defect; the plan is to record and raise with the measured number.
- **Google Fonts in claude.ai artifacts**: worked in this session's pages **(read)**, but the CSP claim in the brief says images only from published files; whether external stylesheets stay allowed is **(inferred)** — re-verify at first publish; the templates must degrade (Georgia) if blocked.
- **fontTools pin**: `4.68.*` is what the checks were calibrated on; a user on a newer fontTools may see IUP-rounding differences in the F013 ±2-unit bound.
- **Same-author derivation**: all forked code is John Knox's; no third-party licence issue. Bodoni Moda/Newsreader reference fonts (OFL) are **not** shipped; the specimen takes comparison faces as paths or URLs.
- **Skill name**: `font-design` could collide with a future official plugin skill; `font-design-skill` as the repo name is unambiguous.
- **Review cost**: six design rounds with a fresh strong-model reviewer each round is the expensive part; the skill must say so up front and let the operator cap rounds.

**Questions**
1. Italic in v0.1.0 as planned (restore + gate), or roman-only with italic documented as future work?
2. May the worked examples quote a handful of public hopsafari.com/movingavg.com titles as charset-trap illustrations, or should they use invented titles only?
3. Should the Bract and Driftwood **six-concept parameter sets** (Foil, Burin, Blind, Field, Cone, Bine; Driftwood, Tideline, Dune, Windswept) ship in `examples/`? (Planned: yes, parameters only.)
4. CI: no Chrome (planned), or add a Linux Chrome job that at least proves `shoot.py`/`opsz.py` run end to end?
5. `font-synthesis: none` as a standing CSS recommendation in the site-wiring template (not in Bract today)?
6. Name-table defaults for projects built with the skill: "Copyright <year> <operator>", licence "for use on <site> only" — or leave the licence field blank and ask every time?
7. Should the skill also install itself for Codex (an `AGENTS.md` + install script, as Impasse does), or Claude Code only for v0.1.0?
8. The operator's repo-directory table: add `font-design-skill/` with remote `windaddict/font-design-skill`? (Planned: yes, at publication.)

---

### Critical Files for Implementation
- hop-safari `tools/bract/gen.js` — the generator to generalise (concepts out, `dropAmt`, italic port target) → `scripts/gen.js`
- hop-safari `tools/bract/build.py` — the builder to parameterise with `font.json`, plus `--static` → `scripts/build.py`
- hop-safari `tools/bract/export.js` — the exporter (compat check, shared-index RDP, fold guard, kern list) to make config-driven → `scripts/export.js`
- hop-safari `tests/test_bract_font.py` — source of the test-suite template and its mutations (with the build session's mutation harness as the harness template) → `scripts/tests/`
- movingavg-website `tools/driftwood/driftwood-gen.js` — lines 131–195, 300–304, 361, 392, 617–620, 677–691: the italic to restore
- hop-safari `tools/bract/concepts/r3-template.html` (and the build session's round-1 and round-2 templates and their builders) — the three concept-page templates to neutralise → `scripts/concepts/`
---

## 12. Operator decisions (2026-11-15)

The operator asked for the skill to run with little supervision until the finished repo has been
reviewed, so the host settled section 11's questions on the plan's own recommendations. Each is
reported to the operator at that gate and can be reversed before publication.

1. Italic: restore it, behind the smoke-run gate in 1.1.
2. Worked examples may quote a few public titles from hopsafari.com and movingavg.com as
   character-set traps. Neutral templates use invented copy.
3. Both six-concept and four-concept parameter sets ship in `examples/`, parameters only.
4. CI runs no Chrome in v0.1.0.
5. `font-synthesis: none` is a recommendation in the site-wiring template, marked as not used by Bract.
6. Name-table copyright and licence: no default; the skill asks every time.
7. Claude Code only for v0.1.0; Codex install is future work.
8. Add the repo to the operator's repo-directory table at publication.
Earlier operator decisions: MIT licence, "Copyright (c) 2026 John Knox"; parameters and docs from both
faces, no font files; repo `windaddict/font-design-skill`, skill name `font-design`, public.
This plan file contained absolute paths from the author's machine; they were scrubbed before publication (2026-11-15), and `tests/test_hygiene.py` keeps them out.

## 13. Independent review (Impasse, Codex, 2026-11-15) and what it changed

15 findings; each checked against the code by the host; all accepted. Where this section conflicts
with an earlier one, this section wins.

| # | Finding | Checked | Change |
|---|---|---|---|
| F001 | The concept pages call `render()`, which Bract's `gen.js` does not have (only the sketch copy `gen-patched.js:772` does) | read | Ship a browser module `scripts/render.js` (from `gen-patched.js` `render`/`layWord` drawing) that the concept-page builder splices in; every round is executed in Chrome in the smoke run, not only parsed. |
| F002 | Config-driven tests can agree with a faulty `font.json` | read, `HAIRLINE_FLOORS`, `EXPECTED_CMAP` are fixed in Bract's test | Reviewed expectations live in a separate `requirements.json` (floors, required characters, axes, instances, titles) written at the guideline phase and changed only with the operator; tests compare the built font against it. The mutation set includes editing `font.json` (dropping an axis, a character, lowering a floor) and must go red. |
| F003 | One-axis builds are claimed but untested; `build.py` hard-codes `axes[1] == opsz` and the four master names | read, `build.py:428` | `build.py` derives axes and masters from config; the smoke run and CI build three fixtures: two-axis roman (neutral), wght-only roman, wght-only italic. |
| F004 | Italic naming, style linkage and CSS wiring unspecified | read, `build_master` sets Regular/fsSelection 0x40\|0x80 | Specify italic name IDs (subfamily "Italic", typographic subfamily), `post.italicAngle`, `fsSelection` italic bit, `macStyle`, file name, `@font-face { font-style: italic }`; test the file's metadata and that a page selects it (`document.fonts.check` and computed font in Chrome). Unwired italic is not advertised. |
| F005 | `dropAmt` covers only the outer L/R swell; the teardrop also uses 0.28 (inner) and 0.3 (S side) | read | `dropAmt` scales the whole teardrop (all three constants by `dropAmt/0.55`); tests for L, R and S cases. |
| F006 | `shoot.py` cannot tie a font request to one of three concurrent Chrome jobs, and 200s do not prove the face was used | read, `ThreadPoolExecutor(--jobs 3)` | Each shot gets a unique query token on its page URL and font URL (`?shot=<id>`); responses are matched per token; the page runs a sentinel check (`document.fonts.check('16px "<Family>"')` and a width comparison against the fallback) and writes the result into the DOM, which Chrome dumps with `--dump-dom` alongside the PNG; a shot fails without it. |
| F007 | Phase 1 asks for 360px screenshots; `shoot.py` refuses under 500 | plan text | The audit uses an iframe wrapper page at 360 (the method Fable used: measure `scrollWidth` vs `clientWidth` inside a 360px iframe) shipped as `scripts/narrow.html`; screenshots stay ≥ 500. |
| F008 | Only round 1 is smoke-tested | plan text | Neutral content and local images for all three rounds; each round built and run in Chrome in the smoke run, including a face switch and a font-load assertion (dumped DOM). CI runs a Linux Chrome job for the concept pages if Chrome is installable on the runner; otherwise local-only, stated. |
| F009 | Concept templates build `innerHTML` from content; `esc()` does not escape quotes | read, `r3-template.html:337` | Templates use `textContent`/`setAttribute`; content JSON embedded via a `<script type="application/json">` block with `<` escaped as `<`; image paths validated as `img/<name>.(jpg|png|webp)`; an adversarial fixture (quotes, `</script>`, `<img onerror>`) must render inertly. |
| F010 | Publication rights: forked code ownership not evidenced | plan text; Bract's font licence is site-only | `NOTICE.md` records provenance of each source (Driftwood generator, movingavg.com; Bract, hopsafari.com) and separates the MIT licence of the code from the fonts and site content (none shipped). **Publication blocker: the operator confirms they hold the rights to relicense both generators under MIT (Driftwood lives in a company repo).** |
| F011 | No path for a character the skeleton table lacks | read, `export.js:31`, `glyph()` returns null | `export.js --charset` (from `requirements.json`) fails early listing missing code points; `references/generator.md` documents adding a skeleton or a composite rule; a test builds a fixture requiring `@` (absent) and asserts the failure names U+0040. |
| F012 | `--static` outputs only checked to load | plan text | For each static: no `fvar`/`gvar`, outlines and advances equal the instancer's at that location, overlap flag kept, name/weight class/italic metadata match; render one with Pillow. Statics are documented as for modern renderers (overlaps kept). |
| F013 | ruff not in requirements; Node ≥ 18 untested | plan text | Pin `ruff` in `requirements-dev.txt`; CI matrix tests Node 20 (stated minimum) and 22. |
| F014 | The export JSON contract changes (axes, groups) but is "frozen" before parallel work | plan text | Step 1 designs `export.schema.json` with the three fixtures; build serially until the schema validates them, then parallelise. |
| F015 | No publication blockers; post-review fixes skip re-checks | plan text | SKILL.md lists blockers (failed self-check or test, browser evidence missing, a required glyph missing, licence/rights unconfirmed, a defect visible at 1×). After material post-review fixes, rerun the affected tests and smoke steps; record. The skill repo itself follows the same rule. |
