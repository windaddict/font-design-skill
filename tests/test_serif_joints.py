"""The joints 0.10.0 fixes: brackets on the stroke's own edge, level leaning ends, the corner cut, the G's chin and the italic r's arm.

WHAT IT'S FOR: 0.9.0 drew a serif bracket on a leaning stroke along the plumb lines, so the bracket's tip stood outside the stroke
(the italic w by up to 14.7 units, the italic W by 18.2, the roman M by 5.6); cut a leaning serif end square to the stroke, so one
corner of the roman M's feet hung below the baseline; sank a head serif's stem straight down, off a leaning stroke's own edge; cut
the shallow stroke of a corner plumb whatever its partner's direction (a 24 to 83 unit tooth on the Z, z, 4, 7 and the italic
corners); and drew the G and the italic r's arm with controls nearer a round extreme than the fit moves it, which folds the edge.
These tests hold each to what a reader of the outlines would check, and the last holds the release to its scope: no glyph but the
named ones changed. The plan is docs/plan-serif-joint-jags.md; each test below names its first assertion by a marker in capitals
(BRACKET-TIP, LEVEL-END, SINK-ON-EDGE, CORNER-TOOTH, G-STEP, G-BOTTOM, R-ARM-UNDER, R-ARM-TOP, SCOPE-OUTLINES), which is the message
that test fails on against the 0.9.0 generator. The assertions before a marker are coverage checks (enough rows were measured and
the named glyphs are among them), so a probe that measures nothing cannot pass.

How the measures work. Nothing is computed from the generator's formulas. tests/joint_probe.js draws glyphs and reports what it drew
(its header defines every figure). The sweeps turn the swell and the wobble off: they bend a straight stroke's edges by 1.3 to 4.3
units at a bracket's height, which would hide the roman M's 2 units; with them off a straight stroke's edges are straight lines and
the measure is exact (0.00 on every plumb head and foot, on 0.9.0 and on the fixed generator).

FONT_DESIGN_JOINT_SCRIPTS names another copy of the whole scripts/ folder (gen.js and export.js), for example a scratch copy carrying
one mutation (the watches in the plan's Verification section); unset, the real one. The 0.9.0 generator is read from git
(tests/joint_changes.py GEN_0_9_0) for the scope test, so that test needs a git checkout.
"""
import concurrent.futures
import functools
import importlib.util as _ilu
import json
import os
import pathlib
import pathlib as _pl
import shutil
import subprocess

import pytest

# Load tests/conftest.py by path: a combined run with scripts/tests/ puts that folder's conftest in sys.modules as
# "conftest", so a plain `from conftest import ...` would get the wrong module.
_spec = _ilu.spec_from_file_location("repo_tests_conftest", _pl.Path(__file__).resolve().parent / "conftest.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

REPO = _mod.REPO
node = _mod.node
run = _mod.run

from joint_changes import ADVANCES, GEN_0_9_0, OUTLINES, RECORDS, kern_pair_allowed  # noqa: E402

SCRIPTS = pathlib.Path(os.environ.get("FONT_DESIGN_JOINT_SCRIPTS", REPO / "scripts"))
PROBE = REPO / "tests" / "joint_probe.js"
EXAMPLES = ("bract", "driftwood", "neutral")
CONCEPT_FILES = [REPO / "examples" / e / "concepts.js" for e in EXAMPLES]
# The equivalence behind retiring headsink-zero-on is a claim about every concept file the repository ships, so its sweep adds the
# two template concept files that test_weight_decisions.py and test_r_leg_join.py already treat as shipped.
TEMPLATE_CONCEPT_FILES = [REPO / "templates" / "concepts.example.js", REPO / "templates" / "concepts.genres.js"]
SINKZERO_CONCEPT_FILES = CONCEPT_FILES + TEMPLATE_CONCEPT_FILES
FONTS = [REPO / "examples" / e / "font.json" for e in EXAMPLES]
MULTS = [1, 1.3, 1.5, 1.65]
EXAMPLE_GROUPS = [("neutral", "roman"), ("neutral", "italic"), ("bract", "roman"), ("driftwood", "roman"), ("driftwood", "italic")]
TOL = 0.05          # units: a bracket tip or a corner on the edge it should be on
TIP_GLYPHS = {("italic", "w"), ("italic", "W"), ("roman", "M")}


# --- running the probe ----------------------------------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _probe(mode, spec_json):
    r = run([node(), str(PROBE), mode, str(SCRIPTS), spec_json])
    assert r.returncode == 0, f"joint_probe.js {mode} exited {r.returncode}:\n{r.stderr[-2000:]}"
    return json.loads(r.stdout)


def sweep(mode, extra=None):
    """The probe's `mode` over the three example concept files (one node process each, run side by side), roman and italic, four
    multipliers; `extra` is merged into every concept after swell 0 and wob 0."""
    specs = [json.dumps({"files": [str(f)], "mults": MULTS, "styles": ["roman", "italic"], "extra": extra or {}}, sort_keys=True) for f in CONCEPT_FILES]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(specs)) as pool:
        parts = list(pool.map(lambda s: _probe(mode, s), specs))
    return [row for part in parts for row in part]


