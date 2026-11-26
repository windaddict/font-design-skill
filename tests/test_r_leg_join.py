"""The capital R's leg leaves its bowl without a nub, in every concept the repo ships, and nothing else changed.

WHAT IT'S FOR: the R's leg started on the bowl's thin closing bar with a hidden-join disk (0.42 of the leg's
width) that was wider than the bar, so a round lump showed in the counter at every weight (15 to 36 units on
Bract's four masters, 0.6 to 2.9 px at the sizes it ships at; docs/plan-r-leg.md section 0). Since 0.5.0 the
leg's start is typed `i`, a T-join: cut parallel to the bar on the bar's centre line, buried, no terminal. These
tests draw the R with the real generator (tests/r_leg_junction.js runs scripts/gen.js and prints what it drew) for
every concept of the five concept files at mult 1 and 1.5, roman and italic, and hold the construction to what a
reader of the outline would check; they also hold the T-join's own rules on hand-built glyphs, prove the
measurement sees the 0.4.0 defect, compare the filled union near the join with the 0.4.0 outline, and compare
every example group's export with the 0.4.0 generator's so the change is known to reach the R only, apart from what 0.10.0
declares (tests/joint_changes.py: the glyphs it redraws, the advances and kerns it moves), which that comparison takes out and
still holds every other glyph to.

FONT_DESIGN_R_GEN names another gen.js to measure (a scratch copy carrying a mutation); unset, the real one. The
0.4.0 generator is read from git (BASELINE_REV) for the comparison tests, so they need a git checkout.

Mutations watched red (2026-11-18, by hand, each applied to scripts/gen.js and restored by digest; the log is in
references/testing.md section 8): M1 the leg's `i` back to `""`; M2 the cut moved to the bar's far edge (the flush
corner of the plan's first draft); M3 a square cut at the centre line; M4 the cut kept and the disk still drawn;
M5 the leg re-rooted below the bar; M6 the leg re-rooted on the bowl's curve; M7 the sample index dropped from the
tee token; and, for test c, the token dropped, the partner search accepting a stroke's end, the tolerance widened
to 4 units, the parallel refusal removed, the cut taken from the partner's chord instead of its local tangent, the
rule widened to `""` ends, the pinned edges bucketed from the angle with a dead band (the crossing construction then reads "=" for both
masters), the burial check at the corners only (the wave), nine probes along the cut instead of the exact crossing test (the narrow trough),
a ring's outer contour taken by push order (the ring drawn the other way round, no-fit variant), the partner measured to sample points
instead of segments (the mid-gap root); for test d the taper term dropped; for test e the italic leg left `""`; for test f M2 and
M4 again; for test b the bowl set made to include the leg, the lower-edge rule inverted, and a warm cache before
the swap. The clamp refusal of the T-join cannot be reached by any geometry (the parallel refusal at 14.5 degrees
bounds the reach at 1.87 widths, under the clamp of 3), so it has no mutation; test c asserts that arithmetic
instead.
"""
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, node, run

sys.path.insert(0, str(REPO / "tests"))
from joint_changes import ADVANCES, OUTLINES, RECORDS, kern_pair_allowed  # noqa: E402

GEN = pathlib.Path(os.environ.get("FONT_DESIGN_R_GEN", REPO / "scripts" / "gen.js"))
JUNCTION = REPO / "tests" / "r_leg_junction.js"
CONCEPT_FILES = sorted((REPO / "examples").glob("*/concepts.js")) + [REPO / "templates" / "concepts.example.js", REPO / "templates" / "concepts.genres.js"]
BASELINE_REV = "598044b"  # 0.4.0, the last release whose R carried the disk
EXAMPLE_GROUPS = [("neutral", "roman"), ("neutral", "italic"), ("bract", "roman"), ("driftwood", "roman"), ("driftwood", "italic")]
TEE = re.compile(r"^(\d+)@(\d+)(L|R|LR|=)/-$")  # partner stroke @ its segment, the edges clipPast pinned past the cut (= neither)


def junction(mode, gen, *files, env=None):
    r = run([node(), str(JUNCTION), mode, str(gen), *map(str, files)], env={**os.environ, **(env or {})})
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


@pytest.fixture(scope="module")
def measured():
    """Every drawing of every concept file with the generator under test: {file: {drawing: record}}."""
    return {f.parent.name + "/" + f.name: junction("measure", GEN, f) for f in CONCEPT_FILES}


