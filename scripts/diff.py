#!/usr/bin/env python3
"""Pixel-diffs two builds of a face: every title, at every review size, at every named instance.

WHAT IT'S FOR: the design-review loop changes the font between rounds (a parameter, a skeleton, a kern) and a
fresh reviewer who has not seen the previous round cannot tell what moved. The suite proves the font is valid and
a screenshot proves what one build looks like; neither shows what a change did to the words the site really sets.
This tool renders the project's titles (font.json `titles`, plus `review.wordmark` when set) at every size in
`review.sizes` and at every named instance of every group, from a BEFORE folder (the previous round's build) and an
AFTER folder (the current build), and writes which renders changed, by how much, and a before / after / diff
picture of each one that did. The reviewer reads `diff.md` first and looks only where the words moved.

    diff.py OUT_DIR --font font.json --before DIR [--after DIR] [--sizes PX ...] [--scale N]

OUT_DIR gets `diff.json` (every render: group, instance, size, title, changed_px, share, bbox, both advance widths,
the files compared per group, the by-value result per group, and the renderer, versions, layout engine and hinting line),
`diff.md` (the changed renders, largest share first, then how many are unchanged, then a `## By value` section) and one PNG per
CHANGED render named `<group>-<instance>-<size>px-<title>.png`: the before render (black on white), the after render, and the
diff (red where the after render has more ink, blue where it has less, grey where both have ink and agree), stacked. Use a fresh
OUT_DIR per round: a PNG left from an earlier run is not removed.

Where the group files are. --before is a folder holding the previous build's group files under their FILE NAMES: the name
`build.py` writes, which is the name part of the group's `file` key when it has one (`build.py --out-dir` writes exactly
these), so a `file` such as `../../static/fonts/F-VF.woff2` is looked up as `F-VF.woff2` and never walks out of the folder.
--after is the same kind of folder; when it is omitted the after side is the shipped files, where font.json puts them. Two groups
whose files share a name would be one file under --before and --after, so the run refuses them (exit 2, both groups named). Copy
`out/` to `work/round-N/` with `cp -R` before each build. Exit 0 whether or not anything changed; exit 2 when --before or
--after lacks a group's file (each missing path is named), when two groups share a file name, or when a group of font.json has
no `instances`; exit 1 when this Pillow lacks the raqm layout engine or a dependency is missing.

The by-value section. A pixel render cannot show a change no title exercises, so each group's two files are also compared by
VALUE, and every difference is listed: glyph order and cmap (every subtable, format 14 included); per common glyph the default
outline with its instructions, every gvar tuple and the hmtx record; the instanced outline and advance at every named instance of
the group (the locations in font.json, so a group with any axes works); `fvar`, `avar`, `STAT`, `GSUB`, `gasp`, `prep`, `fpgm` and
`cvt ` as ttx text; `maxp`'s hinting limits; GPOS pair adjustments by resolved value and the script, feature and lookup
structure; GDEF's classes; HVAR advance deltas by region; the platform-3 name records; `hhea`, `OS/2` and `head` (without
`checkSumAdjustment` and `modified`) field by field; and kerning as HarfBuzz (uharfbuzz) applies it to every two-character
string of the characters both fonts map, at every named instance (N mapped characters make N*N strings per instance, so the
time grows with the square of the character set). It lists every difference and allows none: the reader judges.
It does not compare GPOS or GSUB bytes, GPOS lookups other than pair adjustment beyond their type and flag, rasters, woff2 bytes,
or strings longer than two characters.

How a render is made. The woff2 is read by fontTools and instanced at the instance's location with
`fontTools.varLib.instancer` (what `build.py --static` uses, so what is drawn is what a static font would be), given a
one-instruction `fpgm`, saved to a temporary TrueType file and drawn by Pillow with the raqm layout engine (so GPOS
kerning and `liga` apply), baseline-anchored, grey-antialiased, at size x --scale pixels (default 2) on canvases
of identical size for the two builds. The `fpgm` is the same trick build.py's raster self-checks use
(`raster_font_file`): FreeType autohints a TrueType font that has no font program, and the shipped fonts have none
(measured 2026-11-16: the neutral roman renders the same with its `prep` deleted and differs by 212 to 255 grey
levels once a one-instruction `fpgm` is added, `B` at 16 px, a title at 16 and 40 px). The autohinter moves whole
glyphs by a pixel on tiny outline changes, which is exactly the noise a before / after comparison must not contain.
A pixel counts as changed when its grey level differs by more than 8 of 255, and a render also counts as changed when the title's advance
width differs by more than 0.02 CSS px (a last glyph's advance can move with no ink moving). The canvas holds both builds' full ink
bounds, so a contour moved outside the line box is not clipped. `share` is changed_px divided by the
pixels where either render has ink (grey level under 247), 0 when neither has any.

Exact guarantee: what FreeType drew on this machine from the two files, unhinted, at these sizes and instances. It
is not CoreText, not Chrome and not the page's CSS (no `font-feature-settings`, no letter-spacing, no
`text-rendering`), it renders only the project's own titles, and it says nothing about another machine. A change
the titles do not exercise (a glyph none of them uses) does not show here.
Copyright 2026 John Knox. MIT licence.
"""
import argparse
import io
import json
import pathlib
import re
import sys
import tempfile

