"""Guards a display face built with the font-design skill: the variable woff2 per group, its statics,
its manifest and its build.

WHAT IT'S FOR: this is the test-suite TEMPLATE a project copies beside its font.json. Each guard covers
one way the font could break while every page still looks plausible, because a fallback face sits
behind the custom one in every stack: a character the font lacks renders in the fallback; an axis range
the CSS no longer reaches falls back; the Medium that `font-weight: 500` selects maps to another weight;
a kern table stops varying; a glyph varLib silently skipped ships frozen; a hairline thinner than the
reviewed design; a build that cannot be reproduced. Every expected VALUE comes from requirements.json
(review finding F002), never from font.json or the manifest, so a config edit cannot make the suite
agree with itself. Where a value is recomputed, it is recomputed WITHOUT importing build.py: the font
is read with fontTools and the generator's own numbers come from running export.js afresh (node).

Every test below names the incident it guards and was watched failing under the mutation of that name
in scripts/tests/mutate.py (references/testing.md explains how to run it and what survived).

Copyright 2026 John Knox. MIT licence. Generalised from the author's Bract suite (hopsafari.com).
"""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys

from conftest import SCRIPTS, group_woff2
from fontTools.misc.roundTools import otRound
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FS_ITALIC, FS_REGULAR, FS_USE_TYPO, MAC_ITALIC = 0x01, 0x40, 0x80, 0x02
OVERLAP_SIMPLE = 0x40

# Glyph names as build.py assigns them, restated here (not imported) so a renamed glyph shows up.
GNAME = {" ": "space", ".": "period", ",": "comma", "'": "quoteright", "#": "numbersign", "+": "plus", "&": "ampersand",
         ":": "colon", "?": "question", "!": "exclam", "-": "hyphen", "fi": "f_i", "fl": "f_l", "ff": "f_f",
         "/": "slash", "%": "percent", "$": "dollar", ";": "semicolon", "…": "ellipsis", "–": "endash", "—": "emdash",
         "(": "parenleft", ")": "parenright", "[": "bracketleft", "]": "bracketright", "*": "asterisk",
         "©": "copyright", "•": "bullet", "™": "trademark", "š": "scaron", "ā": "amacron", "é": "eacute"}
GNAME.update({str(i): n for i, n in enumerate("zero one two three four five six seven eight nine".split())})


def gname(k):
    if k in GNAME:
        return GNAME[k]
    return "uni%04X" % ord(k) if len(k) == 1 and ord(k) > 127 else k


def outline(glyphset, name):
    pen = RecordingPen()
    glyphset[name].draw(pen)
    return pen.value


def coords(static, name):
    glyf = static["glyf"]
    return [(otRound(x), otRound(y)) for x, y in glyf[name].getCoordinates(glyf)[0]]


def names_of(font):
    return {n.nameID: n.toUnicode() for n in font["name"].names if n.platformID == 3}


def pair_kerns(static):
    """{(first, second): x-advance} from every PairPos subtable of a static font."""
    out = {}
    for lookup in static["GPOS"].table.LookupList.Lookup:
        for st in lookup.SubTable:
            if lookup.LookupType == 9:
                st = st.ExtSubTable
            if st.Format == 1:
                for first, ps in zip(st.Coverage.glyphs, st.PairSet):
                    for rec in ps.PairValueRecord:
                        out[(first, rec.SecondGlyph)] = getattr(rec.Value1, "XAdvance", 0)
            elif st.Format == 2:
                c1, c2 = st.ClassDef1.classDefs, st.ClassDef2.classDefs
                for first in st.Coverage.glyphs:
                    for second in static.getGlyphOrder():
                        v = st.Class1Record[c1.get(first, 0)].Class2Record[c2.get(second, 0)].Value1
                        if v is not None and getattr(v, "XAdvance", 0):
                            out[(first, second)] = v.XAdvance
    return out


def lay(title, static, kerns):
    """Advance width of a title set in `static`: glyph advances, pair kerns, ff/fi/fl ligatures. Curly
    apostrophes and NBSP are laid as the apostrophe and the space, as export.js lays them."""
    seq, w = [], title.replace("’", "'").replace("‘", "'").replace(" ", " ")
    i = 0
    while i < len(w):
        if w[i:i + 2] in ("ff", "fi", "fl"):
            seq.append(w[i:i + 2])
            i += 2
        else:
            seq.append(w[i])
            i += 1
    hmtx, x, prev = static["hmtx"].metrics, 0, None
    for k in seq:
        g = gname(k)
        if prev is not None:
            x += kerns.get((prev, g), 0)
        x += hmtx[g][0]
        prev = g
    return x


def kern_key(pair_id):
    """"L|V" -> ("L", "V") as glyph names; " |A" is the word space before A."""
    a, b = pair_id.split("|")
    return (gname(a), gname(b))


# --- the cmap and its two decisions ---------------------------------------------------------------------
def test_the_cmap_is_exactly_the_required_set(group, font, req):
    """Review finding F007 (Bract): the quote glyphs are made in the builder and escape every generator
    test unless the cmap is pinned to a declared set. A build that maps something new, or drops a
    character a title uses, fails here with the difference."""
    have = {chr(cp) for cp in font.getBestCmap()}
    want = set(req["cmap"])
    assert have == want, f"{group}: extra: {sorted(have - want)}, missing: {sorted(want - have)}"


def test_every_required_character_is_mapped(group, font, req):
    """The characters the site's titles were mined for (requirements.required_characters) must all be
    in the cmap, or that one character renders in the fallback face while the rest of the title does not."""
    cmap = font.getBestCmap()
    missing = sorted({c for c in req.get("required_characters", "") if ord(c) not in cmap})
    assert not missing, f"{group} lacks {missing}"


def test_nbsp_is_the_space_glyph(group, font, req):
    """Bract: 83 of 93 titles carried a U+00A0; an unmapped NBSP renders as a fallback space of a
    different width. When the requirements include NBSP it must draw the space glyph itself."""
    cmap = font.getBestCmap()
    if " " in req["cmap"]:
        assert cmap.get(0xA0) == cmap[0x20] == "space", f"{group}: NBSP maps to {cmap.get(0xA0)}"
    else:
        assert 0xA0 not in cmap, f"{group}: NBSP is mapped although the requirements leave it out"


def test_ascii_apostrophe_draws_the_right_mark(group, font, req):
    """Sites type every apostrophe as ASCII ' and static builders do not smarten quotes, so U+0027 must
    draw the curly apostrophe (the straight tick stays in the font, unmapped) unless the requirements
    say ascii_apostrophe_curly: false, in which case it draws the tick and U+2019 the curly mark. Either
    way the two glyphs must differ: a tick that IS the apostrophe passed the mapping check in Bract."""
    cmap, gs = font.getBestCmap(), font.getGlyphSet()
    assert "quotesingle" in gs, f"{group}: the straight tick must exist"
    if req.get("ascii_apostrophe_curly", True):
        assert cmap[0x27] == cmap[0x2019] == "quoteright", f"{group}: U+0027 draws {cmap[0x27]}"
        assert "quotesingle" not in cmap.values(), f"{group}: the straight tick must stay unmapped"
    else:
        assert cmap[0x27] == "quotesingle" and cmap[0x2019] == "quoteright", f"{group}: U+0027 draws {cmap[0x27]}, U+2019 {cmap[0x2019]}"
    assert outline(gs, "quoteright") != outline(gs, "quotesingle"), f"{group}: the curly apostrophe and the straight tick are the same outline"


# --- axes, variation, kerning ---------------------------------------------------------------------------
def test_the_axes_and_instances_are_what_the_css_relies_on(group, font, req):
    """A CSS font-weight or font-optical-sizing value outside the axes falls back; a renamed instance
    breaks font pickers. fvar must equal the requirements exactly, axis order included (review F003:
    a one-axis group is as valid as a two-axis one, and the order is what the config said)."""
    R = req["groups"][group]
    axes = [(a.axisTag, (a.minValue, a.defaultValue, a.maxValue)) for a in font["fvar"].axes]
    assert axes == [(t, tuple(float(v) for v in R["axes"][t])) for t in R["axes"]], f"{group}: fvar axes {axes}"
    inst = {font["name"].getDebugName(i.subfamilyNameID): i.coordinates for i in font["fvar"].instances}
    assert inst == {n: {t: float(v) for t, v in loc.items()} for n, loc in R["instances"].items()}, f"{group}: fvar instances {inst}"


def test_every_glyph_with_contours_varies(group, font):
    """varLib logs 'incompatible masters; skipping' and ships the glyph frozen at the default (trap 1).
    The .notdef box is the same in every master on purpose and is the one exemption."""
    gvar = font["gvar"].variations
    frozen = [g for g in font.getGlyphOrder() if g != ".notdef" and font["glyf"][g].numberOfContours > 0 and not gvar.get(g)]
    assert not frozen, f"{group}: glyphs without variations: {frozen}"


def test_each_master_location_reproduces_its_exported_outlines(group, master, export, instance, req):
    """Review finding F013: a gvar entry does not prove every axis moves the glyph. Instancing at a
    master's location must give back that master's exported polygons within two units, for every glyph,
    and its advances exactly. The master set itself must be the reviewed one."""
    R = req["groups"][group]
    assert set(export["masters"]) == set(R["masters"]), f"{group}: export masters {sorted(export['masters'])} are not the reviewed {sorted(R['masters'])}"
    static = instance(group, R["masters"][master])
    for k, g in export["masters"][master]["glyphs"].items():
        name = gname(k)
        got = coords(static, name)
        expected = [tuple(pt) for poly in g["polys"] for pt in poly]
        assert len(got) == len(expected), f"{group} {master} {k}: {len(got)} points in the font, {len(expected)} exported"
        # the font rounds to whole units and varLib infers unchanged points (IUP, tolerance 0.5) in up to
        # three regions at a corner master, so two units is the honest bound; 0.16px at 80px
        worst = max(max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a, b in zip(got, expected))
        assert worst <= 2, f"{group} {master} {k}: instanced outline is {worst} units from the exported master"
        assert static["hmtx"][name][0] == g["adv"], f"{group} {master} {k}: advance {static['hmtx'][name][0]} vs exported {g['adv']}"


