"""Measures how close two neighbouring glyphs of a built variable font come (tests/test_tiki_terminal.py, and the list of pairs to suppress).

WHAT IT'S FOR: the generator spaces a pair from a profile of polygon points, so a square stroke end can be seen at the wrong height and
the automatic kern can pull two letters together until their outlines touch (the Tiki Terminal README, "Spacing"). A test that holds a
face to a minimum gap needs the gap itself, and the person who builds the face needs the list of pairs whose automatic kern to
suppress with a zero hand pair. This module gives both: `scan` measures, the command line prints the list.

Exact guarantee: the contour distance between the outlines HarfBuzz would place, at the five named LOCATIONS. It is not a rendering,
it does not see a glyph lying wholly inside another's counter without crossing it (containment), and it says nothing about axis
settings between the five locations (interior locations).

How it measures. The woff2 is read with fontTools and instanced at the location with `fontTools.varLib.instancer`; every glyph's
contours are read from `glyf` as straight segments (every point must be on-curve, which holds for this builder's polygons). The text a
+ b is shaped with uharfbuzz on the variable font at the same location with `kern` and `liga` on. A pair is measured only when a + b
shapes to the glyph of a alone followed by the glyph of b alone (otherwise a ligature formed across the pair and it is skipped). The
gap is the smallest distance between a segment of a and a segment of b, with b moved right by a's shaped advance (plus b's own x
offset); 0 when two segments cross.

    .venv/bin/python3 tests/pair_gap.py --font examples/tiki-terminal/font.json --under 16
"""
import argparse
import io
import json
import math
import pathlib
import re
import sys

LOCATIONS = {
    "Regular": {"wght": 400, "LEAN": 0},
    "Bold": {"wght": 700, "LEAN": 0},
    "Lean": {"wght": 400, "LEAN": 100},
    "Bold Lean": {"wght": 700, "LEAN": 100},
    "middle": {"wght": 550, "LEAN": 50},
}
LIGATURES = ("fi", "fl", "ff")


def hand_key(unit):
    """The generator's key for a unit: a character, or a ligature's letters. U+2019 and U+0027 both give an ASCII apostrophe."""
    if unit in ("’", "'"):
        return "'"
    return unit


def woff2_path(font_json, group="roman"):
    """Where build.py writes the group's woff2 for this font.json: out_dir/<Family without spaces>-VF.woff2, unless the group names a file."""
    fj = pathlib.Path(font_json).resolve()
    cfg = json.loads(fj.read_text(encoding="utf-8"))
    g = cfg["groups"][group]
    out = fj.parent / cfg.get("out_dir", "out")
    if g.get("file"):
        return out / g["file"]
    token = re.sub(r"\s+", "", cfg["family"])
    return out / (f"{token}-Italic-VF.woff2" if g.get("italic") else f"{token}-VF.woff2")


def kern_set_filter(close, pattern):
    """Keeps the pairs whose two keys each match the font.json `kerning.set` pattern or are a ligature key. The one function the command
    line and the tests both use, so they agree on which pairs a zero hand pair can name."""
    rx = re.compile(pattern)
    ok = lambda k: k in LIGATURES or rx.fullmatch(k) is not None  # noqa: E731
    out = {}
    for pair, gap in close.items():
        a, b = pair.split("|", 1)
        if ok(a) and ok(b):
            out[pair] = gap
    return out


def _segments(font, glyph_name):
    """The glyph's outline as a list of ((x0, y0), (x1, y1)) segments, or [] for a glyph with no contours."""
    glyf = font["glyf"]
    g = glyf[glyph_name]
    if g.numberOfContours == 0:
        return []
    coords, ends, flags = g.getCoordinates(glyf)
    if not all(f & 1 for f in flags):
        raise ValueError(f"glyph {glyph_name} has an off-curve point; pair_gap reads straight segments only")
    segs = []
    start = 0
    for end in ends:
        pts = [tuple(coords[i]) for i in range(start, end + 1)]
        for i, p in enumerate(pts):
            segs.append((p, pts[(i + 1) % len(pts)]))
        start = end + 1
    return segs