def drawings_of(measured, f):
    recs = measured[f.parent.name + "/" + f.name]
    assert len(recs) >= 4, f"{f}: only {len(recs)} drawings"
    for key, r in recs.items():
        assert "error" not in r, f"{key}: the generator threw: {r['error']}"
    return recs


def roman(key):
    return not key.endswith("i")


# --- a: the leg is buried in its bowl --------------------------------------------------------------------------------

@pytest.mark.parametrize("f", CONCEPT_FILES, ids=lambda p: p.parent.name + "/" + p.name)
def test_the_r_leg_is_buried_in_its_bowl_in_every_concept(measured, f):
    """For every concept, mult 1 and 1.5, roman and italic where `x` is mapped: no leg vertex pokes out of the bowl above the
    bowl's lower edge (the nub is 0, into the counter and below the bar alike); the leg body still overlaps the bowl; no disk is
    drawn at the root; the cut's two corners (the body's closing seam) are level, on the bar's centre line (within 0.05 of the
    bar's half-thickness of the midpoint of its edges), buried by at least 0.4 of the half-thickness (measured minimum 0.54), and,
    on the straight roman leg, w / sin(phi) apart with phi the leg's angle to the level bar (the whole cut, 1.24 w at 54 degrees;
    0.62 w is the reach per side); the roman leg's direction is the skeleton's, atan2(-340, 250 xs_eff), and its foot sits on the
    baseline; and the tee token names the same partner stroke and sample at both weights.
    Red on 0.4.0: the nub is 14.97 on Bract text at mult 1 (95 of 134 drawings over 1 unit), with the disk present."""
    recs = drawings_of(measured, f)
    bad = []
    tokens = {}
    for key, r in recs.items():
        mult = 1.5 if "@1.5" in key else 1.0
        xs_eff = (r.get("xs") or 1) * (1 + 0.16 * (mult - 1)) * (0.95 if r["italic"] else 1)
        checks = [
            ("nub", r["nub"] <= 1e-6, f"nub {r['nub']} at {r['nubAt']}"),
            ("below", r["below"] <= 1e-6, f"below the bar {r['below']}"),
            ("overlap", r["overlap"] >= 1, "the leg does not reach the bowl"),
            ("disk", not r["diskAtRoot"], "a disk is drawn at the root"),
            ("level", r["tilt"] <= 1e-6, f"the cut tilts by {r['tilt']}"),
            ("centre", r["centreOffset"] is not None and r["centreOffset"] <= 0.05 * r["halfBar"],
             f"the cut is {r['centreOffset']} off the bar's centre line (half-thickness {r['halfBar']})"),
            ("buried", r["margin"] >= 0.4 * r["halfBar"], f"burial margin {r['margin']} against half-thickness {r['halfBar']}"),
            ("token", r["tee"] is not None and TEE.match(r["tee"]) is not None, f"tee token {r['tee']!r}"),
        ]
        if roman(key):
            phi = math.radians(abs(r["legAngle"]))
            # the width at the root: the width at sample 40 brought back through the swell, which thickens a stroke's ends by swell/2
            # and thins its middle (generator.md section 3), restated from the sample's arc length and the stroke's total
            p40 = next(p for p in r["profile"] if p["j"] == 40)
            w_root = r["w"] * (1 + r["swell"] * 0.5) / (1 + r["swell"] * (0.5 - math.sin(math.pi * p40["s"] / r["total"])))
            want = w_root / math.sin(phi)
            # the skeleton's leg direction after the concept's x transforms: xs (with the weight widening), a uniform shear if any
            skel = math.degrees(math.atan2(-340, 250 * xs_eff - 340 * r["shear"]))
            checks += [
                ("cut length", abs(r["cutLen"] - want) <= 0.03 * w_root,
                 f"cut {r['cutLen']} for a root width of {w_root:.1f} at {r['legAngle']} degrees, expected {want:.1f}"),
                ("angle", abs(r["legAngle"] - skel) <= 0.5, f"leg angle {r['legAngle']}, skeleton {skel:.2f}"),
                ("foot", abs(r["footY"]) <= 1e-6, f"foot at y {r['footY']}"),
            ]
        for name, ok, detail in checks:
            if not ok:
                bad.append(f"{key}: {name}: {detail}")
        tokens.setdefault(key.replace("@1.5", "@1"), set()).add(r["tee"])
    for pair, toks in tokens.items():
        if len(toks) != 1:
            bad.append(f"{pair}: the tee token differs between weights: {sorted(map(str, toks))}")
    assert not bad, "\n".join(bad)