if sys.version_info < (3, 10):
    sys.exit(f"diff.py needs Python >= 3.10 and this is {sys.version_info[0]}.{sys.version_info[1]}; make the skill's venv with a newer one: "
             "python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt, then run .venv/bin/python3 scripts/diff.py ...")

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import specimen  # noqa: E402  (its default_font_file() is build.py's output naming, kept in one place)

THRESHOLD = 8  # grey levels of 255 a pixel must differ by to count as changed
INK_BELOW = 247  # a pixel darker than this has ink (255 - 8)
GAP = 4  # px between the three panels of a PNG
ADVANCE_TOL = 0.02  # CSS px: an advance width that differs by more than this counts as a change even when no pixel moved
HINTING = "autohint suppressed by a one-instruction fpgm (trap 2)"


def need(*names):
    """Import the heavy dependencies lazily so a wrong interpreter names the install command, not a traceback."""
    try:
        import importlib
        return [importlib.import_module(n) for n in names]
    except ImportError as exc:
        sys.exit(f"diff.py cannot import {exc.name or 'a required package'} ({exc}); this interpreter ({sys.executable}) is not the skill's venv. "
                 "Install the requirements into a venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt, "
                 "then run .venv/bin/python3 scripts/diff.py ...")


def require_raqm():
    (features,) = need("PIL.features")
    if not features.check("raqm"):
        sys.exit("diff.py needs a Pillow built with the raqm layout engine, so that GPOS kerning applies and a kern change shows; this "
                 f"Pillow ({sys.executable}) lacks it. Install the pinned one: .venv/bin/pip install -r requirements.txt (requirements.txt names pillow; "
                 "the wheels carry raqm)")


def with_fpgm(font):
    """Give `font` (a TTFont) a one-instruction font program, SVTCA[0], so FreeType takes the bytecode path and does not
    autohint. Returns the font."""
    (tt,) = need("fontTools.ttLib")
    (prog,) = need("fontTools.ttLib.tables.ttProgram")
    fpgm = tt.newTable("fpgm")
    fpgm.program = prog.Program()
    fpgm.program.fromBytecode(b"\x00")
    font["fpgm"] = fpgm
    return font


def instance_file(woff2, location, out_path, hinted=False):
    """Writes the static instance of the variable font at `woff2`, at `location` (user-space axis values; an axis the
    location omits stays at its default), as a TrueType file at `out_path`. Unless `hinted`, it carries the
    one-instruction fpgm that stops FreeType autohinting it. Returns `out_path`. `hinted=True` exists so a test can render the
    same instance the way plain Pillow would."""
    (tt,) = need("fontTools.ttLib")
    (inst,) = need("fontTools.varLib.instancer")
    font = tt.TTFont(str(woff2))
    full = {a.axisTag: a.defaultValue for a in font["fvar"].axes} if "fvar" in font else {}
    unknown = sorted(set(location) - set(full))
    if unknown:
        raise ValueError(f"{woff2}: the instance location names axes the font lacks: {unknown}")
    full.update(location)
    static = inst.instantiateVariableFont(font, full, inplace=False)
    static.flavor = None
    if not hinted:
        with_fpgm(static)
    static.save(str(out_path))
    return out_path


def load_pil_font(path, px):
    """The Pillow font at `px` pixels using the raqm layout engine."""
    (image_font,) = need("PIL.ImageFont")
    return image_font.truetype(str(path), px, layout_engine=image_font.Layout.RAQM)


def layout_name(font):
    (image_font,) = need("PIL.ImageFont")
    return "raqm" if font.layout_engine == image_font.Layout.RAQM else "basic"


