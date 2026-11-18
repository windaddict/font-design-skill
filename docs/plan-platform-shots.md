# Plan: font-design 0.3 — cross-platform rendering shots on GitHub-hosted runners, and a comparison tool

Status: a plan, written 2026-11-17 on branch `platform-shots` (base: `3c4e8d9`, the 0.2.0 release plus the
unreleased lint changes in `CHANGELOG.md` "[Unreleased]"), **revised the same day after the cross-provider
Impasse review** (section 14: fourteen accepted findings plus one host finding, every one checked against the
code or the plan before the body changed) **and after three operator rulings** (section 12). Nothing in it is
built. Markers: **(read)** = checked against the named file at the lines given; **(measured)** = run here,
with the command named; **(inferred)** = not verified, the implementer checks it first. The operator's goal,
verbatim: *"add the ability to use GitHub CI to check font rendering across platforms to the font-design
skill so it can be used in the future."*

**The architectural decision:** the evidence model stays `scripts/shoot.py`'s. Its proofs (the shot token,
the served-200 record, the cookie, the sentinel beacon, the element and italic probes, the missing-character
probe) live in the **server and the injected sentinel**, not in Chrome, so the same instrument runs on a
Windows, macOS or Linux runner once two POSIX seams are closed (section 2.2), **and the same proofs hold for
Firefox** once a second launcher points it at the same tokenised URL (section 2.4, built in this change by
operator ruling 1). The site repo's one-off Playwright script (`movingavg-website/tools/font-shots/shoot.py`)
is the lead for what to record (OS, browser version, Windows font-smoothing registry values, one browser's
failure not losing the other's shots) and not for the mechanism: its proof is `document.fonts` status alone,
which the skill's header names as the check a fallback-serif screenshot passes **(read: `scripts/shoot.py`
item 4, lines 46–50)**. WebKit stays **designed, not built** (section 2.5).

**What the review changed most:** the compare job's artifact paths did not exist as written (F001); nothing
built or staged the served root (F002); the Windows teardown design had the kill order backwards and missed
two blocking points (F003); the specimen is 5,368 px tall at 1280 and a 2400 px shot would have cut most of
its rows (F004); document coordinates are not PNG coordinates once a page has scrolled (F005); positional
row keys could pair different elements across legs (F006); a bad leg stopped the whole comparison (F007); and
a site whose font the skill did not build had no way to run (H1). Each is in the body now.

Contents

0. What was verified, and what the one-off taught
1. The hard constraints (one optional dependency, backward-compatible outputs, testing, docs, honesty)
2. Decision 1 — architecture: `shoot.py` on every runner, Chrome by its CLI and Firefox by Playwright; WebKit designed
3. Decision 2 — what gets shot: the specimen (when there is a `font.json`) and the named pages, at 1× and 1.25×
4. Decision 3 — `scripts/compare-shots.py`: one image per row, every leg at a fixed zoom
5. Decision 4 — the workflow template, how the site is served, cost, the skill's own CI
6. Decision 5 — where it enters the process, the blockers, the "not checked on Windows" wording
7. Tests, each with the mutation that turns it red
8. Docs in the same change
9. Version
10. Acceptance runs
11. Risks, and what is out of scope
12. Operator rulings (the former questions, answered)
13. Work items
14. Plan review reconciliation (Impasse, cross-provider, 2026-11-17)

---

## 0. What was verified, and what the one-off taught

| Claim | What the code or the run says | Status |
|---|---|---|
| The one-off counts a shot only if `document.fonts` shows ≥ 1 loaded face of the family and none in error | `tools/font-shots/shoot.py` lines 74–79 (`PROOF_JS`) and 110–116: `loaded` and `failed` lists; the shot is skipped and recorded as a failure otherwise | (read) right. The skill's `shoot.py` header, item 4, says why this alone is weak: `check()` is true for a face in `error` and for an undeclared family, so it adds the width comparison and the element probe |
| The one-off keeps one browser's shots when the other crashes, and exits 1 | lines 140–147: each browser in its own `try`, the exception appended to `failures`; lines 152–154: exit 1 when `failures` | (read) right |
| It records OS, browser versions and the Windows FontSmoothing registry values | lines 82–96 (`smoothing()` reads `FontSmoothing`, `FontSmoothingType`, `FontSmoothingGamma`, `FontSmoothingOrientation` from `HKCU\Control Panel\Desktop`), 103 (`browser.version`), 138 (`platform.platform()`) | (read) right; the registry read is 15 lines of stdlib (`winreg`) and ports as is. The operator's run read `FontSmoothingType` 2 (ClearType) and orientation RGB; `FontSmoothing` is the on/off flag (`"2"` = on), so the label must come from `FontSmoothingType` (F014) |
| It shoots at device scale 1.0 and 1.25 | line 129: `--scales` default `[1.0, 1.25]`, `type=float`; line 106: `device_scale_factor=scale` | (read) right. The skill's `shoot.py` takes `--scales` as `type=int` (line 826) and names files `@{scale}x` (line 884): 1.25 is refused today |
| The Windows run took about 1.3 minutes | `gh run view 44192132836`: job `shots` started 22:39:17Z, completed 22:40:30Z (73 s), conclusion success | (measured) |
| `windows-latest` is Windows Server 2025 with Chrome and Firefox preinstalled | `actions/runner-images` README: `windows-latest` → Windows Server 2025; its image readme (version 20261111.331.1): Google Chrome 157.0.8103.79, Firefox 160.0, Python 3.12.10, Node 22 | (read, through `gh api` on 2026-11-17). The operator's run reported Chrome 156: an earlier image; the version drifts with the image, which is why `meta.json` must record it per run. The Firefox leg uses Playwright's own Firefox, not the image's (section 2.4), so its version is pinned by `playwright==1.64.1` |
| `macos-latest` and `ubuntu-latest` carry Chrome | `macos-latest` → macOS 26 arm64 (26.7.2): Chrome 156.0.8078.80, Safari 27.2, Firefox 159.0, system Python 3.15.2; `ubuntu-latest` → 24.04.5: Chrome 157.0.8103.50, Chromium 157, Firefox 160.0, Python 3.12.3 | (read, same source). The skill's CI already uses `macos-latest` and `ubuntu-latest` **(read: `.github/workflows/ci.yml` line 51)** and installs its own Chrome on Ubuntu through `browser-actions/setup-chrome@v1` (lines 99–105) |
| Actions minutes are free on public repos; private repos pay per OS | GitHub's billing page: standard hosted runners in public repositories are free; private: Linux 2-core $0.006/min, Windows 2-core $0.010/min, macOS 3–4 core $0.062/min; included usage $12/month (Free), $18 (Pro, Team), expressed as money not minutes; artifact storage 500 MB (Free), 1 GB (Pro), 2 GB (Team), shared with Packages | (read, through WebFetch on 2026-11-17: a summary, so the implementer re-reads the page before the figures go into the template header). The three OS rates sum to $0.078 per minute of a three-leg run (F015) |
| `playwright==1.64.1` exists and needs no npm | PyPI JSON: uploaded 2026-10-22T16:29:58, `requires_python >=3.10`, platform wheels for macOS (x86_64, arm64, universal2), manylinux (x86_64, aarch64), Windows (win32, amd64, arm64); latest is 1.65.2 (2026-11-14) | (measured: `curl https://pypi.org/pypi/playwright/1.64.1/json`). That the wheel carries the Node driver so `pip install` needs no npm is (inferred) from the per-platform wheel names and the one-off workflow, which installs nothing else **(read: `windows-font-shots.yml` lines 22–25)** |
| The skill's `shoot.py` runs on native Windows | `subprocess.Popen(..., start_new_session=True)` (line 617) is **ignored** on Windows (CPython 3.12 `subprocess.py` line 1445: the Windows `_execute_child` takes `unused_start_new_session`) **(read)**; `kill_group()` calls `os.killpg` (line 651), Unix-only, so a hang or a teardown kill on Windows would raise `AttributeError` **(inferred: checked only that `killpg` exists on this Mac)**; `run_chrome()` ends only when the exit code is known **and** stdout has hit EOF (line 629, `if rc is not None and eof.is_set()`), which a surviving helper that inherited the pipe prevents **(read)**; the profile `TemporaryDirectory` (line 677) is cleaned on `with`-exit, outside the `except OSError` that covers only the launch (lines 692–697), and `ignore_cleanup_errors` exists in 3.10+ `tempfile` **(read: CPython 3.12 `tempfile.py` line 939)**. `find_chrome()` already searches `%ProgramFiles%\Google\Chrome\Application\chrome.exe` (lines 316–325); `check-env.py` refuses native Windows only as a platform line (lines 55–61), which the workflow does not run | (read) three Windows seams in the teardown (F003) and one fractional-scale seam; all small |
| The shots job needs no pip install for the Chrome leg | `scripts/shoot.py`'s module-level imports are all standard library (lines 136–155); Pillow is imported inside `crop_bands()` only (line 793) and `--bands none` skips it (`parse_bands`, line 777). `specimen.py` imports fontTools inside `cmap_of()` (line 137), so the specimen step needs `fonttools` and `brotli` | (read) |
| The specimen is far taller than a default shot | `specimen.py` lines 251–252: "last ink at 5,368 px at 1280 wide, past 9,000 at 500"; `shoot.DEFAULT_HEIGHT` is 2400 (line 159) and the proof rows are placed first so they land inside it | (read). A platform shot of the specimen needs `--height` large enough for every row (F004, section 3) |
| The skill already copies the whole `scripts/` folder into the site | `tests/test_copy_into_site.py` header: "copy the WHOLE scripts/ folder (tests included) to tools/<face>/scripts/" | (read). So the workflow can run the **site's own copy**; but a site whose face the skill did not build (movingavg.com's Driftwood: five static woff2 files, no `font.json`) has no specimen to render and loads several font files per page (H1, sections 3 and 5.1) |
| `shoot.py` writes no machine-readable result, and takes one `--font-url` | results are JSON lines on stderr (lines 909–910); `--font-url` is a single value (line 830) checked as one path (lines 720–728) | (read). Section 2.2 adds `--meta FILE` and makes `--font-url` repeatable |
| The specimen's rows can be located without pixel offsets | the proof rows carry `data-fd-spacing`, `data-fd-legibility`, `data-fd-junctions` (`specimen.py` 263–272) and the italic rows `data-fd-probe="italic"` (325–326); the other rows are bare `<p class="f">` (`row()`, lines 111–113) | (read). Section 3 gives every family row a `data-fd-row` key and section 2.2 has the sentinel report each key's box |
| A viewport screenshot is not the document | Chrome's `--screenshot` with `--window-size` captures the window; `getBoundingClientRect()` is relative to the viewport, and `scrollY` is the offset of that viewport in the document | (read: MDN semantics, from memory; F005 accepted). Section 2.2 records viewport coordinates and the scroll offset separately and refuses a scrolled shot |
| `download-artifact@v4` with `pattern` and `merge-multiple: false` puts each artifact under `<path>/<artifact-name>/` | the action's README | (read by the reviewer; F001 accepted; the implementer re-reads the README for the pinned major). Section 5.1's paths follow it |
| `diff.py` has crops and panels to reuse | `compare()`, `triptych()` (lines 152–180), `slug()` (181), `INK_BELOW` (60), `markdown()` (260), `need()` (66–75) | (read). The comparison tool reuses `slug()`, `need()` and the panel-stacking shape; the pixel-difference logic does not apply |
| `SKILL.md` has room | 478 lines against the 500-line test **(measured: `wc -l`)**; the `compatibility` line is 408 characters against the 500 test (`tests/test_versions_and_skill.py` line 67) **(measured: `wc -c`)** | this plan adds at most twelve lines and about ninety characters |
| The docs tests scan Markdown only | `tests/test_docs_commands.py` `DOCS` (lines 20–21) | (read). A YAML template's `run:` lines are not checked by anything today; section 7 adds the guard, importing `registered_flags()` from that test file |
| `test_every_workflow_parses_as_yaml` covers only `.github/workflows/*.yml` | `tests/test_ci_workflow.py` line 81 | (read); section 7 extends it to `templates/*.yml` |
| A `workflow_dispatch` needs the file on the default branch for a first run | `.github/workflows/record-baseline.yml` header, lines 17–19, and its `pull_request` trigger limited by `paths` | (read); section 5.2 does the same |
| The "optional, SKIPPED, NOT PASSED" conventions | `fontbakery-gate.py` exits 3 and prints `SKIPPED, NOT PASSED` when not installed (line 211); `check-env.py`'s `check_fontbakery()` (215–229) reports `optional: … not installed` with the pip command through `importlib.util.find_spec` | (read). The Firefox leg follows both |