# --- b: the measurement sees the defect ------------------------------------------------------------------------------

def test_the_measurement_sees_the_0_4_0_defect():
    """A control, green before and after the fix: the measurement of test a, run in a FRESH node process that installs the
    0.4.0 R skeleton (written into r_leg_junction.js as a literal) before its first and only draw of the R, reports the nub
    (at least 10 units on the first concept of examples/bract at mult 1; 14.97 measured) and the disk. gen.js caches a drawn
    glyph by concept and key (glyph(), the cache lookup), so a swap after any draw of R in the same process reads the fixed
    skeleton: FD_R_CONTROL_WARM=1 does exactly that and must make this control fail, which is asserted too."""
    r = junction("control", GEN, REPO / "examples" / "bract" / "concepts.js")
    # the figure the plan measured on 0.4.0 (docs/plan-r-leg.md section 0), and where it is: the disk's top in the counter, above the
    # bar's upper edge (y 361.5 in that drawing). A measurement that counts the wrong side reports a large number somewhere else
    # (the lower-edge rule inverted reported the leg itself, below the bar, and passed a plain "at least 10": found by mutation 2026-11-19)
    assert abs(r["nub"] - 14.97) < 0.05, f"the measurement does not see the 0.4.0 lump as measured (14.97): nub {r['nub']}"
    assert r["nubAt"][1] > 361, f"the 0.4.0 lump is in the counter, above the bar; the measurement found its worst point at {r['nubAt']}"
    assert r["diskAtRoot"], "the measurement does not see the 0.4.0 disk"
    # a warm cache serves the generator's own R, whatever was installed after the draw: the control then equals a plain draw
    warm = junction("control", GEN, REPO / "examples" / "bract" / "concepts.js", env={"FD_R_CONTROL_WARM": "1"})
    plain = junction("measure", GEN, REPO / "examples" / "bract" / "concepts.js")["bract/concepts.js:text@1"]
    assert (warm["nub"], warm["diskAtRoot"], warm["polys"]) == (plain["nub"], plain["diskAtRoot"], plain["polys"]), \
        f"a warm cache should have served the generator's own R: control {warm['nub']}, plain draw {plain['nub']}"


# --- c: the T-join's own rules -----------------------------------------------------------------------------------------

