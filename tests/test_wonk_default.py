"""An unset wonkAmount draws exactly what 0.11.0 drew (0.12.0).

WHAT IT'S FOR: `wonkAmount` replaces the fixed lean `x -= 0.045 * y` of the letters a concept names in `wonk`. A concept that does not
set it must keep the old drawing to the last coordinate, or every face built with a `wonk` concept changes under a release that
says its output is unchanged. This test draws every glyph of every shipped concept with every key leaning, and compares the drawing
with the one the previous release's generator makes, polygon for polygon.

How the measure works. The previous release is `git show 4efcca7:scripts/gen.js`, the last commit that changed scripts/gen.js
before 0.12.0 (`git log -1 --format=%h -- scripts/gen.js`, 2026-11-25), written to a temporary folder. tests/wonk_amount_probe.js
(mode `old`) loads both generators afresh for each concept and style and reports, per glyph draw, whether polys, adv, L, R, sig and
runs are exactly equal, and whether the old drawing leans at all (differs from the old drawing of the same concept with wonk empty).
The floors keep the test from passing on nothing: it compares at least 7000 draws, and at least 6800 of them are of letters that lean.
The amount 0.045 is restated nowhere in this file; the old generator is the reference.

FONT_DESIGN_WONK_SCRIPTS names another copy of the whole scripts/ folder (see tests/test_wonk_amount.py); unset, the real one.
"""
import importlib.util as _ilu
import json
import os
import pathlib
import pathlib as _pl
import subprocess

# Load tests/conftest.py by path: a combined run with scripts/tests/ puts that folder's conftest in sys.modules as
# "conftest", so a plain `from conftest import ...` would get the wrong module.
_spec = _ilu.spec_from_file_location("repo_tests_conftest", _pl.Path(__file__).resolve().parent / "conftest.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

REPO = _mod.REPO
node = _mod.node
run = _mod.run

SCRIPTS = pathlib.Path(os.environ.get("FONT_DESIGN_WONK_SCRIPTS", REPO / "scripts"))
GEN = SCRIPTS / "gen.js"
PROBE = REPO / "tests" / "wonk_amount_probe.js"
GEN_0_11_0 = "4efcca7"  # the last commit that changed scripts/gen.js before 0.12.0
CONCEPT_FILES = [REPO / "examples" / e / "concepts.js" for e in ("neutral", "bract", "driftwood")]
DRAWS_FLOOR = 7000  # measured 7598 draws on 2026-11-25
LEANING_FLOOR = 6800  # measured 7565 of them leaning on 2026-11-25


def test_an_unset_wonkamount_draws_what_0_11_0_drew(tmp_path):
    """Across the whole generator against the previous release: with every key named in wonk and no wonkAmount, every glyph of every
    shipped concept, roman and italic, at mult 1 and 1.65, is drawn exactly as the 0.11.0 generator draws it."""
    r = subprocess.run(["git", "show", f"{GEN_0_11_0}:scripts/gen.js"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, f"git show {GEN_0_11_0}:scripts/gen.js exited {r.returncode} (this test needs a git checkout with that commit):\n{r.stderr[-1000:]}"
    old = tmp_path / "old" / "gen.js"
    old.parent.mkdir()
    old.write_text(r.stdout, encoding="utf-8")
    draws = []
    for f in CONCEPT_FILES:
        spec = {"file": str(f), "styles": ["roman", "italic"], "mults": [1, 1.65], "old": str(old)}
        p = run([node(), str(PROBE), str(GEN), "old", json.dumps(spec)])
        assert p.returncode == 0, f"wonk_amount_probe.js old exited {p.returncode} on {f}:\n{p.stderr[-2000:]}"
        draws += json.loads(p.stdout)
    assert len(draws) >= DRAWS_FLOOR, f"only {len(draws)} glyph draws were compared, expected at least {DRAWS_FLOOR}"
    leaning = [d for d in draws if d["leaning"]]
    assert len(leaning) >= LEANING_FLOOR, f"only {len(leaning)} of {len(draws)} compared draws are of a letter that leans, expected at least {LEANING_FLOOR}"
    differ = [d for d in draws if not d["same"]]
    assert not differ, (f"WONK-DEFAULT: {len(differ)} of {len(draws)} glyph draws differ from the {GEN_0_11_0} generator; first ten "
                        f"(concept, style, mult, key): {[(d['concept'], d['style'], d['mult'], d['key']) for d in differ[:10]]}")