def canvas_for(fonts, text, px):
    """(width, height, baseline, x0) of a canvas that holds `text` in every font of `fonts` (the same canvas for both builds):
    the union of every font's INK bounds (`getbbox` with the baseline anchor, so a contour moved far above the ascender or past
    the advance is inside it, not clipped before compare() sees it), of the advance width and of the line's ascent and
    descent, plus a margin all round. `x0` is where the pen starts, `baseline` where the baseline sits."""
    margin = max(4, round(px * 0.25))
    boxes = [f.getbbox(text, anchor="ls") for f in fonts]
    left = min([0] + [b[0] for b in boxes])
    right = max([int(f.getlength(text)) + 1 for f in fonts] + [b[2] for b in boxes])
    top = min([-f.getmetrics()[0] for f in fonts] + [b[1] for b in boxes])
    bottom = max([f.getmetrics()[1] for f in fonts] + [b[3] for b in boxes])
    return right - left + 2 * margin, bottom - top + 2 * margin, margin - top, margin - left


def draw(font, text, size, baseline, margin):
    """`text` in black on white, left edge at `margin`, baseline at `baseline`, grey antialiasing."""
    (image,) = need("PIL.Image")
    (image_draw,) = need("PIL.ImageDraw")
    im = image.new("L", size, 255)
    image_draw.Draw(im).text((margin, baseline), text, font=font, fill=0, anchor="ls")
    return im


def compare(a, b):
    """(changed_px, share, bbox, masks) of two same-size L images. bbox is [left, top, right, bottom] in render pixels, or None."""
    (chops,) = need("PIL.ImageChops")
    changed = chops.difference(a, b).point(lambda v: 255 if v > THRESHOLD else 0)
    ink = chops.darker(a, b).point(lambda v: 255 if v < INK_BELOW else 0)
    n_changed, n_ink = changed.histogram()[255], ink.histogram()[255]
    bbox = changed.getbbox()
    return n_changed, (n_changed / n_ink if n_ink else 0.0), (list(bbox) if bbox else None)


def triptych(a, b):
    """before, after and the diff stacked: red where `b` has more ink than `a`, blue where less, grey where both have ink and agree."""
    (image,) = need("PIL.Image")
    (chops,) = need("PIL.ImageChops")
    ink_a, ink_b = a.point(lambda v: 255 - v), b.point(lambda v: 255 - v)
    red = chops.subtract(ink_b, ink_a).point(lambda v: 255 if v > THRESHOLD else 0)
    blue = chops.subtract(ink_a, ink_b).point(lambda v: 255 if v > THRESHOLD else 0)
    both = chops.darker(ink_a, ink_b).point(lambda v: 255 if v > THRESHOLD else 0)
    d = image.new("RGB", a.size, (255, 255, 255))
    d.paste((170, 170, 170), mask=both)
    d.paste((220, 40, 40), mask=red)
    d.paste((40, 80, 220), mask=blue)
    w, h = a.size
    sheet = image.new("RGB", (w, 3 * h + 2 * GAP), (120, 120, 120))
    for i, im in enumerate((a.convert("RGB"), b.convert("RGB"), d)):
        sheet.paste(im, (0, i * (h + GAP)))
    return sheet


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def group_files(cfg, font_json, before, after):
    """{group: (file name, before path, after path)}: where each group's woff2 lives under each folder. The name is the one
    build.py writes (`specimen.default_font_file`, then its name part), so a group with a `file` key such as
    `../../static/F-VF.woff2` is found as `F-VF.woff2` under --before and --after, as `build.py --out-dir` writes it. When `after`
    is None the after side is the shipped file where font.json puts it (resolved). Exits 2 naming both groups when two groups
    share a file name, because they would be one file under a folder and one group would be compared with the other's font."""
    names, out = {}, {}
    for name in cfg["groups"]:
        shipped = specimen.default_font_file(cfg, font_json, name)
        names.setdefault(shipped.name, []).append(name)
        out[name] = (shipped.name, before / shipped.name, shipped.resolve() if after is None else after / shipped.name)
    for fname, groups in names.items():
        if len(groups) > 1:
            sys.stderr.write(f"diff.py: the groups {' and '.join(groups)} share the file name {fname}, so under --before and --after they "
                             "would be one file and one group would be compared with the other's font; give each group a distinct file name\n")
            sys.exit(2)
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# The by-value comparison: what differs between two builds of a group's font, in values a reader or a browser would see.
# ---------------------------------------------------------------------------------------------------------------------------

MAXP_HINTING = ("maxZones", "maxTwilightPoints", "maxStorage", "maxFunctionDefs", "maxInstructionDefs", "maxStackElements", "maxSizeOfInstructions")
VALUE_LINES_IN_MD = 200  # diff.md lists this many differences per group; diff.json holds them all


def ttx_text(font, tag):
    """The table as ttx XML, or None when the font lacks it."""
    if tag not in font:
        return None
    (xml,) = need("fontTools.misc.xmlWriter")
    buf = io.BytesIO()
    w = xml.XMLWriter(buf, newlinestr="\n")
    font[tag].toXML(w, font)
    w.close()
    return buf.getvalue().decode("utf-8")