def per_font(mode, **spec):
    """The probe's `mode` for each of the three example font.json files: {example: rows}."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(FONTS)) as pool:
        parts = list(pool.map(lambda f: _probe(mode, json.dumps({"font": str(f), **spec}, sort_keys=True)), FONTS))
    return dict(zip(EXAMPLES, parts))


def masters_in(italic_only=False):
    """How many masters the three example font.json files declare, counted from the files themselves."""
    n = 0
    for f in FONTS:
        for g in json.loads(f.read_text())["groups"].values():
            if g.get("italic") or not italic_only:
                n += len(g["masters"])
    return n


def head_foot(rows):
    return [r for r in rows if r["kind"] in ("head", "foot")]


def named(rows):
    return {(r["style"], r["key"]) for r in rows}


def worst(rows, field, n=3):
    top = sorted(rows, key=lambda r: -r[field])[:n]
    where = ("file", "font", "concept", "style", "group", "master", "mult", "key", "end")
    return "; ".join(" ".join(str(r[k]) for k in where if k in r) + f" {field} {r[field]:.2f}" for r in top)


# --- a: the bracket stays on the stroke ------------------------------------------------------------------------------------

def _check_tips(rows, prefix):
    """Head and foot ends: no bracket tip outside the stroke. Diag ends: the same on a straight stroke, and the curved ones are
    exactly the italic y, A, M and N, bounded."""
    hf = head_foot(rows)
    over = [r for r in hf if r["out"] > TOL]
    assert not over, f"{prefix}: {len(over)} of {len(hf)} head or foot ends have a bracket tip more than {TOL} outside the stroke; worst {worst(over, 'out')}"
    diag = [r for r in rows if r["kind"] == "diag"]
    bent = [r for r in diag if not r["straight"]]
    straight_over = [r for r in diag if r["straight"] and r["out"] > TOL]
    assert not straight_over, f"{prefix}: a diag end on a straight stroke has a tip outside it: {worst(straight_over, 'out')}"
    assert named(bent) == {("italic", "y"), ("italic", "A"), ("italic", "M"), ("italic", "N")}, \
        f"{prefix}: the diag ends on a curved stroke are {sorted(named(bent))}, expected the italic y, A, M, N"
    bent_over = [r for r in bent if r["out"] > 7.5]
    assert not bent_over, f"{prefix}: a diag end on a curved stroke stands more than 7.5 outside it: {worst(bent_over, 'out')}"


def test_no_head_or_foot_bracket_tip_stands_outside_its_stroke():
    """Every head and foot serif end of every serif concept of the three examples, roman and italic at 10 degrees, mult 1 to 1.65,
    every key of G, swell and wobble off: both bracket tips lie inside the stroke's body (within 0.05 units). The ends on a straight
    stroke that take the diagonal routine already do, and the curved ones (the italic y, A, M and N) stay within 7.5 units, so the
    guard bounds them without moving them. The same with `headSink` 0.6 and with `serifBracket` 0.5, which draw the blended brackets.
    Red on 0.9.0 at BRACKET-TIP: the italic w stands out by up to 14.7 units, the W by 18.2 and the roman M by 5.6."""
    rows = sweep("serifs")
    hf = head_foot(rows)
    assert len(hf) >= 4000 and len([r for r in rows if r["kind"] == "diag"]) >= 5000, f"only {len(hf)} head and foot rows, {len(rows)} in all"
    assert TIP_GLYPHS <= named(hf), f"no head or foot row for {sorted(TIP_GLYPHS - named(hf))}"
    _check_tips(rows, "BRACKET-TIP")
    _check_tips(sweep("serifs", {"headSink": 0.6}), "with headSink 0.6")
    _check_tips(sweep("serifs", {"serifBracket": 0.5}), "with serifBracket 0.5")


# --- b: a leaning end is cut level -------------------------------------------------------------------------------------------

def test_a_leaning_serif_end_is_cut_level():
    """Every head or foot end whose stroke leans (the italic w and W, the roman M) has its two corners on one level line, and the
    roman M's feet do not hang below the baseline. A plumb end is untouched: it was level already.
    Red on 0.9.0 at LEVEL-END: on the Driftwood example the M's corners differ in height by 2.0 to 3.7 units, the italic W's by 2.9
    to 7.9 and the italic w's by 7.3 to 16.1, and the M hangs 1.04 to 2.24 below the baseline."""
    rows = sweep("serifs")
    hf = head_foot(rows)
    leaning = [r for r in hf if abs(r["lean"]) > 1e-9]
    assert named(leaning) == TIP_GLYPHS, f"the head and foot ends that lean are {sorted(named(leaning))}, expected {sorted(TIP_GLYPHS)}"
    assert any(r["concept"] == "driftwood" and r["style"] == "italic" and r["key"] == "w" for r in leaning), "no italic w of the Driftwood example"
    plumb_tilted = [r for r in hf if abs(r["lean"]) <= 1e-9 and r["tilt"] > 1e-6]
    assert not plumb_tilted, f"a plumb end is not level: {worst(plumb_tilted, 'tilt')}"
    tilted = [r for r in leaning if r["tilt"] > 1e-6]
    feet = [r for r in rows if r["style"] == "roman" and r["key"] == "M" and r["kind"] == "foot"]
    assert feet, "no roman M foot measured"
    below = [r for r in feet if r["lowestY"] < -1e-6]
    assert not tilted and not below, \
        f"LEVEL-END: {len(tilted)} of {len(leaning)} leaning ends are cut off the level, worst {worst(tilted, 'tilt') if tilted else 'none'}; " \
        f"{len(below)} of {len(feet)} roman M feet hang below the baseline, lowest y {min(r['lowestY'] for r in feet):.2f}"


