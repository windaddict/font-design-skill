"""Spacing stays where 0.9.0 put it: no advance, spacing profile or kern moves except the G's and the italic r's.

WHAT IT'S FOR: 0.10.0 cuts several ends differently (a slanted corner cut, a level cut on a leaning serif end, a bracket on a leaning
edge), and an italic group reads its sidebearings from the 20 unit bins between the baseline and the x-height or cap line only, so a
moved corner can move an advance by accident (the italic Z by 47 units at mult 1.3, the z by 57 at mult 1.5, without the guard).
The generator therefore reads the spacing profile from the polygon as 0.9.0 cut it (`prof`, docs/plan-serif-joint-jags.md section
0.7). This test holds that promise at full precision: for the three example font.json files, tests/joint_spacing_probe.js draws every
master with the generator under test and with the 0.9.0 generator and reports every glyph whose unrounded advance or 54-bin spacing
profile differs and every ordered pair of glyphs whose unrounded automatic kern differs. Differences are compared to 1e-9 units (the
probe lists nothing smaller).

Three rules decide what may differ (tests/joint_changes.py). Width: only the G and, in an italic group, the r. Kern, no limit: a pair
that kern_pair_allowed admits (roman, G on the left; italic, a G or an r in the pair). Kern, bounded: a roman pair with G on the right
and another glyph on the left may move by at most KERN_BOUND_G_RIGHT (0.05 units), because it reads the G's left profile and the
redrawn bowl's sample points shift that profile. On the three examples 639 such pairs move, by 0.0364 units at most; the operator
chose the bound over holding the G's left profile to 0.9.0's. Every other pair must be the value 0.9.0 computes. The same figures
rounded, and the kern list above export.js's threshold, are in
tests/test_serif_joints.py::test_only_the_named_glyphs_changed_since_0_9_0, which sees only what rounding leaves.

It pins behaviour that already holds, so it passes when written. Three watches prove it, each one edit of scripts/gen.js on a copy
(references/testing.md section 11), and each must turn this test red at SPACING-FROZEN, where the message's three counts say which
rule fired. Widths (W11): in glyph(), `T = 30 + 0.36 * W0` to `T = 31 + 0.36 * W0` grows every sidebearing that is not at its floor
of 8 by 1 unit. An exact kern (W14): in kern(), `if (a.key === "A" && b.key === "V") k -= 0.001;` before `c.k[id] = k;` moves one pair
outside the bounded class by far less than the bound. The bound (W12): in the `L:` line of glyph(), `v + sh` to
`v + sh - (key === "G" && !P.italic ? 0.015 : 0)` moves the roman G's left profile by 0.015 units, which takes six pairs of the
Driftwood Bold from 0.0364 to 0.0514 units and puts nothing else outside its rule.

FONT_DESIGN_JOINT_SCRIPTS names another copy of the whole scripts/ folder to test (gen.js and export.js); unset, the real one. The
0.9.0 generator is read from git (tests/joint_changes.py GEN_0_9_0), so the test needs a git checkout.
"""
import concurrent.futures
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

from joint_changes import ADVANCES, GEN_0_9_0, KERN_BOUND_G_RIGHT, kern_move_bound  # noqa: E402

SCRIPTS = pathlib.Path(os.environ.get("FONT_DESIGN_JOINT_SCRIPTS", REPO / "scripts"))
PROBE = REPO / "tests" / "joint_spacing_probe.js"
EXAMPLES = ("bract", "driftwood", "neutral")


def probe(gen_old, example):
    r = run([node(), str(PROBE), str(SCRIPTS / "gen.js"), str(gen_old), str(REPO / "examples" / example / "font.json")])
    assert r.returncode == 0, f"joint_spacing_probe.js {example} exited {r.returncode}:\n{r.stderr[-2000:]}"
    return json.loads(r.stdout)


def test_no_advance_profile_or_kern_moved_outside_g_and_the_italic_r(tmp_path):
    """For each example font.json, every master: the unrounded advance, left profile and right profile of every glyph outside
    ADVANCES (G in a roman group; G and r in an italic one) equal 0.9.0's; every ordered pair of glyphs whose kern_move_bound is 0
    has the unrounded kern 0.9.0 computes; and every roman pair with G on the right and another glyph on the left has a kern within
    KERN_BOUND_G_RIGHT (0.05 units) of it. The probe is also held to have looked: every master of every group was drawn, 131 glyphs
    or more per master and every ordered pair of them. SPACING-FROZEN is the marker. Its message counts the three kinds of move apart
    and names each pair over the bound with the size of its move, largest first."""
    git = subprocess.run(["git", "-C", str(REPO), "show", f"{GEN_0_9_0}:scripts/gen.js"], capture_output=True)
    assert git.returncode == 0, f"git show {GEN_0_9_0}:scripts/gen.js failed: {git.stderr.decode()[:300]}"
    old = tmp_path / "gen-0.9.0.js"
    old.write_bytes(git.stdout)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(EXAMPLES)) as pool:
        results = dict(zip(EXAMPLES, pool.map(lambda e: probe(old, e), EXAMPLES)))
    bad_glyphs, bad_kerns, over_bound = [], [], []
    for example, res in results.items():
        font = json.loads((REPO / "examples" / example / "font.json").read_text())
        want = [f"{g}/{m}" for g, grp in font["groups"].items() for m in grp["masters"]]
        assert res["masters"] == want, f"{example}: the probe drew {res['masters']}, font.json declares {want}"
        glyphs, pairs = res["checked"]["glyphs"], res["checked"]["pairs"]
        assert glyphs >= 131 * len(want), f"{example}: only {glyphs} glyphs compared for {len(want)} masters"
        assert pairs >= 131 * 131 * len(want), f"{example}: only {pairs} pairs compared for {len(want)} masters"
        for d in res["glyphs"]:
            allowed = ADVANCES["italic" if d["italic"] else "roman"]
            if d["key"] not in allowed:
                bad_glyphs.append(f"{example}/{d['group']}/{d['master']} {d['key']!r} {d['what']}: {d['old']} -> {d['new']}")
        for d in res["kerns"]:
            bound = kern_move_bound(d["italic"], d["a"], d["b"])
            if bound is None:
                continue
            move = abs(d["new"] - d["old"])
            where = f"{example}/{d['group']}/{d['master']} {d['a']}|{d['b']}: {d['old']} -> {d['new']}"
            if bound == 0:
                bad_kerns.append(where)
            elif move > bound:
                over_bound.append((move, f"{where}, moved {move:.4f} units (bound {bound})"))
    over_bound = [text for _, text in sorted(over_bound, reverse=True)]
    assert not bad_glyphs and not bad_kerns and not over_bound, (
        f"SPACING-FROZEN: {len(bad_glyphs)} glyph measures and {len(bad_kerns)} kern pairs moved outside G and the italic r; "
        f"{len(over_bound)} roman pairs with G on the right moved by more than {KERN_BOUND_G_RIGHT} units.\n"
        + "\n".join(bad_glyphs[:8] + bad_kerns[:8] + over_bound[:8]))