def test_an_i_end_is_cut_parallel_to_the_stroke_it_runs_into():
    """Hand-built glyphs drawn with the neutral example's first concept (serif stems, the hidden join a disk) at mult 1 and 1.5,
    through the x-height map at 400 and 600 and at the italic slant, each case under its own concept copy so no case reads
    another's cache. A level bar with a 54 degree stroke starting `i` on it: the record reads tee=0@k with the same k in every
    variant, the cut is level on the bar's drawn centre line, w / sin(phi) long, no terminal. The same on a ring: the cut is
    parallel to the ring's local tangent (not level). A 30 degree bar: parallel within 0.1 degree. An `i` end at the bar's END,
    or 3 units off it, or within 10 degrees of it, or 2.5 units from the bar's end (no joint partner, a sample found, but the cut
    cannot fit inside the bar, which the burial check refuses): the draw throws, naming why. A 15 degree stroke draws with a reach of
    w / (2 tan 15) = 1.87 w per side, under the clamp of 3 w (the clamp cannot be reached: the parallel refusal comes first).
    A 16 degree stroke draws at xh 500 and 600 and in the italic, and throws at xh 400, where the map takes it to 12.9
    degrees: two masters at those x-heights would not share a record. The same stroke typed `""` draws its disk and no token;
    typed `j` it draws a square cut and no token."""
    out = junction("synthetic", GEN, REPO / "examples" / "neutral" / "concepts.js")
    bad = []

    def expect(cond, msg):
        if not cond:
            bad.append(msg)

    ks, mids = set(), set()
    for variant in ("500", "400", "600", "italic", "wide", "nofit"):
        for mult in ("1", "1.5"):
            if variant == "wide" and mult != "1.5":
                continue
            c = out[f"{variant}/{mult}/bar"]
            expect(c["ok"], f"{variant}/{mult}/bar: {c.get('error')}")
            if c["ok"]:
                m = TEE.match(c["tee"] or "")
                expect(m is not None and m.group(1) == "0" and m.group(3) == "L", f"{variant}/{mult}/bar: tee token {c['tee']!r}")
                if m:
                    ks.add(m.group(2))
                expect(c["tilt"] <= 1e-6 and abs(c["cutY"] - c["barY"]) <= 1e-6, f"{variant}/{mult}/bar: cut at y {c['cutY']} tilt {c['tilt']}, bar centre {c['barY']}")
                phi = math.radians(abs(c["legDeg"] - c["partnerDeg"]))
                expect(abs(c["cutLen"] - c["w"] / math.sin(phi)) <= 0.03 * c["w"],
                       f"{variant}/{mult}/bar: cut {c['cutLen']} for width {c['w']} at {math.degrees(phi):.1f} degrees")
                expect(c["legPolys"] == 2 and not c["diskAtRoot"], f"{variant}/{mult}/bar: {c['legPolys']} leg polygons, disk {c['diskAtRoot']}")
                expect(c["ends"].startswith("tee/"), f"{variant}/{mult}/bar: ends {c['ends']}")
            # the same stroke approaching from the other side (down-left, against the bar's direction): the pinned edge is the other one,
            # the token's side letter reads R, nothing else differs
            c = out[f"{variant}/{mult}/mirror"]
            expect(c["ok"], f"{variant}/{mult}/mirror: {c.get('error')}")
            if c["ok"]:
                mm = TEE.match(c["tee"] or "")
                expect(mm is not None and mm.group(3) == "R" and c["tilt"] <= 1e-6 and not c["diskAtRoot"],
                       f"{variant}/{mult}/mirror: {c['tee']!r}, tilt {c['tilt']}")
            # a 440-unit bar puts the root exactly midway between two samples; the partner is the SEGMENT between them, so the token is
            # the same in every variant (the nearest-sample rule picked a different sample per weight here: review of the diff, F007)
            c = out[f"{variant}/{mult}/midgap"]
            expect(c["ok"], f"{variant}/{mult}/midgap: {c.get('error')}")
            if c["ok"]:
                mm = TEE.match(c["tee"] or "")
                expect(mm is not None, f"{variant}/{mult}/midgap: token {c['tee']!r}")
                if mm:
                    mids.add(mm.group(2))
            # a wavy partner: the cut's corners land on crests, inside the stroke, while its middle spans a trough, outside it; the
            # burial check samples the whole cut and refuses (a corner-only check draws it: review of the diff, F005)
            c = out[f"{variant}/{mult}/wave"]
            expect(not c["ok"] and "not buried" in c.get("error", ""), f"{variant}/{mult}/wave: expected a refusal (not buried), got {c}")
            c = out[f"{variant}/{mult}/slope"]
            expect(c["ok"], f"{variant}/{mult}/slope: {c.get('error')}")
            if c["ok"]:
                expect(TEE.match(c["tee"] or "") is not None, f"{variant}/{mult}/slope: tee token {c['tee']!r}")
                expect(c["cutVsPartnerDeg"] <= 0.1, f"{variant}/{mult}/slope: the cut is {c['cutVsPartnerDeg']} degrees off the bar")
                expect(not c["diskAtRoot"], f"{variant}/{mult}/slope: a disk at the root")
            # the ring: its outer contour is told from its inner by area (review of the diff, F006), which the ring drawn the other way round
            # shows: a hand-written closed path keeps its `closed` through fitSkeleton only without the fit (`overshoot` 0, `xh` 500: the
            # `nofit` variant; with the fit on it comes back as an open stroke), so that direction runs there (re-review, R3)
            for name in ("ring", "ringrev") if variant == "nofit" else ("ring",):
                c = out[f"{variant}/{mult}/{name}"]
                expect(c["ok"], f"{variant}/{mult}/{name}: {c.get('error')}")
                if c["ok"]:
                    expect(TEE.match(c["tee"] or "") is not None, f"{variant}/{mult}/{name}: tee token {c['tee']!r}")
                    # the cut follows the ring's centre-line tangent at the root (restated from the ellipse through the concept's transforms;
                    # the sampled centre line steps about 0.7 degrees of parameter), not the level, and not the offset outline's tangent
                    off = abs((c["cutDeg"] - c["expectedDeg"]) % 180)
                    off = min(off, 180 - off)
                    expect(off <= 1.5, f"{variant}/{mult}/{name}: the cut is {off:.2f} degrees off the ring's tangent at the root ({c['expectedDeg']})")
                    expect(c["tilt"] > 5, f"{variant}/{mult}/{name}: the cut should follow the ring's tangent, not be level (tilt {c['tilt']})")
                    expect(not c["diskAtRoot"], f"{variant}/{mult}/{name}: a disk at the root")
            for name, text in (("end", "meets another stroke's end"), ("off", "lies on no other stroke's interior"), ("parallel", "within 14.5 degrees"),
                               ("edge", "not buried")):
                c = out[f"{variant}/{mult}/{name}"]
                expect(not c["ok"] and text in c.get("error", ""), f"{variant}/{mult}/{name}: expected a refusal saying {text!r}, got {c}")
            c = out[f"{variant}/{mult}/disk"]
            expect(c["ok"] and c["tee"] is None and c["diskAtRoot"] and c["ends"].startswith("disk/"), f"{variant}/{mult}/disk: {c}")
            c = out[f"{variant}/{mult}/square"]
            expect(c["ok"] and c["tee"] is None and not c["diskAtRoot"] and c["tilt"] > 1 and c["ends"].startswith("undefined/"), f"{variant}/{mult}/square: {c}")
    expect(len(ks) == 1, f"the bar case's partner segment differs between variants: {sorted(ks)}")
    # the reviewer's crossing construction (re-review, R1): a level bar, a leg from (500, 340) to (750, 0), W 200, xs 1, shear 0.77: the
    # leg's drawn angle to the bar passes through perpendicular between mult 1 and 1.5, so clipPast pins the LEFT edge in one master and
    # the RIGHT edge in the other. The token records the pinned edges as clipPast made them, so the two records differ and the exporter's
    # record comparison refuses the pair; a token bucketed from the angle, with a dead band, read "=" for both and let them interpolate
    a, b = out["500/1/cross"], out["500/1.5/cross"]
    expect(a["ok"] and b["ok"], f"cross: {a.get('error')} / {b.get('error')}")
    if a["ok"] and b["ok"]:
        ta, tb = TEE.match(a["tee"] or ""), TEE.match(b["tee"] or "")
        expect(ta is not None and tb is not None, f"cross: tokens {a['tee']!r} {b['tee']!r}")
        if ta and tb:
            expect(ta.group(2) == tb.group(2), f"cross: the partner segment differs between weights: {a['tee']} {b['tee']}")
            expect({ta.group(3), tb.group(3)} == {"L", "R"}, f"cross: the pinned edges should be L in one master and R in the other, got {a['tee']} {b['tee']}")
            expect((a["pinned"][0] > 0) != (b["pinned"][0] > 0) and (a["pinned"][1] > 0) != (b["pinned"][1] > 0),
                   f"cross: clipPast should pin opposite edges in the two masters, pinned {a['pinned']} and {b['pinned']}")
            expect(a["tee"] != b["tee"], "cross: the two masters' records must differ, so export.js refuses the pair")
    expect(len(mids) == 1, f"the mid-gap case's partner segment differs between variants: {sorted(mids)}")
    # the narrow trough (re-review, R2): the partner's edge dips across the cut over a few units, between two of nine probes; the exact
    # check (the cut crosses the partner's edge) refuses it at both weights, nine probes drew it
    for mult in ("1", "1.5"):
        c = out[f"500/{mult}/trough"]
        expect(not c["ok"] and "crosses that stroke's edge" in c.get("error", ""), f"500/{mult}/trough: expected a refusal on a crossed edge, got {c}")
    c = out["500/1/shallow15"]
    expect(c["ok"], f"500/1/shallow15: {c.get('error')}")
    if c["ok"]:
        # drawn at 16.25 degrees (the 15 degree skeleton stroke steepened by xs 0.92): the shallowest meeting that draws, where the
        # reach per side is w / (2 tan phi), 1.7 widths, under the clamp of 3; the angle refusal at 14.5 degrees comes first always
        phi = math.radians(abs(c["legDeg"] - c["partnerDeg"]))
        expect(14.5 < math.degrees(phi) < 20, f"shallow15 drew at {math.degrees(phi):.2f} degrees")
        expect(abs(c["cutLen"] - c["w"] / math.sin(phi)) <= 0.05 * c["w"], f"shallow15: cut {c['cutLen']} for width {c['w']}, expected {c['w'] / math.sin(phi):.1f}")
        expect(0.5 / math.tan(phi) < 3, "the reach per side at the shallowest drawable angle must be under the clamp of 3 widths")
    for variant, ok in (("500", True), ("600", True), ("italic", True), ("400", False)):
        c = out[f"{variant}/1/shallow16"]
        expect(c["ok"] == ok, f"{variant}/1/shallow16: expected {'a draw' if ok else 'a refusal'}, got {c}")
        if not ok:
            expect("within 14.5 degrees" in c.get("error", ""), f"400/1/shallow16: {c.get('error')}")
    assert not bad, "\n".join(bad)


