"""What 0.10.0 changes in a built face, as data, so every test that says "nothing else moved" reads one list.

WHAT IT'S FOR: 0.10.0 redraws a few glyphs on purpose (brackets on the stroke's own edge, the corner cut along its
partner, the G and the italic r's arm; docs/plan-serif-joint-jags.md section 1) and moves the advances and kerns of two of
them. A test that compares this tree with an older release (tests/test_serif_joints.py against 0.9.0, tests/test_r_leg_join.py
against 0.4.0, tests/test_weight_decisions.py against 0.5.0) would otherwise fail on those declared changes, or, if it simply
skipped whole glyphs, stop seeing a change to any other glyph. These sets name the declared changes, so each comparison drops
exactly them and keeps every other glyph.

The keys are generator keys (the keys of G), not characters: `fl` is the ligature. Each set holds for every master of its group
(measured through export.js and build.py on the three examples, plan section 1).
"""

GEN_0_9_0 = "dae7a54"  # the last commit that changed scripts/gen.js before 0.10.0: `git show dae7a54:scripts/gen.js` is the 0.9.0 generator

_ROMAN = frozenset(["2", "4", "5", "7", "G", "M", "Z", "e", "z", "è", "é", "ê", "ë"])
_ITALIC = frozenset(["2", "4", "5", "7", "E", "F", "G", "L", "W", "Z", "[", "]", "fl", "r", "z", "È", "É", "Ê", "Ë"])

# glyphs whose outlines (polys, raw, runs, keptIdx, minw) change, per (example, group)
OUTLINES = {
    ("neutral", "roman"): _ROMAN,
    ("bract", "roman"): _ROMAN,
    ("driftwood", "roman"): _ROMAN,
    ("neutral", "italic"): _ITALIC,
    ("driftwood", "italic"): _ITALIC | {"w"},
}

# glyphs whose advance changes, and glyphs whose branch record changes, per kind of group
ADVANCES = {"roman": frozenset(["G"]), "italic": frozenset(["G", "r"])}
RECORDS = {"roman": frozenset(["G"]), "italic": frozenset(["G", "r"])}


def kern_pair_allowed(group_is_italic, a, b):
    """May the kern of the pair (a, b) differ from 0.9.0's? Roman: only a pair with G on the left (the G's lower right corner
    held its old value up). Italic: any pair that has a G or an r in it."""
    if group_is_italic:
        return a in ("G", "r") or b in ("G", "r")
    return a == "G"
