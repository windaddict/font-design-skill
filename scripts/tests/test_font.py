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