# --- d: the italic leg keeps its join taper ----------------------------------------------------------------------------

def test_the_italic_leg_keeps_its_join_taper(measured):
    """The italic R's leg is a curve, and a curved stroke whose hidden-join end has no partner thins by 30 % over 0.9 W0 into the
    bowl (the join taper, generator.md section 3). The T-join keeps that taper (operator decision, docs/plan-r-leg.md section
    11), so the italic leg is drawn as 0.4.0 drew it apart from the cut. Restated here from the generator's formulas: at samples
    20, 23 and 26 (inside the taper's reach) the leg's width is W f(theta) m(s) (1 + swell (0.5 - sin(pi s / total))) with
    f = thin + (1 - thin) |sin(theta - nib)|^pow, m = 1 - 0.3 (1 - s / 0.9 W0)^1.5, within 3 %, and at sample 60 (past the
    reach) m is 1. The roman leg is straight and untapered: m is 1 at every sample. Concepts with an optical knob are left out
    (their width law has more factors than this restates)."""
    checked = 0
    bad = []
    for fkey, recs in measured.items():
        for key, r in recs.items():
            if "error" in r or r.get("optical"):
                continue
            tapl = 0.9 * r["W0"]
            for p in r["profile"]:
                f = r["thin"] + (1 - r["thin"]) * abs(math.sin(p["theta"] - r["nib"])) ** r["pow"]
                mm = (1 - 0.3 * (1 - p["s"] / tapl) ** 1.5) if (not roman(key) and p["s"] < tapl) else 1.0
                sw = 1 + r["swell"] * (0.5 - math.sin(math.pi * p["s"] / r["total"]))
                want = r["W"] * f * mm * sw
                if abs(p["width"] / want - 1) > 0.03:
                    bad.append(f"{key} sample {p['j']}: width {p['width']:.2f}, expected {want:.2f} (taper factor {mm:.3f})")
                checked += 1
    assert checked > 100, f"only {checked} samples checked"
    assert not bad, "\n".join(bad[:20])


