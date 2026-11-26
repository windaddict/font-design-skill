"""A `cut` moves two corners and the samples they passed, nothing else (0.11.0).

WHAT IT'S FOR: the fix for the spike on a `cut` end (tests/test_cut_ends.py) can go too far. Pinning every edge sample that lies past
the infinite cut line, for up to 80 steps, removes every spike, but on a curved terminal the body of the stroke itself lies past that
line, so the pin replaces up to 80 samples of the inner edge by one chord, and it also runs on an end the cut did not move. The fix in
the plan bounds the pin by how far the corner moved. These two tests hold that bound from the outside. Both pin behaviour that
0.10.0 already has (a cut moves its corner and nothing else), so they pass on 0.10.0 and are meant to go red under the unbounded
clip: that is the mutation proof in the plan's Verification section.

How the measures work. tests/cut_end_probe.js (its header defines every figure) draws each glyph with its `cut` ends and with every
`cut` end replaced by `butt`:
  reach     how far the cut moved an edge's end corner. 0 means the cut did not move it.
  beyondSpan  how many samples farther along the uncut edge than max(reach, at) differ between the two drawings, up to the middle of
            the stroke. `at` is the corner's place along the uncut edge. Reach is a straight-line distance, and on a curved edge a
            corner that moved by `reach` sits farther along the edge, so the samples between the two are the cut's own, not beyond it.
            (The earlier measure, `beyond`, counted from the first sample outside the straight-line reach and read those as beyond.)
The second test compares the whole generator with the previous release's, glyph by glyph.

FONT_DESIGN_CUT_SCRIPTS names another copy of the whole scripts/ folder (see tests/test_cut_ends.py); unset, the real one.
"""
import subprocess

import test_cut_ends as ce  # the probe runner, the Cane concept and the shipped concepts, shared with the spike tests

# the last commit that changed scripts/gen.js before 0.11.0
GEN_0_10_0 = "d9974f3"
SCOPE_MULTS = [1, 1.65]
MOVED_FLOOR = 235  # measured 262 Cane glyph draws with a moved cut end on 2026-11-25; floor(0.9 * 262)
SPACED_FLOOR = 161  # measured 179 of those with an advance different from 0.10.0's on 2026-11-25; floor(0.9 * 179)


def test_a_cut_moves_no_sample_beyond_its_own_reach():
    """Across functions: the `cut` and the `butt` drawing of one stroke, through params(), strokePolys() and cutEnds(). The Cane
    concept and the six shipped concepts with a cut end, roman and italic, four multipliers: no edge differs between the two drawings
    at any sample farther along the uncut edge than the corner's place along it, or its reach if that is larger (1e-6 units),
    including the edges of ends the cut did not move."""
    rows = ce.cane_rows() + ce.shipped_rows()
    assert len(rows) >= 11000, f"only {len(rows)} edge rows were measured"
    still = [r for r in rows if r["reach"] <= 1e-6]
    assert len(still) >= 1500, f"only {len(still)} edges have a cut that did not move the corner, so ends the cut leaves alone are not measured"
    over = [r for r in rows if r["beyondSpan"] > 0]
    assert not over, (f"CUT-REACH: {len(over)} of {len(rows)} cut-end edges differ from the uncut stroke beyond the cut's reach along the edge, "
                      f"{len([r for r in over if r['reach'] <= 1e-6])} of them on an end the cut did not move; worst {ce.worst(over, 'beyondSpanMax')}")


def _old_generator(tmp_path):
    r = subprocess.run(["git", "show", f"{GEN_0_10_0}:scripts/gen.js"], cwd=ce.REPO, capture_output=True, text=True)
    assert r.returncode == 0, f"git show {GEN_0_10_0}:scripts/gen.js exited {r.returncode} (this test needs a git checkout with that commit):\n{r.stderr[-1000:]}"
    old = tmp_path / "old" / "gen.js"
    old.parent.mkdir()
    old.write_text(r.stdout, encoding="utf-8")
    return old