def test_a_head_sink_of_no_depth_moves_no_point():
    """No lowercase head end has a point above its own centre line, so a head sink of no depth moves nothing. Every concept of the
    three example concept files and of the two template concept files as shipped (swell and wobble on, serif or not), roman and italic
    at 10 degrees, mult 1 to 1.65, and
    every master of every group of the three example font.json files, every key of G: the glyph drawn with headSink 1e-300 is the
    glyph drawn with no key, to 1e-9 units, in every polygon point, the advance and both spacing profiles. A headSink that small
    leaves the sink's line on the end's centre line, so the sink pins exactly the points that stand above it.

    WHAT IT'S FOR: this is the measurement behind retiring the font suite's mutation `headsink-zero-on` (`P.headSink >= 0` in place
    of `> 0`, references/testing.md section 11). While it holds, that mutation draws the same outline as the code on every shipped
    concept and is an equivalent mutation. If it fails, an end has a corner above its centre line again: put the mutation back in
    scripts/tests/mutate.py and build its fixture from the end this message names.
    It pins behaviour that already holds, so it passes when written. Red on 0.9.0 and under watch W2 (`leanS && !legacy` to `false`)
    at HEAD-END-FLAT: the 34 leaning lowercase head ends of the example files and fonts (the italic w) each have one corner up to
    11.3 units above the line. The template files' leaning ends (brush, scotch) mirror example concepts today; watch W17 shows the sweep
    sees one edited away from its twin.
    A coordinate, advance or profile value that is not finite on either side ends the probe with a non-zero exit, so a sink that writes
    NaN cannot read as no movement (watch W15, references/testing.md section 11)."""
    specs = [json.dumps({"files": [str(f)], "mults": MULTS, "styles": ["roman", "italic"]}, sort_keys=True) for f in SINKZERO_CONCEPT_FILES]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(specs)) as pool:
        swept = [row for part in pool.map(lambda s: _probe("sinkzero", s), specs) for row in part]
    for f in TEMPLATE_CONCEPT_FILES:
        name = f"templates/{f.name}"
        assert any(r.get("file") == name for r in swept), f"no run drew {name}: the sweep skipped a shipped concept file"
    shipped = [row for rows in per_font("sinkzero").values() for row in rows]
    assert len(swept) >= 16 * 2 * len(MULTS), f"only {len(swept)} concept runs: 16 concepts, two styles and {len(MULTS)} multipliers are expected"
    assert {(r["style"], r["mult"]) for r in swept} == {(s, m) for s in ("roman", "italic") for m in MULTS}, "a style or a multiplier was not drawn"
    assert len(shipped) == masters_in() and len(shipped) >= 14, f"{len(shipped)} shipped runs for {masters_in()} masters"
    rows = swept + shipped
    assert all(r["glyphs"] >= 131 for r in rows), f"a run compared fewer than 131 glyphs: {min(r['glyphs'] for r in rows)}"
    heads, leaning = sum(r["heads"] for r in rows), sum(r["leaning"] for r in rows)
    assert heads >= 1600 and leaning >= 30, f"only {heads} lowercase head ends were compared, {leaning} of them leaning: the sweep cannot see a leaning end"
    assert any(r.get("file") == "driftwood/concepts.js" and r["style"] == "italic" and r["leaning"] for r in swept), "no leaning head end in the Driftwood italic"
    bad = [r for r in rows if r["maxMove"] > 1e-9 or r["spacing"] > 1e-9]
    where = ("file", "font", "concept", "style", "group", "master", "mult")
    assert not bad, (
        f"HEAD-END-FLAT: in {len(bad)} of {len(rows)} runs a head sink of no depth moved a point ({sum(r['moved'] for r in bad)} glyphs), so "
        "`headsink-zero-on` is no longer an equivalent mutation (references/testing.md section 11). Worst: "
        + "; ".join(" ".join(str(r[k]) for k in where if k in r) + f" {r['at']!r} moved {r['maxMove']:.2f}, spacing {r['spacing']:.2f}"
                    for r in sorted(bad, key=lambda r: -r["maxMove"])[:3]))