# --- e: nothing but the R changed since 0.4.0 --------------------------------------------------------------------------

def gen_dir_under_test(tmp):
    """A folder holding the generator under test beside a copy of export.js (export.js requires ./gen.js)."""
    if GEN.resolve() == (REPO / "scripts" / "gen.js").resolve():
        return REPO / "scripts"
    d = tmp / "new"
    d.mkdir()
    shutil.copyfile(GEN, d / "gen.js")
    shutil.copyfile(REPO / "scripts" / "export.js", d / "export.js")
    return d


def baseline_gen_dir(tmp):
    """The 0.4.0 generator from git, beside a copy of export.js (unchanged by this change)."""
    d = tmp / "old"
    d.mkdir()
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{BASELINE_REV}:scripts/gen.js"], capture_output=True)
    assert r.returncode == 0, f"git show {BASELINE_REV}:scripts/gen.js failed: {r.stderr.decode()[:300]}"
    (d / "gen.js").write_bytes(r.stdout)
    shutil.copyfile(REPO / "scripts" / "export.js", d / "export.js")
    return d


def export(gen_dir, example, group, out):
    r = run([node(), str(gen_dir / "export.js"), "--font", str(REPO / "examples" / example / "font.json"), "--group", group, str(out)])
    assert r.returncode == 0, f"{gen_dir.name} {example}/{group}: export.js exited {r.returncode}: {r.stderr[-1500:]}"
    return json.loads(out.read_text())


def profiles(raw):
    """The 54 bins of 20 units from y -260 that glyph() spaces and kerns by, recomputed from the raw polygons: leftmost and
    rightmost x per bin."""
    L, R = [None] * 54, [None] * 54
    for poly in raw:
        for x, y in poly:
            b = math.floor((y + 260) / 20)
            if 0 <= b < 54:
                L[b] = x if L[b] is None or x < L[b] else L[b]
                R[b] = x if R[b] is None or x > R[b] else R[b]
    return [None if v is None else round(v, 6) for v in L], [None if v is None else round(v, 6) for v in R]


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("r-exports")
    old, new = baseline_gen_dir(tmp), gen_dir_under_test(tmp)
    out = {}
    for example, group in EXAMPLE_GROUPS:
        out[(example, group)] = (export(old, example, group, tmp / f"old-{example}-{group}.json"), export(new, example, group, tmp / f"new-{example}-{group}.json"))
    return out


