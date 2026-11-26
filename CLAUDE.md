# CLAUDE.md: working on the font-design skill

WHAT IT'S FOR: rules for an agent that changes this repository. The skill's own instructions for
designing a face are in `SKILL.md`; this file is about developing the skill itself.

## Choosing how much to test

The checks here are slow, so pick the smallest set that can see the change, and say which set you ran
and why in the commit or pull request. Running less than the full set is a decision you state, not an
omission. Durations recorded so far (this machine, 2026-11-22, one run of each): `scripts/smoke.sh` steps 1 to 5 took
14 min 46 s, and step 7 (layer 2 inside the smoke run) took 27 min 34 s. On 2026-11-25 `scripts/smoke.sh --full` took at most 59 min 12 s (launch to the check that found it done), and its step 7 took 28 min 5 s. On the 0.12.0 tree (2026-11-25, `time` on the whole run) it took 43 min 50 s, and its step 7 took 28 min 22 s. With the Tiki Terminal example added (2026-11-26 UTC, `scripts/smoke.sh --out out/smoke`, steps 1 to 7, wall time from the launch to the log's last line, 04:24:12Z to 05:10:47Z) it took 46 min 35 s, and its step 7 took 30 min 51 s (799 passed, 7 skipped). No duration is recorded for the other layers; when
you time one, add the figure and the date here.

The layers, from cheapest to most expensive:

1. **One or a few repo test files.** `.venv/bin/python3 -m pytest tests/test_<area>.py -q`.
2. **The repo tests.** `.venv/bin/python3 -m pytest -q` (806 tests in 33 files on 2026-11-25, from `pytest --co -q`; `tests/test_docs_commands.py` adds one test per documented command, so the count moves when a doc gains or loses a command). Most
   files start subprocesses (Node, the font build or Chrome).
3. **The font suite on a fixture.** `scripts/tests/test_font.py`, run by path with `--font` and
   `--requirements` (see `pytest.ini`). It is not part of layer 2.
4. **`scripts/smoke.sh`.** Steps 1 to 7: exports and builds all four fixtures, checks reproducibility,
   runs the font suite, the FontBakery gate, EVERY mutation in `scripts/tests/mutate.py`, the concept
   pages and layer 2. `--full` adds the Chrome steps 8 to 11. CI's `test` job runs steps 1 to 7 on four
   machines and takes 60 to 81 minutes per machine.
5. **CI by hand.** `gh workflow run ci.yml --ref <branch>`. It does not run on push.

Which layer a change needs:

| The change touches | Run |
|---|---|
| Prose only: `CHANGELOG.md`, a README, `references/`, `SKILL.md`, `docs/` | `tests/test_docs_commands.py`, `tests/test_hygiene.py`; add `tests/test_versions_and_skill.py` for `SKILL.md` or `VERSION` |
| A workflow in `.github/workflows/` or `templates/platform-shots.yml` | `tests/test_ci_workflow.py`, `tests/test_hygiene.py` |
| One tool that draws no glyph: `shoot*.py`, `compare-shots.py`, `specimen.py`, `diff.py`, `fetch-version.py`, `update-check.py`, `versions.py`, `check-env.py`, `fontbakery-gate.py`, `fallback-metrics.py`, `opsz.py`, `bounds.js`, `mine-*.py`, `scripts/concepts/` | that tool's test files (find them with `grep -l <script name> tests/test_*.py`), plus `tests/test_hygiene.py` |
| What draws or builds a glyph: `gen.js`, `export.js`, `build.py`, `render.js`, or an example's `font.json` | layer 4, `scripts/smoke.sh`: a geometry change can break a fixture no unit test looks at |
| The font suite or its harness: `scripts/tests/` | layer 3 on the neutral fixture, then layer 4 for the mutations |
| A shared helper: `tests/conftest.py`, `requirements*.txt`, `pytest.ini` | layer 2 |
| A release (`VERSION` bump), or a commit a site's pin will move to | layer 4 with `--full`, then layer 5 |

The grep in the tool row finds the files that name a script, which is a lead, not proof that they test
it. If a change reaches more than one row, run the larger layer. If you cannot tell which files a
change reaches, run layer 2.

Narrowing the run does not relax the rule on new tests: a new or changed guard must still be watched
going red under a mutation, as `references/testing.md` section 1 says.

## Version discipline

Two installs with one `VERSION` produce the same font output. That is the exact guarantee, and these rules keep it:

- A change that alters font output (`scripts/gen.js`, `scripts/export.js`, `scripts/build.py`, or the defaults they read) bumps `VERSION`
  in the same change. Later commits under one `VERSION` may change CI, docs or tests, never font output.
- Every CHANGELOG entry carries a line `Font output: unchanged` or `Font output: changes: <what>`.
  `tests/test_versions_and_skill.py` holds it for the current version.
- Every released version gets a tag `v<version>` on the first `main` commit that carries it, pushed after the merge.
  `scripts/fetch-version.py` fetches the code at that tag.
- `manifest.json` records `skill_version`, so a face folder says which version built it (`references/face-folder.md`).

The 0.6.0 entry in the CHANGELOG is the counter-example: two different font sources carried that one number, so
`fetch-version.py` refuses it. The rule forbids a repeat.
