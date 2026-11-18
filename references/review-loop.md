# The design-review loop: build, shoot, a fresh reviewer, change, repeat (≤ 6 rounds)

WHAT IT'S FOR: the protocol for phase 8. The font that leaves phase 7 passes every self-check and
every test, and none of those can see what a reader sees. The loop puts the built font on the
site's real pages and a specimen, screenshots them, hands the crops to a reviewer who has not seen
the build, ranks what comes back by what is visible at 1× on a real page, changes the font, and
goes again until a round finds nothing. Read it before the first round, and read "What a
screenshot proves" before writing the record.

Contents: 1 the round · 2 the tools · 3 the checklist · 4 the fresh-reviewer rule · 5 ranking ·
6 host spot-checks and one mutation · 7 stop rule · 8 the enlarged-root check · 9 what a
screenshot proves · 10 cost

## 1. The round

```
build  →  diff.py (against the previous round's out/, round 2 on)  →  specimen.py
       →  shoot.py (pages × widths × 1×/2×, plus --root 150)
       →  the 360 px reading on EVERY page with the wired font (narrow.html; section 2)
       →  a FRESH reviewer reads every crop against the checklist, with the brief template, the
          operator's goal sentence verbatim and the diff (what changed since the last round)
       →  ranked findings, each naming its crop
       →  parameter / skeleton / kerning changes
       →  the host spot-checks two crops itself and runs one mutation of its own
       →  the suite green  →  copy out/ to work/round-N/ (cp -R)  →  next round
```

Every round ends with the full suite green. The font is not changed between rounds without a
round. Bract took three rounds; Driftwood's versions v1 to 1.000 were the same loop before the
protocol was written down.

## 2. The tools

- **`scripts/build.py --font font.json`** writes the woff2 the pages load.
- **`scripts/diff.py`** pixel-diffs two builds, so a round's reviewer is told where the words moved instead of
  finding it out. Before each build the host copies `out/` to `work/round-N/` (`cp -R`, never `rm`); after
  the build, `.venv/bin/python3 scripts/diff.py work/diff-N --font font.json --before work/round-N` renders every
  title (and `review.wordmark`) at every size in `review.sizes` and every named instance of every group, from the old and the new
  files, and writes `diff.md` (the changed renders, largest share of moved ink first, then "N of M renders
  unchanged"), `diff.json` and a before / after / diff PNG for each changed render (red: more ink after, blue:
  less). Use a fresh directory per round; a PNG from an earlier run is not removed. It exits 0 whether or not
  anything changed, and 2 when either folder lacks a group's file. What it proves: what FreeType drew on
  this machine from the two files, unhinted, laid out with GPOS kerning (raqm), at these sizes; not CoreText, not
  Chrome and not the page's CSS. It renders through the one-instruction `fpgm` that `build.py`'s raster checks
  use, because FreeType autohints the shipped fonts as they are (the neutral roman's `prep` does not prevent
  it: removing it changed nothing, adding the `fpgm` changed `B` at 16 px by 212 grey levels, measured
  2026-11-16, trap 2), and the autohinter would add pixel jumps of its own to a diff. A render also counts as changed when the title's advance width moves by more than 0.02 CSS px (a
  last glyph's advance can move with no ink moving); `diff.md` lists the two widths. A glyph none of the
  titles uses does not show. To compare the font tables themselves, `ttx -s` the two files and diff the
  folders; `diff.py` does not.
- **`scripts/specimen.py`** renders `scripts/specimen.html.tmpl` from `font.json`: the project's
  real titles at every size in `review.sizes`, weights as the site uses them (Medium under
  `medium_below_px`), every surface in `review.surfaces`, the comparison faces (local woff2 or a
  Google Fonts URL), the opsz crossing rows (39, 40, 44, 48 and the intermediate instances such as
  wght 550 / opsz 60), a kerning row, an NBSP-wrap row and a quotes row, with the proof rows FIRST (a default shot is 2400
  CSS px tall and rows at the end of the page fell outside it; the page writes `data-fd-proof-bottom`): spacing
  control strings (each lowercase letter x as `nnxnn ooxoo`, each capital as `HHXHH OOXOO`, each figure
  as `00d00 11d11`, each punctuation mark after `r`, `f` and `y`) and a legibility row, `Il1 O0 B8 rn m
  cl d`, at the smallest review size. They hold only characters the font maps (a group whose control
  letters are unmapped is left out, a word with an unmapped character is dropped) and a junction row
  (`1 4 5 v w A M N V W AVAWMNW vwvwv`, in the Bold at the smallest review size; marked `data-fd-junctions`),
  the glyphs where two strokes meet end to end, where a joint that fills in reads as a blot.