def test_only_the_r_changed_since_0_4_0(exports):
    """Every group of the three examples exported through the real export.js with the 0.4.0 generator (git show) and with the one
    under test: per master, the glyphs whose adv, polys, raw, runs, keptIdx or minw differ are exactly {R} plus the glyphs 0.10.0
    redraws on purpose (tests/joint_changes.py OUTLINES for that group); the glyphs whose branch record differs are exactly {R} plus
    RECORDS; every advance is equal except those of ADVANCES; the 54-bin left and right profiles recomputed here from every glyph's raw
    polygons are equal for every glyph outside that outline set, R included (its profile does not move); the emitted kern list is
    identical pair for pair and value for value except pairs `kern_pair_allowed` admits; titles that contain neither G nor (in an
    italic group) r, space and minStrokeWidth are equal. Green before the fix (nothing differs) and after it; red if the change reaches
    any other glyph, an advance or a kern. The field list is the one this docstring states: a comparison that skipped
    `raw` would pass a change confined to undecimated points, which no execution can observe, so that mutation is recorded as
    uncatchable here. The 0.10.0 sets are taken out so the test still sees every other glyph; a glyph in those sets is held by
    tests/test_serif_joints.py against 0.9.0."""
    fields = ("adv", "polys", "raw", "runs", "keptIdx", "minw")
    bad = []
    for (example, group), (old, new) in exports.items():
        italic = group == "italic"
        outline_set = set(OUTLINES[(example, group)])
        for master in old["masters"]:
            om, nm = old["masters"][master], new["masters"][master]
            where = f"{example}/{group}/{master}"
            assert set(om["glyphs"]) == set(nm["glyphs"]), f"{where}: the glyph set changed"
            changed = sorted(k for k in om["glyphs"]
                             if any(json.dumps(om["glyphs"][k][f], sort_keys=True) != json.dumps(nm["glyphs"][k][f], sort_keys=True) for f in fields))
            expected = sorted({"R"} | outline_set)
            if changed != expected:
                bad.append(f"{where}: outlines changed on {changed}, expected {expected}")
            records = sorted(k for k in om["glyphs"] if om["glyphs"][k]["sig"] != nm["glyphs"][k]["sig"])
            expected_records = sorted({"R"} | set(RECORDS[group]))
            if records != expected_records:
                bad.append(f"{where}: records changed on {records}, expected {expected_records}")
            advs = [k for k in om["glyphs"] if om["glyphs"][k]["adv"] != nm["glyphs"][k]["adv"] and k not in ADVANCES[group]]
            if advs:
                bad.append(f"{where}: advances changed on {advs}")
            prof = [k for k in om["glyphs"] if k not in outline_set and profiles(om["glyphs"][k]["raw"]) != profiles(nm["glyphs"][k]["raw"])]
            if prof:
                bad.append(f"{where}: the spacing profiles changed on {prof}")
            ko, kn = {tuple(x[:2]): x[2] for x in om["kerns"]}, {tuple(x[:2]): x[2] for x in nm["kerns"]}
            diff = sorted(k for k in set(ko) | set(kn) if ko.get(k) != kn.get(k))
            stray = [k for k in diff if not kern_pair_allowed(italic, *k)]
            if stray:
                bad.append(f"{where}: {len(stray)} kern pairs changed outside the allowed set, first {stray[:5]}")
            for f in ("space", "minStrokeWidth"):
                if om[f] != nm[f]:
                    bad.append(f"{where}: {f} changed: {om[f]} -> {nm[f]}")
            for title in om["titles"]:
                if "G" in title or (italic and "r" in title):
                    continue
                if om["titles"][title] != nm["titles"][title]:
                    bad.append(f"{where}: the title {title!r} changed width {om['titles'][title]} -> {nm['titles'][title]}")
    assert not bad, "\n".join(bad)


# --- f: the filled union near the join ---------------------------------------------------------------------------------

def _contours(path):
    cs, cur = [], []
    for verb, pts in path.segments:
        if verb == "moveTo":
            cur = [pts[0]]
        elif verb == "lineTo":
            cur.append(pts[0])
        elif verb == "closePath":
            if cur:
                cs.append(cur)
            cur = []
        else:
            raise RuntimeError(f"unexpected path verb {verb}")
    if cur:
        cs.append(cur)
    return cs


def _union(polys):
    from pathops import Path, union
    p = Path()
    for poly in polys:
        p.moveTo(*poly[0])
        for q in poly[1:]:
            p.lineTo(*q)
        p.close()
    out = Path()
    union([p], out.getPen())
    return _contours(out)