def expected_quote_glyphs(ap_polys, ap_adv, italic_angle=0.0):
    """The six quote glyphs as the builder derives them from the apostrophe, re-derived here from the
    exported apostrophe outline and the rule in references/variable-font-build.md: the straight tick is
    a 13-point half-round over a two-point base, width 0.64 of the apostrophe's plus 70 each side, slanted
    about y=610 by tan(angle) in an italic group; double marks sit 0.8 (ticks) or 1.45 (curly)
    apostrophe-widths apart and the advance grows by the same gap; opening quotes are the apostrophe
    turned 180 degrees about its box centre."""
    xs = [x for p in ap_polys for x, y in p]
    ys = [y for p in ap_polys for x, y in p]
    aw = max(xs) - min(xs)
    tick_adv = round(aw * 0.64 + 140)
    tc = tick_adv / 2
    slant = math.tan(math.radians(italic_angle)) if italic_angle else 0.0

    def tick(cx):
        pts = [(cx + aw * 0.32 * math.cos(math.pi * i / 12), 715 - aw * 0.32 + aw * 0.32 * math.sin(math.pi * i / 12)) for i in range(13)]
        pts += [(cx - aw * 0.13, 505), (cx + aw * 0.13, 505)]
        return [(x + slant * (y - 610), y) for x, y in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    turned = [[(2 * cx - x, 2 * cy - y) for x, y in p] for p in ap_polys]
    gap = aw * 1.45
    shift = lambda polys, d: [[(x + d, y) for x, y in p] for p in polys]
    curly = [[tuple(q) for q in p] for p in ap_polys]
    return {
        "quoteright": (ap_adv, curly),
        "quoteleft": (ap_adv, turned),
        "quotesingle": (tick_adv, [tick(tc)]),
        "quotedbl": (round(tick_adv + aw * 0.8), [tick(tc), tick(tc + aw * 0.8)]),
        "quotedblright": (round(ap_adv + gap), curly + shift(curly, gap)),
        "quotedblleft": (round(ap_adv + gap), turned + shift(turned, gap)),
    }


def test_quote_glyphs_follow_the_apostrophe_in_every_master(group, master, export, instance, req):
    """Review finding F004 (Bract diff review): the quote glyphs are made in build.py, not by the
    generator, so F013 above never sees them. Each must have the advance and outline the apostrophe
    implies, at every master. Driftwood's build gave quotedblleft the straight quotes' advance while
    drawing its second mark 1.45 apostrophe-widths out, so the mark overhung the next letter (#23)."""
    R = req["groups"][group]
    static = instance(group, R["masters"][master])
    ap = export["masters"][master]["glyphs"]["'"]
    for name, (adv, polys) in expected_quote_glyphs(ap["polys"], ap["adv"], R.get("italic_angle", 0)).items():
        assert static["hmtx"][name][0] == adv, f"{group} {master} {name}: advance {static['hmtx'][name][0]}, expected {adv}"
        got = coords(static, name)
        expected = [pt for poly in polys for pt in poly]
        assert len(got) == len(expected), f"{group} {master} {name}: {len(got)} points, expected {len(expected)}"
        worst = max(max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a, b in zip(got, expected))
        assert worst <= 2, f"{group} {master} {name}: outline is {worst} units from the apostrophe-derived shape"


def test_avar_maps_the_reviewed_intermediate_weights(group, font, req):
    """font-weight: 500 must render the Medium the concept pages reviewed, which is not the linear
    midpoint: requirements.avar lists, per axis, the (normalised input, output) pairs the avar table
    must carry, and an axis without an entry must map straight (no intermediate point)."""
    R = req["groups"][group]
    seg = font["avar"].segments if "avar" in font else {}
    for tag in R["axes"]:
        want = [tuple(p) for p in R.get("avar", {}).get(tag, [])]
        s = seg.get(tag, {})
        mids = sorted((i, o) for i, o in s.items() if i not in (-1.0, 0.0, 1.0))
        assert len(mids) == len(want), f"{group} {tag}: avar has {mids}, the requirements want {want}"
        for (i, o), (wi, wo) in zip(mids, sorted(want)):
            assert abs(i - wi) <= 0.01 and abs(o - wo) <= 0.01, f"{group} {tag}: avar maps {i:.3f} -> {o:.3f}, expected {wi} -> {wo}"
        if s:
            assert s.get(-1.0) == -1.0 and s.get(0.0) == 0.0 and s.get(1.0) == 1.0, f"{group} {tag}: avar ends are not fixed"


def test_kerning_and_advances_at_every_master(group, master, export, instance, req, cfg):
    """Review findings F005 and F010 (Bract). At each master's location the pair values, the word space,
    every advance and whole-title widths equal what export.js emitted for that master, so a display
    cut's track reaches the font through the advances and the hand pairs reach every master. The hand
    pairs and titles are the reviewed ones in requirements.json; the exporter's figure for each title
    is the independent recomputation the font must reproduce."""
    R = req["groups"][group]
    static = instance(group, R["masters"][master])
    kerns = pair_kerns(static)
    # the top-level hand pairs hold in every group; a group's own hand_kerns add to or override them
    # (an italic's I-pairs differ from the roman's)
    for pair_id, v in {**req["hand_kerns"], **R.get("hand_kerns", {})}.items():
        pair = kern_key(pair_id)
        assert kerns.get(pair) == v, f"{group} {master}: hand pair {pair} is {kerns.get(pair)}, expected {v}"
    M = export["masters"][master]
    # the word space is PINNED per master in requirements.json (review finding C9): the exporter's own
    # figure is what the F005 mutation edits, so it cannot be the expectation for itself
    assert "word_space" in R and master in R["word_space"], f"{group}: requirements must pin word_space for master {master}"
    pinned = R["word_space"][master]
    assert static["hmtx"]["space"][0] == pinned, f"{group} {master}: word space {static['hmtx']['space'][0]} vs the reviewed {pinned}"
    assert M["space"] == pinned, f"{group} {master}: export.js lays the word space at {M['space']}, the reviewed value is {pinned}"
    wrong_adv = {k: (static["hmtx"][gname(k)][0], g["adv"]) for k, g in M["glyphs"].items() if static["hmtx"][gname(k)][0] != g["adv"]}
    assert not wrong_adv, f"{group} {master}: advances differ from the export, e.g. {list(wrong_adv.items())[:5]}"
    expected = {(gname(a), gname(b)): v for a, b, v in M["kerns"]}
    wrong = {p: (kerns.get(p), v) for p, v in expected.items() if kerns.get(p, 0) != v}
    assert not wrong, f"{group} {master}: {len(wrong)} pairs differ, e.g. {list(wrong.items())[:5]}"
    # a GPOS pair the exporter never emitted is as wrong as a missing one: the first version compared the
    # expected pairs' values only, so a pair added in the builder was invisible (re-review, code-a F005)
    extra = sorted(set(kerns) - set(expected))
    assert not extra, f"{group} {master}: {len(extra)} GPOS pairs the exporter never emitted, e.g. {extra[:5]}"
    # the automatic pass itself is unpinned (its values are the exporter's own, testing.md section 2), so at
    # least this much is held: pairs that are neither hand pairs nor word-space pairs exist and carry
    # non-zero values at this master, or a kern() that returned 0 for every pair would agree with itself
    # and the font would ship with the hand pairs alone (re-review, code-a F004). The hand pairs are
    # classified by font.json's own lists (the requirements pin a subset of them): a classification, not
    # an expected value, and a font.json that emptied its hand list would only move those pairs here.
    hand_ids = set(cfg["kerning"].get("hand", {})) | (set(cfg["kerning"].get("italic_hand", {})) if "italic_angle" in R else set())
    automatic = [v for a, b, v in M["kerns"] if f"{a}|{b}" not in hand_ids and a != " " and b != " "]
    assert automatic and any(automatic), f"{group} {master}: no automatic kern pair with a non-zero value; the exporter emitted {len(M['kerns'])} pairs, " \
                                         f"{len(automatic)} of them automatic"
    for title in req["titles"]:
        assert title in M["titles"], f"font.json titles must include the reviewed title {title!r} so export.js lays it"
        laid = lay(title, static, kerns)
        assert laid == M["titles"][title], f"{group} {master}: {title!r} lays at {laid}, exporter says {M['titles'][title]}"
    tighter = R.get("display_masters_tighter_than", {})
    if master in tighter:
        other = tighter[master]
        assert pinned < R["word_space"][other], \
            f"{group}: {master} word space {pinned} is not tighter than {other}'s {R['word_space'][other]} (requirements.word_space)"
        assert static["hmtx"]["space"][0] < instance(group, R["masters"][other])["hmtx"]["space"][0], \
            f"{group}: {master} word space {static['hmtx']['space'][0]} is not tighter than {other}'s in the font"


def test_kerning_and_advances_at_the_interpolated_location(group, export, instance, req):
    """Review finding F010: the weight the site uses most often may have no master. At
    requirements.interpolated_check every advance and pair value must be within a unit of the mix of
    the two named masters at t, or the avar/gvar/GPOS variation does not interpolate as reviewed."""
    R = req["groups"][group]
    assert "interpolated_check" in R, f"{group}: requirements must name an interpolated_check (location, between, t)"
    ic = R["interpolated_check"]
    static = instance(group, ic["location"])
    A, B = (export["masters"][m] for m in ic["between"])
    t = ic["t"]
    mix = lambda a, b: a + t * (b - a)
    off_adv = [(k, static["hmtx"][gname(k)][0], mix(A["glyphs"][k]["adv"], B["glyphs"][k]["adv"])) for k in A["glyphs"]
               if abs(static["hmtx"][gname(k)][0] - mix(A["glyphs"][k]["adv"], B["glyphs"][k]["adv"])) > 1]
    assert not off_adv, f"{group} at {ic['location']}: advances more than a unit from the interpolation, e.g. {off_adv[:5]}"
    kerns = pair_kerns(static)
    ak = {(gname(a), gname(b)): v for a, b, v in A["kerns"]}
    bk = {(gname(a), gname(b)): v for a, b, v in B["kerns"]}
    off = [(p, kerns.get(p, 0), mix(ak[p], bk[p])) for p in ak if abs(kerns.get(p, 0) - mix(ak[p], bk[p])) > 1]
    assert not off, f"{group} at {ic['location']}: {len(off)} pairs more than a unit from the interpolation, e.g. {off[:5]}"


# --- hairlines, folds, size, metrics --------------------------------------------------------------------
def test_hairlines_clear_the_floor(group, font, export, manifest, req):
    """Review finding F009: the floor is measured on the generator's interior stroke samples, not on
    its parameters, in every master, and the floors are the REVIEWED ones in requirements.json (F002):
    a font.json that lowers a floor and thins the design agrees with itself and still fails here. The
    gasp table asks Windows to antialias every size rather than drop a sub-pixel stroke."""
    R = req["groups"][group]
    m = manifest["groups"][group]
    for master, floor in R["hairline_floors"].items():
        assert m["min_stroke_width"][master] >= floor, f"{group} {master}: manifest says {m['min_stroke_width'][master]} < {floor}"
        got = export["masters"][master]["minStrokeWidth"]
        assert got >= floor, f"{group} {master}: generator measures {got} < {floor}"
        assert got == m["min_stroke_width"][master], f"{group} {master}: manifest and generator disagree"
        # the builder's own measurement from the polygons (review finding C7) must clear the floor too and
        # sit within the 0.15 units that rounding the exported coordinates to 0.1 can move it
        recomputed = m["min_stroke_width_recomputed"][master]
        assert recomputed >= floor, f"{group} {master}: the builder measured {recomputed} from the polygons, below the floor {floor}"
        assert abs(recomputed - got) <= 0.15, f"{group} {master}: builder's {recomputed} and generator's {got} stroke widths disagree by more than 0.15"
    assert "gasp" in font, f"{group}: no gasp table; Windows may drop sub-pixel strokes instead of antialiasing them"
    assert font["gasp"].gaspRange == {int(k): v for k, v in req["gasp"].items()}, f"{group}: gasp {font['gasp'].gaspRange}"


def test_no_stroke_edge_folds_back(group, master, export, req):
    """Bract round 2 (#22): where a bend is tighter than half the stroke width the inside offset edge
    folded into a loop that nonzero winding painted as a lump. This checks the OUTPUT as export.js
    measures it, on the undecimated edges and on the decimated edges that ship, against the reviewed
    thresholds in requirements.fold_units."""
    units = req["fold_units"]
    assert export["foldUnits"] == units, f"export.js measures with {export['foldUnits']}, the requirements say {units}"
    M = export["masters"][master]
    assert M["foldedEdges"] == 0, f"{group} {master}: {M['foldedEdges']} folded edge(s), worst {M['maxBackwardExcursion']} at {M['worstFoldAt']}"
    assert M["maxBackwardExcursion"]["raw"] <= units["raw"]
    assert M["maxBackwardExcursion"]["decimated"] <= units["decimated"]


FOLD_FIXTURE = r"""
const d = require(process.argv[1]);
// a straight stroke body: left edge y=0, right edge y=-10, five samples each, 10 units apart
const L = [[0, 0], [10, 0], [20, 0], [30, 0], [40, 0]], R = [[0, -10], [10, -10], [20, -10], [30, -10], [40, -10]];
const poly = L.concat(R.slice().reverse()), runs = [[0, 4], [5, 9]];
const kept = [0, 2, 4, 5, 7, 9], dec = kept.map(i => poly[i]);
const clean = d.backwardExcursion(poly, runs, dec, kept);
// (a) a fold in the FIRST segment of the left edge: the second sample sits 6 units behind the first
const foldFirst = poly.map(p => p.slice()); foldFirst[1] = [-6, 0];
const a = d.backwardExcursion(foldFirst, runs, kept.map(i => foldFirst[i]), kept);
// (b) a fold only in the decimated edge: the raw edge is clean, two kept points are out of order
const decSwapped = dec.map(p => p.slice()); [decSwapped[1], decSwapped[2]] = [decSwapped[2], decSwapped[1]];
const b = d.backwardExcursion(poly, runs, decSwapped, kept);
// (c) edge runs of unequal length must throw, never read as a clean 0
let c = "returned";
try { d.backwardExcursion(poly, [[0, 4], [5, 8]], dec, kept); } catch (e) { c = "threw: " + e.message; }
console.log(JSON.stringify({ clean, a, b, c, units: d.FOLD_UNITS_DEFAULT }));
"""


def test_the_fold_detector_sees_first_segment_decimated_and_unequal_folds(req):
    """Bract review R4: the fold test above trusts export.js's own verdict. This feeds the detector
    hand-built edges: a clean stroke must read 0 on both measures; a fold in the very first segment must
    be reported on the raw measure above its threshold (the first version of the loop started at the
    second segment and could not see it); a fold present only in the decimated edge must be reported on
    the decimated measure while the raw measure stays clean; and edge runs of unequal length must
    throw (a mutation returning 0 there survived until this case existed)."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", FOLD_FIXTURE, str(SCRIPTS / "export.js")], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    units = req["fold_units"]
    assert out["clean"] == {"raw": 0, "decimated": 0}, out
    assert out["a"]["raw"] > units["raw"], f"a fold in the first segment went unreported: {out['a']}"
    assert out["b"]["raw"] == 0 and out["b"]["decimated"] > units["decimated"], f"a decimated-only fold went unreported: {out['b']}"
    assert out["c"].startswith("threw"), f"unequal edge runs did not throw: {out['c']}"


def test_the_font_is_under_budget(group, cfg, req):
    """A size budget is a promise to the page weight; the requirements hold it, not font.json."""
    path = group_woff2(cfg, group)
    assert path.stat().st_size <= req["size_budget_bytes"], f"{group}: {path.stat().st_size} bytes; the budget is {req['size_budget_bytes']}"


def test_no_glyph_exceeds_the_win_metrics(group, master, instance, req):
    """Review finding F012 (Bract): usWinAscent/Descent are a clipping box on Windows; every glyph of
    every master must fit, accented capitals included (À reached 947 against a copied 940)."""
    static = instance(group, req["groups"][group]["masters"][master])
    os2, glyf = static["OS/2"], static["glyf"]
    for g in static.getGlyphOrder():
        if glyf[g].numberOfContours > 0:
            glyf[g].recalcBounds(glyf)
            assert glyf[g].yMax <= os2.usWinAscent and -glyf[g].yMin <= os2.usWinDescent, \
                f"{group} {master} {g}: y {glyf[g].yMin}..{glyf[g].yMax} outside win -{os2.usWinDescent}..{os2.usWinAscent}"


# The reviewed standard weight names a STAT axis value takes; restated here, not imported from build.py.
STAT_WEIGHT_NAMES = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}
STAT_ELIDABLE = 0x0002


def test_the_line_height_is_the_reviewed_one_on_every_platform(group, font, req):
    """FontBakery's os2_metrics_match_hhea FAIL: with hhea at the glyph extent (957/-255) and typo at 760/-240
    plus a 200 line gap, `line-height: normal` was 1.212 em on a Mac and 1.2 em where USE_TYPO_METRICS is read.
    hhea and OS/2 typo must carry the reviewed ascender and descender, both with a line gap of 0, and
    USE_TYPO_METRICS (held by test_style_metadata_matches_the_group) makes a platform that reads either one
    answer. The numbers are requirements.json's `vertical_metrics`, so a glyph change that moves the extent
    shows up as a reviewed line-height change rather than a silent one."""
    want = req["groups"][group]["vertical_metrics"]
    os2, hhea = font["OS/2"], font["hhea"]
    assert (hhea.ascent, hhea.descent, hhea.lineGap) == (want["ascender"], want["descender"], want["line_gap"]), \
        f"{group}: hhea {(hhea.ascent, hhea.descent, hhea.lineGap)} is not the reviewed {tuple(want.values())}"
    assert (os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap) == (want["ascender"], want["descender"], want["line_gap"]), \
        f"{group}: OS/2 typo {(os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap)} is not the reviewed {tuple(want.values())}"


def test_fs_type_is_the_operators_embedding_decision(group, font, req):
    """fontTools defaults OS/2.fsType to 4 (Preview & Print) and the face never said otherwise; the value is
    a licence decision, so it comes from font.json's names.fs_type (no default) and is held to the reviewed
    `names.fs_type` here. Browsers ignore it for web fonts; installers and some tools do not."""
    assert font["OS/2"].fsType == req["names"]["fs_type"], f"{group}: OS/2 fsType {font['OS/2'].fsType} is not the reviewed {req['names']['fs_type']}"


def test_stat_names_every_named_instance(group, font, req):
    """FontBakery's inconsistencies_between_fvar_STAT FAIL (and the ERROR it caused in another check): varLib
    wrote STAT axis records and no axis values, so a tool that composes instance names from STAT found none.
    Each axis must carry one format-1 value for every coordinate a named instance uses plus the axis default,
    a weight named by its standard name, the default marked elidable and no other, and the elided fallback name
    the style (Regular, or Italic for an italic group). Expected values come from the requirements' axes and
    instances, not from the font."""
    R = req["groups"][group]
    stat = font["STAT"].table
    assert stat.AxisValueCount > 0 and stat.AxisValueArray, f"{group}: STAT has no axis values"
    assert [a.AxisTag for a in stat.DesignAxisRecord.Axis] == list(R["axes"]), f"{group}: STAT axes {[a.AxisTag for a in stat.DesignAxisRecord.Axis]}"
    got = {}
    for v in stat.AxisValueArray.AxisValue:
        assert v.Format == 1, f"{group}: STAT axis value format {v.Format}"
        tag = stat.DesignAxisRecord.Axis[v.AxisIndex].AxisTag
        got.setdefault(tag, {})[v.Value] = (font["name"].getDebugName(v.ValueNameID), bool(v.Flags & STAT_ELIDABLE))
    for tag, (_lo, default, _hi) in R["axes"].items():
        values = {float(loc[tag]) for loc in R["instances"].values()} | {float(default)}
        want = {v: (STAT_WEIGHT_NAMES[int(v)] if tag == "wght" and int(v) in STAT_WEIGHT_NAMES and v == int(v) else f"{v:g}", v == float(default)) for v in values}
        assert got.get(tag) == want, f"{group}: STAT {tag} values {got.get(tag)} are not the requirements' {want}"
    style = "Italic" if "italic_angle" in R else "Regular"
    fallback = font["name"].getDebugName(stat.ElidedFallbackNameID)
    assert fallback == style, f"{group}: STAT elided fallback {fallback!r} is not {style!r}"


def test_the_smart_dropout_program_pairs_with_gasp(group, font, req):
    """FontBakery's smart_dropout FAIL: an unhinted TrueType font has no `prep`, so a renderer that grid-fits
    (Windows GDI, DirectWrite in some modes) may leave a hairline thinner than a pixel out of the bitmap. The
    standard 7-byte program (SCANCTRL, SCANTYPE) asks for dropout control; the requirements hold its bytes.
    The exact guarantee is the program's presence: that a renderer runs it is not testable from a Mac."""
    assert "prep" in font, f"{group}: no prep table; gasp alone does not ask for dropout control"
    assert bytes(font["prep"].program.getBytecode()).hex().upper() == req["tables"]["prep_hex"], \
        f"{group}: prep {bytes(font['prep'].program.getBytecode()).hex().upper()} is not the reviewed {req['tables']['prep_hex']}"
    assert font["maxp"].maxStackElements >= 1, f"{group}: maxp.maxStackElements {font['maxp'].maxStackElements} does not count the prep program's stack"


def test_the_code_page_and_name_platforms_are_the_reviewed_ones(group, font, req):
    """FontBakery's code_pages FAIL (ulCodePageRange1 was 0: no code page declared, so a Windows font
    picker may list the font as supporting none) and no_mac_entries FAIL (varLib and FontBuilder wrote
    Macintosh-platform name records nothing reads any more). Bit 0 is Latin 1."""
    t = req["tables"]
    assert font["OS/2"].ulCodePageRange1 == t["code_page_range1"], f"{group}: ulCodePageRange1 {font['OS/2'].ulCodePageRange1:#x} is not {t['code_page_range1']:#x}"
    mac = [r.nameID for r in font["name"].names if r.platformID == 1]
    assert bool(mac) == t["mac_names"], f"{group}: Macintosh name records for IDs {mac[:6]} but the requirements say mac_names {t['mac_names']}"


def test_glyphs_declare_their_overlaps(group, font):
    """Every contoured glyph is built from overlapping strokes and must say so (OVERLAP_SIMPLE), the
    bit macOS reads to rasterize overlaps without seams."""
    glyf = font["glyf"]
    bare = [g for g in font.getGlyphOrder() if glyf[g].numberOfContours > 0 and not glyf[g].flags[0] & OVERLAP_SIMPLE]
    assert not bare, f"{group}: glyphs without OVERLAP_SIMPLE: {bare[:10]}"


# --- the shipped files, the names, the build ------------------------------------------------------------
def test_the_shipped_fonts_match_their_manifest(cfg, manifest, req, req_path):
    """A source edited without a rebuild, or a font rebuilt without committing the manifest, is how a
    reviewed design and the shipped bytes drift apart silently. Every group the requirements name must
    have a manifest entry whose digest is the file on disk, and every hashed source must be unchanged.
    The manifest must also say the build ran against THIS requirements file (review finding C6): a
    --no-requirements build records null and skipped the required-character check."""
    assert manifest.get("requirements"), "the manifest records no requirements file: the font was built with --no-requirements, so no required-character check ran"
    assert (cfg["_dir"] / manifest["requirements"]).resolve() == req_path, \
        f"the font was built against {manifest['requirements']}, the suite holds it to {req_path}"
    assert set(manifest["groups"]) >= set(req["groups"]), f"manifest covers {sorted(manifest['groups'])}, requirements {sorted(req['groups'])}"
    for group in req["groups"]:
        path = group_woff2(cfg, group)
        m = manifest["groups"][group]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == m["woff2_sha256"], \
            f"{group}: {path.name} is not the manifest's; rebuild: python3 scripts/build.py --font {cfg['_path']}"
        assert m["woff2_bytes"] == path.stat().st_size
    sources = {"gen.js": SCRIPTS / "gen.js", "export.js": SCRIPTS / "export.js", "build.py": SCRIPTS / "build.py",
               "font.json": cfg["_path"], "concepts.js": cfg["_concepts"]}
    assert set(manifest["sources_sha256"]) == set(sources), f"manifest hashes {sorted(manifest['sources_sha256'])}"
    for src, digest in manifest["sources_sha256"].items():
        assert hashlib.sha256(sources[src].read_bytes()).hexdigest() == digest, f"{src} changed since the font was built"


def test_the_font_names_the_project(group, font, req):
    """The name table is what font pickers, licence audits and crash logs show; it must carry the
    reviewed family, copyright, manufacturer, licence and vendor strings, not a placeholder."""
    N, want = names_of(font), req["names"]
    assert N[1] == N[16] == want["family"], f"{group}: family {N[1]!r}/{N[16]!r}"
    assert N[0] == want["copyright"], f"{group}: copyright {N[0]!r}"
    assert N[8] == want["manufacturer"], f"{group}: manufacturer {N[8]!r}"
    assert N[9] == want["designer"], f"{group}: designer {N[9]!r} is not the reviewed {want['designer']!r}"
    assert want["licence_contains"] in N[13], f"{group}: licence {N[13]!r}"
    assert N[11] == want["vendor_url"], f"{group}: vendor URL {N[11]!r}"
    assert font["OS/2"].achVendID.strip() == want["vendor_id"], f"{group}: vendor id {font['OS/2'].achVendID!r}"


def test_style_metadata_matches_the_group(group, font, cfg, req):
    """Review finding F004: an italic group must say so everywhere a renderer looks (post.italicAngle,
    fsSelection ITALIC with REGULAR clear, head.macStyle, subfamily "Italic", a file named
    <Family>-Italic-VF.woff2), or `font-style: italic` synthesises a slant over the roman; a roman
    group must say Regular with an italic angle of 0. USE_TYPO_METRICS stays set in both."""
    R, N = req["groups"][group], names_of(font)
    fs = font["OS/2"].fsSelection
    assert fs & FS_USE_TYPO, f"{group}: USE_TYPO_METRICS cleared"
    if "italic_angle" in R:
        assert font["post"].italicAngle == -R["italic_angle"], f"{group}: post.italicAngle {font['post'].italicAngle}"
        assert fs & FS_ITALIC and not fs & FS_REGULAR, f"{group}: fsSelection {fs:#x}"
        assert font["head"].macStyle & MAC_ITALIC, f"{group}: macStyle {font['head'].macStyle:#x}"
        assert N[2] == N[17] == "Italic" and N[4] == f"{want_family(req)} Italic", f"{group}: names {N[2]!r} {N[17]!r} {N[4]!r}"
        assert group_woff2(cfg, group).name.endswith("Italic-VF.woff2"), f"{group}: file {group_woff2(cfg, group).name}"
    else:
        assert font["post"].italicAngle == 0, f"{group}: post.italicAngle {font['post'].italicAngle}"
        assert fs & FS_REGULAR and not fs & FS_ITALIC, f"{group}: fsSelection {fs:#x}"
        assert not font["head"].macStyle & MAC_ITALIC, f"{group}: macStyle {font['head'].macStyle:#x}"
        assert N[2] == N[17] == "Regular", f"{group}: names {N[2]!r} {N[17]!r}"
        assert not group_woff2(cfg, group).name.endswith("Italic-VF.woff2"), f"{group}: file {group_woff2(cfg, group).name}"


def want_family(req):
    return req["names"]["family"]


def test_the_italic_straight_tick_is_slanted(italic_group, font):
    """Driftwood build.py slanted the straight tick about its middle so a straight quote in italic
    text leans with the letters; a roman tick in an italic font stands out as upright. The top of the
    tick must sit to the right of its bottom."""
    glyf = font["glyf"]
    pts = coords(font, "quotesingle")
    top, bot = max(y for x, y in pts), min(y for x, y in pts)
    top_x = sum(x for x, y in pts if y >= top - 5) / len([1 for x, y in pts if y >= top - 5])
    bot_x = sum(x for x, y in pts if y <= bot + 5) / len([1 for x, y in pts if y <= bot + 5])
    assert top_x > bot_x + 10, \
        f"{italic_group}: quotesingle top x {top_x:.1f} is not right of its bottom x {bot_x:.1f}; glyph {glyf['quotesingle'].numberOfContours} contours"


def test_the_build_is_reproducible(cfg):
    """build.py --check rebuilds from the sources into memory and compares bytes with the shipped
    fonts and manifest; a timestamp, an unsorted table or a random jitter anywhere makes it exit 1.
    The subprocess gets a foreign SOURCE_DATE_EPOCH on purpose: the build must assign its own from
    font.json, not default to the caller's, or the bytes would depend on who ran it (trap 14)."""
    env = {**os.environ, "SOURCE_DATE_EPOCH": "1000000000"}
    r = subprocess.run([sys.executable, str(SCRIPTS / "build.py"), "--font", str(cfg["_path"]), "--check"], capture_output=True, text=True, env=env)
    # the verdict lines, not the SELF-CHECK ok lines that now fill the tail of stderr
    verdict = "\n".join(ln for ln in r.stderr.splitlines() if "--check" in ln or "FAILED" in ln or ln.startswith("  manifest.")) or r.stderr[-2000:]
    assert r.returncode == 0, verdict
    lines = [line for line in r.stderr.splitlines() if line.startswith("build.py --check:")]
    assert len(lines) == len(cfg["groups"]) and all("font identical, manifest identical" in line for line in lines), verdict


# --- the generator's knobs (review finding F005 of the skill plan, issue #24) -----------------------------
DROPAMT_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
const base = Object.assign({}, concepts[0], { tear: true }); delete base.flareAmt; delete base.dropAmt;
const draw = c => {
  const P = m.params(c, 1); const out = {};
  for (const k of Object.keys(m.G)) { const g = m.glyph(k, P); if (g) out[k] = g.polys; }
  return out;
};
// the generator caches glyphs per concept id, so the variant needs its own id to be drawn afresh
const a = draw(base), b = draw(Object.assign({}, base, { id: base.id + "-drop", dropAmt: 0.9 }));
const changed = Object.keys(a).filter(k => JSON.stringify(a[k]) !== JSON.stringify(b[k]));
let threw = null;
try { m.params(Object.assign({}, base, { flareAmt: 0.2 }), 1); } catch (e) { threw = e.message; }
console.log(JSON.stringify({ changed: changed.length, threw }));
"""


TEARDROP_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
const base = Object.assign({}, concepts[0], { tear: true }); delete base.flareAmt; delete base.dropAmt;
function draw(drop) {
  const P = m.params(Object.assign({}, base, { id: base.id + "|drop" + drop, dropAmt: drop }), 1), out = {};
  for (const k of Object.keys(m.G)) { const g = m.glyph(k, P); if (g) out[k] = g; }
  return out;
}
const G = [draw(0), draw(0.55), draw(1.1)];
// one stroke per teardrop kind, found from the branch record "tear=A/B" (A, B in L, R, S or null)
const want = {};
for (const k of Object.keys(G[0])) {
  let open = 0;
  G[0][k].sig.forEach(s => {
    if (!s.startsWith("open")) return;
    const mm = s.match(/tear=(\w+)\/(\w+)/);
    if (mm) for (const [end, kind] of [["A", mm[1]], ["B", mm[2]]]) {
      if ("LRS".includes(kind) && kind.length === 1 && !want[kind]) want[kind] = { glyph: k, open, end, other: end === "A" ? mm[2] : mm[1] };
    }
    open++;
  });
}
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
function edges(g, open) {
  // the open-th polygon with two edge runs is that stroke's body; runs[0] is always the left edge's run
  let seen = 0, pi = -1;
  for (let i = 0; i < g.polys.length; i++) if (g.runs[i].length === 2) { if (seen === open) { pi = i; break; } seen++; }
  const poly = g.polys[pi], runs = g.runs[pi], n = runs[0][1] - runs[0][0] + 1, flipped = runs[0][0] !== 0;
  return { n, L: i => flipped ? poly[runs[0][1] - i] : poly[runs[0][0] + i], R: i => flipped ? poly[runs[1][0] + i] : poly[runs[1][1] - i] };
}
const out = {};
for (const kind of ["L", "R", "S"]) {
  const w = want[kind];
  if (!w) { out[kind] = null; continue; }
  const e = G.map(g => edges(g[w.glyph], w.open)), n = e[0].n;
  // the glyph's sidebearing shifts with its extents, so every build is re-aligned on a reference sample
  // that no teardrop reaches: the far end when it has none, else the middle of the stroke
  const r = w.other === "null" ? (w.end === "A" ? n - 1 : 0) : Math.floor(n / 2);
  const shift = e.map(ed => [ed.L(r)[0] - e[0].L(r)[0], ed.L(r)[1] - e[0].L(r)[1]]);
  const refWidths = e.map(ed => dist(ed.L(r), ed.R(r)));
  // eight samples in from the end: inside the teardrop zone, clear of the cap; skip a sample the fold pin
  // touched (a pinned point equals its predecessor) in any build
  let s = w.end === "A" ? 8 : n - 1 - 8;
  const pinned = i => e.some(ed => dist(ed.L(i), ed.L(i - 1)) < 1e-9 || dist(ed.R(i), ed.R(i - 1)) < 1e-9);
  for (let tries = 0; tries < 12 && pinned(s); tries++) s += w.end === "A" ? 1 : -1;
  const al = (d, p) => [p[0] - shift[d][0], p[1] - shift[d][1]];
  const C = [(e[0].L(s)[0] + e[0].R(s)[0]) / 2, (e[0].L(s)[1] + e[0].R(s)[1]) / 2];
  const dL = d => dist(al(d, e[d].L(s)), C) - dist(e[0].L(s), C), dR = d => dist(al(d, e[d].R(s)), C) - dist(e[0].R(s), C);
  out[kind] = { glyph: w.glyph, end: w.end, sample: s, n, refWidths, width0: dist(e[0].L(s), e[0].R(s)),
    dL55: dL(1), dL110: dL(2), dR55: dR(1), dR110: dR(2), pinned: pinned(s) };
}
console.log(JSON.stringify(out));
"""

def check_teardrop_scaling(out):
    """Shared assertions for the L, R and S teardrop cases (review finding F005 of the skill plan). At a
    sample eight steps inside the teardrop zone, re-aligned for the sidebearing shift and clear of the
    fold pin: the outer edge swells by 0.55 and the inner edge thins by 0.28 of the stroke's half-width
    times the same smoothstep, so outer/inner = 55/28; the symmetric (S) case moves both edges equally;
    and every displacement doubles from dropAmt 0.55 to 1.1, because the knob is linear. Measured in
    the test from the polygons, not from the generator's formula."""
    for kind in "LRS":
        assert out[kind], f"no stroke with a {kind} teardrop end in the branch records"
    L, R, S = out["L"], out["R"], out["S"]
    for d in (L, R, S):
        assert not d["pinned"], f"{d['glyph']}: the sample is on a pinned point"
        assert max(d["refWidths"]) - min(d["refWidths"]) < 1e-6, f"{d['glyph']}: the reference sample moved; the re-alignment is wrong"
    want = 55 / 28
    assert L["dL55"] > 0 and L["dR55"] < 0, f"L case ({L['glyph']}): outer {L['dL55']:.3f} must swell and inner {L['dR55']:.3f} must thin"
    assert abs(L["dL55"] / -L["dR55"] - want) < 0.02 * want, f"L case: outer/inner is {L['dL55'] / -L['dR55']:.3f}, expected {want:.3f}"
    assert R["dR55"] > 0 and R["dL55"] < 0, f"R case ({R['glyph']}): outer {R['dR55']:.3f} must swell and inner {R['dL55']:.3f} must thin"
    assert abs(R["dR55"] / -R["dL55"] - want) < 0.02 * want, f"R case: outer/inner is {R['dR55'] / -R['dL55']:.3f}, expected {want:.3f}"
    assert S["dL55"] > 0 and S["dR55"] > 0, f"S case ({S['glyph']}): both edges must swell, got {S['dL55']:.3f} / {S['dR55']:.3f}"
    assert abs(S["dL55"] - S["dR55"]) < 1e-6 + 0.005 * S["dL55"], f"S case: the swell is not symmetric: {S['dL55']:.3f} / {S['dR55']:.3f}"
    for d in (L, R, S):
        for edge in ("dL", "dR"):
            assert abs(d[edge + "110"] - 2 * d[edge + "55"]) < 1e-6 + 0.005 * abs(d[edge + "110"]), \
                f"{d['glyph']} {edge}: {d[edge + '55']:.3f} at dropAmt 0.55 but {d[edge + '110']:.3f} at 1.1; the knob is not linear"


def test_dropamt_scales_the_outer_inner_and_symmetric_teardrop(cfg):
    """Review finding F005 of the skill plan: dropAmt must scale the WHOLE teardrop, the outer swell,
    the inner thinning and the symmetric case together. A test that only asks whether dropAmt changes
    something stays green when one of the three constants stops listening (a mutation found exactly
    that). This finds a stroke with an L, an R and an S teardrop in the project's first concept (tear
    forced on) from the branch records and measures each edge's displacement at dropAmt 0, 0.55 and 1.1."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", TEARDROP_FIXTURE, str(SCRIPTS / "gen.js"), str(cfg["_concepts"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    check_teardrop_scaling(json.loads(r.stdout))


def test_dropamt_changes_the_teardrops_and_flareamt_with_tear_throws(cfg):
    """Issue #24: `flareAmt` was a dead knob whenever `tear: true`, because the flare swell never applies
    to teardrop terminals, and nothing said so. The project's first concept with teardrops on must draw
    differently at dropAmt 0.9 than at the default, and a concept that sets flareAmt beside tear must
    make params() throw an error naming dropAmt."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", DROPAMT_FIXTURE, str(SCRIPTS / "gen.js"), str(cfg["_concepts"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["changed"] > 0, "dropAmt 0.9 drew every glyph exactly as the default did: the knob is dead"
    assert out["threw"] and "dropAmt" in out["threw"], f"flareAmt beside tear:true did not throw naming dropAmt: {out['threw']!r}"


def test_export_refuses_a_required_character_without_a_skeleton(cfg, req, tmp_path):
    """Review finding F011: a character the skeleton table lacks used to be dropped in silence, and the
    page rendered it in the fallback face. With --requirements naming "@" (no skeleton), export.js must
    exit 1 and name U+0040 so the operator adds a skeleton or changes the content."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    fixture = tmp_path / "requirements-at.json"
    fixture.write_text(json.dumps({"required_characters": "A@"}))
    group = next(iter(req["groups"]))
    cmd = [node, str(SCRIPTS / "export.js"), "--font", str(cfg["_path"]), "--group", group, "--requirements", str(fixture), str(tmp_path / "out.json")]
    r = subprocess.run(cmd, cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 1, f"export.js exited {r.returncode}; stderr: {r.stderr[-500:]}"
    assert "U+0040" in r.stderr, f"the failure does not name U+0040: {r.stderr[-500:]}"
    assert not (tmp_path / "out.json").exists(), "export.js wrote an export although a required character was missing"


def build_cmd(cfg, scripts, group, out_dir, *extra):
    return [sys.executable, str(scripts / "build.py"), "--font", str(cfg["_path"]), "--group", group, "--out-dir", str(out_dir), *extra]


def test_build_refuses_a_required_character_without_a_skeleton(cfg, group, export, scripts, tmp_path):
    """Review finding C6: build.py ran export.js WITHOUT --requirements, so a normal build never made the
    F011 check above; it ran only when someone invoked export.js by hand. Now a build given a
    requirements file naming "@" (no skeleton) must exit 1 naming U+0040 and write nothing, on the
    export path (export.js refuses) and on the --masters path (build.py applies the same rule to the
    loaded glyph keys itself, since no export runs there)."""
    fixture = tmp_path / "requirements-at.json"
    fixture.write_text(json.dumps({"required_characters": "A@"}))
    out_dir = tmp_path / "out"
    r = subprocess.run(build_cmd(cfg, scripts, group, out_dir, "--requirements", str(fixture)), capture_output=True, text=True)
    assert r.returncode == 1, f"build.py exited {r.returncode} on the export path although '@' has no skeleton; stderr: {r.stderr[-600:]}"
    assert "U+0040" in r.stderr, f"the export-path refusal does not name U+0040: {r.stderr[-600:]}"
    assert not out_dir.exists(), "build.py wrote output although a required character was missing (export path)"
    masters = tmp_path / "masters.json"
    masters.write_text(json.dumps(export))
    r = subprocess.run(build_cmd(cfg, scripts, group, out_dir, "--requirements", str(fixture), "--masters", str(masters)), capture_output=True, text=True)
    assert r.returncode == 1, f"build.py exited {r.returncode} on the --masters path although '@' has no glyph; stderr: {r.stderr[-600:]}"
    assert "U+0040" in r.stderr, f"the --masters refusal does not name U+0040: {r.stderr[-600:]}"
    assert not out_dir.exists(), "build.py wrote output although a required character was missing (--masters path)"


def test_build_refuses_a_masters_json_that_overstates_its_stroke_width(cfg, group, export, req_path, scripts, tmp_path):
    """Review finding C7: under --masters the self-checks trusted minStrokeWidth from the JSON, so a
    hand-edited export could clear a hairline floor on paper. build.py now measures the minimum interior
    stroke width from the polygons itself and refuses a JSON whose stated figure is more than 0.15 units
    away, naming the master, the stated location and the measured one. Exact guarantee: an overstatement
    of up to 0.15 units still passes, because the exported coordinates are rounded to 0.1 units."""
    master = next(iter(export["masters"]))
    stated = export["masters"][master]["minStrokeWidth"]
    doctored = json.loads(json.dumps(export))  # a copy: the export fixture is shared by the session
    doctored["masters"][master]["minStrokeWidth"] = round(stated + 0.5, 2)
    path = tmp_path / "masters-raised.json"
    path.write_text(json.dumps(doctored))
    out_dir = tmp_path / "out"
    r = subprocess.run(build_cmd(cfg, scripts, group, out_dir, "--requirements", str(req_path), "--masters", str(path)), capture_output=True, text=True)
    assert r.returncode == 1, f"build.py exited {r.returncode} although {master}'s minStrokeWidth was raised by 0.5; stderr: {r.stderr[-600:]}"
    assert "minStrokeWidth" in r.stderr and master in r.stderr, f"the refusal does not name the master and the figure: {r.stderr[-600:]}"
    assert export["masters"][master]["minStrokeAt"] in r.stderr, f"the refusal does not name the exporter's location {export['masters'][master]['minStrokeAt']!r}"
    assert not out_dir.exists(), "build.py wrote output from a masters JSON whose stroke width it should not have trusted"


def test_build_refuses_a_masters_json_whose_parameters_differ_from_the_generator(cfg, group, export, req_path, scripts, tmp_path):
    """Re-review finding code-a F002: the --masters path checked concept and mult against font.json but took
    W, thin and track from the JSON, and W sets the interior reach of the stroke-width recomputation, so a
    JSON that tripled W passed the C7 check with its minStrokeAt reading "doctored". build.py now reads the
    parameters back from gen.js params() and refuses a JSON whose W (here), thin or track differs, naming
    the master, the key and both values. Doctoring W alone, with the stated stroke width untouched, is the
    weakest edit: on this fixture the recomputed minimum does not move with W, so only the parameter check
    can refuse it (the C7 tolerance check stays green either way)."""
    master = next(iter(export["masters"]))
    doctored = json.loads(json.dumps(export))
    doctored["masters"][master]["W"] = export["masters"][master]["W"] * 3
    path = tmp_path / "masters-W.json"
    path.write_text(json.dumps(doctored))
    out_dir = tmp_path / "out"
    r = subprocess.run(build_cmd(cfg, scripts, group, out_dir, "--requirements", str(req_path), "--masters", str(path)), capture_output=True, text=True)
    assert r.returncode == 1, f"build.py exited {r.returncode} although {master}'s W was tripled in the masters JSON; stderr: {r.stderr[-600:]}"
    assert f"{master}: the export records W = " in r.stderr and "gen.js params() gives" in r.stderr, \
        f"the refusal does not name W and the generator's value: {r.stderr[-600:]}"
    assert not out_dir.exists(), "build.py wrote output from a masters JSON whose W it should not have trusted"


def test_build_refuses_a_masters_json_with_a_polygon_record_missing(cfg, group, export, req_path, scripts, tmp_path):
    """Re-review finding code-a F003: load_masters() and the self-checks zipped a glyph's raw, runs, polys and
    keptIdx lists, and Python's zip stops at the shortest, so a JSON whose keptIdx list was one record short
    in every master (the cross-master comparison then still agrees) built and shipped with that polygon's
    fold and decimation checks skipped in silence. build.py now refuses it naming the glyph and the lengths."""
    doctored = json.loads(json.dumps(export))
    glyph = next(k for k, g in doctored["masters"][next(iter(doctored["masters"]))]["glyphs"].items() if len(g["keptIdx"]) > 1)
    for M in doctored["masters"].values():
        M["glyphs"][glyph]["keptIdx"] = M["glyphs"][glyph]["keptIdx"][:-1]
    path = tmp_path / "masters-short.json"
    path.write_text(json.dumps(doctored))
    out_dir = tmp_path / "out"
    r = subprocess.run(build_cmd(cfg, scripts, group, out_dir, "--requirements", str(req_path), "--masters", str(path)), capture_output=True, text=True)
    assert r.returncode == 1, f"build.py exited {r.returncode} although {glyph!r}'s keptIdx list is one record short; stderr: {r.stderr[-600:]}"
    assert f"{glyph}: the per-polygon lists have unequal lengths" in r.stderr, f"the refusal does not name the glyph and the lengths: {r.stderr[-600:]}"
    assert not out_dir.exists(), "build.py wrote output from a masters JSON with a polygon record missing"


# --- static instances (--static DIR; review finding F012 of the skill plan) --------------------------------
def test_static_instances_exist_and_match_the_variable_font(group, instance_name, cfg, req, static_dir):
    """Statics are for @font-face rules that need a single weight (older renderers, email, print).
    Each one named in the requirements must exist as TTF and woff2, carry no variation tables, equal an
    independent instantiation of the shipped variable font at its location (outlines and advances,
    exactly, after rounding), keep OVERLAP_SIMPLE on every contoured glyph, and carry the instance's
    name, weight class and the group's italic bits. A static that loads but draws nothing is caught by
    rendering one glyph through FreeType."""
    R = req["groups"][group]
    location = R["instances"][instance_name]
    stem = f"{want_family(req).replace(' ', '')}-{instance_name.replace(' ', '')}"
    ttf_path, woff2_path = static_dir / f"{stem}.ttf", static_dir / f"{stem}.woff2"
    assert ttf_path.is_file() and woff2_path.is_file(), f"{group} {instance_name}: expected {ttf_path.name} and {woff2_path.name} in {static_dir}"
    vf_path = group_woff2(cfg, group)
    ref = instancer.instantiateVariableFont(TTFont(vf_path), dict(location), inplace=False)
    for path in (ttf_path, woff2_path):
        st = TTFont(path)
        for t in ("fvar", "gvar", "avar", "STAT"):
            assert t not in st, f"{path.name}: {t} table present in a static"
        want_vm = R["vertical_metrics"]
        assert (st["hhea"].ascent, st["hhea"].descent, st["hhea"].lineGap) == (want_vm["ascender"], want_vm["descender"], want_vm["line_gap"]) \
            == (st["OS/2"].sTypoAscender, st["OS/2"].sTypoDescender, st["OS/2"].sTypoLineGap), f"{path.name}: static line metrics differ from the reviewed {want_vm}"
        assert st["OS/2"].fsType == req["names"]["fs_type"], f"{path.name}: static fsType {st['OS/2'].fsType}"
        assert not [r for r in st["name"].names if r.platformID == 1] or req["tables"]["mac_names"], f"{path.name}: Macintosh name records in a static"
        assert st.getGlyphOrder() == ref.getGlyphOrder(), f"{path.name}: glyph order differs from the variable font"
        for g in st.getGlyphOrder():
            assert st["glyf"][g].numberOfContours == ref["glyf"][g].numberOfContours, f"{path.name} {g}: contour count"
            if st["glyf"][g].numberOfContours > 0:
                assert coords(st, g) == coords(ref, g), f"{path.name} {g}: outline differs from an instantiation at {location}"
                assert st["glyf"][g].flags[0] & OVERLAP_SIMPLE, f"{path.name} {g}: OVERLAP_SIMPLE missing"
            assert st["hmtx"][g] == tuple(otRound(v) for v in ref["hmtx"][g]), f"{path.name} {g}: advance differs from an instantiation at {location}"
        N = names_of(st)
        assert N[1] == N[16] == want_family(req) and N[2] == N[17] == instance_name and N[4] == f"{want_family(req)} {instance_name}", \
            f"{path.name}: names {N.get(1)!r} {N.get(2)!r} {N.get(4)!r} {N.get(17)!r}"
        assert N.get(9) == req["names"]["designer"], f"{path.name}: static designer {N.get(9)!r} is not the reviewed {req['names']['designer']!r}"
        if "wght" in location:
            assert st["OS/2"].usWeightClass == location["wght"], f"{path.name}: usWeightClass {st['OS/2'].usWeightClass}"
        italic = "italic_angle" in R
        fs = st["OS/2"].fsSelection
        assert bool(fs & FS_ITALIC) == italic and bool(st["head"].macStyle & MAC_ITALIC) == italic, \
            f"{path.name}: italic bits fsSelection {fs:#x} macStyle {st['head'].macStyle:#x}"
        assert st["post"].italicAngle == (-R["italic_angle"] if italic else 0), f"{path.name}: post.italicAngle {st['post'].italicAngle}"
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("L", (120, 120), 0)
    ImageDraw.Draw(im).text((20, 90), "H", font=ImageFont.truetype(str(ttf_path), 40), fill=255, anchor="ls")
    assert im.getextrema()[1] > 0, f"{ttf_path.name}: FreeType rendered nothing"


# --- optical corrections: hzThin, roundGain, diagThin (0.2, item 3) -----------------------------------------
OPTICAL_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
// monoline, nib 0, every end a plain butt: the pen width is then 1 everywhere and the only variation in a
// stroke's width is the optical factor. `s` stays "serif" because the corner pass (E, z) runs only for a
// serifed concept; the serif polygons are separate from the stroke bodies measured below. The fit is kept
// (overshoot 10) because the flat-line and corner assertions need it.
const ends = {}; for (const k of Object.keys(concepts[0].ends)) ends[k] = "butt"; ends.s = "serif";
const base = Object.assign({}, concepts[0], { thin: 1, nib: 0, pow: 1, swell: 0, wob: 0, tear: false, overshoot: 10, ends });
delete base.thinGrow; delete base.flareAmt; delete base.dropAmt;
const VARIANTS = {
  none: {}, hz: { hzThin: 0.9 }, round: { roundGain: 1.05 }, diag: { diagThin: 0.94 },
  // the bound's extra cases (finding R3): a gain below 1, and a hzThin above 1 that multiplies the gain term
  roundLow: { roundGain: 0.85 }, hzHigh: { hzThin: 1.4 }, hzHighRound: { hzThin: 1.4, roundGain: 1.05 },
  all: { hzThin: 0.9, roundGain: 1.05, diagThin: 0.94 }, ones: { hzThin: 1, roundGain: 1, diagThin: 1 },
  // the unfitted c has a curve tighter than the gain radius; the fitted one flattens it (the fit pulls the
  // centre line in by the half width), so the saturated end of the weight is only visible without the fit
  roundNoFit: { roundGain: 1.05, overshoot: 0 },
};
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
function bodies(g) {
  // the stroke bodies in drawing order: the polygons with two edge runs
  const out = [];
  g.polys.forEach((poly, i) => {
    if (g.runs[i].length !== 2) return;
    const runs = g.runs[i], flipped = runs[0][0] !== 0, n = runs[0][1] - runs[0][0] + 1;
    out.push({ poly, n, L: j => flipped ? poly[runs[0][1] - j] : poly[runs[0][0] + j], R: j => flipped ? poly[runs[1][0] + j] : poly[runs[1][1] - j] });
  });
  return out;
}
const maxY = poly => Math.max(...poly.map(p => p[1])), maxX = poly => Math.max(...poly.map(p => p[0]));
const res = { W0: base.W, variants: {} };
for (const [vn, extra] of Object.entries(VARIANTS)) {
  res.variants[vn] = {};
  for (const mult of [1, 1.5]) {
    const P = m.params(Object.assign({}, base, extra, { id: "optical-" + vn }), mult);
    const g = k => m.glyph(k, P);
    const r = {};
    const l = bodies(g("l"))[0], mid = Math.floor(l.n / 2);
    r.l_w = dist(l.L(mid), l.R(mid));
    const d = bodies(g("-"))[0]; r.dash_w = dist(d.L(Math.floor(d.n / 2)), d.R(Math.floor(d.n / 2)));
    const o = g("o"); r.o_right = maxX(o.polys[0]) - maxX(o.polys[1]);
    r.o_top = maxY(o.polys[0]); r.o_bot = Math.min(...o.polys[0].map(p => p[1]));
    const x = bodies(g("x"))[0], xm = Math.floor(x.n / 2), mp = j => [(x.L(j)[0] + x.R(j)[0]) / 2, (x.L(j)[1] + x.R(j)[1]) / 2];
    r.x_w = dist(x.L(xm), x.R(xm)); r.x_theta = Math.atan2(mp(xm + 1)[1] - mp(xm - 1)[1], mp(xm + 1)[0] - mp(xm - 1)[0]);
    r.z_top = maxY(bodies(g("z"))[0].poly);
    r.tops = {}; for (const k of ["c", "e", "s"]) r.tops[k] = Math.max(...g(k).polys.map(maxY));
    const E = bodies(g("E")); r.E_stem_top = maxY(E[0].poly); r.E_bar_top = maxY(E[1].poly);
    const c = bodies(g("c"))[0], cn = c.n, pin = j => j > 0 && (dist(c.L(j), c.L(j - 1)) < 1e-9 || dist(c.R(j), c.R(j - 1)) < 1e-9);
    r.c_mid = []; r.c_w = []; r.c_pin = [];
    for (let j = 0; j < cn; j++) {
      r.c_mid.push([(c.L(j)[0] + c.R(j)[0]) / 2, (c.L(j)[1] + c.R(j)[1]) / 2]); r.c_w.push(dist(c.L(j), c.R(j)));
      r.c_pin.push(pin(j) || pin(j + 1));
    }
    res.variants[vn][mult] = r;
  }
}
// h: with every knob explicitly 1, every glyph is the glyph without the keys, exactly
let same = true, count = 0;
for (const mult of [1, 1.5]) {
  const A = m.params(Object.assign({}, base, { id: "optical-same-a" }), mult), B = m.params(Object.assign({}, base, VARIANTS.ones, { id: "optical-same-b" }), mult);
  for (const k of Object.keys(m.G)) {
    const a = m.glyph(k, A), b = m.glyph(k, B);
    if (!a) continue;
    count++;
    if (JSON.stringify(a.polys) !== JSON.stringify(b.polys)) same = false;
  }
}
res.same = same; res.glyphs = count;
console.log(JSON.stringify(res));
"""


def run_optical(cfg):
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", OPTICAL_FIXTURE, str(SCRIPTS / "gen.js"), str(cfg["_concepts"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def expected_curvature_weight(mids, W0, RADIUS=2.5):
    """The documented curvature weight (references/generator.md section 3), restated from a stroke's centre
    line: the turning angle at a sample over the mean length of its two chords, times 2.5 x W0, capped at 1.
    The end samples take the weight of their neighbour. The centre line is the midpoint of the two output
    edges, so nothing here comes from the generator's own arithmetic."""
    n, out = len(mids), []
    for i in range(n):
        j = min(n - 2, max(1, i))
        (ax, ay), (bx, by), (cx, cy) = mids[j - 1], mids[j], mids[j + 1]
        ux, uy, vx, vy = bx - ax, by - ay, cx - bx, cy - by
        ds = (math.hypot(ux, uy) + math.hypot(vx, vy)) / 2
        kappa = abs(math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)) / ds if ds > 0 else 0
        out.append(min(1.0, kappa * RADIUS * W0))
    return out


def test_optical_corrections_change_only_the_strokes_they_name(cfg):
    """Item 3 of the 0.2 plan. One knob per variant, then all three together, so no expectation mixes two
    factors by accident (review finding F007: the first draft expected a diagonal's width from `diagThin`
    alone while `hzThin` also applied at that angle). The base concept is monoline with nib 0 and plain butt
    ends, so every width is W times the optical factor and nothing else. Expected values are the configured
    ratio or the documented formula restated here with this test's own trigonometry; the angle of the `x`
    stroke and the curvature of the `c` are read from the output polygons, never from the generator.

    Mutations (scripts/tests/mutate.py): hzThin without its cos^2 weight (the plumb `l` thins); a curvature
    weight of 1 on every open stroke (the straight `l` swells); a weight of 0 on every open stroke (the `c`
    never swells); no diagonal weight (the `x` stays full width); a fit that ignores the factor (the `z`
    bar's top edge misses 500); a corner that ignores it (the `E` stem overshoots its bar)."""
    out = run_optical(cfg)
    V, W0 = out["variants"], out["W0"]
    for mult in ("1", "1.5"):
        W = W0 * float(mult)
        for name, r in ((n, v[mult]) for n, v in V.items()):
            where = f"{name} at mult {mult}"
            # a: a plumb straight stem is untouched by every knob (cos^2 90 deg = 0, sin^2 180 deg = 0, curvature 0)
            if name != "roundNoFit":
                assert abs(r["l_w"] - W) < 0.05, f"{where}: the `l` stem is {r['l_w']:.3f} wide, expected {W}"
        # b: a level bar thins by hzThin, and by nothing else
        assert abs(V["hz"][mult]["dash_w"] - 0.9 * W) < 0.05, f"hz at mult {mult}: the `-` bar is {V['hz'][mult]['dash_w']:.3f} wide, expected {0.9 * W}"
        for n in ("none", "round", "diag"):
            assert abs(V[n][mult]["dash_w"] - W) < 0.05, f"{n} at mult {mult}: the `-` bar is {V[n][mult]['dash_w']:.3f} wide, expected {W}"
        # c: the ring's right extreme (a vertical tangent on a closed stroke) swells by roundGain
        got = V["round"][mult]["o_right"]
        assert abs(got - 1.05 * W) < 0.1, f"round at mult {mult}: the `o` is {got:.3f} thick at its right extreme, expected {1.05 * W}"
        assert abs(V["none"][mult]["o_right"] - W) < 0.1, f"none at mult {mult}: the `o` is {V['none'][mult]['o_right']:.3f} thick at its right extreme, expected {W}"
        # c2: the configured overshoot is what a round top gets, whatever the knobs do to the stroke's width
        for vn in ("none", "hz", "round", "diag", "all"):
            r = V[vn][mult]
            assert abs(r["o_top"] - 510) < 0.1 and abs(r["o_bot"] + 10) < 0.1, \
                f"{vn} at mult {mult}: the `o` spans {r['o_bot']:.2f} to {r['o_top']:.2f}, expected -10 to 510 (overshoot 10 past the lines)"
        # d: an open stroke swells by the weight of its local curvature. Every sample of the `c` is compared with
        # the width the documented formula gives for the curvature read off the OUTPUT centre line.
        for vn in ("round", "roundNoFit"):
            r = V[vn][mult]
            cw = expected_curvature_weight(r["c_mid"], W0)
            # a fold-pinned sample is not the pen law's (the pin copies its neighbour), so it is left out
            seen = [c for c, pinned in zip(cw, r["c_pin"]) if not pinned]
            worst = max(abs(w - W * (1 + 0.05 * c)) for w, c, pinned in zip(r["c_w"], cw, r["c_pin"]) if not pinned)
            assert worst < 0.05, f"{vn} at mult {mult}: the `c` is up to {worst:.3f} off W x (1 + 0.05 x curvature weight) at one sample"
            if vn == "roundNoFit":
                assert max(seen) > 0.99, \
                    f"{vn} at mult {mult}: the unfitted `c` never reaches a curvature weight of 1 (max {max(seen):.3f}); the fixture cannot observe the cap"
                assert max(r["c_w"]) > 1.049 * W, f"{vn} at mult {mult}: the widest `c` sample is {max(r['c_w']):.3f}, expected {1.05 * W}"
            else:
                assert max(seen) > 0.5, \
                    f"{vn} at mult {mult}: the fitted `c` never reaches a curvature weight of 0.5 (max {max(seen):.3f}); the fixture cannot observe the weighting"
                assert max(r["c_w"]) > 1.02 * W, f"{vn} at mult {mult}: the widest `c` sample is {max(r['c_w']):.3f}, the roundGain never reached it"
        # e: a diagonal thins by diagThin x sin^2(2 theta); theta is read from the centre line of the output
        x = V["diag"][mult]
        th = x["x_theta"]
        assert abs(x["x_w"] - W * (1 - 0.06 * math.sin(2 * th) ** 2)) < 0.05, \
            f"diag at mult {mult}: the `x` stroke (theta {math.degrees(th):.1f} deg) is {x['x_w']:.3f} wide, expected {W * (1 - 0.06 * math.sin(2 * th) ** 2):.3f}"
        # e2: all three together, the full product restated; the stroke is straight, so the curvature weight is 0
        a = V["all"][mult]
        th = a["x_theta"]
        want = W * (1 - 0.1 * math.cos(th) ** 2) * (1 - 0.06 * math.sin(2 * th) ** 2) * (1 + 0.05 * 0)
        assert abs(a["x_w"] - want) < 0.05, \
            f"all at mult {mult}: the `x` stroke (theta {math.degrees(th):.1f} deg) is {a['x_w']:.3f} wide, expected the product {want:.3f}"
        # f: the fit follows the thinning, so a flat bar's outer edge still sits on the x-line
        assert abs(V["hz"][mult]["z_top"] - 500) < 0.1, f"hz at mult {mult}: the `z` bar's top edge is at {V['hz'][mult]['z_top']:.2f}, expected 500"
        # g: and the corner reach follows it, so the stem ends flush with the bar's outer edge
        hzr = V["hz"][mult]
        assert abs(hzr["E_stem_top"] - hzr["E_bar_top"]) < 0.1, f"hz at mult {mult}: the `E` stem tops out at {hzr['E_stem_top']:.2f}, its bar at {hzr['E_bar_top']:.2f}"
        # the same lines with no knob set, so f and g measure a difference the knob made; and with all three
        # set, where a fit or a corner that wrongly gave the straight bar the round gain would miss by 2.25
        for vn in ("none", "all"):
            r = V[vn][mult]
            assert abs(r["z_top"] - 500) < 0.1, f"{vn} at mult {mult}: the `z` bar's top edge is at {r['z_top']:.2f}, expected 500"
            assert abs(r["E_stem_top"] - r["E_bar_top"]) < 0.1, f"{vn} at mult {mult}: the `E` stem tops out at {r['E_stem_top']:.2f}, its bar at {r['E_bar_top']:.2f}"
    # h: with every knob explicitly 1 every glyph is the glyph with no knob, exactly
    assert out["same"] and out["glyphs"] > 100, f"explicit 1s changed a glyph (same={out['same']}, {out['glyphs']} glyphs compared)"


REFUSAL_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
const cases = JSON.parse(process.argv[3]), out = [];
for (const [knob, spec] of cases) {
  const value = spec && typeof spec === "object" && spec.nan ? NaN : spec;
  let msg = null;
  try { m.params(Object.assign({}, concepts[0], { id: "refuse", [knob]: value }), 1); } catch (e) { msg = e.message; }
  out.push([knob, spec, msg]);
}
console.log(JSON.stringify(out));
"""


def refusal_results(cfg, cases):
    """Runs params() once per (knob, value) and returns [(knob, value, error message or None)]. A value of {"nan": 1} is sent as NaN."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", REFUSAL_FIXTURE, str(SCRIPTS / "gen.js"), str(cfg["_concepts"]), json.dumps(cases)], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# every optical knob and the open interval params() must accept, written here and not read from the generator (review finding G6: the first
# version built its bad cases from its own fixture and never sent `diagThin: null` or `roundGain: null`)
OPTICAL_RANGES = {"hzThin": (0.5, 1.5), "diagThin": (0.5, 1.5), "roundGain": (0.8, 1.25)}


def test_the_optical_knobs_refuse_values_outside_their_ranges(cfg):
    """params() throws, naming the knob, for every optical knob (hzThin and diagThin outside (0.5, 1.5), roundGain outside (0.8, 1.25)) given
    null, a string, NaN, a boolean, a value just below, just above, far outside, or either bound (the intervals are open), and accepts a value
    just inside either bound, the middle and 1. The cases are written in this test (OPTICAL_RANGES), the product of every knob and every kind
    of bad value, so a knob that forgot one kind (the Impasse review's `diagThin: null`) fails by name.

    Mutations: the range check removed; and one that accepts `diagThin: null` only."""
    cases, want = [], {}
    for knob, (lo, hi) in OPTICAL_RANGES.items():
        bad = [None, "1", "NaN", {"nan": 1}, True, lo - 0.01, hi + 0.01, lo, hi, -1, 0, 100]
        good = [lo + 0.01, (lo + hi) / 2, hi - 0.01, 1]
        for v in bad:
            cases.append([knob, v])
            want[(knob, json.dumps(v))] = "refuse"
        for v in good:
            cases.append([knob, v])
            want[(knob, json.dumps(v))] = "accept"
    for knob, spec, msg in refusal_results(cfg, cases):
        verdict = want[(knob, json.dumps(spec))]
        label = f"{knob}={'NaN' if isinstance(spec, dict) else json.dumps(spec)}"
        if verdict == "refuse":
            assert msg and knob in msg, f"{label}: params() did not refuse it by name: {msg!r}"
        else:
            assert msg is None, f"{label}: params() refused a value inside the range: {msg!r}"


# --- the x-height (xh) and the unbracketed serif (serifBracket) (0.2, item 4) -----------------------------
XH_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
// the project's first concept with every end a plain butt (so no serif, flare or beak decides a position), no swell and no wobble
// (so a width is the pen's), and the fit on: the lines under test are the fit's targets
const ends = {}; for (const k of Object.keys(concepts[0].ends)) ends[k] = "butt";
const base = Object.assign({}, concepts[0], { swell: 0, wob: 0, tear: false, overshoot: 10, ends });
delete base.flareAmt; delete base.dropAmt;
const maxY = p => Math.max(...p.map(q => q[1])), minY = p => Math.min(...p.map(q => q[1]));
function bodies(g) { return g.polys.filter((p, i) => g.runs[i].length === 2); }
const res = { W0: base.W, dot: base.dot, runs: {} };
for (const xh of [500, 600, 400]) for (const mult of [1, 1.5]) {
  const P = m.params(Object.assign({}, base, { id: "xh" + xh, xh }), mult), g = k => m.glyph(k, P), r = {};
  const o = g("o"); r.o_top = maxY(o.polys[0]); r.o_bot = minY(o.polys[0]);
  r.n_stem_top = maxY(bodies(g("n"))[0]); r.z_top = maxY(bodies(g("z"))[0]);
  const d = bodies(g("-"))[0]; r.dash_cy = (maxY(d) + minY(d)) / 2;
  const dd = bodies(g("d")); r.d_stem_top = maxY(dd[0]); r.d_bowl_top = maxY(dd[1]);
  r.H_top = maxY(g("H").polys[0]); r.O_top = maxY(g("O").polys[0]); r.zero_top = maxY(g("0").polys[0]); r.l_top = maxY(g("l").polys[0]);
  const ap = g("'").polys; r.apos = [Math.min(...ap.map(minY)), Math.max(...ap.map(maxY))];
  r.colon = g(":").polys.map(p => (maxY(p) + minY(p)) / 2).sort((a, b) => a - b);
  r.i_dot = g("i").polys.filter(p => minY(p) > 500).map(p => (maxY(p) + minY(p)) / 2);
  // h: the same polygons and points per polygon at every xh, for every key
  const P5 = m.params(Object.assign({}, base, { id: "xh500c" + xh }), mult); let diff = null;
  for (const k of Object.keys(m.G)) {
    const a = m.glyph(k, P5), b = g(k);
    if (!a) continue;
    if (a.polys.length !== b.polys.length || a.polys.some((p, i) => p.length !== b.polys[i].length)) { diff = k; break; }
  }
  r.shape_diff = diff;
  res.runs[xh + "/" + mult] = r;
}
console.log(JSON.stringify(res));
"""


def ymap(y, xh):
    """The documented x-height map (references/generator.md section 7), restated: descenders and ascenders stay, the body scales to xh,
    the band between the x-line and the ascender scales from xh to 740."""
    if y <= 0 or y >= 740:
        return y
    return y * xh / 500 if y <= 500 else xh + (y - 500) * (740 - xh) / 240


def test_xh_moves_the_lowercase_lines_and_leaves_the_capitals(cfg):
    """Item 4 of the 0.2 plan. At xh 600 and 400, Regular and Bold, with every end a butt so no terminal decides a position: the round
    `o` lands at xh plus the overshoot; a butt stem end sits on the new x-line; a flat bar's outer edge sits on it; the hyphen scales with
    the body; ascenders stay at 740; capitals, figures and the apostrophe stay where they are drawn; the colon's two dots sit on the
    baseline and the x-line (the rule reads the UNMAPPED dot position, review F006: at xh 600 the mapped 420 would read 504 and miss
    it); the i's dot is carried by the map; and no glyph gains or loses a polygon or a point. Expected values restate the documented map.

    Mutations: round targets left at the literal 500; flat targets left at 500; the map applied to capitals and the apostrophe; the band
    above the x-line left unmapped; the dot rule reading the mapped position."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", XH_FIXTURE, str(SCRIPTS / "gen.js"), str(cfg["_concepts"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    for xh in (600, 400):
        for mult in (1, 1.5):
            R, B = out["runs"][f"{xh}/{mult}"], out["runs"][f"500/{mult}"]
            where = f"xh {xh} at mult {mult}"
            ov = 10
            # a ring's measured extreme sits up to 1.2 units outside the line plus overshoot even at xh 500 (the offset of a stroke whose
            # width varies with direction: measured 511.15 for a Bold at xh 500), so the absolute bound is 1.6 and the shift is the exact check
            assert abs(R["o_top"] - (xh + ov)) < 1.6 and abs(R["o_bot"] + ov) < 1.6, \
                f"{where}: the `o` spans {R['o_bot']:.2f} to {R['o_top']:.2f}, expected {-ov} to {xh + ov}"
            assert abs((R["o_top"] - B["o_top"]) - (xh - 500)) < 0.5, f"{where}: the `o` top moved by {R['o_top'] - B['o_top']:.2f} from xh 500, expected {xh - 500}"
            assert abs(R["n_stem_top"] - xh) < 0.05, f"{where}: the `n` stem ends at {R['n_stem_top']:.2f}, expected the x-line {xh}"
            assert abs(R["z_top"] - xh) < 0.1, f"{where}: the `z` bar's top edge is at {R['z_top']:.2f}, expected the x-line {xh}"
            assert abs(R["dash_cy"] - 260 * xh / 500) < 0.1, f"{where}: the `-` is centred at {R['dash_cy']:.2f}, expected {260 * xh / 500}"
            assert abs(R["d_stem_top"] - 740) < 0.05, f"{where}: the `d` stem ends at {R['d_stem_top']:.2f}, expected 740"
            assert abs(R["d_bowl_top"] - (xh + ov)) < 1.6 and abs((R["d_bowl_top"] - B["d_bowl_top"]) - (xh - 500)) < 0.5, \
                f"{where}: the `d` bowl tops out at {R['d_bowl_top']:.2f} (xh 500: {B['d_bowl_top']:.2f}), expected {xh + ov}"
            for k in ("H_top", "O_top", "zero_top", "l_top"):
                assert abs(R[k] - B[k]) < 0.01, f"{where}: {k} moved from {B[k]:.2f} to {R[k]:.2f}; capitals, figures and ascenders do not follow xh"
            assert abs(R["H_top"] - 700) < 0.05 and abs(R["O_top"] - 710) < 1.6 and abs(R["l_top"] - 740) < 0.05, \
                f"{where}: H {R['H_top']}, O {R['O_top']}, l {R['l_top']}"
            assert all(abs(a - b) < 0.01 for a, b in zip(R["apos"], B["apos"])), f"{where}: the apostrophe moved from {B['apos']} to {R['apos']}"
            W = out["W0"] * mult
            rd = W * out["dot"]
            low, high = R["colon"]
            assert abs(low - (rd - 4)) < 0.05 and abs(high - (xh - rd + 4)) < 0.05, \
                f"{where}: the colon's dots are centred at {low:.2f} and {high:.2f}, expected {rd - 4:.2f} and {xh - rd + 4:.2f}"
            assert len(R["i_dot"]) == 1 and abs(R["i_dot"][0] - ymap(680, xh)) < 0.05, f"{where}: the `i` dot is at {R['i_dot']}, expected {ymap(680, xh):.2f}"
            assert R["shape_diff"] is None, f"{where}: {R['shape_diff']!r} has a different polygon or point count than at xh 500"


BRANCH_FIXTURE = r"""
const fs = require("fs"), path = require("path");
const m = require(process.argv[1]);
const cfg = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const concepts = m.loadConcepts(path.resolve(path.dirname(process.argv[2]), cfg.concepts));
let compared = 0; const flips = [];
for (const [gname, group] of Object.entries(cfg.groups)) {
  const italic = group.italic ? (group.italic_angle || 10) : false;
  for (const [mname, spec] of Object.entries(group.masters)) {
    const c0 = m.conceptById(concepts, spec.concept);
    // each master twice: as the project draws it, and with every end but the serif a curl (no shipped face uses curl, so without this
    // variant the curl test is never exercised and a mutation of it survives, as it did on the first run)
    const curl = Object.assign({}, c0.ends); for (const k of Object.keys(curl)) if (k !== "s") curl[k] = "curl";
    for (const [vn, c] of [["as drawn", c0], ["curls", Object.assign({}, c0, { ends: curl, tear: false, dropAmt: undefined })]]) {
     const sigs = {};
     for (const xh of [500, 400, 600]) {
      const P = m.params(Object.assign({}, c, { id: c.id + "|branch" + vn + xh, xh }), spec.mult, italic);
      for (const k of Object.keys(m.G)) {
        const g = m.glyph(k, P); if (!g) continue;
        const s = JSON.stringify(g.sig);
        if (xh === 500) { sigs[k] = s; continue; }
        compared++;
        if (sigs[k] !== s && flips.length < 5) flips.push(gname + "/" + mname + " (" + vn + ") xh " + xh + " " + k + ": " + sigs[k] + " -> " + s);
      }
     }
    }
  }
}
console.log(JSON.stringify({ compared, flips }));
"""


def test_xh_does_not_change_any_branch_record(cfg):
    """Review findings F004 and F005 of the 0.2 plan: a legal xh must not flip a geometry-dependent decision, or the exporter refuses a
    group (or worse, two masters decide differently and interpolate a hybrid). The decisions that enter the branch record (curved, the
    teardrop side, the serif kind, vert, the beak side, partner identity) are taken on the UNMAPPED skeleton, so the whole record is the
    xh 500 record. This draws every key of every master of the project's own groups, roman and italic, at xh 500, 400 and 600, and
    compares each glyph's record. It is also the executable form of the margin measurement (references/generator.md section 12).

    Mutation `xh-branch-mapped`: the serif-kind and vert tests read the drawn tangent instead of the unmapped one."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", BRANCH_FIXTURE, str(SCRIPTS / "gen.js"), str(cfg["_path"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["compared"] > 1000, f"only {out['compared']} glyph records were compared; the fixture is not drawing the project's masters"
    assert not out["flips"], "xh changed a branch record:\n  " + "\n  ".join(out["flips"])


SPACING_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
const base = Object.assign({}, concepts[0]);
const res = { track: base.track || 0, W0: base.W, runs: {} };
for (const xh of [500, 600]) {
  const P = m.params(Object.assign({}, base, { id: "sp" + xh, xh }), 1), r = {};
  for (const k of ["o", "n", "a", "v"]) { const g = m.glyph(k, P); r[k] = { adv: g.adv, polys: g.polys }; }
  r.kern = m.kern(m.glyph("a", P), m.glyph("v", P), P); r.kern_oo = m.kern(m.glyph("o", P), m.glyph("o", P), P);
  res.runs[xh] = r;
}
console.log(JSON.stringify(res));
"""


def band_profile(polys):
    """Per 20-unit bin from y = -260: the leftmost and rightmost x of any polygon point in it (the documented measure, section 8)."""
    L, R = [None] * 54, [None] * 54
    for p in polys:
        for x, y in p:
            b = math.floor((y + 260) / 20)
            if 0 <= b < 54:
                L[b] = x if L[b] is None else min(L[b], x)
                R[b] = x if R[b] is None else max(R[b], x)
    return L, R


def restate_sidebearing(polys, top, W0, track, W=None):
    """The left sidebearing the documented formula gives: bins of 20 from -260, the band [0, top), each bin's depth capped at 0.2 x top,
    T = 30 + 0.36 W0 - 0.25 (W - W0) + track, sbL = max(8, T - mL / 2)."""
    L, R = band_profile(polys)
    xs = [x for p in polys for x, y in p]
    minX = min(xs)
    b0, b1 = math.floor(260 / 20), math.floor((top + 260) / 20)
    cap = 0.2 * top
    mL = sum(min(L[b] - minX, cap) if L[b] is not None else cap for b in range(b0, b1)) / (b1 - b0)
    T = 30 + 0.36 * W0 - 0.25 * ((W or W0) - W0) + track
    return max(8, T - 0.5 * mL)


def restate_kern(a, b, ref, top, W0):
    """The automatic kern of a lowercase pair from the documented rule (section 8): the pair's mean gap over the band against the
    n|n reference, 0.75 of the excess over 8, clamped to -170, capped at -50 when either glyph covers under 35 % of the band, never
    closer than 14 + 0.05 W, and at most 80."""
    def prof(g):
        L, R = band_profile(g["polys"])
        return L, R

    def gap(ga, gb):
        (_, Ra), (Lb, _) = prof(ga), prof(gb)
        s, n, minraw = 0.0, 0, math.inf
        for i in range(54):
            if Ra[i] is None or Lb[i] is None:
                continue
            raw = (ga["adv"] - Ra[i]) + Lb[i]
            minraw = min(minraw, raw)
            if 0 <= -260 + i * 20 < top:
                s += raw
                n += 1
        return (s / n if n else None), minraw

    def cover(g):
        L, _ = prof(g)
        b0, b1 = math.floor(260 / 20), math.floor((top + 260) / 20)
        return sum(1 for i in range(b0, b1) if L[i] is not None) / (b1 - b0)
    rg = gap(ref, ref)[0]
    mean, minraw = gap(a, b)
    k = 0
    if mean is not None and mean - rg > 8:
        k = -0.75 * (mean - rg - 8)
    k = max(k, -170)
    if min(cover(a), cover(b)) < 0.35:
        k = max(k, -50)
    if math.isfinite(minraw):
        k = max(k, 14 + 0.05 * W0 - minraw)
    return min(k, 80)


def test_xh_sets_the_spacing_band(cfg):
    """Spacing follows the x-line: the sidebearing band and the kerning band of a lowercase glyph run from the baseline to xh, not to 500
    (generator.md section 8). Measured in 0.2 on the neutral example at xh 600: the `o` left sidebearing is 52.2 with a band of 500 and
    47.0 with a band of 600, so the property is observable. The `o|o` kern is 0 in both (the gap is the reference gap), so the kern
    half uses `a|v`, which is -49.05 with the band at 600 and -63.12 with it at 500. Both are recomputed here from the output polygons
    and the documented formula, never from the generator's own figures.

    Mutations: `xh-band-500` (the glyph's band stays 500); `xh-kern-band-500` (the kern's band stays 500)."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", SPACING_FIXTURE, str(SCRIPTS / "gen.js"), str(cfg["_concepts"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    W0, track = out["W0"], out["track"]
    for xh in (500, 600):
        run = out["runs"][str(xh)]
        sb = min(x for p in run["o"]["polys"] for x, y in p)  # the glyph is shifted so its leftmost ink sits at the left sidebearing
        want = restate_sidebearing(run["o"]["polys"], xh, W0, track)
        assert abs(sb - want) < 0.05, f"xh {xh}: the `o` left sidebearing is {sb:.3f}, the documented formula over a band of {xh} gives {want:.3f}"
    wrong = restate_sidebearing(out["runs"]["600"]["o"]["polys"], 500, W0, track)
    right = restate_sidebearing(out["runs"]["600"]["o"]["polys"], 600, W0, track)
    assert abs(wrong - right) > 1, f"a band of 500 and of 600 give the same `o` sidebearing ({wrong:.2f}, {right:.2f}); the fixture cannot observe the band"
    run = out["runs"]["600"]
    want_k = restate_kern(run["a"], run["v"], run["n"], 600, W0)
    wrong_k = restate_kern(run["a"], run["v"], run["n"], 500, W0)
    assert abs(want_k - wrong_k) > 1, f"the `a|v` kern is {want_k:.2f} over either band; the fixture cannot observe the kern band"
    assert abs(run["kern"] - want_k) < 0.05, f"xh 600: the `a|v` kern is {run['kern']:.3f}, the documented rule over a band of 600 gives {want_k:.3f}"


def test_xh_outside_its_range_is_refused(cfg):
    """params() throws, naming xh, for a value below 400, above 600, a string or null; the bounds themselves are allowed."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    js = r"""
const m = require(process.argv[1]); const c = m.loadConcepts(process.argv[2])[0], res = {};
for (const v of [399, 601, "500", null, 400, 600]) {
  try { m.params(Object.assign({}, c, { id: "x", xh: v }), 1); res[JSON.stringify(v)] = null; } catch (e) { res[JSON.stringify(v)] = e.message; }
}
console.log(JSON.stringify(res));"""
    r = subprocess.run([node, "-e", js, str(SCRIPTS / "gen.js"), str(cfg["_concepts"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    for v in ("399", "601", '"500"', "null"):
        assert out[v] and "xh" in out[v], f"xh {v}: params() did not refuse it by name: {out[v]!r}"
    assert out["400"] is None and out["600"] is None, f"the bounds 400 and 600 must be allowed: {out['400']!r} {out['600']!r}"


SLAB_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
const base = Object.assign({}, concepts[0], { id: "slab" });
base.ends = Object.assign({}, base.ends, { s: "serif" });
if (base.serifLen === undefined) base.serifLen = 0.5;
if (base.serifH === undefined) base.serifH = 0.6;
const res = { W0: base.W, serifH: base.serifH, serifGrow: base.serifGrow || 0, runs: {} };
for (const mult of [1, 1.5]) for (const b of ["undef", 0, 0.5, 1]) {
  const c = Object.assign({}, base, { id: "slab" + b });
  if (b !== "undef") c.serifBracket = b;
  const P = m.params(c, mult), r = {};
  for (const k of ["I", "n", "v"]) {
    const g = m.glyph(k, P);
    // serif polygons: one edge run, 26 or 15 points (a ball is 64, a ring or a beak is another count)
    r[k] = g.polys.filter((p, i) => g.runs[i].length === 1 && (p.length === 26 || p.length === 15)).map(p => ({ len: p.length, ys: p.map(q => q[1]), pts: p }));
  }
  res.runs[mult + "/" + b] = r;
}
console.log(JSON.stringify(res));
"""


def test_an_unbracketed_serif_is_a_slab_with_the_bracketed_point_count(cfg):
    """Item 4 of the 0.2 plan: `serifBracket` blends each serif construction between today's bracketed form (1) and a slab (0) with the same
    number of points, so a bracket can interpolate between masters. Three constructions are covered (review finding F013 corrected the
    diagonal's count to 26): the foot and symmetric head of `I`, the lowercase head of `n`, and the diagonal serif of `v`. At 0 every point
    of a serif lies between the line and one serif height from it, and both are reached; at 1 the extreme is 1.7 serif heights from the line (1.9 for the lowercase
    head); at 0.5 it is strictly between; the point count is 26, 15 and 26 at all three; and 1 is exactly the polygon with no key set.
    The serif height is restated: SW = W0 (W / W0)^serifGrow, h = SW serifH.

    Mutations: `bracket-ignored` (the blend factor forced to 1); `bracket-count` (the slab drawn as a six-point rectangle); `bracket-diag`
    (the diagonal serif not given the blend)."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", SLAB_FIXTURE, str(SCRIPTS / "gen.js"), str(cfg["_concepts"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    # glyph, point count, the line the serif stands on, the side it grows to (+1 up, -1 down), the extreme in serif heights at 1
    cases = [("I", 26, 0, 1, 1.7), ("I", 26, 700, -1, 1.7), ("n", 15, 500, -1, 1.9), ("n", 26, 0, 1, 1.7), ("v", 26, 500, -1, 1.7)]
    for mult in (1, 1.5):
        W = out["W0"] * mult
        h = out["W0"] * (W / out["W0"]) ** out["serifGrow"] * out["serifH"]
        for glyph, count, line, side, reach in cases:
            def serifs(b, glyph=glyph, count=count, line=line):
                polys = [p for p in out["runs"][f"{mult}/{b}"][glyph] if p["len"] == count and abs(sum(p["ys"]) / len(p["ys"]) - line) < 2 * h]
                assert polys, f"{glyph} at serifBracket {b}, mult {mult}: no {count}-point serif near y {line}"
                return polys
            where = f"{glyph} {count}-point serif at y {line}, mult {mult}"
            for p in serifs(0):
                # the slab's vertical sides are straight segments sampled by quad(), so their points lie between the two lines
                a, z = min(line, line + side * h), max(line, line + side * h)
                assert all(a - 0.05 <= y <= z + 0.05 for y in p["ys"]) and min(p["ys"]) <= a + 0.05 and max(p["ys"]) >= z - 0.05, \
                    f"{where}: at serifBracket 0 the serif spans {min(p['ys']):.2f} to {max(p['ys']):.2f}, expected the slab {a:.2f} to {z:.2f}"
            for b, lo, hi in ((1, reach * h, reach * h), (0.5, h + 0.05, reach * h - 0.05)):
                ext = max(max(abs(y - line) for y in p["ys"]) for p in serifs(b))
                assert lo - 0.05 <= ext <= hi + 0.05, \
                    f"{where}: at serifBracket {b} the extreme is {ext / h:.3f} serif heights from the line, expected {lo / h:.3f} to {hi / h:.3f}"
            for b in ("undef", 0, 0.5, 1):
                assert all(p["len"] == count for p in serifs(b)), f"{where}: the point count changed at serifBracket {b}"
            assert [p["pts"] for p in serifs(1)] == [p["pts"] for p in serifs("undef")], f"{where}: serifBracket 1 is not the polygon with no key set"
    # `slab` really differs from `bracketed`, so the checks above cannot pass on identical polygons
    zero, one = out["runs"]["1/0"]["I"], out["runs"]["1/1"]["I"]
    assert [p["pts"] for p in zero] != [p["pts"] for p in one], "serifBracket 0 draws the same serifs as 1"


def test_serifbracket_outside_zero_to_one_is_refused(cfg):
    """params() throws, naming serifBracket, for -0.01, 1.01, a string and null; 0 and 1 are allowed."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    js = r"""
const m = require(process.argv[1]); const c = m.loadConcepts(process.argv[2])[0], res = {};
for (const v of [-0.01, 1.01, "1", null, 0, 1]) {
  try { m.params(Object.assign({}, c, { id: "x", serifBracket: v }), 1); res[JSON.stringify(v)] = null; } catch (e) { res[JSON.stringify(v)] = e.message; }
}
console.log(JSON.stringify(res));"""
    r = subprocess.run([node, "-e", js, str(SCRIPTS / "gen.js"), str(cfg["_concepts"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    for v in ("-0.01", "1.01", '"1"', "null"):
        assert out[v] and "serifBracket" in out[v], f"serifBracket {v}: params() did not refuse it by name: {out[v]!r}"
    assert out["0"] is None and out["1"] is None, f"the bounds 0 and 1 must be allowed: {out['0']!r} {out['1']!r}"


# --- junctions: joints and crotch (0.2, item 9), and the refused apex ---------------------------------------
JOINTS_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
// the project's first concept with every end a plain butt, so that with `joints` off nothing cuts a joint level and no terminal decides a position
const ends = {}; for (const k of Object.keys(concepts[0].ends)) ends[k] = "butt";
const base = Object.assign({}, concepts[0], { swell: 0, wob: 0, tear: false, overshoot: 10, ends });
delete base.flareAmt; delete base.dropAmt; delete base.joints;
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
function bodies(g) {
  const out = [];
  g.polys.forEach((poly, i) => {
    if (g.runs[i].length !== 2) return;
    const runs = g.runs[i], fl = runs[0][0] !== 0, n = runs[0][1] - runs[0][0] + 1;
    out.push({ poly, n, L: j => fl ? poly[runs[0][1] - j] : poly[runs[0][0] + j], R: j => fl ? poly[runs[1][0] + j] : poly[runs[1][1] - j] });
  });
  return out;
}
const res = {};
for (const mult of [1, 1.5]) for (const joints of ["off", true]) for (const mode of ["", "/disk"]) {
  // "/disk": the shipped sans concepts' mapping, where the empty end (a hidden join) is a disk; the plain variant maps it to a butt
  const c = Object.assign({}, base, { id: "joints" + joints + mode, ends: Object.assign({}, base.ends, mode ? { "": "disk" } : {}) });
  if (joints === true) c.joints = true;
  const P = m.params(c, mult), r = {};
  const V = m.glyph("V", P), v0 = bodies(V)[0], n = v0.n, a = v0.L(n - 1), b = v0.R(n - 1), p = v0.L(n - 3), q = v0.R(n - 3);
  const cx = [(a[0] + b[0]) / 2 - (p[0] + q[0]) / 2, (a[1] + b[1]) / 2 - (p[1] + q[1]) / 2], cl = Math.hypot(cx[0], cx[1]);
  r.V = { yL: a[1], yR: b[1], w: dist(a, b), tx: cx[0] / cl, sig: V.sig[0] };
  const L = bodies(m.glyph("L", P));
  r.L = { stem_min: Math.min(...L[0].poly.map(q => q[1])), base_min: Math.min(...L[1].poly.map(q => q[1])) };
  r.disks = {}; for (const k of ["V", "A", "W", "M", "N", "v", "w"]) r.disks[k] = m.glyph(k, P).polys.filter(p => p.length === 64).length;
  res[mult + "/" + joints + mode] = r;
}
console.log(JSON.stringify(res));
"""


def run_node(cfg, fixture):
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", fixture, str(SCRIPTS / "gen.js"), str(cfg["_concepts"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_joints_opt_in_cuts_a_sans_joint_level(cfg):
    """Item 9 of the 0.2 plan. The level cuts where two stroke ends meet (V W A M N 1 4 v w) and the squared corners (E F L Z z 2 5 7)
    belonged to serif concepts only: for any other concept the V's apex was two stroke ends drawn in whatever `ends[""]` maps. With
    `joints: true` a sans concept gets the same pass. Measured on the project's first concept with every end a butt: with `joints`, both
    edge points of the `V`'s joint end lie on the baseline (a level cut) and its record reads `/joint`, and the `L`'s stem reaches the
    base's outer edge (a squared corner); without it the two edge points differ in y by the stroke's width times the tangent's x
    component (a perpendicular cut, restated from the output polygon), the record has no `joint`, and the stem stops short.

    Also with the shipped sans mapping of the empty end to a disk, where a joint must draw no disk (finding G7 of the Impasse review of 0.2).

    Mutations `joints-ignored` (the pass reads `ends.s` only) and `joints-keep-disk` (a joint keeps its disk)."""
    out = run_node(cfg, JOINTS_FIXTURE)
    for mult in ("1", "1.5"):
        on, off = out[f"{mult}/true"], out[f"{mult}/off"]
        assert abs(on["V"]["yL"]) < 0.05 and abs(on["V"]["yR"]) < 0.05, \
            f"mult {mult}: with joints the V's joint end is at y {on['V']['yL']:.2f} and {on['V']['yR']:.2f}, expected 0 and 0"
        assert "/joint" in on["V"]["sig"], f"mult {mult}: with joints the V's record is {on['V']['sig']!r}, expected an end of `joint`"
        want = off["V"]["w"] * abs(off["V"]["tx"])
        assert want > 10, f"mult {mult}: the fixture's V cut would differ by only {want:.2f} units, too little to observe"
        assert abs(abs(off["V"]["yL"] - off["V"]["yR"]) - want) < 0.05, \
            f"mult {mult}: without joints the V's two edge points differ by {abs(off['V']['yL'] - off['V']['yR']):.2f}, expected width x |T_x| = {want:.2f}"
        assert "joint" not in off["V"]["sig"], f"mult {mult}: without joints the V's record has a joint: {off['V']['sig']!r}"
        assert abs(on["L"]["stem_min"] - on["L"]["base_min"]) < 0.05, \
            f"mult {mult}: with joints the L's stem ends at {on['L']['stem_min']:.2f}, its base's outer edge at {on['L']['base_min']:.2f}"
        assert off["L"]["stem_min"] - off["L"]["base_min"] > 1, \
            f"mult {mult}: without joints the L's stem already reaches the base's outer edge ({off['L']['stem_min']:.2f} vs {off['L']['base_min']:.2f})"
        # the shipped sans concepts map the empty end to a disk (review finding G7): with joints no terminal is drawn at a joint, so the
        # glyphs carry no 64-point disk, the V's joint is still a level cut, and its record still says joint; without joints the disks are drawn
        d_on, d_off = out[f"{mult}/true/disk"], out[f"{mult}/off/disk"]
        # the `A`'s crossbar has two free ends of its own, which keep their disks; every other glyph here is joints only
        want_disks = {"V": 0, "A": 2, "W": 0, "M": 0, "N": 0, "v": 0, "w": 0}
        assert d_on["disks"] == want_disks, \
            f"mult {mult}: with joints and a disk for the empty end, a terminal is still drawn at a joint: {d_on['disks']}, expected {want_disks}"
        assert d_off["disks"]["V"] >= 1 and d_off["disks"]["A"] >= 1, \
            f"mult {mult}: without joints the disk mapping draws no disk on V and A ({d_off['disks']}); the fixture cannot see one"
        assert abs(d_on["V"]["yL"]) < 0.05 and abs(d_on["V"]["yR"]) < 0.05 and "/joint" in d_on["V"]["sig"], \
            f"mult {mult}: with joints and a disk mapping the V's joint end is at y {d_on['V']['yL']:.2f} and {d_on['V']['yR']:.2f}, record {d_on['V']['sig']!r}"


CROTCH_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
const base = Object.assign({}, concepts[0], { swell: 0, wob: 0, tear: false });
base.ends = Object.assign({}, concepts[0].ends, { s: "serif" });
if (base.serifLen === undefined) base.serifLen = 0.5;
if (base.serifH === undefined) base.serifH = 0.6;
if (base.flareAmt === undefined) base.flareAmt = 0.2;
if (base.flareLen === undefined) base.flareLen = 90;
delete base.dropAmt; delete base.crotch;
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
function bodies(g) {
  const out = [];
  g.polys.forEach((poly, i) => {
    if (g.runs[i].length !== 2) return;
    const runs = g.runs[i], fl = runs[0][0] !== 0, n = runs[0][1] - runs[0][0] + 1;
    out.push({ poly, n, L: j => fl ? poly[runs[0][1] - j] : poly[runs[0][0] + j], R: j => fl ? poly[runs[1][0] + j] : poly[runs[1][1] - j] });
  });
  return out;
}
const mid = (b, j) => [(b.L(j)[0] + b.R(j)[0]) / 2, (b.L(j)[1] + b.R(j)[1]) / 2];
const res = { W0: base.W, runs: {} };
const KEYS = Object.keys(m.G);
for (const mult of [1, 1.5]) {
  const build = c => { const P = m.params(Object.assign({}, base, { id: "crotch" + JSON.stringify(c.crotch) + mult }, c), mult); return k => m.glyph(k, P); };
  const g0 = build({ crotch: 0 }), g3 = build({ crotch: 0.3 }), gu = build({});
  const r = { strokes: [], same: {}, minw: {} };
  for (const k of ["V", "A"]) {
    const A = g0(k), B = g3(k), a = bodies(A), b = bodies(B);
    // the crotch token is recorded only when crotch is set, so the acute ends are read from the crotch 0.3 build
    B.sig.forEach((sig, j) => {
      const mm = sig.match(/crotch=(\d)\/(\d)/);
      [["A", mm[1]], ["B", mm[2]]].forEach(([end, v]) => {
        if (v !== "1") return;
        const n = a[j].n, k0 = end === "A" ? 0 : n - 1, step = end === "A" ? 1 : -1, ref = Math.floor(n / 2);
        // the first sample at least eight steps in that the fold pin touched in neither build (the Bold's tighter angle pins the first ones)
        const isPinned = (x, q) => [x.L, x.R].some(E => dist(E(q), E(q - step)) < 1e-9 || dist(E(q), E(q + step)) < 1e-9);
        let s = k0 + 8 * step; while (Math.abs(s - k0) < 40 && (isPinned(a[j], s) || isPinned(b[j], s))) s += step;
        // the partner: another stroke whose end centre is within 3 units of this end's centre; a point 12 samples along it
        let pp = null;
        a.forEach((o, oj) => {
          if (oj === j) return;
          [[0, 1], [o.n - 1, -1]].forEach(([ok, os]) => { if (!pp && dist(mid(o, ok), mid(a[j], k0)) < 3) pp = mid(o, ok + 12 * os); });
        });
        const shift = [b[j].L(ref)[0] - a[j].L(ref)[0], b[j].L(ref)[1] - a[j].L(ref)[1]];
        const al = p => [p[0] - shift[0], p[1] - shift[1]];
        const chain = []; for (let q = s; q !== k0 + step * -1; q -= step) chain.push(mid(a[j], q));
        const pinned = isPinned(a[j], s) || isPinned(b[j], s);
        r.strokes.push({ glyph: k, stroke: j, end, L0: a[j].L(s), R0: a[j].R(s), L3: al(b[j].L(s)), R3: al(b[j].R(s)), partner: pp, chain, pinned,
          refShift: Math.hypot(...shift), refW: [dist(a[j].L(ref), a[j].R(ref)), dist(b[j].L(ref), b[j].R(ref))] });
      });
    });
    r.minw[k] = [A.minw, B.minw];
  }
  // c: glyphs with no acute joint (a stem, an arch, corners) are identical at 0 and 0.3; e: crotch 0 is the crotch-undefined glyph, for every key
  ["l", "n", "E", "F", "L", "T", "H", "š", "ê", "Ô"].forEach(k => { r.same[k] = JSON.stringify(g0(k).polys) === JSON.stringify(g3(k).polys); });
  let unsetSame = true; for (const k of KEYS) { const a = g0(k), b = gu(k); if (a && JSON.stringify(a.polys) !== JSON.stringify(b.polys)) unsetSame = false; }
  r.unsetSame = unsetSame;
  r.acute = KEYS.filter(k => { const g = g3(k); return g && g.sig.some(s => /crotch=1\/|crotch=\d\/1/.test(s)); });
  res.runs[mult] = r;
}
console.log(JSON.stringify(res));
"""


def test_crotch_thins_only_the_inner_edge_of_an_acute_joint(cfg):
    """Item 9 of the 0.2 plan. `crotch` thins, over the last 1.1 W0 of an arm that ends in an acute JOINT (the V and A's apex), only the edge
    on the partner's side, by `crotch x e` of the half width, with e the smoothstep of the sample's distance from the end. The outer
    edge keeps its line and the counter opens. Measured at the first sample at least eight steps before the joint end that the fold pin left alone (the Bold's tighter
    angle pins the first ones), on the `V`'s and the `A`'s arms,
    mult 1 and 1.5, with the build re-aligned on a sample far from the joint (the sidebearing shifts): the edge nearer the partner arm
    (found from the partner's output, not from the generator) moved inward by 0.3 e (w / 2), e restated from the arc distance
    read off the output centre line (within 2 %); the other edge did not move (under 1e-6); `l`, `n`, the corners of `E F L T H` and the
    right-angled joints of the caron and circumflex (`š ê Ô`) are identical at 0 and 0.3; the hairline minimum of `V` and `A` is unchanged (the teardrop's reach
    keeps it out of the
    floor); and crotch 0 draws every glyph exactly as no key.

    Mutations: both edges thin; every end thins (no acute test, no partner); a corner counts as a joint; the reach grows to 2 W0."""
    out = run_node(cfg, CROTCH_FIXTURE)
    W0 = out["W0"]
    for mult in ("1", "1.5"):
        r = out["runs"][mult]
        for k, same in r["same"].items():
            assert same, f"mult {mult}: {k} differs between crotch 0 and 0.3, but it has no acute joint"
        for k, (m0, m3) in r["minw"].items():
            assert abs(m0 - m3) < 1e-9, \
                f"mult {mult}: {k} hairline minimum is {m0:.3f} at crotch 0 and {m3:.3f} at 0.3; the crotch must stay outside the floor's interior"
        assert r["unsetSame"], f"mult {mult}: crotch 0 draws a glyph differently from no crotch key"
        # the glyphs whose records name an acute joint: the end-to-end joints of the plan's survey (1 4 5 v w A M N V W), the trademark sign's
        # diagonals and the composites that carry an A or an N. A corner (2 3 7 z B Z) counted as a joint would add six keys.
        want_acute = sorted("1 4 5 v w A M N V W ™ Á À Â Ä Ñ".split())
        assert sorted(r["acute"]) == want_acute, f"mult {mult}: glyphs with an acute joint in their record: {sorted(r['acute'])}, expected {want_acute}"
        found = {(s["glyph"], s["end"]) for s in r["strokes"]}
        assert len(r["strokes"]) >= 2 and {"V", "A"} <= {g for g, _ in found}, f"mult {mult}: the records name no acute joint on V and A: {sorted(found)}"
        for s in r["strokes"]:
            where = f"mult {mult} {s['glyph']} stroke {s['stroke']} end {s['end']}"
            assert not s["pinned"], f"{where}: the sample is on a pinned point"
            assert abs(s["refW"][0] - s["refW"][1]) < 1e-6, f"{where}: the reference sample's width changed; the re-alignment is wrong"
            assert s["partner"], f"{where}: no partner arm found in the output"
            L0, R0 = s["L0"], s["R0"]
            near_left = math.dist(L0, s["partner"]) < math.dist(R0, s["partner"])
            ctr = [(L0[0] + R0[0]) / 2, (L0[1] + R0[1]) / 2]
            w = math.dist(L0, R0)
            d = sum(math.dist(p, q) for p, q in zip(s["chain"], s["chain"][1:]))
            u = 1 - d / (1.1 * W0)
            e = u * u * (3 - 2 * u)
            want = 0.3 * e * (w / 2)
            assert 0 < u < 1 and want > 5, f"{where}: the sample (distance {d:.1f}) is outside the thinning reach or the thinning ({want:.2f}) is too small to observe"
            crotch, outer = (s["L3"], s["R3"]) if near_left else (s["R3"], s["L3"])
            crotch0, outer0 = (L0, R0) if near_left else (R0, L0)
            moved = math.dist(crotch, crotch0)
            assert abs(moved - want) <= 0.02 * want + 1e-6, f"{where}: the crotch-side edge moved {moved:.3f}, expected 0.3 x {e:.3f} x w/2 = {want:.3f}"
            assert abs(math.dist(crotch, ctr) - (w / 2 - want)) < 0.02 * want + 1e-6, f"{where}: the crotch-side edge did not move inward by {want:.3f}"
            assert math.dist(outer, outer0) < 1e-6, f"{where}: the outer edge moved by {math.dist(outer, outer0):.6f}"


def test_apex_is_refused_until_built(cfg):
    """`apex` (a pointed apex) is designed, not built, in 0.2: the plan's own arithmetic shows one depth rule cannot serve the `A` and the
    `M` (the Bold `M`'s crotch would reach y = 26). A knob that does nothing is the dead-knob shape of issue #24, so params() throws, naming
    `apex` and the section of references/generator.md that holds the design. Also: `joints` must be a boolean and `crotch` a number from 0
    to 0.6.

    Mutation `apex-accepted`: the throw is removed."""
    node = shutil.which("node")
    assert node, "node is not on PATH"
    js = r"""
const m = require(process.argv[1]); const c = m.loadConcepts(process.argv[2])[0], res = {};
const tries = {
  apex: [["apex", 10]], joints: [["joints", "yes"], ["joints", 1], ["joints", true], ["joints", false]],
  crotch: [["crotch", -0.1], ["crotch", 0.61], ["crotch", "0.2"], ["crotch", null], ["crotch", 0.6], ["crotch", 0]],
};
for (const [name, list] of Object.entries(tries)) for (const [k, v] of list) {
  try { m.params(Object.assign({}, c, { id: "x", [k]: v }), 1); res[k + "=" + JSON.stringify(v)] = null; } catch (e) { res[k + "=" + JSON.stringify(v)] = e.message; }
}
console.log(JSON.stringify(res));"""
    r = subprocess.run([node, "-e", js, str(SCRIPTS / "gen.js"), str(cfg["_concepts"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["apex=10"] and "apex" in out["apex=10"] and "generator.md" in out["apex=10"], f"apex was not refused naming apex and generator.md: {out['apex=10']!r}"
    for case in ('joints="yes"', "joints=1", "crotch=-0.1", "crotch=0.61", 'crotch="0.2"', "crotch=null"):
        assert out[case] and case.split("=")[0] in out[case], f"{case}: params() did not refuse it by name: {out[case]!r}"
    for case in ("joints=true", "joints=false", "crotch=0.6", "crotch=0"):
        assert out[case] is None, f"{case} must be allowed: {out[case]!r}"


STRESS_FIXTURE = r"""
const m = require(process.argv[1]);
const concepts = m.loadConcepts(process.argv[2]);
const S = m.S;
// a deterministic generator (mulberry32), so a failure names a glyph that can be drawn again
let seed = 20261116;
function rnd() {
  seed = (seed + 0x6D2B79F5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
const pick = a => a[Math.floor(rnd() * a.length)], between = (a, b) => a + (b - a) * rnd();
// angles from the horizontal, in degrees, clustered on the decisions' own thresholds: a level stroke (the beak gate, 0.5 unit), 30 degrees
// (|T_y| = 0.5, vert), 5.7 degrees off plumb (|T_x| = 0.1, the serif kind) and anything
const ANGLES = [() => between(-0.2, 0.2), () => between(28, 32) * pick([-1, 1]), () => 90 - between(4, 7.5) * pick([-1, 1]), () => between(0, 180)];
const f = v => +v.toFixed(2);
function stroke(x, y, deg, len, endsA, endsB) {
  const a = deg * Math.PI / 180, x1 = x + Math.cos(a) * len, y1 = y + Math.sin(a) * len;
  if (rnd() < 0.3) { // a cubic bowed by up to 12 units, either way
    const b = between(-12, 12), c = Math.cos(a), n = Math.sin(a);
    const p1 = [x + c * len / 3 - n * b, y + n * len / 3 + c * b], p2 = [x + c * 2 * len / 3 + n * b, y + n * 2 * len / 3 - c * b];
    return [S(`M ${f(x)} ${f(y)} C ${f(p1[0])} ${f(p1[1])} ${f(p2[0])} ${f(p2[1])} ${f(x1)} ${f(y1)}`, endsA, endsB), x1, y1];
  }
  return [S(`M ${f(x)} ${f(y)} L ${f(x1)} ${f(y1)}`, endsA, endsB), x1, y1];
}
const FLAGS = ["", "s", "t", "u", "x", "j"];
const KEYS = [];
// the last 150: a stroke that ends within 30 units of the x-line on a slight bow, so the curl's tail (the last 16 samples) straddles the
// x-line and the drawn cross product can take the opposite sign of the unmapped one (finding R1: the handedness of the spiral)
for (let i = 500; i < 650; i++) {
  const a = between(20, 80), len = 220, ey = between(485, 530), ex = between(200, 420), c = Math.cos(a * Math.PI / 180), n = Math.sin(a * Math.PI / 180);
  const key = "\u0298" + i, [s0] = stroke(ex - c * len, ey - n * len, a, len, "", "t");
  m.G[key] = [s0]; KEYS.push(key);
}
for (let i = 0; i < 500; i++) {
  const key = "ʘ" + i, strokes = [];
  let x = between(60, 400), y = between(20, 680);
  const [s0, x1, y1] = stroke(x, y, ANGLES[i % 4](), between(120, 420), pick(FLAGS), pick(["", "", "j"]));
  strokes.push(s0);
  if (rnd() < 0.6) { // a partner: another stroke that starts within 1-3 units of the first's end, the 2-unit pairing threshold between
    const off = between(1, 3) * pick([-1, 1]), [s1] = stroke(x1, y1 + off, ANGLES[(i + 1) % 4](), between(120, 420), pick(["", "j"]), pick(FLAGS));
    strokes.push(s1);
  }
  m.G[key] = strokes; KEYS.push(key);
}
const base = Object.assign({}, concepts[0], { swell: 0, wob: 0, tear: false });
delete base.dropAmt;
const flare = { s: "serif", t: "flare", u: "flare", x: "exit", "": "disk", j: "disk" };
const VARIANTS = {
  serif: { ends: Object.assign({}, flare), overshoot: 10 },
  beak: { ends: Object.assign({}, flare, { s: "butt" }), beak: true, overshoot: 0, flareAmt: 0.2, flareLen: 90 },
  curl: { ends: { s: "serif", t: "curl", u: "curl", x: "curl", "": "disk", j: "curl" }, overshoot: 10 },
  tear: { ends: Object.assign({}, flare), tear: true, dropAmt: 0.55, overshoot: 10, flareAmt: undefined },
  joints: { ends: { s: "butt", t: "flare", u: "disk", x: "butt", "": "disk", j: "disk" }, joints: true, crotch: 0.3, overshoot: 10, flareAmt: 0.2, flareLen: 90 },
};
const res = { flips: [], compared: 0, seen: { beak: 0, partner: 0, curled: 0, tear: 0, joint: 0, corner: 0, curved: 0, serifDiag: 0, crotch: 0 } };
for (const [vn, v] of Object.entries(VARIANTS)) for (const it of [false, 12]) {
  const sigs = {};
  for (const xh of [500, 400, 600]) {
    const c = Object.assign({}, base, v, { id: "stress" + vn + xh + it, xh });
    if (c.flareAmt === undefined) delete c.flareAmt;
    const P = m.params(c, 1, it);
    for (const k of KEYS) {
      const g = m.glyph(k, P), s = JSON.stringify(g.sig);
      if (xh === 500) {
        sigs[k] = s;
        if (/beak[AB]=[1-9]/.test(s)) res.seen.beak++;
        if (/joins=\d|\/\d[ab]/.test(s)) res.seen.partner++;
        if (/ends=curl|curl\//.test(s)) res.seen.curled++;
        if (/tearcap/.test(s)) res.seen.tear++;
        if (/\/joint|joint\//.test(s)) res.seen.joint++;
        if (/\/corner|corner\//.test(s)) res.seen.corner++;
        if (/curved=true/.test(s)) res.seen.curved++;
        if (/serif[AB]=diag/.test(s)) res.seen.serifDiag++;
        if (/crotch=1|\/1"/.test(s)) res.seen.crotch++;
      } else {
        res.compared++;
        if (sigs[k] !== s && res.flips.length < 6) res.flips.push(vn + (it ? " italic" : "") + " xh " + xh + " " + k + ": " + sigs[k] + " -> " + s);
      }
    }
  }
}
console.log(JSON.stringify(res));
"""


def test_no_decision_reads_a_mapped_coordinate(cfg):
    """The general guard behind `test_xh_does_not_change_any_branch_record` (Impasse review of 0.2, findings G1 and G2: the beak gate and the
    partner pairing read the drawn points, and only a stroke 0.45 units off level, or two ends 1.8 apart, could show it). The project's own
    glyphs sit far from every threshold, so this draws 500 synthetic glyphs with a fixed seed, built to sit ON them: strokes level to within
    0.2 degrees (the beak gate's 0.5 unit), at 30 degrees (`vert`), 5.7 degrees off plumb (the serif kind), curved by up to 12 units, and a
    second stroke starting 1-3 units from the first's end (the 2-unit pairing), in five concepts (serif, beak with flare ends, curl, teardrop,
    sans with `joints`), roman and slanted, and compares every glyph's branch record at xh 500, 400 and 600. It counts the decisions it reached,
    so a generator that stops reaching them is a failure and not a pass.

    Mutations: the beak gate reads the drawn points; the pairing reads the drawn endpoints."""
    out = run_node(cfg, STRESS_FIXTURE)
    assert out["compared"] >= 10000, f"only {out['compared']} glyph records were compared"
    seen = out["seen"]
    floors = {"beak": 30, "partner": 300, "curled": 30, "tear": 100, "joint": 100, "corner": 100, "curved": 150, "serifDiag": 100, "crotch": 30}
    for name, floor in floors.items():
        assert seen[name] >= floor, \
            f"the stress glyphs reached the `{name}` decision only {seen[name]} times (expected at least {floor}); the generator no longer exercises it"
    assert not out["flips"], "xh changed a branch record on a synthetic glyph:\n  " + "\n  ".join(out["flips"])


def test_open_curve_extremes_stay_within_the_documented_bound_of_the_overshoot(cfg):
    """Impasse review of 0.2, finding G3: the round fit gives every round extreme the half width of a fully weighted curve, which is exact for a
    ring (the `o` lands on its overshoot) and not for an open curve, whose weight at the extreme is below 1 (about 0.6 on the fitted `c`). The
    top of an open curve (`c`, `e`, `s`) therefore sits off its target by `hw |roundGain - 1| (1 - cw)` at most, where `hw` is the level half
    width `W f(0) hzThin / 2`: generator.md states that bound. Measured on the monoline fixture (f(0) = 1) as the shift of each top from the
    same glyph without roundGain, at roundGain 1.05, 0.85 (a gain below 1) and 1.05 with hzThin 1.4 (the level factor multiplies the gain
    term), and held to `(W / 2) hzThin |roundGain - 1|` plus 0.1; the shifts are not all zero, so the check can see a fit that is off.

    Mutation `optical-fit-overcorrect`: round extremes are fitted with a weight of 2, which doubles the error of an open curve."""
    both = run_optical(cfg)
    out, W0 = both["variants"], both["W0"]
    # (variant, the same without roundGain, the level factor hzThin, roundGain)
    for vn, base, hz, rg in (("round", "none", 1.0, 1.05), ("roundLow", "none", 1.0, 0.85), ("hzHighRound", "hzHigh", 1.4, 1.05)):
        for mult in ("1", "1.5"):
            W = W0 * float(mult)
            bound = (W / 2) * hz * abs(rg - 1)
            shifts = {k: out[vn][mult]["tops"][k] - out[base][mult]["tops"][k] for k in ("c", "e", "s")}
            for k, v in shifts.items():
                assert abs(v) <= bound + 0.1, \
                    f"{vn} at mult {mult}: the `{k}` top shifted by {v:.2f}, beyond the bound {bound:.2f} = (W / 2) hzThin |roundGain - 1|"
            assert max(abs(v) for v in shifts.values()) > 0.3, f"{vn} at mult {mult}: no open-curve top moved ({shifts}); the check cannot see a fit that is off"



RECORD_FIXTURE = r"""
const fs = require("fs"), path = require("path");
const m = require(process.argv[1]);
const cfg = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const concepts = m.loadConcepts(path.resolve(path.dirname(process.argv[2]), cfg.concepts));
const out = { unset: [], withCrotch: [] };
for (const [gname, group] of Object.entries(cfg.groups)) {
  const italic = group.italic ? (group.italic_angle || 10) : false;
  for (const [mname, spec] of Object.entries(group.masters)) {
    const c = m.conceptById(concepts, spec.concept);
    if (c.crotch) continue; // a project that sets crotch records it, by design
    const P = m.params(c, spec.mult, italic), Q = m.params(Object.assign({}, c, { id: c.id + "|crotch", crotch: 0.3 }), spec.mult, italic);
    for (const k of Object.keys(m.G)) {
      const g = m.glyph(k, P), h = m.glyph(k, Q);
      if (g) out.unset.push(...g.sig);
      if (h) out.withCrotch.push(...h.sig);
    }
  }
}
console.log(JSON.stringify(out));
"""


def test_an_unset_crotch_leaves_the_0_1_branch_record(cfg):
    """Impasse re-review, finding R2: recording `crotch=a/b` on every open stroke would make 0.2 refuse a 0.1 project whose masters fall on
    opposite sides of the new acute test, although nothing is thinned. The token is written only when `crotch` is set. With it unset,
    every stroke of every master of the project's own groups matches the 0.1 grammar (open or ring, sample count, both ends, curved, taper,
    teardrop sides, partners, end outcomes, then beak, teardrop cap and serif tokens), plus the one documented 0.2 token, the handedness of
    a curl (`curlsg`, which only a curl end writes); with `crotch` 0.3 the token is there. The baseline digests exclude the record, so this
    is the direct assertion.

    Mutation `crotch-token-always`: the token is written whether or not crotch is set."""
    import re
    node = shutil.which("node")
    assert node, "node is not on PATH"
    r = subprocess.run([node, "-e", RECORD_FIXTURE, str(SCRIPTS / "gen.js"), str(cfg["_path"])], cwd=SCRIPTS, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    old = re.compile(r"(dot|ring n=\d+ A=\S* B=\S* curved=false tap=00 tear=null/null joins=-/-"
                     r"|open n=\d+ A=\S* B=\S* curved=(true|false) tap=[01]{2} tear=\S+/\S+ joins=\S+/\S+ ends=\S+/\S+"
                     r"( beak[AB]=\d+| tearcap[AB]| serif[AB]=\w+)*( curlsg=-?\d/-?\d)?)")
    assert len(out["unset"]) > 1000, f"only {len(out['unset'])} records were read; the fixture is not drawing the project's masters"
    bad = [s for s in out["unset"] if not old.fullmatch(s)]
    assert not bad, f"{len(bad)} records are not in the 0.1 form with crotch unset; first: {bad[0]!r}"
    assert any(re.search(r" crotch=(1/\d|\d/1)( |$)", s) for s in out["withCrotch"]), "crotch 0.3 recorded no acute joint on any stroke"
    assert sum(" crotch=" in s for s in out["withCrotch"]) > 100, "crotch 0.3 does not record the token on the open strokes"
