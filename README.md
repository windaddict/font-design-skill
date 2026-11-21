# font-design — a Claude Code skill for making a website its own typeface

![version](https://img.shields.io/badge/version-0.8.0-blue) ![licence](https://img.shields.io/badge/licence-MIT-green)

A skill that designs, builds and ships a custom display typeface for a website as a self-hosted
variable web font. The face is generated from centre-line skeletons by a parametric generator, chosen
across three rounds of interactive concept pages set on the site's real titles, reviewed on real pages
at real sizes by a strong model and by an independent cross-provider reviewer, and guarded by
self-checks in the build and mutation-tested tests in the site.

By [John M. P. Knox](https://www.movingavg.com/about.html) of [Moving Average](https://www.movingavg.com),
an advisory firm for CEOs and founders of B2B SaaS and MedTech companies (see "About the author" below).

It is the process John Knox used to make **Bract** (hopsafari.com, 2026-11-15), the full-process
worked example (`references/examples/bract.md`). The generator and most of the rules come from an
earlier face, **Driftwood** (movingavg.com, 2026-11-14): built before the process was written down,
by a static union pipeline into five CFF files, it is the design precedent whose lessons and bugs
informed the skill, not a product of these nine phases (`references/examples/driftwood.md`).
Everything learned from both — including the bugs found afterwards — is in the code, the tests and
`references/`. No font files or site content ship here; see `NOTICE.md`.

## What a run looks like

1. **Audit the site** (headless screenshots, the AI-tells list) and fix what changes what the font must do.
2. **Derive guidelines** from the stylesheet and the built pages: sizes, hairline floor, charset traps.
3. **Round 1** — about six concepts as parameter sets, rendered on real titles; a reviewer shortlists.
4. **Round 2** — the shortlist on mock-ups of the redesigned pages with a face picker.
5. **Round 3** — finalists head to head, the reviewer's verdict in the page; the operator picks and names.
6. **Plan the build**, then have the plan reviewed independently (Impasse) before writing code.
7. **Build** one variable font per group (roman; italic as a second file) with self-checks that fail
   the build; wire the CSS; run the skill's test suite against the face folder; watch every guard fail under its mutation.
8. **Design-review loop**, at most six rounds, each with a fresh reviewer reading real-page screenshots.
9. **Ship**: independent review of the finished diff, one re-review, the record, deploy on the operator's word.

The skill stops at every gate and asks; between gates it works alone. `SKILL.md` has the phases;
`references/process.md` has the detail.

## Install

```sh
git clone https://github.com/windaddict/font-design-skill ~/.claude/skills/font-design
cd ~/.claude/skills/font-design
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

A site keeps only a face folder (`tools/<face>/`: `font.json`, `concepts.js`, `requirements.json`, optionally
`skeletons.js`, and the build output); every skill command runs from the skill's install and takes the path to
`font.json`, so no scripts are copied into the site. `manifest.json` records the skill version that built the face, and
`scripts/update-check.py` tells the operator what a newer skill would change before the face is rebuilt.
`references/face-folder.md` is the contract.

**Releases.** Each released version is tagged `v<version>` on the first `main` commit that carries it, and one `VERSION`
means the same font output. `scripts/fetch-version.py` puts the skill's code at a released version into a folder, so an
old build can be reproduced (the CHANGELOG's `## Releases` section lists the tags).

Requirements: Node ≥ 20; Python ≥ 3.10 with `fonttools==4.68.*`, `brotli`, `skia-pathops`, `pillow`, `uharfbuzz`, `unicodedata2`
(CI runs 3.12; 3.10 and 3.11 are not run by anything here); Chrome or Chromium for the review tools
(`$CHROME` or the per-OS default); bash; a Pillow with the raqm layout engine for `scripts/diff.py` (the wheel carries it and needs libfribidi:
`brew install fribidi` on macOS, `apt install libfribidi0` on Debian/Ubuntu). **Platforms: macOS and Linux are supported. Native Windows is
not (the scripts are bash and the venv path is `.venv/bin/python3`); on Windows use WSL.**
`.venv/bin/python3 scripts/check-env.py` reports what is missing, with the command that fixes each piece. Optional but recommended:
the Impasse skill (independent review), the `frontend-design` plugin (aesthetic audit), and the
strongest model your agent host offers for the design reviews. `references/fallbacks.md` says what to
do without each.

Optional, for the platform run (how the face renders on Windows, macOS and Linux): GitHub Actions on the
site's repository. The site keeps a short caller, `templates/platform-shots.yml`, pinned to a full skill
commit SHA; it calls the skill's reusable workflow `.github/workflows/platform-shots-reusable.yml`, which
checks out the skill's scripts at that commit and the site's own pages and fonts, so the site carries no
copy of the scripts and its fonts never enter the skill's repository. It shoots the pages with headless
Chrome and Playwright's Firefox on GitHub-hosted Windows Server, macOS and Ubuntu runners, and `scripts/compare-shots.py` stacks
each row from every leg in one image. Nothing new is needed on your machine: every leg installs
`playwright==1.64.1` on its runner (the pin in `requirements-platform.txt`), and the Firefox legs also
download Playwright's Firefox. Install `requirements-platform.txt` locally only to run
`shoot.py --browser firefox` yourself. A runner is not a reader's machine, and Safari and phones are not
checked (`references/review-loop.md` section 9).

## Try it on the neutral example

```sh
node scripts/export.js --font examples/neutral/font.json --group roman --requirements examples/neutral/requirements.json out/roman.json
.venv/bin/python3 scripts/build.py --font examples/neutral/font.json --static examples/neutral/out/static
.venv/bin/python3 -m pytest scripts/tests/test_font.py -q --font examples/neutral/font.json --requirements examples/neutral/requirements.json
.venv/bin/python3 scripts/tests/mutate.py --font examples/neutral/font.json --requirements examples/neutral/requirements.json
.venv/bin/python3 scripts/fontbakery-gate.py --font examples/neutral/font.json --requirements examples/neutral/requirements.json
node scripts/concepts/build-page.js --template round1 --concepts examples/neutral/concepts.js --content examples/neutral/content.json out/round1.html
mkdir -p out/fonts && cp examples/neutral/out/Sampler-VF.woff2 out/fonts/Sampler-VF.woff2
.venv/bin/python3 scripts/shoot.py out/shots --serve out --pages round1.html --widths 500 1280 --family Sampler --font-url /fonts/Sampler-VF.woff2
```

The last two lines put the built woff2 where the page expects it (`content.json` names
`fonts/Sampler-VF.woff2`) and tell `shoot.py` what every shot must prove: that `Sampler` rendered
and that the font file was served 200. A shot without `--family` and `--font-url` is a picture, not
evidence, and `shoot.py` does not call it evidence.

`bash scripts/smoke.sh` runs the whole sequence (`--full` adds the browser steps). Run it before the
first use of the skill on a machine and after every update of the skill, before starting a project
with it. The "Sampler" face it builds is a fixture, not a design: an upright low-contrast serif
unlike either precedent, with a two-axis roman and a one-axis italic so every code path runs. It
is a finished sample with two concepts (`text`, `display`) for speed; a real run writes about six
concepts in round 1 and sets its floors from its own measurements.

## Layout

| Path | What |
|---|---|
| `SKILL.md` | The skill: phases, gates, blockers, tool table, reference index |
| `scripts/` | Generator, exporter, builder, review tools, concept-page builder and templates, the test templates |
| `references/` | The face-folder contract, the process in detail, the traps, the generator parameters, the build, the review loop, testing, fallbacks, the Bract worked example and the Driftwood precedent |
| `templates/` | `font.json` and `requirements.json` examples, the `font.json` and manifest schemas, `concepts.js` skeleton, record and plan templates, reviewer briefs, Impasse instructions, `platform-shots.yml` (the short caller of the cross-platform rendering workflow a site copies) |
| `examples/` | `neutral/` (the smoke fixture), `bract/`, `driftwood/` (parameters and configuration only, under neutral name tables; MIT like the rest of the repo) |
| `tests/` | The repo's own tests: hygiene, versions, schemas and concepts, the review tools on fixtures (`shoot.py`'s server and sentinel in real Chrome where one is found), a face folder inside a sample site served by the skill's scripts, the site-wiring template filled against that site, every documented command's flags, a smoke build |
| `docs/plan.md` | The plan this repo was built from and its independent review |

## Screenshots

The repo ships none: every review PNG is of a real site's pages, and no screenshot of them would be
neutral. `scripts/shoot.py` produces them in a minute; the neutral example's pages are the only ones a
README image would ever show.

## About the author

John M. P. Knox founded [Moving Average Inc.](https://www.movingavg.com), an advisory firm for CEOs
and founders of B2B SaaS and MedTech companies, and works with them as an advisor on strategic AI,
SaaS and MedTech decisions. This skill comes out of that work: it is a worked example of an AI agent
doing a long, specialist job with little supervision, kept honest by tests that are checked by
mutation and by an independent reviewer from a different AI provider. The first face it records,
Driftwood, was drawn for movingavg.com. For advisory work, see
[movingavg.com](https://www.movingavg.com).

## Licence

MIT, Copyright (c) 2026 John Knox — the code, the documentation and the parameter sets in
`examples/`. A font you build with it from your own parameters belongs to you, under whatever
licence you put in its name table. One exception: the names **Bract** and **Driftwood MA** identify
the original sites' faces and are not licensed for reuse as font names. The example files build
under the neutral family names "Bract Example" and "Driftwood Example"; the shipped fonts are
licensed to their sites only and are not in this repo. `NOTICE.md` has the provenance.