- **`scripts/shoot.py --serve DIR --font-url PATH --pages ... --widths 500 667 889 1280 1600`**
  serves the built site and the specimen from a self-terminating `http.server` on a free port and
  shoots each page at 1× and 2× (`--force-device-scale-factor=2`). 667 and 889 are where Bract's
  contents and essay H1s crossed 40 px, the start of the opsz axis; choose the widths where your
  fluid sizes cross the axis. `--root 150` injects `html{font-size:150%}` to see rem-sized type at
  a reader's enlarged default (section 8). Widths under 500 are refused (trap 7). A shot fails
  unless the page and the font were served 200 for that shot's token, Chrome exited 0, the PNG is
  new and the page's DOM sentinel says the family loaded (trap 15). Crops of fixed bands are
  written beside each PNG so a finding can name its crop.
- **`scripts/narrow.html`, the 360 px reading, on every page, every round.** Phase 1 measured the
  pages in the face being replaced; a wider face overflows a title that fit (the fixture site's
  NBSP-joined frontispiece title at 48 px: 360 px in Georgia, 384 in Sampler, which `smoke.sh` step
  11 proves on every run). Per page:
  `shoot.py OUT --serve <site root> --pages __fd/narrow.html --widths 500 --scales 1 --dump-dom --no-sentinel --query url=/<page>.html --query width=360 --query family=<Family>`,
  then read the dumped `.dom.html`: the page passes only with `data-fd-overflow="false"` at
  `data-fd-narrow-stage="fonts"` (the `load`-stage reading was taken before the web font applied),
  which `narrow.html` writes only when the inner page was served 200, none of its faces failed and a
  face of the family loaded (`data-fd-narrow-inner-http`, `data-fd-narrow-fonts-failed`,
  `data-fd-narrow-family`); a 404 page or a page without its font lays out narrow too, and reads
  `error`.
  An overflow outranks every other finding (every phone shows it) and is fixed in the CSS or the
  content in the same round; a page still overflowing at the last round is a publication blocker
  (`SKILL.md` section 4). `narrow_verdict()` in `shoot.py` reads the two attributes.
- **The platform run: `templates/platform-shots.yml` and `scripts/compare-shots.py`.** It answers one
  question the local shots cannot: does the face hold up in other browsers on other operating systems,
  above all the hairlines at the smallest sizes under Windows' DirectWrite. It is made once per face, not
  every round (section 7 says when). The operator copies the template to
  `<site>/.github/workflows/platform-shots.yml`, fills its `env:` slots (the template's header says what
  each one holds: the site's copy of `scripts/`, the built root, the command that builds it, the family, the
  font paths, the pages, the `font.json`, the scales), commits it to the default branch (a first
  `workflow_dispatch` needs it there), and runs `gh workflow run platform-shots.yml`. Each **leg** is one
  runner OS and one browser: Windows Server, macOS and Ubuntu runners, each in Chrome and in Playwright's
  Firefox. A leg runs the site's copy of `shoot.py` at 1280 px and device scales 1 and 1.25 on the
  specimen (only when the site has a `font.json`; shot with `--height 6000` and `--require-captured`, so a row
  below the capture fails the leg instead of dropping out of the comparison) and on the named pages, always with `--family`, `--font-url`, `--rows` and `--meta`. Then a
  compare job runs `compare-shots.py` over every leg that finished. Read the result with
  `gh run download -n platform-shots-compare`: `compare.md` and one PNG per row.
  - `--browser firefox` shoots through `scripts/shoot_playwright.py` (Playwright's own Firefox build,
    pinned by `requirements-platform.txt` to `playwright==1.64.1`) and runs the same server proofs as a
    Chrome shot. It is optional: install it with `.venv/bin/pip install -r requirements-platform.txt`, then
    `.venv/bin/python3 -m playwright install firefox`. Without the package, `shoot.py --browser firefox`
    exits 3 with `SKIPPED, NOT PASSED` and that command (references/fallbacks.md, "No Playwright").
  - `--rows` writes `<png>.rows.json` beside each PNG, only after that shot's proofs passed: the box of
    every `data-fd-row` element and of every element the probe counted, in viewport CSS px, with its text
    and computed size, weight and style, and the page's scroll offset. `--meta FILE` writes the platform,
    the browser and its user agent, the Windows font-smoothing registry values, the verified shots and the
    failures; it changes no verdict. `--font-url` may repeat, for a family in several files: every named
    path the shot requested must be served 200, and at least one must be requested. `--scales` takes
    fractions (1.25 writes `@1.25x`).
  - `.venv/bin/python3 scripts/compare-shots.py OUT LEG_DIR LEG_DIR --zoom 4 --min-legs 2` crops each row
    from every leg, zooms it with nearest-neighbour resampling (subpixel colour is kept: it is part of the
    finding), labels it from the leg's meta (OS, browser version, scale, ClearType setting), and stacks the
    legs in one PNG. It refuses a leg without a meta file, a PNG without its rows file and a scrolled shot,
    and compares the rest; it exits 1 only when fewer than `--min-legs` legs were accepted. A row is paired
    across legs only when its key, text and computed style are equal in every leg; otherwise it is listed
    under "Mismatched". Its ink share per leg is a hint of where to look; the PNG is the evidence.
  - Read `compare.md` top-down: "Refused" and "Mismatched" first, then the rows, which come smallest size
    first. Rank what it shows as section 5 says. What the run proves is section 9's paragraph.