def test_only_glyphs_with_a_moved_cut_end_changed_since_0_10_0(tmp_path):
    """The whole generator against the previous release (scripts/gen.js at d9974f3): every concept of the five shipped concept files
    and the Cane concept, roman and italic, mult 1 and 1.65, every key of G. A glyph whose polygons, advance or spacing profiles
    differ from 0.10.0's has an edge whose `cut` moved the corner. This also holds the three other callers of the clip (a corner, a
    joint and a T-join) to what they drew before, but only in glyphs with no moved cut end: in a glyph that has one, a change by
    another caller is not told apart from the cut's own change."""
    old = _old_generator(tmp_path)
    pairs = ce._parallel([ce.spec_json(files=[str(f)], all=True) for f in ce.CONCEPT_FILES], "cutconcepts")
    by_label = {f"{f.parent.name}/{f.name}": f for f in ce.CONCEPT_FILES}
    specs = [ce.spec_json(files=[str(by_label[r["file"]])], only=r["concept"], mults=SCOPE_MULTS, styles=ce.STYLES, old=str(old)) for r in pairs]
    specs.append(ce.spec_json(inline=[ce.CANE], only="cane", mults=SCOPE_MULTS, styles=ce.STYLES, old=str(old)))
    rows = ce._parallel(specs, "glyphs")
    runs = {}
    for r in rows:
        runs.setdefault((r["file"], r["concept"], r["style"]), []).append(r)
    assert len(runs) >= 60, f"only {len(runs)} concept and style runs were drawn"
    assert len(rows) >= 15000, f"only {len(rows)} glyph draws were compared"
    unchanged = [k for k, rs in runs.items() if all(x["same"] for x in rs)]
    assert len(unchanged) >= 50, f"only {len(unchanged)} of {len(runs)} runs drew every glyph exactly as 0.10.0 did"
    bad = [r for r in rows if not r["same"] and not r["movedCut"]]
    names = "; ".join(f"{r['file']} {r['concept']} {r['style']} mult {r['mult']} key {r['key']}" for r in bad[:10])
    assert not bad, f"CUT-SCOPE: {len(bad)} of {len(rows)} glyph draws changed since {GEN_0_10_0} with no cut corner moved: {names}"


def test_a_moved_cut_end_moves_the_spacing_with_its_outline(tmp_path):
    """Spacing follows the clipped outline (0.11.0): a `cut` end carries no `prof`, so glyph() reads its spacing profile from the
    clipped body, and the spike points that 0.10.0 counted as ink no longer set the advance. The Cane concept, roman and italic, mult 1
    and 1.65, against scripts/gen.js at d9974f3. Passes when written; proof by mutation (references/testing.md section 12, W6): a
    generator that clips the outline but keeps the spiked body for the profile draws every advance as 0.10.0 did.
    What it holds is narrower than its name: enough advances move. It does not compare an advance or a kern with the one the clipped
    outline should give, so a profile read from some other wrong body that also moves the advances would pass."""
    old = _old_generator(tmp_path)
    rows = ce._probe("glyphs", ce.spec_json(inline=[ce.CANE], only="cane", mults=SCOPE_MULTS, styles=ce.STYLES, old=str(old)))
    moved = [r for r in rows if r["movedCut"]]
    assert len(moved) >= MOVED_FLOOR, f"only {len(moved)} of {len(rows)} Cane glyph draws have a cut that moved a corner"
    spaced = [r for r in moved if abs(r["adv"] - r["oldAdv"]) > 1e-6]
    assert len(spaced) >= SPACED_FLOOR, (f"CUT-SPACING: only {len(spaced)} of {len(moved)} Cane glyph draws with a moved cut end have an "
                                         f"advance different from {GEN_0_10_0}'s; the spacing profile still reads the unclipped body")