What the one-off taught, carried into the design: Chrome on Windows drew with subpixel (coloured)
antialiasing and visibly lighter than macOS Chrome; Firefox on Windows drew grayscale and close to macOS;
comparing them meant hand-cropping the same row at 7× from each OS's PNG; a runner is not a reader's laptop;
Playwright 1.49.1's bundled Firefox 132 crashed on `windows-latest` and 1.64.1 fixed it, while Firefox from
1.64.1 still fails on the author's Mac ("Could not find profile folder", unexplained). All five are
**(operator's measurements of 2026-11-17, not re-run here)**.

---

## 1. The hard constraints

### 1.1 One optional dependency, in its own file; the skill's venv is unchanged

`requirements.txt` stays as it is **(read: six packages)**. The Firefox leg needs `playwright==1.64.1`, pinned in
a new **`requirements-platform.txt`** (`-r requirements.txt` plus that line), installed only where Firefox is
wanted: the template's Firefox legs, and an operator who runs the leg locally. `check-env.py` gains an
optional row like FontBakery's (`optional: playwright not installed (the Firefox leg of the platform shots is
skipped until it is): <pip> install -r <requirements-platform.txt>; then <python> -m playwright install
firefox`). `shoot.py --browser firefox` without Playwright exits 3 with `SKIPPED, NOT PASSED` and that command,
never 0. The Chrome legs install nothing beyond `fonttools`, `brotli` (the specimen) and nothing at all when
there is no specimen; the compare job installs `pillow`. A test holds the template's pins to the requirements
files (section 7).

### 1.2 Backward-compatible outputs

Every existing `shoot.py` invocation keeps its behaviour and its file names: `--scales 1 2` still writes
`@1x` and `@2x` (the new format is `@{scale:g}x`; **measured:** `f"{2.0:g} {1.25:g} {1.0:g}"` prints
`2 1.25 1` on the venv's Python 3.12); one `--font-url` means what it meant; `--browser` defaults to `chrome`;
`--meta` and `--rows` are opt-in; the beacon URL is unchanged (rows travel on a second request), so
`tests/test_shoot.py`'s 50-odd beacon and probe tests are the compatibility guard. `specimen.py`'s rows gain
one attribute each; the DOM tests that read `data-fd-spacing`, `data-fd-legibility`, `data-fd-junctions`,
`data-fd-probe` keep passing **(read: `smoke.sh` 193–198 greps those attributes; nothing greps the whole `<p` tag)**.

### 1.3 Testing discipline

Every guard below names its test and the weakest mutation that must turn it red (`references/testing.md`
section 3). Tests execute the shipped scripts: `shoot.py` through `serve()` and real Chrome (the `site`
fixture and `one_shot()` of `tests/test_shoot.py` lines 189–229 **(read)**), a fake browser for process
behaviour (lines 832–887 **(read)**; the new fakes are Python one-liners, not `#!/bin/sh`, so the same tests run
on the Windows leg of the skill's own workflow, F010), `compare-shots.py` through its `main()` on fixtures
built in tmp, the Firefox launcher through real Playwright where it is installed (named "firefox", skipped
loudly otherwise, as the "chrome" tests are). Workflow tests read text and say so, as `tests/test_ci_workflow.py`
does **(read: header lines 6–8)**. Repo guards record their mutation in the docstring and in
`references/testing.md` section 8.

### 1.4 Docs in the same change

Section 8 lists every file. `tests/test_docs_commands.py` checks every documented flag against the script,
`tests/test_versions_and_skill.py` checks the version in `VERSION`, `SKILL.md`, the README badge, the
CHANGELOG's top entry and `package.json` **(read: lines 22–34)**.

### 1.5 Honesty about what a runner proves

The exact guarantee of a platform shot, which every doc that names the tool repeats (section 6.3): *what the
recorded browser (Chrome of the recorded version, headless with `--disable-gpu`; or Playwright's Firefox of
the recorded version) drew on a GitHub-hosted virtual machine of the recorded OS with the recorded
font-smoothing settings and no physical display, at the recorded device scale, with the same served-200,
sentinel, element and italic proofs as every other `shoot.py` shot.* It is not a reader's machine (display,
scaling, ClearType tuning, browser version and GPU raster path differ), Playwright's Firefox is not the
image's or a reader's Firefox build, it is not Edge or Safari, and a run that was never made proves nothing:
the record says "checked on Windows: run <id>, <what it showed>" or "not checked on Windows", never a
rounded-up "fine on Windows".

---

## 2. Decision 1 — architecture

### 2.1 The options, weighed

| | A. `shoot.py` on each runner (Chrome) | B. A Playwright script (the one-off, generalised) | C. Hybrid: `shoot.py`'s server and sentinel, a Playwright launcher for Firefox (and WebKit) |
|---|---|---|---|
| Evidence | The seven proofs of the header, unchanged **(read: items 1–7)** | `document.fonts` status: weaker, and a second model to keep in sync with the first | The server-side proofs (2, 3, 5, 6, 7) hold for any browser pointed at the tokenised URL; item 1 becomes "the launcher returned a PNG and raised nothing" |
| Browsers | Chrome only (Edge is the same engine, unverified) | Chrome, Firefox, WebKit | Chrome by the CLI; Firefox (built), WebKit (designed) by Playwright |
| Dependency | none | `playwright==1.64.1` pinned, browser downloads per run (Firefox about 90 MB **(inferred)**), the known Mac failure | the same, optional, loudly skipped when absent |
| Native Windows | three teardown seams and fractional `--scales` (section 0); bash not needed for one `python scripts/shoot.py` line | works (the one-off ran) | both |
| What WebKit proves | — | that Playwright's WebKit build laid out and loaded the font; on macOS it draws through the system CoreText so it is the nearest thing to Safari, on Linux and Windows through its own stack. **Not Safari**: not Safari's version, not its font-loading or `font-synthesis` behaviour, and no Safari release ships Playwright's WebKit **(inferred from Playwright's own documentation, from memory; not re-read)** | the same statement, on the launcher's label |