def outline(font, name):
    """A glyph's default outline as comparable data: components, or coordinates, end points and flags, plus its TrueType
    instructions (hinting changes pixels without moving a point)."""
    g = font["glyf"][name]
    program = bytes(g.program.getBytecode()) if hasattr(g, "program") else b""
    if g.isComposite():
        return ("composite", tuple((c.glyphName, c.x, c.y, getattr(c, "transform", None) is not None and tuple(map(tuple, c.transform)))
                                   for c in g.components), program)
    coords, ends, flags = g.getCoordinates(font["glyf"])
    return ("simple", tuple(coords), tuple(ends), tuple(flags), program)


def variations(font, name):
    """Every gvar tuple of a glyph: its full support per axis and its deltas."""
    if "gvar" not in font:
        return ()
    return tuple((tuple(sorted(tv.axes.items())), tuple(tv.coordinates)) for tv in font["gvar"].variations.get(name, []))


def region_key(region):
    return tuple((a.StartCoord, a.PeakCoord, a.EndCoord) for a in region.VarRegionAxis)


def hvar_advance(font, name):
    """A glyph's advance-width variation from HVAR, resolved: {region: delta}, each region as its (start, peak, end) per axis,
    zero deltas left out. Resolved by value because the variation store's row numbers are not part of what a browser sees."""
    t = font["HVAR"].table
    idx = t.AdvWidthMap.mapping[name] if t.AdvWidthMap is not None else font.getGlyphID(name)
    data = t.VarStore.VarData[idx >> 16]
    row = data.Item[idx & 0xFFFF]
    regions = t.VarStore.VarRegionList.Region
    out = {}
    for ri, delta in zip(data.VarRegionIndex, row):
        if delta:
            key = region_key(regions[ri])
            out[key] = out.get(key, 0) + delta
    return out


def resolved_value(font, value):
    """A GPOS ValueRecord as data: each numeric field, and each variation device resolved through GDEF's variation store to
    {region: delta}."""
    if value is None:
        return None
    out = {}
    for k, v in sorted(vars(value).items()):
        if v is None:
            continue
        if hasattr(v, "DeltaFormat"):
            if v.DeltaFormat == 0x8000:  # a VariationIndex: StartSize is the outer index, EndSize the inner
                store = font["GDEF"].table.VarStore
                data = store.VarData[v.StartSize]
                regions = store.VarRegionList.Region
                deltas = {}
                for ri, d in zip(data.VarRegionIndex, data.Item[v.EndSize]):
                    if d:
                        key = region_key(regions[ri])
                        deltas[key] = deltas.get(key, 0) + d
                if deltas:  # an all-zero device adjusts nothing, the same as no device
                    out[k] = ("variation", tuple(sorted(deltas.items())))
            else:
                out[k] = ("device", repr(vars(v)))
        elif v:
            out[k] = v
    return out


def gpos_pairs(font):
    """{(lookup index, first, second): (value1, value2)}: the adjustment a shaper applies to each pair, by resolved value.
    Within a lookup the FIRST subtable that matches the pair decides, even with a zero record (a format 2 class pair always
    matches once the first glyph is covered); a pair whose deciding record adjusts nothing is left out, so an explicit zero
    and an absent pair compare equal."""
    out = {}
    if "GPOS" not in font:
        return out
    order = font.getGlyphOrder()
    for li, lookup in enumerate(font["GPOS"].table.LookupList.Lookup):
        decided = {}
        for st in lookup.SubTable:
            if lookup.LookupType == 9:
                st = st.ExtSubTable
            if getattr(st, "LookupType", lookup.LookupType) != 2:
                continue
            if st.Format == 1:
                for first, ps in zip(st.Coverage.glyphs, st.PairSet):
                    for rec in ps.PairValueRecord:
                        decided.setdefault((first, rec.SecondGlyph),
                                           (resolved_value(font, rec.Value1), resolved_value(font, getattr(rec, "Value2", None))))
            elif st.Format == 2:
                c1, c2 = st.ClassDef1.classDefs, st.ClassDef2.classDefs
                for first in st.Coverage.glyphs:
                    for second in order:
                        rec = st.Class1Record[c1.get(first, 0)].Class2Record[c2.get(second, 0)]
                        decided.setdefault((first, second),
                                           (resolved_value(font, rec.Value1), resolved_value(font, getattr(rec, "Value2", None))))
        for (first, second), (v1, v2) in decided.items():
            if v1 or v2:
                out[(li, first, second)] = (v1 or None, v2 or None)
    return out