# --- c: the head sink follows the edge ------------------------------------------------------------------------------------------

def test_the_head_sink_moves_a_leaning_stem_end_along_its_own_edge():
    """For every lowercase head end of every serif concept with headSink 0.6 against the same concept without the key, swell and
    wobble off: every point the sink moved still lies on the unsunk stem (within 0.01). A plumb stem's edge is a vertical line, so
    sinking straight down kept it there; a leaning stem's edge is not, so the pin must run along the edge.
    Red on 0.9.0 at SINK-ON-EDGE: the italic w's corner leaves its edge by 1.8 to 1.9 units on the Driftwood example and 2.5 to 3.4
    on Bract text (swell on); with the swell off 3.6 at most."""
    rows = sweep("sink")
    assert len(rows) >= 1000, f"only {len(rows)} lowercase head ends measured"
    idle = [r for r in rows if r["moved"] == 0]
    assert not idle, f"the sink moved no point on {len(idle)} ends, so nothing was measured there: {idle[:2]}"
    leaning = [r for r in rows if abs(r["lean"]) > 1e-9]
    assert any(r["concept"] == "driftwood" and r["style"] == "italic" and r["key"] == "w" for r in leaning), "no italic w of the Driftwood example"
    assert named(leaning) == {("italic", "w")}, f"the lowercase heads that lean are {sorted(named(leaning))}, expected the italic w only"
    off = [r for r in rows if r["sinkOut"] > 0.01]
    assert not off, f"SINK-ON-EDGE: {len(off)} of {len(rows)} sunk stem ends leave the stem's edge; worst {worst(off, 'sinkOut')}"
    plumb = [r for r in rows if abs(r["lean"]) <= 1e-9 and r["sinkOut"] > 0.01]
    assert not plumb, f"a plumb stem's sunk end left its edge: {worst(plumb, 'sinkOut')}"