**Decision (operator ruling 1): C, with Firefox built and WebKit designed.** The evidence model is one
(`shoot.py`'s server and sentinel); the launcher is the only thing that differs per browser; Firefox adds the
second major rendering stack on Windows (DirectWrite through Firefox's own text path, which the one-off saw
draw grayscale where Chrome drew subpixel) at the cost of one pinned optional dependency. Reasons B is still
rejected: a weaker second proof model invites a reviewer to read a fallback-face PNG as evidence, which is the
failure `shoot.py` exists to prevent.

### 2.2 `scripts/shoot.py` changes (work item A1)

1. **Fractional scales.** `--scales` becomes `type=float` (line 826); file names use `@{scale:g}x` (line 884);
   `crop_bands()` rounds the box to integers (`int(round(top * scale))`, line 806); the Chrome flag
   `--force-device-scale-factor=1.25` is passed as written (Chrome parses the value as a double **(inferred;
   the acceptance run on Windows is the check)**).
2. **Teardown on Windows (F003), three parts, each named in `kill_group()`'s docstring.**
   (a) When `os` has no `killpg`, run `taskkill /T /F /PID <pid>` **first** (it kills the tree from the parent
   down; once the parent is dead, `/T` finds no tree), then `p.kill()` for the case `taskkill` is missing or
   failed (`FileNotFoundError`, non-zero exit), then `p.wait(timeout=10)`. (b) `run_chrome()`'s wait for stdout
   EOF (line 629) is bounded: after `kill_group()` has run, or once `done_at` is set and `EXIT_GRACE` has
   passed, the reader threads are joined with the existing 10 s timeout (line 641) and the function returns
   what was read; a helper that still holds the pipe cannot hold the run (today it can, on every OS, when a
   kill misses a helper). (c) The profile directory is opened with `TemporaryDirectory(dir=profile_root,
   ignore_cleanup_errors=True)` (3.10+, `ruff.toml` targets py310 **(read)**), and after the `with` block the
   directory is checked: if it still exists, a `NOTE:` departure names it ("profile <path> left behind: a
   browser helper still held it; not evidence of a page fault") so the shot is not failed for a teardown leak
   and the leak is not silent. A clean shot never reaches (a); the Windows leg of the skill's own workflow runs
   the kill test (section 7) so (a) and (b) are executed on Windows, not only reasoned about.
3. **`--meta FILE`.** Writes one JSON file after the run: `platform` (`platform.platform()`), `system`,
   `machine`, `python`, `browser` (`chrome` or `firefox`), `launcher` (the Chrome binary path, or
   `playwright <version>`), `font_smoothing` (the four registry values on Windows, `null` elsewhere: the
   one-off's `smoothing()`, ported), `args`, `shots` (every verified result dict, with `ua`, `rows` and the
   shot's `height`), `failed` (the `FAILED:` strings) and `departures`. The run still exits 1 when anything
   failed; `--meta` changes no verdict. A leg directory may hold several `meta*.json` (one per invocation,
   section 3); `compare-shots.py` reads them all.
4. **The browser version from the page.** The sentinel adds `navigator.userAgent` to the beacon (`ua=`); the
   result dict gains `ua` (headless Chrome reports `HeadlessChrome/157.0.…`, Firefox `Firefox/<ver>`
   **(inferred)**). `chrome.exe --version` prints nothing on Windows **(inferred)**, so the page is the one
   cross-platform source.
5. **`--rows`: element boxes per shot (F005, F006).** With `--rows`, the sentinel, after the probe, collects
   every `[data-fd-row]` element and every element the probe counted (section 3), and records per element:
   `key` (the attribute, or `probe-<n>` in document order), `x`, `y`, `w`, `h` **in viewport coordinates**
   (`getBoundingClientRect()` as is), the element's own text (first 80 characters), the computed `font-size`,
   `font-weight`, `font-style`, and `captured` (`y + h ≤ the viewport height`). Once per shot it records
   `scroll_x`, `scroll_y`, `viewport_w`, `viewport_h`. Viewport coordinates are PNG coordinates (times the
   scale) **only when the page has not scrolled**: a headless shot of a `--window-size` window starts at the
   document's top, and a page whose script scrolled would shift every box. `shoot()` therefore records the
   scroll and `compare-shots.py` refuses the shot's rows when `scroll_x` or `scroll_y` is non-zero, naming it
   ("scrolled by N px: boxes are not PNG coordinates"). It POSTs the JSON to `/__fd/rows?shot=<token>` with
   `fetch(..., {keepalive: true})`; the server records it per token **only when the request carries the
   shot's cookie**, as the beacon is (`same_shot()`, line 482 **(read)**). `shoot()` waits for the rows as it
   waits for the beacon (`BEACON_WAIT`) and writes `<png>.rows.json` **after every proof has passed**; a
   failed shot writes none; a verified shot whose rows never arrived is **failed** ("no rows arrived"), never
   written half. Why a second request: the beacon is a GET `Image()` URL (line 304 **(read)**) and a specimen
   has about a hundred rows.
6. **`--font-url` repeatable (H1).** `action="append"`. Exact guarantee, replacing item 5's: *every named
   path that this shot's browser requested was served 200 to it, and at least one named path was requested.*
   A page that uses only two of a family's five files is not failed for the three it never asked for; a
   named path that was requested and not served 200 fails the shot as today; a shot that requested none of
   them fails ("none of the named font paths was requested"). The element probe (item 6) still proves the
   face on the visible text.
7. **`--browser chrome|firefox`** (section 2.4): `chrome` is today's path; `firefox` calls
   `shoot_playwright.capture()` in place of `run_chrome()` and then runs the same proofs.

`rows.json` schema (fixed here so A, B and E can be built in parallel):

```json
{"shot": "7f3a…", "page": "/review/specimen.html", "width": 1280, "height": 6000, "scale": 1.25,
 "scroll_x": 0, "scroll_y": 0, "viewport_w": 1280, "viewport_h": 6000,
 "ua": "Mozilla/5.0 … HeadlessChrome/157.0.8103.79 …",
 "rows": [{"key": "legibility", "x": 24, "y": 312.5, "w": 610.2, "h": 21.3, "text": "Il1 O0 B8 rn m cl d",
           "font_size": "15.2px", "font_weight": "500", "font_style": "normal", "captured": true}]}
```

Coordinates are CSS px relative to the viewport; the comparison multiplies by `scale`. The same font gives
the same advances and line boxes on every OS **(inferred: Chrome and Firefox lay out from the font's
unhinted metrics on every platform; a one-pixel disagreement is absorbed by the 2 px margin the crop takes;
the matching rule of section 4.1 refuses the pair when the text or computed style differs)**.

### 2.3 What is not changed

The sentinel's visibility, face, weight, italic and missing-character logic; the beacon URL's fields; the
server's path containment; `narrow.html`, `opsz.py`; native Windows stays unsupported for the **skill** (the
runner runs one script, not the process); `check-env.py`'s platform line.

### 2.4 The Firefox leg (work item E1): `scripts/shoot_playwright.py`

A new module, imported by `shoot.py` only when `--browser firefox` is given, so `shoot.py` keeps its
standard-library-only import block (section 0) and its owner keeps one file.

```
capture(browser, url, out_png, width, height, scale, timeout, dump_dom=False) -> Capture(ua, dom_text, error)
```

- `browser` is `firefox` (`webkit` is refused with the sentence of 2.5 until built). The module imports
  `playwright.sync_api` inside `capture()`; an `ImportError` is turned into `shoot.py`'s exit 3,
  `SKIPPED, NOT PASSED: --browser firefox needs playwright: .venv/bin/pip install -r requirements-platform.txt,
  then .venv/bin/python3 -m playwright install firefox`. A Playwright that is installed without its Firefox
  raises at `launch()`; that is a failed run (exit 1, the error named), not a skip: the operator asked for the
  leg and it did not run.
- `p.firefox.launch()`; `new_context(viewport={"width": width, "height": height},
  device_scale_factor=scale)`; `page.goto(url, wait_until="networkidle", timeout=timeout*1000)`; then it
  waits until the page's `<html>` carries `data-fd-shot` (the sentinel writes it last, line 285 **(read)**)
  or the timeout; `page.screenshot(path=out_png, full_page=False)` — the viewport of `height` px, the same
  frame as Chrome's `--window-size` shot, so `rows.json` means the same thing; with `dump_dom`,
  `page.content()` is the DOM. The context, browser and Playwright are closed in `finally`; any exception
  is returned as `error`, and `shoot()` raises `RuntimeError` from it exactly as it does for a Chrome exit
  code (item 1 for Firefox: "Playwright returned a PNG and raised nothing"). Items 2–7 then run on the same
  server records: the HTML response set the cookie in Firefox's jar, every later request carries it, the
  beacon and the rows POST are recorded by cookie. No Chrome flag (`--virtual-time-budget`, `--disable-gpu`)
  has a Firefox twin; `networkidle` plus the sentinel attribute is the settle rule, stated in the header.
- **The macOS Firefox profile failure** ("Could not find profile folder" from 1.64.1 on the author's Mac,
  unexplained) is recorded in the module header, in `fallbacks.md` and in `test_firefox_…`'s docstring. The
  test that launches Firefox skips loudly with that exact message when `launch()` raises it, and says the
  leg is to be judged on the runner; the skill's own workflow (section 5.2) is the measurement, and if the
  macOS Firefox leg fails there too, the matrix `exclude`s it with the reason in a comment and the CHANGELOG
  records it.
- `check-env.py`: `check_playwright()` in the optional group, after `check_fontbakery()`; it also reports
  whether the Firefox browser is installed when the package is (`playwright` exposes the browser path
  through its registry **(inferred; else the row reports the package only and says so)**).

### 2.5 Designed, not built: WebKit

`capture("webkit", …)` is one `p.webkit.launch()` away, and the proofs would hold. It stays out because it
would prove little for its cost: on Linux and Windows Playwright's WebKit draws through a text stack no
reader has; on macOS it is close to Safari but **Safari itself is on the macOS runner** (27.2 in the image,
section 0) and a Safari leg would be driven by `safaridriver`, a different tool, which is the better future
item; and every WebKit leg bills macOS minutes to be meaningful. When built, its label is "Playwright WebKit,
not Safari" with the sentence of 2.1, and `requirements-platform.txt` is unchanged (the same package).

---

## 3. Decision 2 — what gets shot

**The review specimen when the site has a `font.json`, the operator's named pages always; at 1280 CSS px,
device scales 1 and 1.25; `--family` and `--font-url` on every shot.**

- **The specimen** (`specimen.py` from the site's `font.json`, written under the served root as the review
  loop already does **(read: `SKILL.md` phase 8)**) carries the rows the question is about: the spacing control
  strings at 24 px, the legibility row and the junction row at the smallest review size, the readable rows at
  every site size on every surface, the italic rows with their probe. Every family row gets
  `data-fd-row="<key>"` (work item A2): `spacing-<kind>`, `legibility`, `junctions`,
  `readable-<surface>-<size>-<weight>`, `bold-<surface>-<size>`, `wordmark-<surface>-<size>`,
  `wrapmax-<surface>`, `opsz-<size>`, `mid-<n>`, `italic-<n>`, `compare-<n>`, `kern-<size>`, `nbsp`,
  `quotes`; `specimen.py` refuses a duplicate key. **It is shot in its own invocation with `--height 6000`
  (F004)**: the page's last ink is at 5,368 px at 1280 **(read: `specimen.py` 251–252)** and the default 2400
  would capture the proof rows only; `rows.json`'s `captured` flag is the check that every row is inside, and
  the acceptance run asserts it (section 10). Chrome's headless window accepts a 6000 px height **(inferred;
  the one-off used Playwright's `full_page`, which is a different mechanism; acceptance step 3 is the check)**.
- **Pages-only sites (H1).** When `FD_FONT_JSON` is empty the specimen step and the specimen invocation are
  skipped (`if: env.FD_FONT_JSON != ''`), and the pages are the whole leg. movingavg.com's Driftwood is the
  case: five static woff2 files, no `font.json`, several files loaded per page; its `FD_FONT_URLS` lists the
  five paths and `--font-url` is repeated for each (section 2.2 item 6).
- **The named pages** at the default 2400 height in a second invocation (`--meta meta-pages.json`): the rows
  are the elements the probe counted (`probe-<n>`), so the title at the smallest display size on the real
  page is compared too; a title below 2400 px is `captured: false` and listed, not cropped.
- **Width 1280 only.** A row must wrap the same way in every leg for its box to be comparable; at 1280 the
  specimen's titles do not wrap (the `wrapmax` row wraps by design in a 14em measure, identically everywhere
  since the measure is in ems). The phase-8 loop keeps shooting 500–1600 on the author's machine; the platform
  question is rendering, not layout.
- **Scales 1 and 1.25**: 1× is where the hairline question lives (one CSS px = `1000/size` units,
  `guidelines.md` section 2 **(read)**); 1.25× is Windows' most common display scaling and what the one-off
  shot; 2× is what the local loop already covers. The template exposes `scales` as an input, default `1 1.25`.
- **`--bands none`** (the comparison crops rows) and **`--jobs 2`** on the runners (two browsers at once on a
  2-core VM **(inferred)**).

Per leg, the output directory holds `specimen-1280@1x.png`, `specimen-1280@1.25x.png`, `<page>-1280@…png`,
one `.rows.json` beside each verified PNG, `meta-specimen.json` (when there is a specimen) and `meta-pages.json`.

---

## 4. Decision 3 — `scripts/compare-shots.py`

### 4.1 Design

```
compare-shots.py OUT_DIR LEG_DIR [LEG_DIR ...] [--zoom N] [--rows KEY ...] [--min-legs N]
```

Each `LEG_DIR` is one `shoot.py --rows --meta` run (one OS × one browser, one or two `meta*.json`). The tool:

1. **Accepts or refuses each leg on its own (F007).** A leg without a `meta*.json`, or whose meta files name
   no verified shot, is refused with the directory named and **the comparison goes on with the others**; a
   PNG named in `shots` without its `.rows.json` refuses that shot only (the file is written only after the
   proofs, section 2.2, so its absence means an unverified or hand-copied PNG); a shot with non-zero
   `scroll_x`/`scroll_y` is refused as "scrolled" (F005). Every refusal is in `compare.md` under "Refused".
   Exit 0 when at least `--min-legs` (default 2) legs were accepted, whatever was refused; exit 1 below it
   (one leg compares nothing), with `compare.md` still written so the reasons are read.
2. **Labels come from the meta, never from directory names**: `Windows-11-10.0.26100 · HeadlessChrome/157.0 ·
   1.25x · ClearType, RGB` — system and release from `platform`, the browser token from `ua`, the scale, and on
   Windows the smoothing summary from **`FontSmoothingType`** (`2` = ClearType, `1` = standard grayscale,
   absent or `0` with `FontSmoothing` `"0"` = off) and **`FontSmoothingOrientation`** (`1` = RGB, `0` = BGR)
   (F014; `FontSmoothing` is the on/off flag and is printed only when it is `"0"`).
3. **Pairs rows by key, then checks they are the same element (F006).** A key is compared only when it is
   present in every accepted leg **and** its `text`, `font_size`, `font_weight` and `font_style` are equal
   across them; a key whose fields differ (a `probe-<n>` that landed on a different element, a specimen whose
   titles changed between legs) is listed under "Mismatched" with the differing fields per leg and is not
   cropped. A key missing from some legs is under "Not in every leg"; a row with `captured: false` in any leg
   under "Below the capture".
4. For each compared row: crops `(x − 2, y − 2, x + w + 2, y + h + 2) × scale` from each leg's PNG, scales the
   crop by `--zoom` (default 4) with **nearest-neighbour** resampling so pixels stay pixels, converts nothing
   (subpixel colour is the finding), paints a one-line label strip above each crop (Pillow's default bitmap
   font, no font file) and stacks the legs vertically in command-line order. Writes
   `OUT_DIR/<page>-<key>@<scale:g>x.png`.
5. **Ink figure, relative to the crop's own background (F011).** `L_bg` = the median luminance of the crop's
   one-pixel border (the row's margin: background on paper and on cloth alike); ink = mean of `|L − L_bg|` over
   the crop, divided by 255. `compare.md` prints each leg's figure as a share of the first leg's. The figure is
   a hint for where to look, stated as such; the PNG is the evidence. A crop whose border is not uniform
   (border luminance spread over 32 levels) prints `ink n/a` for that leg instead of a number.
6. Writes `compare.md` (rows grouped by page, then by `font_size` ascending so the smallest sizes come first,
   each with its PNG name and the per-leg ink shares; then "Mismatched", "Not in every leg", "Below the capture",
   "Refused"; then every accepted leg's platform line) and `compare.json`, and prints the `compare.md` path.

Reuse from `diff.py`: `slug()` for file names, the panel-stacking shape of `triptych()`, the Pillow import
guard `need()` with its venv message **(read: lines 66–75)**. Not reused: `compare()`'s pixel threshold,
`instance_file()`, raqm (no text is laid out).

### 4.2 Why boxes from the page and not pixel offsets

The one-off's reviewer hand-cropped at 7× because the only way to find the same row in two PNGs was by eye.
The sentinel knows every row's viewport box after fonts are ready, so each leg carries its own map and the
tool never assumes two legs laid out identically; where they did not, the boxes differ and the row is still
cropped correctly in each, and where the paired elements are not the same element, the match rule says so.

---

## 5. Decision 4 — the workflow template and the skill's own CI

### 5.1 `templates/platform-shots.yml` (work item C1)

An operator copies it to `<site>/.github/workflows/platform-shots.yml` and fills the slots in its `env:`
block: `FD_SCRIPTS` (the site's copy, `tools/<face>/scripts`), `FD_SERVE` (the built static root, Bract:
`static-pages/`), `FD_BUILD` (**F002**: the command that builds or stages `FD_SERVE`, e.g. `python tools/
builder/update-static-pages.py -c pages.yaml`; empty for a site that commits its built root, and the step is
skipped), `FD_FAMILY`, `FD_FONT_URLS` (one root-relative path per line, a multi-line scalar; several for a
family in several files, H1), `FD_PAGES` (one page per line), `FD_FONT_JSON` (`tools/<face>/font.json`, or
empty for a site with no skill-built font: no specimen, H1), `FD_SCALES` (`1 1.25`). **Every expansion is
quoted (F008)**: `"$FD_FAMILY"` (family names have spaces), and the multi-line slots are read into arrays with
`mapfile -t PAGES <<< "$FD_PAGES"` and expanded as `"${PAGES[@]}"`; `--font-url` is repeated per line of
`FD_FONT_URLS` by a small bash loop building an array of `--font-url <path>` pairs. The header comment states
what the run is for, what it proves (section 1.5's sentence), what it costs (the figures of section 0 with
the date they were read, the note that they are free on a public repository), that it is not a merge gate,
and that the first `workflow_dispatch` needs the file on the default branch.

```
on: workflow_dispatch
      inputs (each optional, overriding the env slot when given; F013): pages, scales, font_urls, family, browsers
             (default "chrome firefox")
permissions: contents: read
jobs:
  shots:
    strategy: fail-fast: false
              matrix: os: [windows-latest, macos-latest, ubuntu-latest]; browser: [chrome, firefox]
    runs-on: ${{ matrix.os }}; timeout-minutes: 15
    defaults.run.shell: bash                       # Git Bash on Windows: one set of lines for three OSes
    steps (every step after checkout carries if: contains(inputs.browsers || 'chrome firefox', matrix.browser),
           so a dispatch with browsers "chrome" skips the three Firefox legs in seconds):
      actions/checkout@v4
      actions/setup-python@v5 (python-version "3.12")   # the macOS image's system Python is 3.15 (section 0)
      (FD_BUILD non-empty) run: eval "$FD_BUILD"           # F002: build or stage the served root
      (FD_FONT_JSON non-empty) pip install "fonttools==4.68.*" brotli   # the specimen's charset check
      (browser firefox) pip install -r "$FD_SCRIPTS/../requirements-platform.txt" || pip install playwright==1.64.1
                        python -m playwright install firefox           # Firefox installed in its leg only
      (ubuntu, browser chrome) the apparmor userns sysctl step and browser-actions/setup-chrome@v1, from ci.yml
      (FD_FONT_JSON non-empty) python "$FD_SCRIPTS/specimen.py" --font "$FD_FONT_JSON" --requirements "<beside it>"
                               --font-url "${FONT_URLS[0]}" [--italic-url …] "$FD_SERVE/review/specimen.html"
      (FD_FONT_JSON non-empty) python "$FD_SCRIPTS/shoot.py" leg --serve "$FD_SERVE" --pages review/specimen.html
                               --widths 1280 --scales $SCALES --height 6000 --family "$FD_FAMILY" "${FONT_URL_ARGS[@]}"
                               --browser "${{ matrix.browser }}" --rows --meta leg/meta-specimen.json --bands none --jobs 2
      python "$FD_SCRIPTS/shoot.py" leg --serve "$FD_SERVE" --pages "${PAGES[@]}" --widths 1280 --scales $SCALES
             --family "$FD_FAMILY" "${FONT_URL_ARGS[@]}" --browser "${{ matrix.browser }}" --rows
             --meta leg/meta-pages.json --bands none --jobs 2
      actions/upload-artifact@v4 (if: always(); name: platform-shots-${{ matrix.os }}-${{ matrix.browser }};
             path: leg/; retention-days: 14; if-no-files-found: error)
  compare:
    needs: shots; if: always()                      # one leg's failure must not lose the others' comparison
    runs-on: ubuntu-latest; timeout-minutes: 10
    steps:
      actions/checkout@v4; setup-python 3.12; pip install pillow
      actions/download-artifact@v4 (pattern: platform-shots-*; path: legs; merge-multiple: false)
             # F001: each artifact lands in legs/<artifact-name>/ with meta*.json at its root, because the
             # uploaded path was the leg directory itself
      python "$FD_SCRIPTS/compare-shots.py" compare legs/*/        # refuses bad legs one by one, continues
      cat compare/compare.md >> "$GITHUB_STEP_SUMMARY"
      actions/upload-artifact@v4 (if: always(); name: platform-shots-compare; path: compare/; retention-days: 14)
      a final step that fails the job when needs.shots.result != 'success', AFTER the upload: the run is red,
      the evidence that exists is kept.
```

Pinned to major tags (`@v4`, `@v5`, `@v1`), the repo's convention **(read: `ci.yml` lines 34–36, 58, 81, 99)**;
SHA pinning is a repo-wide hardening, out of scope here. Timeouts: 15 minutes per leg against a measured 73 s
for a Chrome leg; a Firefox leg adds its browser download.

**Why the site's own copy and not a checkout of the skill**: SKILL.md phase 7 copies `scripts/` into the site
(section 0), so the version that shot the pages is the version under test in the site, the site's `.woff2`
is on disk in `FD_SERVE`, and the workflow needs no token or second repository. `requirements-platform.txt`
is at the skill's root, not in `scripts/`, so the Firefox step falls back to the literal pin when the site did
not copy it; the test of section 7 holds the two pins equal. The specimen is rendered in the job because the
review loop keeps it out of the commit **(read: `SKILL.md` phase 8)**.

**How the font is found**: `--serve "$FD_SERVE"` serves the built root; each `--font-url` is a root-relative
path the stylesheet uses; `shoot.py` proves the requested ones were served 200 to that shot (section 2.2
item 6). Nothing is copied or looked up.

**Cost line for the header (F015)**, from section 0's prices: the three Chrome legs at about 1.5 minutes each
cost about 1.5 × ($0.006 + $0.010 + $0.062) ≈ **$0.12**; the three Firefox legs at about 2.5 minutes each
(the browser download) about $0.20; a full six-leg run **about $0.30** against $12 of included usage per month
on a private repository under the Free plan, and free on a public one. macOS is 80 % of either figure: an
operator who wants Windows alone removes the other two labels from the matrix. Artifacts: about 20 PNGs of a
few hundred KB each per leg **(inferred; the acceptance run measures it)**, 14-day retention, against 500 MB
shared storage on Free. The figures carry the date they were read and the sentence "re-check GitHub's
billing page".

### 5.2 The skill's own CI (work item C2)

- **`ci.yml` `chrome` job**: `smoke.sh` step 9 adds `--rows --meta` and `--height 6000` to the specimen shoot
  and runs `compare-shots.py` on that single leg with `--min-legs 1`, so the tool executes on every push on
  Linux, a rows file is produced and read, and every specimen row reads `captured: true` (a `grep` in the step,
  the F004 guard on the fixture). `tests/test_ci_workflow.py` already holds the chrome job to `smoke.sh
  --full` **(read: lines 33–35)**.
- **A new `.github/workflows/platform-shots.yml` in the skill repo**: the template with the slots filled for
  the neutral fixture, with `FD_BUILD` set to the staging the fixture needs (**F002**): build the neutral font
  (`python scripts/build.py --font examples/neutral/font.json`, as the chrome job does **(read: `ci.yml` line
  114)**), copy `tests/fixtures/site-sample` to `out/platform/site`, copy the two woff2 files to
  `out/platform/site/fonts/`, and wire Sampler into the copied stylesheet exactly as `smoke.sh` step 11 does
  **(read: step 11, lines 238–270)**; `FD_SCRIPTS=scripts`, `FD_SERVE=out/platform/site`, `FD_FAMILY=Sampler`,
  `FD_FONT_URLS=/fonts/Sampler-VF.woff2` (and the italic), `FD_PAGES=index.html essay.html`,
  `FD_FONT_JSON=examples/neutral/font.json`. One extra step per leg (**F010**): `python -m pytest
  tests/test_shoot.py -q -k "kill_group or fractional or meta or rows"` so the Windows teardown code and the
  rows path run natively on Windows and on macOS, not only on the author's Mac. Triggers:
  `workflow_dispatch`, and `pull_request` limited by `paths` to `scripts/shoot.py`, `scripts/shoot_playwright.py`,
  `scripts/specimen.py`, `scripts/compare-shots.py`, `templates/platform-shots.yml`, `requirements-platform.txt`
  and itself. Free on the public repo. **This is the release proof** that the tool runs on Windows and macOS in
  both browsers: acceptance step 4 reads its six legs and its comparison before the version is bumped. A test
  holds the two YAML files together (section 7).

### 5.3 `references/` and `smoke.sh`

`smoke.sh` gains no new numbered step (step 9's shoot gains three flags and one compare line). `review-loop.md`
section 2 gets the tool bullet; `fallbacks.md` "## Windows" the paragraph (section 8).

---

## 6. Decision 5 — where it enters the process

### 6.1 Phase 8

After the round that would end the loop (a round reporting nothing visible at 1× on a real page, or round
six), and at any round the operator asks for, the host asks the operator to run the workflow (`gh workflow
run platform-shots.yml`, then `gh run download -n platform-shots-compare`; the first dispatch needs the file
on the default branch, section 0) and reads `compare.md` top-down: the smallest sizes first, the "Refused" and
"Mismatched" lists before trusting any row. It is one reading per face, not one per round, because the
question it answers (does the hairline survive DirectWrite at the smallest sizes, in Chrome and in Firefox)
changes only when the design's `thin`, the floors or the smallest sizes change; a round that changes those
re-runs it. **Ranking**: a stroke that breaks up or drops out on a real page at 1× in any leg is a finding at
1× on a real page and is fixed in the design (`thin`, Medium under the smallest sizes, the floor), as
`guidelines.md` section 2 already prescribes **(read: lines 56–62)**; a stroke that reads lighter but
continuous is recorded in the record's rendering section with the compare PNG named, not a defect. Reopening
the loop is the operator's call, as every other round is.

### 6.2 Phase 9 and the publication blockers (operator ruling 2)

**Not a blocker.** The runner is not a reader's machine, an operator may have no GitHub Actions, and the
skill's blockers are about evidence for the shipped build on the renderer that reviewed it **(read:
`SKILL.md` section 4)**. The record's line becomes a two-way slot in `templates/font-record.md` (lines
134–136 today read "Windows has not been looked at" **(read)**): either *"Windows: <browser and version from
`ua`> on <platform>, ClearType <type, orientation>, run <id> of <date>, `compare.md` at <path>: <what the
smallest rows showed, one sentence each for the legibility row, the junction row and the smallest real-page
title; Firefox the same>"*, or *"not checked on Windows"* with the claim it limits, as today. The "Open items"
slot (line 170) keeps `Windows` only in the second case. Phase 9's live check is unchanged.

### 6.3 Wording that changes

Every sentence that today says Windows cannot be checked becomes "is not checked unless the platform run was
made, and then only as headless Chrome and Playwright's Firefox on a GitHub-hosted runner":
`references/fallbacks.md` "## Windows" (lines 95–97), `references/guidelines.md` line 66 ("cannot be checked
from a Mac"), `references/review-loop.md` section 9 (line 183: Firefox moves from the "nothing about" list to
"Firefox only through the platform run's Playwright build"), `references/traps.md` row 21's detection cell,
`SKILL.md` line 417 (Safari and phones stay unverified; Windows and Firefox move to "unless the platform run
was made"), `templates/font-record.md` 134–136 and 170. The exact guarantee of section 1.5 is stated once in
full in `review-loop.md` section 9 and referred to from the others.

---

## 7. Tests, each with the mutation that turns it red

All new; existing tests are unchanged except where named. "chrome" in a name means the test runs real Chrome
through `shoot.py` and skips loudly without one (the CI chrome job runs them by name **(read: `ci.yml` line
118)**); "firefox" means real Playwright Firefox, skipped loudly without the package or its browser, and
skipped with the recorded message on the macOS profile failure (section 2.4). Fake browsers are Python
one-liners (`sys.executable -c …`) so the same tests run on Windows (F010).

**`tests/test_shoot.py` (work item A1t)**

| Test | Asserts | Weakest mutation watched red |
|---|---|---|
| `test_scales_accept_a_fraction_and_name_the_file_by_it` | `main([… "--scales", "1", "1.25", "2"])` with a fake browser writes `x-1280@1x.png`, `x-1280@1.25x.png`, `x-1280@2x.png` (the `@2x` name unchanged from 0.2) | `type=int` restored (argparse error); `@{scale}x` restored (`@1.0x`, `@2.0x`) |
| `test_crop_bands_rounds_a_fractional_box` (F009) | `crop_bands()` at scale 1.25 with band `head:0:901` on a 1280×2400 PNG writes a crop of height `round(901 × 1.25)` = 1126 (901 × 1.25 = 1126.25, a true fraction; 900 × 1.25 = 1125 exactly and could not fail) | `int(round())` removed (Pillow truncates or raises on the float box **(inferred)**; either way the height is not 1126 or the call fails) |
| `test_kill_group_ends_a_grandchild_that_holds_stdout` (F010) | the fake browser is `python -c` that spawns a grandchild `python -c "import time; time.sleep(60)"` inheriting stdout, prints `</html>`, then sleeps; `run_chrome(..., complete=…)` with `EXIT_GRACE` 1 returns within 4 s, the grandchild is dead (its pid no longer answers `os.kill(pid, 0)` on POSIX / `OpenProcess` on Windows), and the parent is reaped | the grandchild kill dropped (`p.kill()` alone leaves the sleeper holding the pipe: the run waits for EOF until the test's 10 s ceiling); on Windows: `taskkill` run after `p.kill()` (the tree is gone, the sleeper survives) |
| `test_run_chrome_returns_after_a_kill_even_when_a_helper_holds_stdout` | with `kill_group` monkeypatched to kill the parent only, `run_chrome()` still returns within `EXIT_GRACE + 10 + 1` s with `killed` true and the stdout read so far | the bounded join after the kill removed (the function blocks until the test's ceiling) |
| `test_shoot_notes_a_profile_directory_a_helper_left_behind` | a fake browser that creates a file in its `--user-data-dir` and spawns a sleeper holding it open (on Windows the directory then cannot be removed; on POSIX the test forces the case by making the directory read-only before exit); `shoot()` returns, a `NOTE:` names the profile path, the shot is not failed | `ignore_cleanup_errors=True` removed (an `OSError` propagates out of `shoot()`); the departure line removed |
| `test_meta_file_records_the_platform_the_verified_shots_the_failures_and_the_exit_code` (chrome) | two pages on the `site` fixture, one in Probe and one in Georgia; `main([… "--family", "Probe", "--font-url", "/fonts/Probe.woff2", "--meta", f])` returns 1; `meta.json` has one shot with `verified` true, a `ua` containing `Chrome/` and a `height`, one entry in `failed` naming the Georgia page, `platform == platform.platform()`, `browser == "chrome"`, `font_smoothing` None off Windows | the `failed` list dropped from the file; `ua` dropped from the beacon; `return 1 if failed else 0` → `0` |
| `test_chrome_rows_json_carries_every_marked_row_in_viewport_coordinates_with_the_scroll_and_scale` (chrome, F005) | a page with three `data-fd-row` elements at absolute CSS positions (one at `top: 3000px`, below a 2400 capture), shot at scale 1 and 2 with `rows=True`; each key present; `x, y, w, h` within 1 px of the CSS values in both shots (CSS px, not device px); `scroll_y == 0`, `viewport_h == 2400`; the third row has `captured: false` | the rect reported in device px (the scale-2 shot fails); `captured` computed against the document height; `scroll_y` omitted |
| `test_chrome_a_page_that_scrolled_records_the_offset` (chrome, F005) | a page whose script calls `scrollTo(0, 500)` before fonts ready: `rows.json` has `scroll_y` 500 and the first row's `y` is its CSS top minus 500 | the sentinel adding `scrollY` back into `y` (document coordinates: `y` equals the CSS top) |
| `test_chrome_rows_json_is_not_written_for_a_shot_that_failed_its_proof` (chrome) | a page in Georgia with `data-fd-row` elements, `require_family="Probe"`: `shoot()` raises and no `.rows.json` exists | the rows file written before the proof checks |
| `test_chrome_a_verified_shot_whose_rows_never_arrive_is_failed` (chrome) | the server's `/__fd/rows` handler monkeypatched to drop the body: `shoot(rows=True)` raises "no rows arrived" and writes no rows file | the wait made optional (a PNG without rows passes) |
| `test_rows_from_another_shots_browser_are_ignored_and_noted` | a POST to `/__fd/rows?shot=A` carrying cookie `fd_shot=B` is not recorded for A and appears in `server.departures` (the pattern of line 339 **(read)**) | the cookie check dropped on the rows handler |
| `test_chrome_font_urls_pass_when_each_requested_one_is_served_and_fail_when_none_is_requested_or_one_404s` (chrome, H1) | the `site` fixture with `--font-url /fonts/Probe.woff2 --font-url /fonts/Probe-Italic.woff2`: a page using the roman only passes; the same page with `--font-url /fonts/Nothing.woff2 --font-url /fonts/Probe.woff2` passes (Nothing was never requested); a page in Georgia fails "none of the named font paths was requested"; a page whose stylesheet names `/fonts/Missing.woff2` (404) with that path given fails naming it | "every named path served 200" (the italic case fails); "any named path served 200" (the 404 case passes) |
| `test_a_shot_whose_browser_dies_does_not_stop_the_run_and_the_run_exits_1` | fake browser exits 1 for one of two URLs; `main()` returns 1, the other PNG exists, `meta.json` lists one shot and one failure | the `except (RuntimeError, ValueError)` in `one()` narrowed to `ValueError`; the exit-code line |
| `test_browser_firefox_without_playwright_exits_3_and_names_the_install` | with `sys.modules["playwright"] = None`, `main([… "--browser", "firefox"])` exits 3 and prints `SKIPPED, NOT PASSED` with `requirements-platform.txt` and `playwright install firefox` | exit code 0 or 1; the install command dropped |
| `test_firefox_shot_is_verified_by_the_same_server_proofs` (firefox) | on the `site` fixture, `shoot(..., browser="firefox", require_family="Probe", font_url=[…])` passes on the Probe page (`ua` contains `Firefox/`, `font == "loaded"`, the probe count ≥ 1) and raises on the Georgia page with the same message as Chrome | the launcher skipping the beacon wait (the Georgia page passes with `font` None); the cookie not sent (Playwright context with cookies disabled: the beacon is ignored and the shot fails even on the Probe page, which is the other direction, so this mutation proves the proofs run, not that they pass) |

**`tests/test_shoot.py`, specimen part (A2t)**

| Test | Asserts | Mutation |
|---|---|---|
| `test_specimen_gives_every_family_row_a_unique_data_fd_row_key` | every `<p class="f…">` in the neutral specimen carries `data-fd-row`; keys are unique; the proof rows' keys are exactly `spacing-lower`, `spacing-upper`, `spacing-figures`, `spacing-punct`, `legibility`, `junctions`; the readable keys carry the surface name | the surface dropped from the readable key (paper and cloth collide); `row()` writing the attribute only when `attrs` is given |
| `test_specimen_refuses_a_duplicate_row_key` | `build()` with a forged duplicate (a surface list naming `paper` twice) raises naming the key | the uniqueness check removed |

**`tests/test_compare_shots.py` (B1t)**, on legs built in tmp: PNGs drawn with Pillow (a dark bar per row at
the box the rows file names, red-fringed in one leg, one leg on a dark "cloth" background), `rows.json` and
`meta.json` written by the test from the schema in section 2.2 (the schema is the contract), and one test
(`test_compare_reads_a_rows_file_shoot_py_wrote`, chrome) runs `shoot.py --rows --meta` for real on the `site`
fixture and feeds the result in, so the two tools are proved to agree on the shipped files.

| Test | Asserts | Mutation |
|---|---|---|
| `test_compare_writes_one_image_per_row_at_the_zoom_with_every_leg_in_order` | two legs, three rows: three PNGs named `<page>-<key>@1x.png`, each `zoom × (w+4) × scale` wide and `legs × (zoom × (h+4) × scale + label)` tall; the second leg's crop is below the first's | the zoom ignored; a leg dropped; the order reversed |
| `test_compare_refuses_a_bad_leg_and_still_compares_the_others` (F007) | three legs, one without meta: `compare.md` lists it under "Refused", the other two are compared, exit 0; with `--min-legs 3` exit 1 and `compare.md` still written | the refusal raising instead of continuing; the exit code ignoring `--min-legs` |
| `test_compare_refuses_a_png_without_rows_and_a_scrolled_shot` (F005) | a shot in `meta.shots` without its `.rows.json`, and one with `scroll_y` 300: both under "Refused" with the reason, neither cropped | either check removed |
| `test_compare_pairs_rows_by_key_and_fields_not_by_key_alone` (F006) | `probe-2` in leg A is `"Title" 48px 400 normal` and in leg B `"Byline" 16px 400 italic`: listed under "Mismatched" with both field sets, no PNG; the same key with equal fields is cropped | the field comparison dropped (the mismatch is cropped) |
| `test_compare_omits_a_row_a_leg_lacks_and_a_row_below_the_capture_and_says_so` | a key present in one leg only is under "Not in every leg" with the leg named; a `captured: false` row under "Below the capture"; neither has a PNG | the key intersection replaced by the first leg's keys |
| `test_compare_ink_is_measured_against_the_crops_own_background` (F011) | a dark bar on white and the same bar inverted on a near-black background give equal ink figures; a red (255,0,0) bar and a grey bar of equal luminance on white give equal figures; a crop whose border is a gradient prints `ink n/a` | `L_bg` fixed at 255 (the cloth crop reads near 1.0); `convert("L")` replaced by the R channel; the uniform-border check removed |
| `test_compare_md_orders_rows_by_font_size_ascending_and_labels_legs_from_meta` (F014) | the first row listed is the smallest `font_size`; each leg's heading carries the `ua` browser token and the platform, not the directory name; a Windows meta with `FontSmoothingType` 2 and `FontSmoothingOrientation` 1 is labelled `ClearType, RGB`, with type 1 `grayscale`, with `FontSmoothing` `"0"` `smoothing off` | the sort removed; the label from `dir.name`; the label read from `FontSmoothing` |
| `test_compare_reads_several_meta_files_in_one_leg` | a leg with `meta-specimen.json` and `meta-pages.json`: shots from both are compared | only `meta.json` read |

**`tests/test_check_env.py` (E1t)**: `test_check_env_reports_playwright_as_optional_with_the_install_command`
(with `sys.modules["playwright"] = None`, the row says `optional: playwright not installed` and names
`requirements-platform.txt` and `playwright install firefox`; exit code unchanged). Mutation: the row made
required (exit 1); the install command dropped.

**`tests/test_ci_workflow.py` (C1t)**, text checks stated as such:

| Test | Asserts | Mutation |
|---|---|---|
| `test_the_platform_template_is_manual_runs_three_oses_and_two_browsers_without_fail_fast_and_compares_whatever_finished` | `templates/platform-shots.yml`: `on:` is `workflow_dispatch` only, with inputs `pages`, `scales`, `font_urls`, `family`, `browsers` (F013); the matrix lists the three `-latest` labels and `[chrome, firefox]`; `fail-fast: false`; both jobs have `timeout-minutes`; the compare job has `needs: shots` and `if: always()`, and so do both upload steps (F007); every `run:` step runs under `shell: bash`; both shoot lines carry `--family`, `--rows`, `--meta`, `--bands none`, `--browser`, and the specimen line `--height 6000` (F004); the download step has `pattern`, `path: legs` and `merge-multiple: false`, and the compare line reads `legs/*/` (F001); the Firefox install step is conditioned on `matrix.browser == 'firefox'`; the `FD_BUILD` step exists and is conditioned on the slot being non-empty (F002); the specimen steps are conditioned on `FD_FONT_JSON` (H1) | each clause removed in turn; `--family` dropped (a picture, not evidence); `merge-multiple: true`; the download `path` removed |
| `test_the_template_quotes_every_expansion` (F008) | no `$FD_` or `${FD_` expansion in a `run:` line stands outside double quotes except the array expansions `"${PAGES[@]}"` and `"${FONT_URL_ARGS[@]}"`, which must be quoted that way | `--family $FD_FAMILY` unquoted |
| `test_the_template_run_lines_use_flags_the_scripts_parse` | every `--flag` in the template's `run:` lines that name `shoot.py`, `specimen.py` or `compare-shots.py` is in `registered_flags()` of that script (imported from `tests/test_docs_commands.py`: the shipped checker, not a copy) | `--meta` misspelled in the template |
| `test_the_template_pins_what_the_requirements_files_pin` | the template's `fonttools` spec equals `requirements.txt`'s; its literal `playwright==` fallback equals `requirements-platform.txt`'s | a pin changed in one file |
| `test_the_skills_platform_workflow_is_the_template_with_the_neutral_slots_filled` | `.github/workflows/platform-shots.yml` equals the template after the slot values are substituted, with exactly two additions: the `pytest -k` step (F010) and the `pull_request` trigger with its `paths` | a step edited in one file only; a path dropped |
| `test_every_workflow_parses_as_yaml` (extended) | the glob gains `templates/*.yml`; the template parses as is (the slots are plain `env:` values, no `{{`) | a `run:` scalar with an unquoted `: ` |
| `test_the_chrome_job_runs_compare_shots_on_the_tall_specimen_leg` | `smoke.sh` step 9 passes `--rows --meta --height 6000` and runs `compare-shots.py … --min-legs 1` and greps `"captured": true` | either flag removed |

**`references/testing.md` section 8** gets a block "Added with the platform shots (0.3)" listing every row
above with the date each was watched red, and any survivor found while writing them, in the file's own voice
**(read: the 0.2 blocks, lines 355 on)**.

---

## 8. Docs in the same change

| File | Change |
|---|---|
| `SKILL.md` | version line and frontmatter `version: 0.3.0`; `compatibility` gains "optionally GitHub Actions and `playwright` (requirements-platform.txt) for the cross-platform rendering shots" (≈ 90 characters, 408 → under 500); phase 8: two sentences on when the platform run is made and how `compare.md` is read (6.1); section 3 line 417; section 5 tool table: `shoot.py` row gains `--browser`, `--rows`, `--meta`, repeatable `--font-url`, fractional `--scales`; one new row each for `scripts/compare-shots.py` and `scripts/shoot_playwright.py` with their exact guarantees; section 6: `templates/` line names `platform-shots.yml`. Budget: ≤ 12 lines (478 → ≤ 490) |
| `README.md` | badge 0.3.0; Requirements paragraph: one sentence naming the template, `requirements-platform.txt` and that the Chrome legs need no new local dependency; Layout table's `templates/` row |
| `CHANGELOG.md` | `## [0.3.0] — <date>`, the `[Unreleased]` lint entry folded under it (ruling 3): Added (`compare-shots.py`, `shoot_playwright.py`, the template, the skill's own workflow, `--browser`, `--rows`, `--meta`, repeatable `--font-url`, `requirements-platform.txt`, the `check-env.py` row), Changed (`--scales` float, the Windows teardown, `specimen.py` row keys, the record template's Windows slot), the exact guarantee sentence, the cost line, "Designed, not built: WebKit" (2.5), the macOS Firefox profile failure as a Known issue, and the Impasse findings of section 14 under "Findings, kept because they are about how the work was done" |
| `VERSION`, `package.json` | 0.3.0 |
| `requirements-platform.txt` | new: `-r requirements.txt`, `playwright==1.64.1`, with the comment why this version (the Windows Firefox crash of 1.49.1) |
| `scripts/check-env.py` | `check_playwright()` optional row; header sentence |
| `references/review-loop.md` | section 2: the `compare-shots.py` bullet with the command and the `--browser firefox` line; section 9 rewritten around section 1.5's guarantee |
| `references/fallbacks.md` | "## Windows": the two-way statement (6.3); a new short "## No Playwright" paragraph (the Firefox leg is skipped loudly, the Chrome legs stand; the macOS profile failure) |
| `references/guidelines.md` | line 66 |
| `references/traps.md` | row 21 detection cell |
| `references/process.md` | phase 8 "Do." gains the platform run clause; phase 9 the record slot |
| `references/testing.md` | header function list; section 8 block (section 7) |
| `templates/font-record.md` | lines 134–136 and 170: the two-way slot (6.2) |
| `templates/reviewer-brief-design-round.md` | one optional slot: "`{{compare.md}}` from the platform run, when one was made; read Refused and Mismatched first, then the smallest sizes" |
| `templates/platform-shots.yml` | new; its header comment is the operator-facing doc (purpose, guarantee, cost with date, slots, the default-branch note) |
| `scripts/compare-shots.py`, `scripts/shoot_playwright.py`, `scripts/shoot.py`, `scripts/specimen.py` | module headers: WHAT IT'S FOR, usage, exact guarantee, in the repo's form; `shoot.py`'s item 5 rewritten for repeatable `--font-url`, item 1 gains the Firefox sentence, the Windows paragraph rewritten |
| `scripts/smoke.sh` | step 9's lines |
| `docs/plan-platform-shots.md` | this file. `tests/test_versions_and_skill.py::test_the_plan_is_kept_and_names_the_review_findings` reads `docs/plan.md` only **(read: lines 107–112)**, so no test names this plan; `SKILL.md`'s reference index does not list the 0.2 plan either **(read: section 6)**, so this one is not added there |

`examples/neutral/README.md` unchanged.

---

## 9. Version

**0.3.0 (operator ruling 3).** A new tool, a new launcher module, a new template, a new workflow, an optional
requirements file, three new `shoot.py` flags, two widened ones; every existing invocation and output name is
unchanged (section 1.2). The `[Unreleased]` lint additions **(read: `CHANGELOG.md` lines 6–14)** ship under
0.3.0.

---

## 10. Acceptance runs

In this order, on this machine, then on GitHub, before the Impasse diff review:

1. `.venv/bin/python3 -m pytest tests -q` (the repo suite with the new files; the chrome-named tests run
   here; the firefox-named tests skip with the recorded profile message if this Mac still shows it, and the
   skip line is pasted into the commit message).
2. `bash scripts/smoke.sh --full`: step 9 writes `out/smoke/shots-specimen/specimen-1280@1x.rows.json` with
   every row `captured: true` at `--height 6000`, `meta.json`, and `compare-shots.py` on that leg with
   `--min-legs 1` writes `compare.md` listing every specimen row once.
3. `.venv/bin/python3 scripts/shoot.py out/plat/mac --serve out/smoke/review --pages specimen.html --widths 1280 --scales 1 1.25 --height 6000 --family Sampler --font-url /fonts/Sampler-VF.woff2 --font-url /fonts/Sampler-Italic-VF.woff2 --rows --meta out/plat/mac/meta-specimen.json --bands none`
   exits 0, names `specimen-1280@1.25x.png`, and its `rows.json` has `captured: true` on every row and
   `scroll_y` 0.
4. Push the branch; open the pull request; the skill's `platform-shots.yml` runs on `pull_request` (section
   5.2): six legs, each artifact holding `meta-specimen.json` and `meta-pages.json` with a `ua` naming
   `HeadlessChrome` or `Firefox`, the Windows metas with four `font_smoothing` values, the per-leg `pytest -k`
   step green on Windows and macOS, and the `compare` job's summary showing every specimen row with six legs,
   nothing under "Refused" or "Mismatched". Download `platform-shots-compare`, read the legibility and junction
   rows at 1× and 1.25×, and record in the CHANGELOG what the neutral Sampler's hairline did on Windows in each
   browser (one sentence each; it is a fixture, so the finding is about the tool working, not the face). If
   the macOS Firefox leg fails with the profile error, record it, `exclude` it with the reason, and re-run.
5. Break one leg deliberately once (F013): dispatch with the `font_urls` input set to `/fonts/missing.woff2`;
   every leg exits 1 ("none of the named font paths was requested"), the compare job refuses all six (exit 1
   below `--min-legs`), the run is red, and the artifacts still hold the metas naming the failure. Then
   dispatch with `browsers` set to `chrome`: the three Firefox legs skip in seconds and the comparison has
   three legs. This is the workflow's own watch-it-fail.
6. `.venv/bin/python3 scripts/check-env.py` green with the new optional row; `ruff check scripts/ tests/`;
   `npm run check`; `npm run lint:js` unchanged.
7. Impasse review of `git diff --cached` with `templates/impasse-diff-instruction.txt`; reconcile; one
   re-review; one commit on `platform-shots`.

---

## 11. Risks, and what is out of scope

**Risks**

- **Headless, software-rasterised Chrome is not a reader's Chrome.** `--headless=new --disable-gpu`
  (`shoot.py` line 683 **(read)**) rasterises on the CPU; a reader's Chrome composites on the GPU. Glyphs are
  drawn by the same Skia text path with DirectWrite on Windows **(inferred)**, but this is the largest
  unverified link, and section 1.5's sentence names it.
- **Playwright's Firefox is not the image's Firefox.** It is Playwright's own build at the version 1.64.1
  bundles; a reader runs Mozilla's release. Same engine, different build and version; `ua` records which.
- **The runner's font-smoothing settings are the VM's.** `meta.json` records them so a reading is never
  detached from them.
- **Image drift.** Chrome 156 → 157 between the operator's run and the readme read today; the macOS label
  moved to macOS 26 arm64. Every PNG's `ua` and `platform` travel with it; `compare.md` prints them.
- **The rows POST can race the browser's exit.** Chrome under `--virtual-time-budget` exits when the budget
  is spent; Firefox when Playwright closes it after the sentinel attribute appears. A late rows POST fails the
  shot loudly (section 2.2 item 5), never writes a PNG without rows. `keepalive: true` is the mitigation
  **(inferred)**; the six-leg acceptance run is the check.
- **A 6000 px headless window.** Chrome's and Firefox's limits on viewport height are not known here
  **(inferred)**; acceptance steps 3 and 4 check `captured: true` on every specimen row in every leg. If a
  browser caps the height, the fallback is two specimen shots with `?fdtop=` offsets, out of scope until seen.
- **The Windows teardown is exercised only by a hang.** The grandchild test runs on the Windows leg of the
  skill's own workflow (F010); the clean path is what the shots exercise.
- **`SKILL.md`'s 500 lines.** 478 today; ≤ 12 added. If phase 8's sentences do not fit, they go to
  `review-loop.md` and `SKILL.md` keeps the tool-table rows and one clause.
- **A private site repo pays for macOS.** 80 % of the run's cost; the header shows the one-line matrix edit.
- **The first `workflow_dispatch` needs the file on the default branch** (section 0). The template header
  says so; the skill's own workflow has the `pull_request` trigger for the same reason.
- **`eval "$FD_BUILD"`** runs an operator-written command from the operator's own workflow file in the
  operator's own repository: the same trust as any `run:` line, stated in the header.

**Out of scope** (each named where it arose): WebKit and Safari (2.5, designed); Edge (same engine as Chrome,
unverified, one matrix entry away); Android and iOS; a pixel-difference verdict between platforms (they are
expected to differ; the tool shows, it does not judge); making the skill itself run on native Windows
(`smoke.sh`, the venv path); SHA-pinning the actions repo-wide; a real-display or GPU-rasterised shot;
publishing the shots as a merge gate; re-running the platform shots every round (one per face by default,
6.1); any change to the hairline floor rule itself; a reviewer agent reading `compare.md` for the host (the
host reads it, as 6.1 says).

---

## 12. Operator rulings (the former questions, answered 2026-11-17)

1. **Build the Firefox leg now** — ruled yes. Section 2.4 is built in this change: the optional Playwright
   launcher on `shoot.py`'s own server, tokenised URL and cookie proofs; `playwright==1.64.1` in
   `requirements-platform.txt`; a `check-env.py` optional row; a browser dimension in the template with
   Firefox installed only in its legs; loudly skipped when Playwright is absent; the macOS Firefox profile
   failure recorded. WebKit stays designed (2.5), with the reasons there.
2. **Record line, not a publication blocker** — ruled as recommended (6.2).
3. **Version 0.3.0 with the unreleased lint changes folded in** — ruled as recommended (9).

No question is open.

---

## 13. Work items

| id | title | kind | files | verifiable_by |
|---|---|---|---|---|
| P1 | Impasse review of this plan; findings reconciled in section 14 (done 2026-11-17) | docs | docs/plan-platform-shots.md | section 14 names every finding with its verdict and the evidence read or run |
| A1 | `shoot.py`: fractional `--scales` and `@{scale:g}x` names, `crop_bands` rounding, the three-part Windows teardown (taskkill-first `kill_group`, bounded EOF wait, `ignore_cleanup_errors` with the profile departure), `--meta FILE` with the Windows font-smoothing read, `ua` in the beacon, `--rows` (viewport boxes, scroll, `?fdh=`, the `/__fd/rows` POST recorded by cookie, `<png>.rows.json` after the proofs, "no rows arrived" failure), repeatable `--font-url` with the new item-5 guarantee, `--browser` dispatching to `shoot_playwright.capture()` | code | scripts/shoot.py | the 0.2 `tests/test_shoot.py` green unchanged; acceptance step 3 exits 0 and writes `specimen-1280@1.25x.png`, its `.rows.json` with every row captured, and `meta-specimen.json` |
| A1t | the sixteen `shoot.py` tests of section 7 (Python-fake browsers so they run on Windows), each watched red under its named mutation | test-new | tests/test_shoot.py | `.venv/bin/python3 -m pytest tests/test_shoot.py -q` green; each docstring names the mutation and the date it was red |
| A2 | `specimen.py`: `data-fd-row` keys on every family row, the duplicate-key refusal, the `row()` signature | code | scripts/specimen.py, scripts/specimen.html.tmpl | `smoke.sh` step 9's greps still pass; `test_specimen_gives_every_family_row_a_unique_data_fd_row_key` green |
| A2t | the two specimen tests | test-new | tests/test_shoot.py | green; red under the surface-less key |
| E1 | `scripts/shoot_playwright.py` (2.4): `capture()`, the exit-3 skip text, the settle rule, the macOS profile note; `requirements-platform.txt`; `check-env.py`'s `check_playwright()` | code | scripts/shoot_playwright.py, requirements-platform.txt, scripts/check-env.py | `shoot.py … --browser firefox` on the `site` fixture passes the Probe page on a machine where Firefox launches; exit 3 with the install text where Playwright is absent |
| E1t | `test_firefox_shot_is_verified_by_the_same_server_proofs`, `test_browser_firefox_without_playwright_exits_3_and_names_the_install`, `test_check_env_reports_playwright_as_optional_with_the_install_command` | test-new | tests/test_shoot_playwright.py, tests/test_check_env.py | green or loudly skipped with the profile message; red under the named mutations |
| B1 | `scripts/compare-shots.py` (section 4): per-leg acceptance and refusal, several `meta*.json`, labels from meta with the `FontSmoothingType` rule, key-and-fields pairing, crops at `--zoom`, background-relative ink, `compare.md`, `compare.json`, `--min-legs` | code | scripts/compare-shots.py | `compare-shots.py out/cmp out/plat/mac --min-legs 1` exits 0 and lists every specimen row once |
| B1t | the eight comparison tests, including the one that feeds a real `shoot.py --rows --meta` leg in | test-new | tests/test_compare_shots.py | green; each docstring names its mutation and date |
| C1 | `templates/platform-shots.yml` with its header (purpose, guarantee, cost with the date read, slots, the default-branch note), the inputs, the quoting, the `FD_BUILD` and `FD_FONT_JSON` conditions, the artifact paths; `.github/workflows/platform-shots.yml` as the template filled for the neutral fixture with the staging `FD_BUILD`, the per-leg `pytest -k` step and the `pull_request` paths | code | templates/platform-shots.yml, .github/workflows/platform-shots.yml | acceptance step 4: six green legs and a compare summary on the pull request |
| C1t | the seven workflow tests of section 7 (one extends `test_every_workflow_parses_as_yaml`) | test-new | tests/test_ci_workflow.py | green; red under `--family` dropped from the template's shoot line and under `merge-multiple: true` |
| C2 | `smoke.sh` step 9: `--rows --meta --height 6000`, the captured grep and the single-leg compare; `ci.yml` unchanged otherwise | code | scripts/smoke.sh | `bash scripts/smoke.sh --full --from 9` writes `compare.md`; `test_the_chrome_job_runs_compare_shots_on_the_tall_specimen_leg` green |
| D1 | the docs of section 8 except the version files and `check-env.py`: SKILL.md phase 8, section 3, tool table, index; README; review-loop 2 and 9; fallbacks (Windows, No Playwright); guidelines 66; traps 21; process 8–9; testing.md header and section 8; the record and brief templates | docs | SKILL.md, README.md, references/review-loop.md, references/fallbacks.md, references/guidelines.md, references/traps.md, references/process.md, references/testing.md, templates/font-record.md, templates/reviewer-brief-design-round.md | `pytest tests/test_docs_commands.py tests/test_versions_and_skill.py -q` green; `wc -l SKILL.md` ≤ 490 |
| D2 | the platform run on the pull request read and recorded: six metas, the compare summary, the missing-font and chrome-only dispatches (acceptance steps 4 and 5); the macOS Firefox leg's outcome | live-acceptance |  | the run ids and the per-browser Sampler sentences pasted into the CHANGELOG entry and the commit message |
| H1 | integration: VERSION, package.json, SKILL.md frontmatter and version line, README badge, `CHANGELOG.md` `[0.3.0]` from the handbacks with the lint entry folded in and the "Designed, not built: WebKit" heading | docs | VERSION, package.json, SKILL.md, README.md, CHANGELOG.md | `pytest tests/test_versions_and_skill.py -q` green |
| H2 | acceptance runs 1–3 and 6 of section 10 | live-acceptance |  | the outputs pasted into the commit message |
| H3 | Impasse review of the staged diff, reconcile, one re-review, commit | live-acceptance |  | the review record names every finding and its verdict; one commit on `platform-shots` |

File ownership (no file has two writers): **A** owns `scripts/shoot.py`, `scripts/specimen.py`,
`scripts/specimen.html.tmpl`, `tests/test_shoot.py`; **E** owns `scripts/shoot_playwright.py`,
`requirements-platform.txt`, `scripts/check-env.py`, `tests/test_shoot_playwright.py`, `tests/test_check_env.py`
(E's Firefox proof test lives in its own file so A and E share none); **B** owns `scripts/compare-shots.py`,
`tests/test_compare_shots.py`; **C** owns `templates/platform-shots.yml`, `.github/workflows/platform-shots.yml`,
`scripts/smoke.sh`, `tests/test_ci_workflow.py`; **D** owns the references and templates of D1; **H** the
version files. The seams are fixed in this plan: A and E meet at `capture()`'s signature and the exit-3 text
(2.4); A and B at the `rows.json` and `meta*.json` schemas (2.2, 3); C at the flag names. A, B and E run in
parallel on those; C after A's flags exist (it can be drafted against the plan); D needs nothing from the code.
Split before implementing: A, B and E are the three long items and share no file.

---

## 14. Plan review reconciliation (Impasse, cross-provider, 2026-11-17)

Fourteen findings accepted from the first draft, plus one host finding. Each was checked against the code or
the plan before the body changed; where this section and an earlier section disagree, the body already
carries the change.

| # | Finding | Checked how | Verdict | What changed |
|---|---|---|---|---|
| F001 (critical) | `download-artifact@v4` with `pattern`, `merge-multiple: false` and no `path` puts each artifact in `./<artifact-name>/`, and uploading `shots/` stored `<os>/…` inside it, so the compare line's `shots/*/` named nothing | the action's documented layout (reviewer); the first draft's upload path `shots/` and download without `path` (read in the draft) | accepted | 5.1: each leg uploads its own directory `leg/` under the name `platform-shots-<os>-<browser>`, so the artifact root holds `meta*.json`; the download names `path: legs` with `merge-multiple: false`, and the compare line reads `legs/*/`; `test_the_platform_template_…` holds `pattern`, `path`, `merge-multiple: false` and the glob, red under `merge-multiple: true` |
| F002 | No step builds or stages `FD_SERVE`; a site that builds its root in CI, and the skill's own fixture, had nothing to serve | the first draft's step list (read); `smoke.sh` step 11 stages the fixture site (read: lines 238–270) | accepted | 5.1: an `FD_BUILD` slot run under `eval` when non-empty (empty for a committed root); 5.2: the skill's workflow sets it to the neutral build plus the fixture staging step 11 does; the template test holds the conditioned step |
| F003 | Windows teardown: `taskkill /T` must run before `p.kill()`; `run_chrome()` waits for stdout EOF, which a surviving helper holds; `TemporaryDirectory` cleanup raises on Windows while a helper holds the profile, outside the `OSError` handling | `shoot.py` 629 (`rc is not None and eof.is_set()`), 641 (`join(timeout=10)`), 677 (`with TemporaryDirectory`), 692–697 (the `except OSError` covers the launch only) (read); `tempfile.py` 939 `ignore_cleanup_errors` (read) | accepted | 2.2 item 2 designs all three: taskkill first then `p.kill()`, a bounded EOF wait after a kill or after the grace, `ignore_cleanup_errors=True` plus a `NOTE:` departure naming a leftover profile; three tests in 7 (`test_kill_group_ends_a_grandchild…`, `test_run_chrome_returns_after_a_kill…`, `test_shoot_notes_a_profile_directory…`) |
| F004 | The specimen's last ink is about 5,368 px at 1280 (`specimen.py` 251–252) against the default 2400 capture; most rows would be below the shot and the acceptance claims assumed otherwise | `specimen.py` 251–252 and `shoot.DEFAULT_HEIGHT` 159 (read) | accepted | 3: the specimen is shot in its own invocation with `--height 6000`; `captured` is the check; `smoke.sh` step 9 greps it; acceptance steps 2–4 assert every row captured; a browser height cap is a named risk (11) |
| F005 | Document coordinates (rect + `scrollY`) are not PNG coordinates for a viewport screenshot once the page scrolled; the planned test scrolled a row into place and would have asserted the wrong thing | the semantics of `getBoundingClientRect()` and a `--window-size` screenshot (reviewer; read from memory here) | accepted | 2.2 item 5: viewport coordinates, `scroll_x`/`scroll_y`/`viewport_*` recorded once per shot, `compare-shots.py` refuses a scrolled shot; the scrolled test now asserts the offset is recorded (`test_chrome_a_page_that_scrolled_records_the_offset`) and `test_compare_refuses_a_png_without_rows_and_a_scrolled_shot` holds the refusal |
| F006 | Positional `probe-<n>` keys can pair different elements across legs (a leg with one more visible element shifts every later key) | the first draft's key rule (read) | accepted | 4.1 item 3: a key is compared only when `text`, `font_size`, `font_weight`, `font_style` are equal across legs; otherwise "Mismatched" with the fields; `test_compare_pairs_rows_by_key_and_fields_not_by_key_alone` |
| F007 | A bad leg (no meta, no verified shot) exited 2 and stopped the comparison of the others; the compare upload was not `if: always()` | the first draft's 4.1 item 1 and 5.1 (read) | accepted | 4.1 item 1: refuse the leg, continue, "Refused" list, exit non-zero only below `--min-legs`; 5.1: both uploads `if: always()`; `test_compare_refuses_a_bad_leg_and_still_compares_the_others` |
| F008 | Unquoted shell expansions in the template (`--family $FD_FAMILY`; family names have spaces); `FD_PAGES` as a bare string | the first draft's step list (read) | accepted | 5.1: every expansion quoted, multi-line slots read with `mapfile -t` into arrays, `"${PAGES[@]}"`, `"${FONT_URL_ARGS[@]}"`; `test_the_template_quotes_every_expansion` |
| F009 | `900 × 1.25 = 1125` exactly, so the rounding test could not fail | arithmetic | accepted | 7: band `head:0:901` (1126.25 → 1126); the test's docstring says why 900 was unusable |
| F010 | The kill test must spawn a grandchild that inherits stdout (the real failure mode), and should run on the Windows leg of the skill's own workflow | `run_chrome()` 617–629: the pipe is what a helper holds (read) | accepted | 7: `test_kill_group_ends_a_grandchild_that_holds_stdout` with a Python grandchild sleeping on the inherited pipe; fake browsers are Python one-liners so the tests run on Windows; 5.2: a per-leg `pytest -k "kill_group or fractional or meta or rows"` step in the skill's workflow |
| F011 | `255 − L` over the crop measures the background on dark surfaces (the cloth rows), so the ink share would be meaningless there | `specimen.py` surfaces: `cloth` is `#1d2a3a` with light ink (read: `examples/neutral/font.json` `review.surfaces`) | accepted | 4.1 item 5: ink is the mean of `|L − L_bg|` against the median luminance of the crop's one-pixel border; a non-uniform border prints `ink n/a`; `test_compare_ink_is_measured_against_the_crops_own_background` with a cloth crop |
| F013 | Acceptance step 5 dispatched a changed `FD_FONT_URL`, which was an `env` slot, not a `workflow_dispatch` input | the first draft's `on:` block (read) | accepted | 5.1: inputs `pages`, `scales`, `font_urls`, `family`, `browsers`, each overriding its slot when given; 10 step 5 uses `font_urls` and `browsers`; the template test holds the inputs |
| F014 | The ClearType label was to be read from `FontSmoothing` (the on/off flag); ClearType is `FontSmoothingType` 2, and the orientation `FontSmoothingOrientation` | the one-off's `smoothing()` keys (read: lines 89–93) and the operator's recorded values (FontSmoothingType 2, RGB) | accepted | 4.1 item 2 and section 0's one-off row; `test_compare_md_orders_rows…` holds the three label cases, red when read from `FontSmoothing` |
| F015 | The cost was computed as $0.24; at the page's rates a three-leg run of 1.5 minutes is about $0.12 (1.5 × $0.078) | arithmetic on section 0's prices | accepted | 5.1: $0.12 for the three Chrome legs, about $0.30 for six legs with Firefox (2.5 minutes each for the browser download, an estimate the acceptance run replaces); section 0's billing row names the $0.078 sum |
| H1 (host) | `specimen.py` needs the skill's `font.json`; a site whose font the skill did not build (movingavg.com's Driftwood: five static woff2, no `font.json`) must run pages-only; pages there load several woff2 files, and `--font-url` takes one path | `specimen.py` `--font` required (read: line 387); `shoot.py` `--font-url` single (read: 830, 720–728) | accepted | 3: `FD_FONT_JSON` empty skips the specimen step and shot (pages-only legs); 2.2 item 6: `--font-url` repeatable with the exact guarantee "every named path this shot requested was served 200, and at least one was requested"; `FD_FONT_URLS` multi-line; `test_chrome_font_urls_pass_when_each_requested_one_is_served…` |

No finding was rejected. F012 was not among the accepted findings handed back and has no row. The three
operator rulings (section 12) are decisions, not findings, and changed sections 1.1, 2.1, 2.4, 2.5, 6.2, 9
and the work items (E1, E1t added; A1 gains `--browser`; ownership split so `shoot.py` and the launcher have
different writers).