- Chrome is found through `$CHROME`, then per-OS defaults. Without Chrome, see
  references/fallbacks.md: the loop cannot end on "nothing visible at 1×", and missing browser
  evidence blocks publication unless the operator waives it in writing; the waiver is recorded in
  the font record and stated in the shipped docs.

The flags above are the scripts' own; `tests/test_docs_commands.py` checks every documented flag
against the script that parses it.

## 3. The checklist

The reviewer reads every crop against these, in this order (Bract's plan, section 7):

1. **Readable** at every size the site uses: the smallest sizes in Medium on the main surface
   (open counters, hairlines present, NBSP honoured, curly apostrophes); the Bold at heading sizes
   (no clogging, serifs grown but not slab, the wordmark on its dark surface); the Regular at the
   large sizes (reads as intended, not brittle; descenders clear at the site's tight
   `line-height`).
2. **Smooth across opsz**: the crossing rows (39 vs 40 vs 44 vs 48) and the fluid H1 at the widths
   where it crosses the axis.
3. **Unique**: beside the face it replaces and the body face at two sizes (Bract: 28 and 48 px).
4. **Complements** the brand: the surfaces and the chrome it sits in; harmony with the body face.
5. **Spacing, then kerning.** Read the control strings first, for rhythm: a letter that crowds or
   gaps between `nn`/`oo` (lowercase), `HH`/`OO` (capitals) or `00`/`11` (figures) is a spacing
   finding, and a spacing finding is fixed before any kern is added to cover it (a Glyphs tutorial's
   heuristic: many pairs under 10 units mean the spacing is off, not the kerning). Then punctuation after `r f y`, the
   pair row and the real titles.
6. **Rendering integrity**: no seams at overlaps at 2×, no tofu, no `gvar` dropouts at an
   intermediate opsz.
7. **Fits at 360 px**: the `narrow.html` reading of every page, with the wired font, says
   `data-fd-overflow="false"` at stage `fonts` (section 2). The host runs it; the reviewer reads
   the verdicts and names the page and the element when one overflows.
8. **Legibility at the smallest size**: the row `Il1 O0 B8 rn m cl d` at the smallest display size
   the site sets. Say which pairs read as one another (`I` and `l` and `1`, `O` and `0`, `rn` and
   `m`, `cl` and `d`) and whether the site can tolerate it there. Do not ask for a "dyslexia font":
   the research behind this skill found no evidence that one helps.
9. **Junctions at the smallest size**: the junction row at the smallest review size, in the Bold. Say
   which of `1 4 5 v w A M N V W` close up or darken where two strokes meet (a blot, a filled crotch) and
   whether the site can tolerate it at that size. `y` and `k` are not in the row because their strokes
   cross and do not end on each other.

## 4. The fresh-reviewer rule

Each round's reviewer is a **new subagent context** that has not seen the build or the previous
round. Give it `templates/reviewer-brief-design-round.md` filled in: the operator's goal sentence
**verbatim** (Bract: "a readable and unique font that complements the design and branding"), the
checklist, the crop directory, the sizes and surfaces, and what changed since the last round
(parameters and numbers, not verdicts) and, from round 2, `diff.md` of the last build against this one (the
reviewer may open the changed renders' PNGs, and must still read every crop against the checklist: a diff
shows what moved, not whether the new state is good). Do not give it the previous reviewer's findings; a
reviewer handed a hypothesis tends to return it confirmed. Use the strongest model available; if
none is above the host, label every verdict "same-model review" (references/fallbacks.md).

## 5. Ranking

Findings are ranked by **visibility at 1× on a real page**, then visible at 2×, then visible only
in the specimen. Each finding names its crop and says what it changes for the font (a parameter, a
skeleton, a kern) or for the site (a CSS rule). Bract round 1's top finding was "the Bold reads as a
different family" (seen at 1× on two H2s); its fix was `serifGrow` 0.6 → 0.35. A finding visible
only at 4× in the specimen is polish and goes to the record's open items if the loop stops first.

The platform run (section 2) ranks the same way. A stroke that breaks up or drops out at 1× on a real
page in any leg is a 1× finding, fixed in the design (`thin`, Medium under the smallest sizes, the floor;
`references/guidelines.md` section 2). A stroke that reads lighter but stays continuous is not a defect:
it goes in the record's rendering section with the compare PNG named. Reopening the loop for it is the
operator's call, as every round is.

## 6. Host spot-checks and one mutation

A subagent's finding is a lead, not a fact. Before changing the font the host opens **two crops
itself** and confirms the finding is there (Bract's round 2 measured the `t` foot instead of
changing it: at 1× its lowest ink row equalled the round letters' overshoot row; the finding was
accepted as "measured, not a defect"). The host also runs **one mutation of its own** per round on
a guard the round touched, so a changed test is watched to fail in the same session that changed
it. From round 2 on, aim the two spot-checks at the two largest `share` entries of `diff.md`: that is where the
round's change shows most, and a finding there is cheapest to confirm.

## 7. Stop rule

Stop when a round reports **nothing visible at 1× on a real page**, every page fits at 360 px with
the wired font, and the suite, self-checks and size budget are green; or at **round 6**, when what
remains is visible only at 2× or in the specimen, recorded as open items for the operator to decide
on. At round 6 with a defect still visible at 1× on a real page, or a page still overflowing at
360 px, stop before phase 9 and ask the operator: revise the design (back to phase 5 or 6) or leave
the face unshipped; that defect is a publication blocker (`SKILL.md` section 4), and the round limit
does not turn it into an open item. The operator may cap the rounds earlier (section 10). Bract stopped at
round 3: the face met the goal, no font defect was visible at 1×, and the remaining items (Bold
capital `I` serifs heavy at 24–30 px; `r.` at 80 px overhanging after the arm was lengthened) went
to the record as polish.

**The platform run** (section 2) comes after the round that would end the loop (or round 6), and at
any round the operator asks for. One run per face is enough, because the question it answers changes
only when the design's `thin`, the floors or the smallest sizes change; a round that changes those
re-runs it. It is not a publication blocker: an operator may have no GitHub Actions. Without a run the
record says "not checked on Windows" with the claim it limits.

## 8. The enlarged-root check

Rem sizes scale with the reader's default font size, so a region of the design space no CSS rule
reaches at a 16 px root is reachable at 24 px (trap 8). `shoot.py --root 150` renders the pages as
a 24 px root would. Bract's reading: at 1280 px the Bold H2s came out at 41 px (the `clamp()` was
governed by `3.2vw`; the 2.2 rem maximum needs a viewport over 1650 px), one unit into the opsz
range; at 1× nothing was visible. That is one width and one size, not a review of the (Bold,
opsz > 40) region; the record says so and lists the rest as unchecked. Run the check every round
that touches the Bold or the display cut, and write what it did and did not cover.