def _point_seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / n))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _crosses(s, t):
    p1, p2 = s
    p3, p4 = t
    d1, d2 = _cross(p3, p4, p1), _cross(p3, p4, p2)
    d3, d4 = _cross(p1, p2, p3), _cross(p1, p2, p4)
    return ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4))


def _seg_dist(s, t):
    if _crosses(s, t):
        return 0.0
    return min(_point_seg(s[0], *t), _point_seg(s[1], *t), _point_seg(t[0], *s), _point_seg(t[1], *s))


def scan(woff2_path_, location, limit):
    """Returns {"measured": n, "close": {"a|b": gap}}: n pairs measured at the location, and every one whose gap is under `limit` units
    (rounded to 0.1). Pairs are every two units (a mapped character with contours, or fi, fl, ff) in either order."""
    import uharfbuzz as hb
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    path = pathlib.Path(woff2_path_)
    vf = TTFont(path)
    cmap = vf.getBestCmap()
    inst = instancer.instantiateVariableFont(TTFont(path), dict(location))
    buf = io.BytesIO()
    plain = TTFont(path)
    plain.flavor = None
    plain.save(buf)
    hbfont = hb.Font(hb.Face(buf.getvalue()))
    hbfont.set_variations(dict(location))
    order = inst.getGlyphOrder()

    def shape(text):
        b = hb.Buffer()
        b.add_str(text)
        b.guess_segment_properties()
        hb.shape(hbfont, b, {"kern": True, "liga": True})
        return [(order[i.codepoint], p.x_advance, p.x_offset) for i, p in zip(b.glyph_infos, b.glyph_positions)]

    units = {}  # text -> (glyph name, segments, xmin, xmax)
    candidates = [chr(cp) for cp in sorted(cmap)] + list(LIGATURES)
    for text in candidates:
        shaped = shape(text)
        if len(shaped) != 1:
            continue
        name = shaped[0][0]
        segs = _segments(inst, name)
        if not segs:
            continue
        xs = [p[0] for s in segs for p in s]
        units[text] = (name, segs, min(xs), max(xs))

    measured = 0
    close = {}
    for ta, (na, sa, _, amax) in units.items():
        for tb, (nb, sb, bmin, _) in units.items():
            shaped = shape(ta + tb)
            if [s[0] for s in shaped] != [na, nb]:
                continue
            measured += 1
            shift = shaped[0][1] + shaped[1][2]
            if bmin + shift - amax >= limit:
                continue
            sbs = [((p[0] + shift, p[1]), (q[0] + shift, q[1])) for p, q in sb]
            lo = bmin + shift - limit
            hi = amax + limit
            near_a = [s for s in sa if max(s[0][0], s[1][0]) >= lo]
            near_b = [s for s in sbs if min(s[0][0], s[1][0]) <= hi]
            best = None
            for s in near_a:
                for t in near_b:
                    d = _seg_dist(s, t)
                    if best is None or d < best:
                        best = d
                        if d == 0.0:
                            break
                if best == 0.0:
                    break
            if best is not None and best < limit:
                key = hand_key(ta) + "|" + hand_key(tb)
                gap = round(best, 1)
                if key not in close or gap < close[key]:
                    close[key] = gap
    return {"measured": measured, "close": close}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--font", required=True, help="font.json of the face (names the group's woff2 and the kern set)")
    ap.add_argument("--woff2", help="another woff2 to measure (a build with other hand kerns); --font still gives the kern set")
    ap.add_argument("--group", default="roman")
    ap.add_argument("--under", type=float, default=16, help="list pairs closer than this many units at any location")
    a = ap.parse_args(argv)
    cfg = json.loads(pathlib.Path(a.font).read_text(encoding="utf-8"))
    woff2 = pathlib.Path(a.woff2) if a.woff2 else woff2_path(a.font, a.group)
    union = {}
    counts = []
    for name, loc in LOCATIONS.items():
        r = scan(woff2, loc, a.under)
        counts.append(f"{name}: {r['measured']} measured, {len(r['close'])} under {a.under:g}")
        for k, v in r["close"].items():
            union[k] = min(v, union.get(k, v))
    out = {k: 0 for k in sorted(kern_set_filter(union, cfg["kerning"]["set"]))}
    print(json.dumps(out, ensure_ascii=False))
    print("; ".join(counts) + f"; {len(out)} pairs in the kern set", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