def gpos_structure(font):
    """The GPOS script and feature lists and each lookup's type and flag: what selects the pairs."""
    if "GPOS" not in font:
        return None
    (xml,) = need("fontTools.misc.xmlWriter")
    t = font["GPOS"].table
    buf = io.BytesIO()
    w = xml.XMLWriter(buf, newlinestr="\n")
    t.ScriptList.toXML(w, font)
    t.FeatureList.toXML(w, font)
    w.close()
    lookups = tuple((lk.LookupType, lk.LookupFlag, getattr(lk, "MarkFilteringSet", None),
                     getattr(lk.SubTable[0], "ExtensionLookupType", None) if lk.SubTable else None) for lk in t.LookupList.Lookup)
    return buf.getvalue(), lookups


def gdef_classes(font, glyphs):
    """GDEF's glyph classes, mark attachment classes and mark glyph sets, restricted to `glyphs`."""
    if "GDEF" not in font:
        return None
    t = font["GDEF"].table

    def cls(cd):
        return None if cd is None else tuple(sorted((g, c) for g, c in cd.classDefs.items() if g in glyphs))
    sets = getattr(t, "MarkGlyphSetsDef", None)
    mark_sets = None if sets is None else tuple(tuple(sorted(g for g in cov.glyphs if g in glyphs)) for cov in sets.Coverage)
    return cls(getattr(t, "GlyphClassDef", None)), cls(getattr(t, "MarkAttachClassDef", None)), mark_sets


def table_fields(table, skip=()):
    out = {}
    for k, v in sorted(vars(table).items()):
        if k in skip or k.startswith("_") or k == "tableTag":
            continue
        out[k] = repr(vars(v)) if hasattr(v, "__dict__") else repr(v)
    return out


def ttf_bytes(font):
    """The font as plain TrueType bytes (HarfBuzz does not read woff2)."""
    buf = io.BytesIO()
    flavor = font.flavor
    font.flavor = None
    font.save(buf)
    font.flavor = flavor
    return buf.getvalue()


def where_text(location):
    return "(" + ", ".join(f"{k}={v:g}" for k, v in location.items()) + ")"


def instanced_font(woff2, location):
    """A TTFont of the static instance of `woff2` at `location` (user-space axis values; an omitted axis stays at its default)."""
    (tt,) = need("fontTools.ttLib")
    (inst,) = need("fontTools.varLib.instancer")
    font = tt.TTFont(str(woff2))
    full = {a.axisTag: a.defaultValue for a in font["fvar"].axes} if "fvar" in font else {}
    unknown = sorted(set(location) - set(full))
    if unknown:
        raise ValueError(f"{woff2}: the instance location names axes the font lacks: {unknown}")
    full.update(location)
    return inst.instantiateVariableFont(font, full, inplace=False)


def shaped(blob, location, strings):
    """{string: ((glyph name, x_advance, y_advance, x_offset, y_offset), ...)} at one location, default features."""
    (hb,) = need("uharfbuzz")
    font = hb.Font(hb.Face(blob))
    font.set_variations(dict(location))
    out = {}
    for s in strings:
        buf = hb.Buffer()
        buf.add_str(s)
        buf.guess_segment_properties()
        hb.shape(font, buf, {})
        out[s] = tuple((font.glyph_to_string(i.codepoint), p.x_advance, p.y_advance, p.x_offset, p.y_offset)
                       for i, p in zip(buf.glyph_infos, buf.glyph_positions))
    return out