# --- d: the corner cut -------------------------------------------------------------------------------------------------------

def test_a_corner_bar_ends_on_the_far_edge_of_the_stroke_it_meets():
    """At a corner (two stroke ends within 2 units, one steep and one shallow) the shallow stroke's two corners lie within 0.05
    units of the body of the stroke it meets, when that stroke is straight; swell and wobble off. Where it is a curve (the 2, where
    the bar meets the bowl's end, and the e family, where the bar meets the bowl's start) the cut follows the tangent and the edge
    curves away: at most 1.5 units on the 2 and 8.0 on the e family. With the concepts as shipped, every corner of every master of
    the three example font.json files stands at most 2.0 units out.
    Red on 0.9.0 at CORNER-TOOTH: the roman Z reads 49.2, the z 53.3, the 4 44.4, the 7 32.6 and the italic corners 12.1 or more."""
    rows = sweep("corners")
    assert len(rows) >= 2000, f"only {len(rows)} corner ends measured"
    need = {("roman", k) for k in ("Z", "z", "4", "7", "2", "e")}
    assert need <= named(rows), f"missing corners: {sorted(need - named(rows))}"
    straight = [r for r in rows if not r["partnerCurved"]]
    teeth = [r for r in straight if r["tooth"] > TOL]
    assert not teeth, f"CORNER-TOOTH: {len(teeth)} of {len(straight)} corners stand more than {TOL} outside a straight partner; worst {worst(teeth, 'tooth')}"
    curved = [r for r in rows if r["partnerCurved"]]
    assert {r["key"] for r in curved} == {"2", "e", "è", "é", "ê", "ë"}, f"the corners against a curved partner are {sorted({r['key'] for r in curved})}"
    far = [r for r in curved if r["tooth"] > (1.5 if r["key"] == "2" else 8.0)]
    assert not far, f"a corner against a curved partner stands too far out: {worst(far, 'tooth')}"
    shipped = per_font("corners")
    for example, srows in shipped.items():
        assert srows, f"{example}: no corner ends measured"
        out = [r for r in srows if r["tooth"] > 2.0]
        assert not out, f"{example} as shipped: {len(out)} corners stand more than 2.0 outside the stroke they meet; worst {worst(out, 'tooth')}"


# --- e: the G and the italic r's arm -------------------------------------------------------------------------------------------

def test_the_g_bowl_runs_into_its_stem_without_a_step():
    """The G's first stroke, drawn in every master of every group of the three examples (14 masters, roman and italic), has no
    three-sample turn of 25 degrees or more on either edge (the largest sum of three consecutive turning angles, from sample 3 to
    sample n-4, repeated points skipped).
    Red on 0.9.0 at G-STEP: the bowl turned into the stem at 45 degrees and the pen width jumped there, which reads 42.8 to 119.7."""
    rows = [r for rs in per_font("edges", glyph="G", stroke=0, joint=3, centre=True).values() for r in rs]
    assert len(rows) == masters_in() and len(rows) >= 14, f"{len(rows)} G drawings for {masters_in()} masters"
    assert all(r["samples"] > 100 for r in rows)
    bad = [r for r in rows if max(r["lo"]["w3"], r["hi"]["w3"]) > 25]
    assert not bad, "G-STEP: " + "; ".join(f"{r['font']} {r['group']} {r['master']} {max(r['lo']['w3'], r['hi']['w3']):.1f}" for r in bad)


def test_the_g_bottom_curve_does_not_dip_or_kink_at_its_lowest_point():
    """The same drawings: after the G's lowest point (the end of its third skeleton segment) the centre line never falls below its
    highest level so far by more than 0.005 units, and the outer edge turns by at most 3.0 degrees at any one sample within 12
    samples of that point.
    Red on 0.9.0 at G-BOTTOM: the fit lifts the extreme but not the next control, so the centre line dips 0.83 units on the
    Driftwood Bold and 0.51 on the neutral TextBold, and the joint turns 4.1 degrees."""
    rows = [r for rs in per_font("edges", glyph="G", stroke=0, joint=3, centre=True).values() for r in rs]
    assert len(rows) == masters_in(), f"{len(rows)} G drawings for {masters_in()} masters"
    assert all(isinstance(r["centreFall"], (int, float)) and isinstance(r["jointTurn"], (int, float)) for r in rows)
    bad = [r for r in rows if r["centreFall"] > 0.005 or r["jointTurn"] > 3.0]
    assert not bad, "G-BOTTOM: " + "; ".join(f"{r['font']} {r['group']} {r['master']} fall {r['centreFall']:.3f} turn {r['jointTurn']:.2f}" for r in bad)