def _segdist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy or 1
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _bdist(p, polys):
    return min(_segdist(p, poly[i], poly[(i + 1) % len(poly)]) for poly in polys for i in range(len(poly)))


def _pdist(p, polyline):
    """Distance to an OPEN polyline (no closing edge): the leg's side edges."""
    return min(_segdist(p, polyline[i], polyline[i + 1]) for i in range(len(polyline) - 1))


def _edge_samples(contours):
    """Every vertex of the contours and three points along each edge: a straight edge that protrudes between two legal vertices
    (the flush cut of the plan's first draft: its corners sit on the leg's sides, its middle stands proud of the bar) is seen only
    along the edge."""
    for c in contours:
        for i in range(len(c)):
            a, b = c[i], c[(i + 1) % len(c)]
            yield a
            for t in (0.25, 0.5, 0.75):
                yield (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


@pytest.fixture(scope="module")
def dumps(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("r-dumps")
    old = baseline_gen_dir(tmp) / "gen.js"
    return {f.parent.name + "/" + f.name: (junction("dump", old, f), junction("dump", GEN, f)) for f in CONCEPT_FILES}


@pytest.mark.parametrize("f", CONCEPT_FILES, ids=lambda p: p.parent.name + "/" + p.name)
def test_the_filled_union_near_the_join_is_the_old_outline_plus_the_leg(dumps, f):
    """What a reader sees is the nonzero union of the R's polygons, whose boundary includes the crossings of the leg's sides with the
    bar's edges, which no vertex test can see. For every drawing: the union of the polygons under test (skia-pathops, what
    build.py's raster check uses) has, in the window y 150-450 from the stem to past the root (x up to 480 from the stem's
    left edge), every boundary vertex and three points along every boundary edge within 0.05 units of the 0.4.0 stem-and-bowl outline
    or of one of the leg's two side edges (open polylines; a vertex-only check passed the flush cut, whose corners lie on the leg's
    sides while its middle stands proud of the bar: found by the M2 mutation on 2026-11-19)
    (measured worst 0.015, skia's float rounding); and between the stem and the point where either construction first touches the
    bar (the new cut's left corner, the old disk's left extreme), above the bar's centre line, the two unions' boundaries coincide
    both ways within 0.05 (measured 0.000): no step on the bar's top edge. The window starts at the stem, not at the root: a
    step left of the root would be missed by a window that started there. Red on 0.4.0 (the disk's arc is on the boundary) and
    under the flush-cut mutation (the cut's corners sit on the bar's edge and skia keeps them as boundary vertices).
    The two drawings are brought into one frame on the middle sample of the stem's first edge run (tests/r_leg_junction.js dump), a
    point no end construction moves; the stem's end corner is not used, because a cut stem end moves it and the frame would move with it."""
    pytest.importorskip("pathops", reason="skia-pathops is in requirements.txt; the union check needs it")
    old_all, new_all = dumps[f.parent.name + "/" + f.name]
    bad = []
    for key in new_all:
        o, n = old_all[key], new_all[key]
        if "error" in o or "error" in n:
            bad.append(f"{key}: {o.get('error') or n.get('error')}")
            continue
        ob, nb = o["bodies"], n["bodies"]
        old_stem_bowl = o["polys"][:ob[-1]]
        new_leg = n["polys"][nb[-1]]
        half = len(new_leg) // 2
        sides = [new_leg[:half], new_leg[half:]]
        U_new, U_old = _union(n["polys"]), _union(o["polys"])
        worst = 0.0
        for p in _edge_samples(U_new):
            if not (150 < p[1] < 450 and 0 < p[0] < 480):
                continue
            d = min(_bdist(p, old_stem_bowl), _pdist(p, sides[0]), _pdist(p, sides[1]))
            worst = max(worst, d)
        if worst > 0.05:
            bad.append(f"{key}: a union boundary vertex near the join is {worst:.3f} units off the old outline and the leg's sides")
        cut_left = min(new_leg[0][0], new_leg[-1][0])
        top = lambda p: 120 < p[0] < cut_left - 1 and 341 < p[1] < 420  # noqa: E731
        step = max([_bdist(p, U_old) for p in _edge_samples(U_new) if top(p)] + [_bdist(p, U_new) for p in _edge_samples(U_old) if top(p)] + [0.0])
        if step > 0.05:
            bad.append(f"{key}: the bar's top edge steps by {step:.3f} units between the stem and the join")
    assert not bad, "\n".join(bad)