def value_diff(old_path, new_path, locations):
    """(differences, strings shaped per location): every difference between the font at `old_path` and the one at `new_path`, as
    sentences, in the order of the sections listed in the module docstring. `locations` are the group's named-instance locations
    (axis tag to user-space value). An empty list means no difference in any of the compared values; it is not a proof that the
    files are byte-identical."""
    (tt,) = need("fontTools.ttLib")
    old, new = tt.TTFont(str(old_path)), tt.TTFont(str(new_path))
    out = []

    go, gn = old.getGlyphOrder(), new.getGlyphOrder()
    out += [f"glyph {g}: missing from the after font" for g in go if g not in gn]
    out += [f"glyph {g}: only in the after font" for g in gn if g not in go]
    common = [g for g in go if g in gn]
    if common != [g for g in gn if g in go]:
        out.append("glyph order: the common glyphs are in a different order")

    # cmap: every subtable, not only the one a platform would pick; format 14 keeps its mappings in uvsDict
    # keyed by (platform, encoding, language), which the OpenType spec makes unique per subtable (fontTools refuses a repeat)
    so = {(t.platformID, t.platEncID, t.language): t.cmap for t in old["cmap"].tables if t.format != 14}
    sn = {(t.platformID, t.platEncID, t.language): t.cmap for t in new["cmap"].tables if t.format != 14}
    uo = {(t.platformID, t.platEncID): {k: sorted(map(tuple, v)) for k, v in t.uvsDict.items()} for t in old["cmap"].tables if t.format == 14}
    un = {(t.platformID, t.platEncID): {k: sorted(map(tuple, v)) for k, v in t.uvsDict.items()} for t in new["cmap"].tables if t.format == 14}
    if uo != un:
        out.append(f"cmap variation sequences (format 14) differ: {uo} -> {un}")
    for key in sorted(set(so) | set(sn)):
        if key not in so or key not in sn:
            out.append(f"cmap subtable {key}: present in only one font")
            continue
        for cp, g in sorted(so[key].items()):
            if sn[key].get(cp) != g:
                out.append(f"cmap {key} U+{cp:04X}: {g} -> {sn[key].get(cp)}")
        out += [f"cmap {key} U+{cp:04X}: new, maps to {g}" for cp, g in sorted(sn[key].items()) if cp not in so[key]]
    co, cn = old.getBestCmap(), new.getBestCmap()

    for g in common:
        if outline(old, g) != outline(new, g):
            out.append(f"glyph {g}: default outline differs")
        if variations(old, g) != variations(new, g):
            out.append(f"glyph {g}: gvar tuples differ (support regions or deltas)")
        if old["hmtx"][g] != new["hmtx"][g]:
            out.append(f"glyph {g}: hmtx {old['hmtx'][g]} -> {new['hmtx'][g]}")

    for tag in ("fvar", "avar", "STAT", "GSUB", "gasp", "prep", "fpgm", "cvt "):
        if ttx_text(old, tag) != ttx_text(new, tag):
            out.append(f"{tag.strip()}: differs")
    for k in MAXP_HINTING:
        if getattr(old["maxp"], k, None) != getattr(new["maxp"], k, None):
            out.append(f"maxp {k}: {getattr(old['maxp'], k, None)} -> {getattr(new['maxp'], k, None)}")
    if gpos_structure(old) != gpos_structure(new):
        out.append("GPOS: script, feature or lookup structure differs")
    if gdef_classes(old, set(common)) != gdef_classes(new, set(common)):
        out.append("GDEF: glyph classes, mark attachment classes or mark glyph sets differ")
    po, pn = gpos_pairs(old), gpos_pairs(new)
    shared = set(common)
    for key in sorted(set(po) | set(pn)):
        if key[1] not in shared or key[2] not in shared:
            continue  # a pair with a glyph only one font has is already listed as a glyph difference
        if po.get(key) != pn.get(key):
            out.append(f"GPOS pair {key[1]}|{key[2]} (lookup {key[0]}): {po.get(key)} -> {pn.get(key)}")
    if ("HVAR" in old) != ("HVAR" in new):
        out.append("HVAR: present in only one font")
    elif "HVAR" in old:
        for g in common:
            a, b = hvar_advance(old, g), hvar_advance(new, g)
            if a != b:
                out.append(f"glyph {g}: HVAR advance variation differs ({a} -> {b})")
        for side in ("LsbMap", "RsbMap", "VOrgMap"):
            if (getattr(old["HVAR"].table, side, None) is None) != (getattr(new["HVAR"].table, side, None) is None):
                out.append(f"HVAR: {side} present in only one font")

    # keyed by every identifying field but the platform, so two records that share an ID and a language stay apart
    no = {(n.nameID, n.platEncID, n.langID): n.toUnicode() for n in old["name"].names if n.platformID == 3}
    nn = {(n.nameID, n.platEncID, n.langID): n.toUnicode() for n in new["name"].names if n.platformID == 3}
    for k in sorted(set(no) | set(nn)):
        if no.get(k) != nn.get(k):
            out.append(f"name {k[0]} (encoding {k[1]}, language 0x{k[2]:04X}): {no.get(k)!r} -> {nn.get(k)!r}")
    if {n.platformID for n in old["name"].names} != {n.platformID for n in new["name"].names}:
        out.append("name: the set of platforms differs")
    for tag, skip in (("hhea", ()), ("OS/2", ()), ("head", ("checkSumAdjustment", "modified"))):
        fo, fn = table_fields(old[tag], skip), table_fields(new[tag], skip)
        for k in sorted(set(fo) | set(fn)):
            if fo.get(k) != fn.get(k):
                out.append(f"{tag} {k}: {fo.get(k)} -> {fn.get(k)}")

    # the instanced outline and advance at every named instance, so a difference between the masters' tables shows
    for loc in locations:
        where = where_text(loc)
        io_, in_ = instanced_font(old_path, loc), instanced_font(new_path, loc)
        for g in common:
            if outline(io_, g) != outline(in_, g):
                out.append(f"glyph {g} @ {where}: instanced outline differs")
            if io_["hmtx"][g] != in_["hmtx"][g]:
                out.append(f"glyph {g} @ {where}: advance {io_['hmtx'][g]} -> {in_['hmtx'][g]}")

    # kerning as HarfBuzz applies it, over every two-character string of the characters both fonts map
    chars = sorted(chr(cp) for cp in co if cp in cn and cp >= 0x20)
    strings = [a + b for a in chars for b in chars]
    bo, bn = ttf_bytes(old), ttf_bytes(new)
    for loc in locations:
        where = where_text(loc)
        sh_o, sh_n = shaped(bo, loc, strings), shaped(bn, loc, strings)
        for s in strings:
            if sh_o[s] != sh_n[s]:
                out.append(f"shaped {s!r} @ {where}: first advance {sh_o[s][0][1] if sh_o[s] else None} -> "
                           f"{sh_n[s][0][1] if sh_n[s] else None} ({sh_o[s]} -> {sh_n[s]})")
    return out, len(strings)