def _arm_rows():
    rows = [r for rs in per_font("edges", glyph="r", stroke=1, joint=1, italicOnly=True).values() for r in rs]
    assert len(rows) == masters_in(italic_only=True) and len(rows) >= 4, f"{len(rows)} italic r drawings for {masters_in(italic_only=True)} italic masters"
    return rows


def test_the_italic_r_arm_underside_runs_into_its_terminal_without_a_notch():
    """The italic r's arm (the second stroke of GI.r), in every italic master of the three examples: the underside (the edge with
    the lower y at the arm's joint sample) has no three-sample turn of 35 degrees or more.
    Red on 0.9.0 at R-ARM-UNDER: the arm's extreme is lowered by the fit and the terminal is not, so the underside folds; 50.3 to
    115.4 degrees."""
    rows = _arm_rows()
    bad = [r for r in rows if r["lo"]["w3"] > 35]
    assert not bad, "R-ARM-UNDER: " + "; ".join(f"{r['font']} {r['master']} {r['lo']['w3']:.1f}" for r in bad)


def test_the_italic_r_arm_top_edge_has_no_dip():
    """The same arms: the top edge (the edge with the higher y at the joint sample) has no three-sample turn of 15 degrees or more.
    Red on 0.9.0 at R-ARM-TOP: the centre line humps over the terminal's control, which dips the top edge; 18.1 to 34.2 degrees."""
    rows = _arm_rows()
    bad = [r for r in rows if r["hi"]["w3"] > 15]
    assert not bad, "R-ARM-TOP: " + "; ".join(f"{r['font']} {r['master']} {r['hi']['w3']:.1f}" for r in bad)


# --- f: the release's scope ----------------------------------------------------------------------------------------------------

def _export(gen_dir, example, group, out):
    r = run([node(), str(gen_dir / "export.js"), "--font", str(REPO / "examples" / example / "font.json"), "--group", group, str(out)])
    assert r.returncode == 0, f"{gen_dir.name} {example}/{group}: export.js exited {r.returncode}: {r.stderr[-1500:]}"
    return json.loads(pathlib.Path(out).read_text())


