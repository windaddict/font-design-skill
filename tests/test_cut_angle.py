"""A `cut` end keeps its cut angle unless the clamp holds a corner (0.13.0).

WHAT IT'S FOR: when the corner a cut shortens stops short of the cut line, the other corner can run out to the old line (the cut edge
tilts) or to the parallel line through the shortened corner (the cut keeps its angle). The plan chose the second: the terminal stays full
and the cut stays level. This test holds that choice. It passes on 0.12.0, where both corners sit on one line unless the clamp holds one,
and proves itself by mutation: a generator that cuts the two corners of an end along two different lines fails it at CUT-ANGLE:.

The rows of tests/test_cut_step.py `all_rows()` are grouped into ends by (set, file, concept, style, mult, key, stroke, end); ends with a
`stacked` row are left out (the fold pin moved the end). An end is FREE when one of its rows has `reach` over 1e-6 and none of its rows
has `back` false with `reach` over `width` less 0.05 (the corner that runs out was not held by the clamp of one stroke width). `tilt`
is the angle in degrees between the cut L-to-R corner segment and the cut direction (tests/cut_end_probe.js).
"""
import test_cut_step as cs

TOL = cs.TOL


def test_a_cut_end_keeps_its_cut_angle_unless_the_clamp_holds_a_corner():
    """Across functions: both corners of one end, through the corner placement, `cutSide` and the clamp. No free end has its cut edge more
    than 0.5 degrees off the cut angle. Fails at CUT-ANGLE: under the mutation (5,932 of 5,964 free ends, worst 41.8 degrees)."""
    ends = {}
    for r in cs.all_rows():
        ends.setdefault((r["set"], r["file"], r["concept"], r["style"], r["mult"], r["key"], r["stroke"], r["end"]), []).append(r)
    free = []
    for rows in ends.values():
        if any(r["stacked"] for r in rows):
            continue
        if not any(r["reach"] > 1e-6 for r in rows):
            continue
        if any(not r["back"] and r["reach"] > r["width"] - TOL for r in rows):
            continue
        free.append(dict(rows[0]))
    assert len(free) >= 5000, f"only {len(free)} cut ends are free of the clamp"
    tilted = [r for r in free if r["tilt"] > 0.5]
    assert not tilted, (f"CUT-ANGLE: {len(tilted)} of {len(free)} cut ends have their cut edge more than 0.5 degrees off the cut angle; "
                        f"worst {cs.ce.worst(tilted, 'tilt')}")