def run(cfg, font_json, before, after, out_dir, sizes, scale):
    """Renders and compares; writes diff.json, diff.md and the PNGs; returns the diff.json dict."""
    import PIL
    (tt,) = need("fontTools")
    (features,) = need("PIL.features")
    bad = [name for name, group in cfg["groups"].items() if not group.get("instances")]
    if bad:
        sys.stderr.write("diff.py: these groups of font.json have no `instances` (a missing key or an empty list), so there is nothing to render "
                         "and an empty diff would read as 'unchanged': " + ", ".join(bad) + "\n")
        sys.exit(2)
    files = group_files(cfg, font_json, before, after)  # exits 2 on a shared file name, before anything is written
    missing = [str(p) for _rel, b, a in files.values() for p in (b, a) if not p.is_file()]
    if missing:
        sys.stderr.write("diff.py: these group files are missing, so nothing was compared:\n" + "".join(f"  {m}\n" for m in missing))
        sys.exit(2)
    titles = list(cfg.get("titles", []))
    wordmark = cfg.get("review", {}).get("wordmark")
    if wordmark and wordmark not in titles:
        titles.append(wordmark)
    if not titles:
        sys.exit("diff.py: font.json has no `titles` and no review.wordmark to render")
    sizes = sizes or [float(s) for s in cfg["review"]["sizes"]]
    out_dir.mkdir(parents=True, exist_ok=True)
    entries, layout, used, values = [], None, {}, {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for gname, group in cfg["groups"].items():
            _name, bpath, apath = files[gname]
            for k, inst in enumerate(group["instances"]):
                loc = dict(inst["location"])
                bttf = instance_file(bpath, loc, tmp / f"b-{gname}-{k}.ttf")
                attf = instance_file(apath, loc, tmp / f"a-{gname}-{k}.ttf")
                for size in sizes:
                    px = max(1, round(size * scale))
                    fb, fa = load_pil_font(bttf, px), load_pil_font(attf, px)
                    layout = layout_name(fa)
                    for title in titles:
                        w, h, base, margin = canvas_for((fb, fa), title, px)
                        ib, ia = draw(fb, title, (w, h), base, margin), draw(fa, title, (w, h), base, margin)
                        n, share, bbox = compare(ib, ia)
                        raw_b, raw_a = fb.getlength(title) / scale, fa.getlength(title) / scale
                        moved = abs(raw_a - raw_b) > ADVANCE_TOL  # compared UNROUNDED: rounding first can turn 0.0204 into 0.020
                        adv_b, adv_a = round(raw_b, 3), round(raw_a, 3)  # rounded for display only
                        entry = {"group": gname, "instance": inst["name"], "size": size, "title": title, "changed_px": n,
                                 "share": round(share, 6), "bbox": bbox, "advance_before": adv_b,
                                 "advance_after": adv_a, "advance_changed": moved, "panel": [w, h], "png": None}
                        if n or moved:
                            stem = f"{slug(gname)}-{slug(inst['name'])}-{size:g}px-{slug(title)}"
                            used[stem] = used.get(stem, 0) + 1
                            name = f"{stem}.png" if used[stem] == 1 else f"{stem}-{used[stem]}.png"
                            triptych(ib, ia).save(out_dir / name)
                            entry["png"] = name
                        entries.append(entry)
    for gname, group in cfg["groups"].items():
        _name, bpath, apath = files[gname]
        locations = []
        for inst in group["instances"]:
            if inst["location"] not in locations:
                locations.append(dict(inst["location"]))
        lines, n_strings = value_diff(bpath, apath, locations)
        values[gname] = {"differences": lines, "strings_shaped": n_strings, "locations": locations}
    changed = sorted((e for e in entries if e["changed_px"] or e["advance_changed"]),
                     key=lambda e: (-e["share"], -abs(e["advance_after"] - e["advance_before"]), e["group"], e["instance"], e["size"], e["title"]))
    result = {"tool": "diff.py", "before": str(before), "after": str(after) if after is not None else "the shipped files",
              "files": {g: {"name": name, "before": str(b), "after": str(a)} for g, (name, b, a) in files.items()},
              "scale": scale, "threshold": THRESHOLD, "advance_tolerance": ADVANCE_TOL, "gap": GAP,
              "layout": layout, "hinting": HINTING,
              "renderer": {"pillow": PIL.__version__, "freetype": features.version("freetype2"), "fonttools": tt.version, "raqm": features.version("raqm")},
              "renders": len(entries), "changed": len(changed), "entries": entries, "values": values}
    (out_dir / "diff.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "diff.md").write_text(markdown(result, changed), encoding="utf-8")
    return result


def markdown(result, changed):
    n, m = result["changed"], result["renders"]
    lines = ["# Visual diff between two builds", "",
             f"before: `{result['before']}`  \nafter: `{result['after']}`", "",
             f"**{n} of {m} renders changed** (a render is one title at one size at one instance; a pixel counts as changed when its grey "
             f"level differs by more than {result['threshold']} of 255, or when the advance width of the title differs by more than "
             f"{result['advance_tolerance']} CSS px: the last glyph's advance can change with no ink moving).", ""]
    if changed:
        lines += ["| share | changed px | advance before to after (px) | group | instance | size | title | picture |", "|---|---|---|---|---|---|---|---|"]
        for e in changed:
            lines.append(f"| {e['share']:.4f} | {e['changed_px']} | {e['advance_before']:g} to {e['advance_after']:g} | {e['group']} | "
                         f"{e['instance']} | {e['size']:g} | {e['title']} | `{e['png']}` |")
        lines += ["", "Each picture stacks the before render, the after render and the diff (red: more ink after, blue: less, grey: both agree). "
                  "Aim the host's two spot-checks at the two largest shares.", ""]
    lines += [f"{m - n} of {m} renders unchanged.", "", "## By value", "",
              "Each group's before and after files compared by value (outlines, metrics, kerning, tables); "
              f"up to {VALUE_LINES_IN_MD} lines per group here, all of them in diff.json: "
              "the reader judges which differences were meant.", ""]
    for g, v in result["values"].items():
        diffs = v["differences"]
        if not diffs:
            lines.append(f"{g}: no difference by value ({v['strings_shaped']} strings shaped at {len(v['locations'])} named instance(s)).")
            continue
        lines += [f"{g}: {len(diffs)} difference(s) by value:", ""]
        lines += [f"- {d}" for d in diffs[:VALUE_LINES_IN_MD]]
        if len(diffs) > VALUE_LINES_IN_MD:
            lines.append(f"- and {len(diffs) - VALUE_LINES_IN_MD} more, all in diff.json")
    lines += ["",
              f"Renderer: Pillow {result['renderer']['pillow']}, FreeType {result['renderer']['freetype']}, fontTools {result['renderer']['fonttools']}, "
              f"layout engine {result['layout']}, at {result['scale']}x; {result['hinting']}.",
              "What this proves: what FreeType drew on this machine from the two files, unhinted, at these sizes and instances. "
              "It is not CoreText, not Chrome and not the page's CSS."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", help="the folder to write diff.json, diff.md and the PNGs into (use a fresh one per round)")
    ap.add_argument("--font", required=True, help="the project's font.json")
    ap.add_argument("--before", required=True, help="a folder holding the previous build's group files under their file names")
    ap.add_argument("--after", help="a folder holding the current build's group files under their file names (default: the shipped files, where font.json puts them)")
    ap.add_argument("--sizes", nargs="+", type=float, metavar="PX", help="CSS px sizes to render (default: review.sizes)")
    ap.add_argument("--scale", type=int, default=2, help="render at size x SCALE pixels (default 2)")
    args = ap.parse_args(argv)
    if args.scale < 1:
        ap.error("--scale must be at least 1")
    require_raqm()
    try:
        cfg = json.loads(pathlib.Path(args.font).read_text(encoding="utf-8"))
        after = pathlib.Path(args.after) if args.after else None
        result = run(cfg, args.font, pathlib.Path(args.before), after, pathlib.Path(args.out), args.sizes, args.scale)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        sys.exit(f"diff.py: {type(exc).__name__}: {exc}")
    print(f"diff.py: {result['changed']} of {result['renders']} renders changed; wrote {pathlib.Path(args.out) / 'diff.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