def gen_0_9_0_dir(tmp):
    """The 0.9.0 generator from git, beside a copy of the export.js under test."""
    d = tmp / "old"
    d.mkdir()
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{GEN_0_9_0}:scripts/gen.js"], capture_output=True)
    assert r.returncode == 0, f"git show {GEN_0_9_0}:scripts/gen.js failed: {r.stderr.decode()[:300]}"
    (d / "gen.js").write_bytes(r.stdout)
    shutil.copyfile(SCRIPTS / "export.js", d / "export.js")
    return d


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    """Every example group exported through export.js with the 0.9.0 generator and with the one under test: {(example, group): (old, new)}."""
    tmp = tmp_path_factory.mktemp("joint-exports")
    old = gen_0_9_0_dir(tmp)
    jobs = [(old, e, g, tmp / f"old-{e}-{g}.json") for e, g in EXAMPLE_GROUPS] + [(SCRIPTS, e, g, tmp / f"new-{e}-{g}.json") for e, g in EXAMPLE_GROUPS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        done = list(pool.map(lambda j: _export(*j), jobs))
    n = len(EXAMPLE_GROUPS)
    return {EXAMPLE_GROUPS[i]: (done[i], done[n + i]) for i in range(n)}


def test_only_the_named_glyphs_changed_since_0_9_0(exports):
    """Every group of the three examples exported through the real export.js with the 0.9.0 generator (git show) and with the one
    under test: per master, the glyphs whose polys, raw, runs, keptIdx or minw differ are exactly tests/joint_changes.py OUTLINES
    for that group; the glyphs whose branch record differs are exactly RECORDS; the glyphs whose advance differs are a subset of
    ADVANCES; every kern pair that differs (added, dropped or changed) is allowed by kern_pair_allowed; the word space and the
    minimum stroke width are equal; and every title that has no G (and, in an italic group, no r) is laid to the same width.
    Red on 0.9.0 at SCOPE-OUTLINES: nothing differs yet, so the set is empty: "outlines changed on [], expected [...]".

    What the kern comparison sees, exactly: the kern list export.js writes, which build.py puts in the font unchanged. Each value is
    rounded to a whole unit (`Math.round`), only pairs of glyphs in the face's `kerning.set` are listed, and only pairs whose rounded
    value reaches `kerning.threshold` in some master. So this test does compare kerns, and it cannot see a move that rounding absorbs
    or a pair outside `kerning.set`. Since 0.10.0 a roman pair with G on the right moves by up to 0.0364 units before rounding (639
    pairs on the three examples). None of them changes a listed value, which is why this test passes: the one that rounds to another
    whole number, the Driftwood roman Bold's u-acute before G (-21.5065 to -21.4970, -22 to -21), is outside Driftwood's
    `kerning.set` and is never written. tests/test_joint_spacing.py holds the unrounded values. Watched red at SCOPE-KERNS under W13
    (references/testing.md section 11): every roman kern with G on the right made 1 unit tighter in kern()."""
    fields = ("polys", "raw", "runs", "keptIdx", "minw")
    outlines, records, advances, kerns, other = [], [], [], [], []
    for (example, group), (old, new) in exports.items():
        italic = group == "italic"
        for master in old["masters"]:
            om, nm = old["masters"][master], new["masters"][master]
            where = f"{example}/{group}/{master}"
            assert set(om["glyphs"]) == set(nm["glyphs"]), f"{where}: the glyph set changed"
            def differs(k):
                return any(json.dumps(om["glyphs"][k][f], sort_keys=True) != json.dumps(nm["glyphs"][k][f], sort_keys=True) for f in fields)

            changed = sorted(k for k in om["glyphs"] if differs(k))
            if changed != sorted(OUTLINES[(example, group)]):
                outlines.append(f"{where}: outlines changed on {changed}, expected {sorted(OUTLINES[(example, group)])}")
            recs = sorted(k for k in om["glyphs"] if om["glyphs"][k]["sig"] != nm["glyphs"][k]["sig"])
            if recs != sorted(RECORDS[group]):
                records.append(f"{where}: records changed on {recs}, expected {sorted(RECORDS[group])}")
            advs = sorted(k for k in om["glyphs"] if om["glyphs"][k]["adv"] != nm["glyphs"][k]["adv"])
            if not set(advs) <= ADVANCES[group]:
                advances.append(f"{where}: advances changed on {advs}, allowed {sorted(ADVANCES[group])}")
            ko, kn = {tuple(x[:2]): x[2] for x in om["kerns"]}, {tuple(x[:2]): x[2] for x in nm["kerns"]}
            diff = sorted(p for p in set(ko) | set(kn) if ko.get(p) != kn.get(p))
            stray = [p for p in diff if not kern_pair_allowed(italic, *p)]
            if stray:
                kerns.append(f"{where}: {len(stray)} kern pairs changed outside the allowed set, first {stray[:5]}")
            for f in ("space", "minStrokeWidth"):
                if om[f] != nm[f]:
                    other.append(f"{where}: {f} changed: {om[f]} -> {nm[f]}")
            for title in om["titles"]:
                if "G" in title or (italic and "r" in title):
                    continue
                if om["titles"][title] != nm["titles"][title]:
                    other.append(f"{where}: the title {title!r} changed width {om['titles'][title]} -> {nm['titles'][title]}")
    assert not outlines, "SCOPE-OUTLINES:\n" + "\n".join(outlines)
    assert not records, "the branch records changed on the wrong glyphs:\n" + "\n".join(records)
    assert not advances, "\n".join(advances)
    assert not kerns, "SCOPE-KERNS:\n" + "\n".join(kerns)
    assert not other, "\n".join(other)
