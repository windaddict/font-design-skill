# Fallbacks: what to do when a tool the skill expects is missing

WHAT IT'S FOR: the skill assumes a strongest model for the design reviews, Impasse for the
independent plan and diff reviews, the frontend-design plugin for the aesthetic pass, Chrome for
the screenshots, claude.ai artifacts for the concept pages, and a Mac. Each can be absent. This
file says, for each, what the skill still does, what it must say it did not do, and what it must
never do silently. Read it in "Before you start", when the tool check reports a gap.

The rule under every entry: **never skip a gate silently, and never let a weaker review read as a
stronger one.** Record every substitution in the plan's review section and the record.

## No strongest model (Fable)

Use the strongest model the Agent tool offers. If none is above the host, run each review in a
**fresh subagent context** of the host model, with the brief template and no memory of the build,
and label every verdict "same-model review — breadth, not independence". Never let the builder's
own context be the reviewer: it has the hypotheses it built on and returns them confirmed.

## No Impasse

The plan review (phase 6) and the diff review (phase 9) are gates. Do not step past one. Offer
the operator three options and ask, with a recommendation (the first):

1. **Install Impasse** (`~/.claude/skills/impasse`, a git clone) and run the gate as designed.
2. **A fresh-context host review** with the reviewer stance pasted from
   `templates/impasse-plan-instruction.txt` or `templates/impasse-diff-instruction.txt`, run as a
   new subagent, **labelled same-provider**, with the host's own view written down first so the
   two can be compared.
3. **Proceed without the independent review**, with the operator's explicit words ("skip the
   independent review") recorded in the plan's "Independent review and what it changed" section.

This mirrors the operator's standing rule: if Impasse cannot run, stop and ask; do not proceed past
a gate silently, and do not quietly substitute a same-provider review.

## Impasse present but no Codex (no cross-provider backend)

Impasse's own ladder applies: different provider > same provider in a fresh process > self-review,
and the runner emits an `independence_notice` for anything below the top rung. Surface that notice
in the plan's review section verbatim and weight agreement accordingly: agreement between two
runs of one provider is less evidence than agreement across providers. Impasse refuses to
self-review `kind=code` and refuses self-review on a shell host; respect both.

## No frontend-design plugin

The audit still runs. `references/site-audit.md` section 3 carries the plugin's five calibration
traits and the two sites' tells, so the aesthetic pass has a list to work from. Say in the audit
record that the pass was unaided.

## No Chrome

`scripts/shoot.py` finds Chrome through `$CHROME`, then the macOS app path, the Windows install
paths (Program Files, Program Files (x86), LocalAppData), then `google-chrome`, `chromium` and the
like on PATH. `scripts/check-env.py` reports whether it found one. If none is found:

- there is no browserless specimen: `scripts/specimen.py` writes HTML only. Use `scripts/build.py`'s
  own FreeType rasters (Pillow) as the only rendering evidence, render a title with Pillow's
  `ImageFont.truetype` on the built woff2/TTF by hand, and state that it proves FreeType rendering
  only, not CoreText, DirectWrite or any browser. `scripts/diff.py` still runs without Chrome: it needs no
  browser, and its before / after renders are the same kind of evidence (FreeType, unhinted, on this machine),
  never browser evidence. It does need Pillow's raqm layout engine (so that GPOS kerning applies): without it `diff.py` refuses naming the fix, `scripts/check-env.py` reports it as a required piece (`brew install fribidi` on macOS, `apt install libfribidi0` on Debian/Ubuntu), and the fallback is the by-hand Pillow render above;
- the design-review loop **cannot stop on "no defect at 1× on a real page"**, because no real page
  was rendered; it ends as "not browser-reviewed", recorded as an open item in the record;
- `scripts/opsz.py` cannot run, so the `opsz` endpoints are "assumed CSS px, unmeasured" in the
  record (trap 6);
- the publication blocker "browser evidence missing" (`SKILL.md` section 4, `references/process.md`
  section 11) applies: the face does not ship until someone with a browser runs the loop with
  `shoot.py --family` and `--font-url` (a shot without them is a picture, not evidence). Missing
  browser evidence blocks publication unless the operator waives it in writing; the waiver is
  recorded in the font record and stated in the shipped docs, and nothing else lifts the blocker.
  The host's own judgement that the FreeType rasters "look fine" is not a waiver.

## No claude.ai artifact publishing

The concept pages are self-contained HTML. Open them locally (`file://` works for the generator
rendering; comparison web fonts from a Google Fonts URL still need the network) or serve them with
`shoot.py --serve`. The operator publishes if they want a link to click through. The constraints
in `references/concept-pipeline.md` section 4 still apply to a page that may be published later.

## No FontBakery

`scripts/fontbakery-gate.py` exits 3, saying SKIPPED, NOT PASSED, and `smoke.sh` step 4b prints the same and
goes on. Phase 7's gate holds only when the gate ran: install the dev requirements
(`.venv/bin/pip install -r requirements-dev.txt`) and run it, or get the operator's written waiver and record
it in the font record. Do not read a skipped gate as a pass: the font suite pins what the project decided,
and FontBakery is the only check here on what the format expects (code pages, name platforms, STAT,
dropout control, metrics that agree).

## Windows

Native Windows is not supported: `smoke.sh` and the documented commands are bash, and the venv path is
`.venv/bin/python3`. Run the whole skill inside WSL (`wsl --install`, then the Linux install steps in
the README inside the WSL shell). **Inside WSL, install Chrome or Chromium in the Linux distribution**: the
Windows install paths `shoot.py` lists come from environment variables (`ProgramFiles`, `LocalAppData`) that WSL
normally does not set, and `/mnt/c` paths are not candidates, so a Windows Chrome is not searched for from WSL (set
`$CHROME` yourself if you must). The review screenshots are then the Linux Chrome's, and a Windows rendering (DirectWrite
hinting, the `prep` program) is not checked by anything here: record "not checked on Windows" with the
claim it limits (trap 21).

## Linux host

Chrome via `$CHROME` or `google-chrome`; the interpreter via `sys.executable`; everything else
identical. Two differences to expect and record: the FreeType raster budgets are per machine
(trap 31), so a self-check may read a different grey-level difference, and a raised budget carries
the measured number beside it, never a disabled check; and the review screenshots are Chrome on
Linux (Skia over FreeType), which proves a third rasteriser and not the operator's.

## When several are missing at once

Say so up front, in one list, before phase 1, and let the operator decide whether to start.
A run with no Chrome and no Impasse can still audit, write guidelines, run the concept pages
locally and build a font that passes its self-checks; it cannot claim the font was reviewed, and
the record must say exactly which checks were and were not run.