## 9. What a screenshot proves, and does not

A PNG from `shoot.py` on the operator's machine is what Chrome's headless renderer drew on that
machine (CoreText on a Mac), with the font the server logged as 200 for that shot. By itself it proves
nothing about Safari, Firefox, Windows (DirectWrite), Android or iOS, and nothing about the browser's
`opsz` choice unless `scripts/opsz.py` measured it.

**The platform run's exact guarantee** (section 2; every other document that names the run refers here).
A leg's PNG is what the recorded browser drew: Chrome of the recorded version, headless with
`--disable-gpu`, or Playwright's Firefox of the recorded version. It drew on a GitHub-hosted virtual
machine of the recorded OS (Windows Server, macOS and Ubuntu runners, as the leg's `meta*.json` records
them), with the recorded font-smoothing settings, no physical display, at the recorded device scale. The
shot passed the same served-200, sentinel, element and italic proofs as every other `shoot.py` shot.
A GitHub-hosted runner is not a reader's laptop: the display, the scaling, the ClearType tuning, the
browser version and the GPU raster path all differ. Playwright's Firefox is not the Firefox build a
reader installs. The run does not check Safari, Edge, phones or a real display. A run that was never
made proves nothing, so the record says either "checked on Windows: run <id>, <what it showed>" or "not
checked on Windows", never "fine on Windows". `compare-shots.py` shows the legs side by side and does not
judge them: platforms are expected to differ.

Two readings a screenshot cannot replace: a unit test (a rendering
check is evidence, kept with the record, not a test that runs in CI), and the operator's own eyes
on the deployed page. Screenshots are not tracked in the repo; the record names the directory and
`shoot.py` reproduces them.

## 10. Cost

Six rounds with a fresh strong-model reviewer each round is the expensive part of the whole skill:
each round is a build, a full shoot (Bract: 8 pages × 5 widths × 2 scales plus the specimen), and
a long reviewer context reading dozens of crops. Say so to the operator before round 1 and let them
cap the rounds; a cap below 6 is recorded in the record with the open items it leaves. A round
that changes nothing but polish is a reason to stop, not to spend another.
