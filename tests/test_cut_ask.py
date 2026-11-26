"""A shortened `cut` corner sits where the cut asks and on its cut line (0.13.0).

WHAT IT'S FOR: tests/test_cut_step.py holds the shortened corner to the stroke's edge. A corner can be on the edge and still be wrong:
too far back along it (the cut took more than it asked) or short of the cut line. These two tests bound where the corner may sit. Both
pin behaviour 0.12.0 already has (its corner sits exactly where the straight cut asks), so they pass when written and prove themselves
by mutation: a generator that moves a corner that moved back half as far again fails both (references/testing.md section 14).

How the measures work (tests/cut_end_probe.js defines every figure). `ask`: how far a straight stroke of the end's width and direction is
shortened on one edge by the cut. `at`: how far along the uncut edge the corner sits. `pastLine`: the corner's signed distance past
the cut line through the middle of the uncut end. `stacked` ends (the fold pin moved the end sample, so the end's direction cannot be
read from its corners) are left out. `exhausted` ends (an edge too short for its cut, finding F001) are left out of the second test
only: their corner stops on the last sample of the near half, possibly short of the line by design.

ASK_TOL is 0.5 units along the edge. On 0.12.0 seven rows exceed `ask` by up to 0.10, so 0.05 is too tight; a wrong walk misses by tens.
"""
import test_cut_step as cs

TOL = cs.TOL
ASK_TOL = 0.5


def test_a_cut_corner_on_the_edge_sits_no_farther_back_than_the_cut_asks():
    """Across functions: the `cut` and the `butt` drawing of one stroke. Among edges whose corner the cut moved back and that lie on the
    edge, none has the corner farther along the edge than the straight cut asks (within 0.5 units). A walk that goes too far fails at
    CUT-ASK: (mutation: 1,020 of 1,064 edges, worst 74.53 over `ask`)."""
    rows = [r for r in cs.all_rows() if r["back"] and not r["stacked"] and r["off"] <= TOL]
    assert len(rows) >= 900, f"only {len(rows)} edges are moved back, not stacked and on the edge"
    over = [dict(r, over=r["at"] - r["ask"]) for r in rows if r["at"] > r["ask"] + ASK_TOL]
    assert not over, (f"CUT-ASK: {len(over)} of {len(rows)} corners sit more than {ASK_TOL} farther back along the edge than the cut asks; "
                      f"worst {cs.ce.worst(over, 'over')}")


def test_no_cut_corner_stops_short_of_its_cut_line():
    """Across functions: the same drawings. Among edges whose corner the cut moved back, not stacked and not exhausted, none has the
    corner short of the cut line by more than 0.05 units: on the stroke's side of the line, so the cut took more than the line asks. A
    corner moved too far back fails at CUT-SHORT: (mutation: 6,014 of 6,183 edges, worst 48.71 short of the line). What this test does NOT
    see (build review F004): a walk that stops early, before the edge crosses the line, leaves the corner on the outward side (positive
    pastLine), and passes. The design allows that case when the edge does not cross the line within the reach (the cut line then moves
    to the corner), and the probe has no independent measure of where the uncut edge crosses the line, so no test tells the two apart."""
    rows = [r for r in cs.all_rows() if r["back"] and not r["stacked"] and not r["exhausted"]]
    assert len(rows) >= 5500, f"only {len(rows)} edges are moved back, not stacked and not exhausted"
    short = [dict(r, shortBy=-r["pastLine"]) for r in rows if r["pastLine"] < -TOL]
    assert not short, f"CUT-SHORT: {len(short)} of {len(rows)} corners stop more than {TOL} short of their cut line; worst {cs.ce.worst(short, 'shortBy')}"
