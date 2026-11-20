#!/usr/bin/env python3
"""Builds a project's display face as variable TrueType fonts (woff2) from the generator's exported
masters, one file per group in font.json.

WHAT IT'S FOR: the one place a face's tables, axes and self-checks are decided, for every project that
uses this skill. export.js draws the masters of one group as polygons; this turns each master into a
static TrueType font (fontTools FontBuilder), merges them with varLib into a variable font whose axes,
avar map, named instances, floors, budgets, cmap decisions and name strings all come from font.json,
and refuses to write anything a test would later reject. Nothing site-specific lives in this file.

    python3 scripts/build.py --font font.json                 # export, build and self-check every group; write
    python3 scripts/build.py --font font.json --group italic  # one group; the manifest keeps the others' entries
    python3 scripts/build.py --font font.json --check         # rebuild to memory; exit 1 if the shipped bytes differ
    python3 scripts/build.py --font font.json --static DIR    # also write a static TTF + woff2 per named instance
    python3 scripts/build.py --font font.json --group roman --masters export.json   # reuse an export (re-checked)
    python3 scripts/build.py --font font.json --out-dir DIR --eps 0.5 --ttf vf.ttf  # build elsewhere, inspect the TTF
    python3 scripts/build.py --font font.json --requirements req.json   # name the reviewed requirements explicitly
    python3 scripts/build.py --font font.json --no-requirements         # build with no required-character check

Requirements (review finding C6): the build needs the project's requirements.json so the exporter's
required-character check runs on every build, not only when someone remembers --requirements. The
default is `requirements.json` beside font.json; a missing file is logged and REFUSED unless
--no-requirements is given explicitly, so a build can never skip the check by accident. On the export
path the file is passed to export.js, which exits 1 naming every character without a skeleton; on the
--masters path the same rule (export.js missingCharacters: the space, NBSP under nbsp_to_space, the
apostrophes and the four quotes derived from the apostrophe are not glyph keys) is applied here to the
loaded glyph keys. The manifest records the path used, relative to font.json, or null.

Paths: the keys INSIDE font.json (out_dir, `manifest`, `concepts`, a group's `file`) resolve relative to
the DIRECTORY OF font.json, so the same font.json works from a site's root and from inside the face's
folder. Every path given on the COMMAND LINE (--static, --out-dir, --masters, --ttf, --keep-masters,
--requirements, --font itself) resolves relative to the working directory, as a shell does; an absolute
path stays absolute. (The first version resolved --static and --out-dir from font.json's directory, so
`--static examples/neutral/out/static` typed from the skill directory landed under examples/neutral/
twice while the tests' `--static-dir` with the same text read the working directory; independent
re-review, docs F007.) --out-dir DIR is a whole build elsewhere: the woff2s AND the manifest go into
DIR (the `manifest` key is ignored under --out-dir, so a key that points the manifest back beside the
tool cannot write outside DIR; second dry run, finding 15; likewise a group's `file` keeps only its name, so
`../../static/F-VF.woff2` lands in DIR as `F-VF.woff2`), and the manifest's `file` entries name the
woff2s where they were written, relative to font.json's directory, with `..` steps when they lie outside it
(a site that keeps font.json in tools/face/ and ships the woff2 under static/ records
`../../static/F-VF.woff2`, so the manifest, and `--check` against it, work in any clone); only a woff2
on another drive (Windows), where no relative path exists, is recorded absolute. The exporter's
masters JSON (about 10 MB per group) is written to a temporary directory and discarded unless
--keep-masters PATH names where to keep it; nothing but the woff2s, the manifest and (with --static)
the statics is ever written into out_dir.

Skeleton override (0.6.0): when font.json names `skeletons`, a bare .js file name beside it (refused when it has a directory
part, does not end .js, names no file, or takes the name of one of the five hashed sources), export.js applies that file's
function to the generator's skeleton tables before drawing and records its name and sha256 in the export. The manifest then
hashes six sources, not five: gen.js, export.js, build.py, font.json, concepts.js and the override under its own name, and
records `skeletons` (the name); without the key neither appears, so a project without it builds the manifest 0.5.0 built.
--masters refuses an export whose override name, presence or sha256 disagrees with font.json and the file as it is now
(review F002 of docs/plan-skeleton-overrides.md), because that path never runs export.js.

Output per group: <out_dir>/<Family>-VF.woff2, or <Family>-Italic-VF.woff2 for an italic group (spaces
removed from the family; `group.file` overrides, relative to out_dir), plus one <out_dir>/manifest.json
covering every group (font.json `manifest` overrides). The woff2 and the manifest are meant to be tracked.

Every check that passes prints one `SELF-CHECK ok: <group>: <what>` line on stderr and the first one that
fails ends the build with `SELF-CHECK FAILED: <why>` and exit 1, so "read every self-check line" is a
thing a person can do.

The contours overlap on purpose (each stroke, serif and terminal is its own polygon) and the glyphs
carry the OVERLAP_SIMPLE flag; rasterizers fill them by the nonzero winding rule. Not unioning keeps the
masters point-compatible. What that costs and what checks it is in self_checks() below.

Exact guarantees of the self-checks, so nobody rounds them up:
- "compatible" means the same contour count, the same point count per contour and the same branch
  signature from the generator in every master; it is not a proof that corresponding points are the
  same feature, only that export.js's record says each stroke took the same path. --masters JSON gets
  the same checks as a fresh export (and a fresh export gets them too: load_masters() does not know
  which it is reading).
- what load_masters() RECOMPUTES from the polygons and refuses to take from the JSON: the fold measure
  (fold_excursion) and the minimum interior stroke width per master (min_interior_stroke_width,
  review finding C7). The stated minStrokeWidth must agree with the recomputed figure within 0.15
  units or the build is refused naming both glyphs. 0.15, not less, because the exported raw
  coordinates are rounded to 0.1 units (export.js toFixed(1)), which moves a paired-point distance by
  up to 0.14, while the exporter measured unrounded geometry; the honest neutral fixture differs by
  up to 0.06. So a stated figure can overstate the truth by up to 0.15 units unnoticed, and no more.
  The master parameters the recomputation depends on are NOT taken from the JSON: W, thin and track
  per master are read back from gen.js (`node -e`, params() on the concept and multiplier font.json
  names, no drawing) and the JSON's figures must equal them, because W decides which samples count as
  interior (reach = 1.1 x W / mult from either end), so a JSON that overstated W could hide a thin end
  region from the recomputation (independent re-review, code-a F002). That makes --masters need node
  too; it saves the export, not the generator. Per glyph, the four lists raw / runs / polys / keptIdx
  must have one entry per polygon; a shorter list is refused naming the glyph, and every zip over them
  is strict, because Python's zip stops at the shortest list in silence (re-review, code-a F003).
  What is still TAKEN FROM THE JSON unverified: the advances, the kern pair values, the word space,
  the title widths, the glyph branch records, mult and minStrokeAt (the exporter's own location
  string, recorded beside the recomputed one). The tests in scripts/tests/test_font.py hold those
  against a fresh export and against requirements.json.
  The recomputation reads each stroke body (a polygon with two edge runs) and each ring pair (an
  inner ring is the only polygon the generator orients negative; its outer ring is the polygon
  before it) and pairs edge points as the fold guard does; a point equal to its neighbour on the same
  edge was moved by the generator's fold pin or end clip and is skipped, as the generator's own
  measure was taken before those moves.
- the raster checks compare FreeType renderings (Pillow) of each glyph of each MASTER at font.json's
  raster sizes: decimated against undecimated outlines, and overlapping against a skia-pathops union.
  They prove nothing about Chrome, CoreText or DirectWrite; the review loop's screenshots do that.
  The measured differences are per machine (FreeType build); the manifest records what this build saw.
- the hairline floors are measured on the generator's interior samples (export.js), not on pixels.
- instancing is checked at every named instance: the result has no fvar and the same contour counts.
  That is a structural check; the F013 test (scripts/tests/test_font.py) checks the outlines.
- --static writes a TTF and a woff2 per named instance through fontTools.varLib.instancer with the
  overlaps KEPT (the OVERLAP_SIMPLE flag stays on). They are for modern renderers; nothing here unions
  them for old PostScript workflows. Each static is checked: no fvar/gvar/avar, the same glyph count,
  outlines and advances byte-equal to a second, independent instantiation at that location, the overlap
  flag on every contoured glyph, name/weight-class/italic metadata matching the instance, and one glyph
  rendered through FreeType to prove the file loads. Names are written here, not by instancer's
  updateFontNames, which needs STAT AxisValue records that a designspace without STAT labels never has.
  Bold bits and RIBBI style linking are not set: the statics are for @font-face rules with explicit weights.
- SOURCE_DATE_EPOCH is ASSIGNED from font.json before any table is compiled; a caller's value cannot
  change the bytes (a setdefault did, once).

Copyright 2026 John Knox. MIT licence. Derived from the author's Bract builder (hopsafari.com, commit
90a085c) and Driftwood builder (movingavg.com, commit 67a4e5b).
"""
import argparse
import array
import hashlib
import io
import json
import math
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import tempfile

# Two guards before anything else is imported, so a wrong interpreter fails with the command that fixes it
# instead of a traceback from the middle of the build (zip(strict=) needs 3.10; fontTools is the venv's).
# `scripts/check-env.py` reports the same facts for the whole toolchain.
if sys.version_info < (3, 10):
    sys.exit(f"build.py needs Python >= 3.10 and this is {sys.version_info[0]}.{sys.version_info[1]}; make the skill's venv with a newer one: "
             "python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt, then run .venv/bin/python3 scripts/build.py ...")
try:
    from fontTools import varLib
    from fontTools import version as fonttools_version
    from fontTools.designspaceLib import DesignSpaceDocument, InstanceDescriptor, SourceDescriptor
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    from fontTools.fontBuilder import FontBuilder
    from fontTools.misc.roundTools import otRound
    from fontTools.otlLib.builder import buildStatTable
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.ttLib import TTFont, newTable
    from fontTools.ttLib.tables import ttProgram
    from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates, flagOnCurve, flagOverlapSimple
    from fontTools.ttLib.tables.ttProgram import Program
    from fontTools.varLib import instancer
except ImportError as exc:
    sys.exit(f"build.py cannot import fontTools ({exc}); this interpreter ({sys.executable}) is not the skill's venv. "
             "Install the requirements into it: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt, "
             "then run .venv/bin/python3 scripts/build.py ...")

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT_SOURCES = ["gen.js", "export.js", "build.py"]  # hashed into the manifest beside font.json and concepts.js
# the names the manifest's sources_sha256 already uses, which a face's skeletons file may not take (it is keyed by its bare name)
HASHED_SOURCE_NAMES = SCRIPT_SOURCES + ["font.json", "concepts.js"]
SKELETONS_NAME = re.compile(r"^[^/\\]+\.js$")  # a bare .js file name beside font.json, as export.js and font.schema.json require
EXPORT_SCHEMA = "font-design/export/v1"
MANIFEST_SCHEMA = "font-design/manifest/v1"
# Defaults for the optional font.json keys; every value a project can override is read from the config.
DEFAULT_FOLD_UNITS = {"raw": 4, "decimated": 10}
DEFAULT_RASTER = {"budget": {"decimation": 48, "union": 48, "seam": 24}, "sizes": [16, 40, 80]}
# OS/2.fsType: the embedding permissions are the operator's licence decision, so font.json must state them
# (names.fs_type, no default). Bits 1-3 are mutually exclusive levels (restricted, preview and print, editable);
# bit 8 forbids subsetting. Bit 9 (bitmap-only embedding) is refused: this build writes no embedded bitmaps, so the
# setting would promise a font that only a bitmap strike could satisfy. Browsers ignore the field for web fonts.
FS_TYPE_VALID_BITS = 0x010E
FS_TYPE_BITMAP_ONLY = 0x0200
FS_TYPE_LEVELS = 0x000E
# TrueType `prep` program of the standard "smart dropout" snippet (what gftools fix-nonhinting writes):
# PUSHW[0] 0x01FF, SCANCTRL, PUSHB[0] 4, SCANTYPE. A renderer that runs `prep` then turns on a pixel for a stroke thinner than one pixel.
PREP_SMART_DROPOUT = bytes([0xB8, 0x01, 0xFF, 0x85, 0xB0, 0x04, 0x8D])
CODE_PAGE_LATIN1 = 0x1  # OS/2 ulCodePageRange1 bit 0: Latin 1 (code page 1252)
REQUIRED_KEYS = ["family", "version", "concepts", "out_dir", "groups", "charset", "kerning", "size_budget_bytes", "names", "source_date_epoch"]

# fsSelection bits (OS/2) and macStyle bits (head)
FS_ITALIC, FS_BOLD, FS_REGULAR, FS_USE_TYPO = 0x01, 0x20, 0x40, 0x80
MAC_ITALIC = 0x02
TICK_MIDDLE = 610  # the straight tick's vertical middle; an italic tick is slanted about this line

NAMES = {" ": "space", ";": "semicolon", "…": "ellipsis", "[": "bracketleft", "]": "bracketright",
         "š": "scaron", "ā": "amacron", "é": "eacute", "/": "slash", "(": "parenleft", ")": "parenright",
         "%": "percent", "$": "dollar", "&": "ampersand", ".": "period", ",": "comma", "'": "quoteright",
         ":": "colon", "!": "exclam", "?": "question", "-": "hyphen", "–": "endash", "—": "emdash",
         "fi": "f_i", "fl": "f_l", "ff": "f_f", "#": "numbersign", "+": "plus", "*": "asterisk",
         "©": "copyright", "•": "bullet", "™": "trademark"}
DIGITS = "zero one two three four five six seven eight nine".split()
QUOTE_GLYPHS = ("quotesingle", "quotedbl", "quotedblright", "quoteleft", "quotedblleft")


def gname(k):
    """Glyph name for a generator key: the AGL names above, digits by name, other non-ASCII as uniXXXX."""
    if k in NAMES:
        return NAMES[k]
    if k.isdigit():
        return DIGITS[int(k)]
    if len(k) == 1 and ord(k) > 127:
        return "uni%04X" % ord(k)
    return k


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def log(msg):
    print(msg, file=sys.stderr)


class CheckFailed(Exception):
    pass


def check(cond, msg):
    if not cond:
        raise CheckFailed(msg)


def ok(what):
    """One line per self-check that passed, so a reader can tell a check that ran from one that was skipped."""
    log(f"SELF-CHECK ok: {what}")


def relpath_posix(path, base_dir):
    """`path` relative to `base_dir` as a POSIX string, `..` steps included; the absolute path only when the two share
    no anchor (os.path.relpath raises ValueError across Windows drives)."""
    try:
        return pathlib.PurePath(os.path.relpath(path, base_dir)).as_posix()
    except ValueError:
        return pathlib.Path(path).as_posix()


def resolve_from(base_dir, value):
    """A path written INSIDE font.json, relative to the directory of font.json (W6); absolute stays absolute."""
    p = pathlib.Path(value).expanduser()
    return p.resolve() if p.is_absolute() else (pathlib.Path(base_dir) / p).resolve()


def resolve_arg(value):
    """A path given on the command line: relative to the working directory, as the shell that typed it
    expects (independent re-review, docs F007); absolute stays absolute."""
    return pathlib.Path(value).expanduser().resolve()


# --- configuration ------------------------------------------------------------------------------------
def load_config(font_path, out_dir_override=None):
    """font.json, with its paths resolved relative to its own directory and the optional keys defaulted.
    The returned dict carries the resolved paths under keys beginning with an underscore."""
    font_path = pathlib.Path(font_path).resolve()
    check(font_path.is_file(), f"no such font.json: {font_path}")
    try:
        cfg = json.loads(font_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CheckFailed(f"{font_path} is not valid JSON: {exc}") from exc
    for k in REQUIRED_KEYS:
        check(k in cfg, f"font.json lacks the required key {k!r}")
    check(isinstance(cfg["groups"], dict) and cfg["groups"], "font.json groups must be a non-empty object")
    cfg["_path"] = font_path
    cfg["_dir"] = font_path.parent
    cfg["_concepts"] = (font_path.parent / cfg["concepts"]).resolve()
    check(cfg["_concepts"].is_file(), f"concepts file {cfg['_concepts']} does not exist")
    # skeletons: the face's own skeleton override (gen.js applySkeletons), a bare .js name beside font.json, hashed into the
    # manifest under that name; absent, nothing about the build changes (0.6.0; docs/plan-skeleton-overrides.md)
    if "skeletons" in cfg:
        sk = cfg["skeletons"]
        check(isinstance(sk, str) and SKELETONS_NAME.match(sk),
              f"font.json skeletons must name a .js file beside font.json (a bare file name, no directory part): {json.dumps(sk)}")
        check(sk not in HASHED_SOURCE_NAMES,
              f"font.json skeletons may not take the name of a hashed source ({', '.join(HASHED_SOURCE_NAMES)}): {sk}; rename the file")
        cfg["_skeletons"] = font_path.parent / sk
        check(cfg["_skeletons"].is_file(), f"font.json skeletons names no file: {cfg['_skeletons']}")
    # out_dir and `manifest` (keys in the file) resolve against the directory of font.json; --out-dir (a
    # command-line path) against the working directory; under --out-dir the manifest lands in that
    # directory too, whatever the `manifest` key says
    cfg["_out_dir"] = resolve_arg(out_dir_override) if out_dir_override else resolve_from(font_path.parent, cfg["out_dir"])
    cfg["_manifest"] = resolve_from(cfg["_out_dir"], cfg["manifest"]) if cfg.get("manifest") and not out_dir_override else cfg["_out_dir"] / "manifest.json"
    cfg["_out_dir_override"] = bool(out_dir_override)
    cfg.setdefault("fold_units", dict(DEFAULT_FOLD_UNITS))
    cfg.setdefault("raster", json.loads(json.dumps(DEFAULT_RASTER)))
    names = cfg["names"]
    fs_type = names.get("fs_type")
    check(isinstance(fs_type, int) and not isinstance(fs_type, bool),
          "font.json names.fs_type is required and has no default: it is the font's embedding permission, a licence decision. "
          "Set 0 (installable) for an open font, 4 (Preview & Print) for a proprietary face; 2 (Restricted) makes some tools refuse the font")
    check(not fs_type & FS_TYPE_BITMAP_ONLY,
          f"font.json names.fs_type {fs_type} sets bit 9 (bitmap-only embedding): this build writes no embedded bitmaps, so the font could not satisfy it")
    check(fs_type & ~FS_TYPE_VALID_BITS == 0 and bin(fs_type & FS_TYPE_LEVELS).count("1") <= 1,
          f"font.json names.fs_type {fs_type} is not a valid OS/2 fsType (bits 1-3 are exclusive; only bits 1, 2, 3 and 8 are accepted)")
    typo = cfg.get("typo_metrics")
    if typo is not None:
        check(isinstance(typo, dict) and set(typo) <= {"ascender", "descender", "line_gap"} and {"ascender", "descender"} <= set(typo),
              "font.json typo_metrics takes ascender and descender (and line_gap, which must be 0)")
        check(typo["ascender"] > 0 >= typo["descender"], f"font.json typo_metrics: ascender {typo['ascender']} must be > 0 and descender {typo['descender']} <= 0")
        check(typo.get("line_gap", 0) == 0,
              "font.json typo_metrics.line_gap must be 0: the face sets no extra leading in the font; use CSS line-height "
              "(a non-zero gap gives each platform a different line height)")
    cfg.setdefault("decimation_eps", 1)
    cfg.setdefault("titles", [])
    for k in ("nbsp_to_space", "ascii_apostrophe_curly"):
        check(isinstance(cfg["charset"].get(k), bool), f"charset.{k} must be true or false")
    for gn, g in cfg["groups"].items():
        g["_name"] = gn
        for k in ("italic", "axes", "masters", "instances", "hairline_floors"):
            check(k in g, f"group {gn} lacks {k!r}")
        check(len(g["masters"]) >= 2, f"group {gn}: a variable font needs at least two masters")
        tags = [a["tag"] for a in g["axes"]]
        check(len(tags) == len(set(tags)) and tags, f"group {gn}: axis tags must be unique and at least one")
        for a in g["axes"]:
            check(a["min"] <= a["default"] <= a["max"], f"group {gn} axis {a['tag']}: min <= default <= max")
            if "map" in a:
                users = [u for u, d in a["map"]]
                check(a["min"] in users and a["max"] in users, f"group {gn} axis {a['tag']}: the avar map must include both ends")
        for mn, m in g["masters"].items():
            check(set(m["location"]) == set(tags), f"group {gn} master {mn}: location must name exactly the axes {tags}")
            check(mn in g["hairline_floors"], f"group {gn}: no hairline floor for master {mn}")
        for inst in g["instances"]:
            check(set(inst["location"]) == set(tags), f"group {gn} instance {inst['name']}: location must name exactly the axes {tags}")
        if g["italic"]:
            g["_angle"] = float(g.get("italic_angle", 10))
            check(0 < g["_angle"] <= 30, f"group {gn}: italic_angle must be in (0, 30]")
        else:
            g["_angle"] = 0.0
            check("italic_angle" not in g, f"group {gn}: italic_angle is set on a group that is not italic")
    # two groups must never write one file: under --out-dir a group file keeps only its name, so a/F-VF.woff2
    # and b/F-VF.woff2 would otherwise land on the same path and the second group would overwrite the first
    seen = {}
    for gn in cfg["groups"]:
        dest = group_file(cfg, gn)
        why = " (under --out-dir a group's file keeps only its name)" if cfg["_out_dir_override"] else ""
        check(dest not in seen, f"groups {seen.get(dest)} and {gn} both write {dest}{why}")
        seen[dest] = gn
    return cfg


def family_token(cfg):
    return cfg["family"].replace(" ", "")


def group_file(cfg, group_name):
    """Where the group's woff2 lives: out_dir/<Family>-VF.woff2, -Italic-VF for an italic group, or group.file.
    Under --out-dir only group.file's NAME is kept, so a file such as ../../static/F-VF.woff2 cannot write
    outside DIR (the same rule as the manifest key; it used to escape DIR by its .. steps)."""
    g = cfg["groups"][group_name]
    if g.get("file"):
        if cfg.get("_out_dir_override"):
            return cfg["_out_dir"] / pathlib.PurePath(g["file"]).name
        return (cfg["_out_dir"] / g["file"]).resolve()
    return cfg["_out_dir"] / (f"{family_token(cfg)}-Italic-VF.woff2" if g["italic"] else f"{family_token(cfg)}-VF.woff2")


def style_names(cfg, group):
    """The style strings a group's variable font carries: Regular or Italic (review finding F004)."""
    fam, style = cfg["family"], "Italic" if group["italic"] else "Regular"
    return {"style": style, "full": f"{fam} {style}", "ps": f"{family_token(cfg)}-{style}",
            "file_stem": f"{family_token(cfg)}-Italic-VF" if group["italic"] else f"{family_token(cfg)}-VF"}


# --- quotes: derived from the apostrophe --------------------------------------------------------------
def quote_glyphs(ap_polys, ap_adv, italic_angle=0.0):
    """The straight tick (quotesingle), double quotes and opening quotes, all from the apostrophe's
    outline. Every transform is affine, so the derived glyphs are point-compatible across masters
    whenever the apostrophe is. For an italic group the tick is slanted about its middle (y = 610) by
    tan(angle), as Driftwood's build did; the curly marks come from the already slanted apostrophe.
    quotedblleft advances by the apostrophe's advance plus the gap between its two marks, like
    quotedblright (Driftwood carried the straight quotes' advance there and the second mark overhung)."""
    axs = [x for p in ap_polys for x, y in p]
    aw = max(axs) - min(axs)
    dbl_gap = aw * 1.45  # the second mark sits one mark-width plus a clear gap to the right
    slant = math.tan(math.radians(italic_angle)) if italic_angle else 0.0

    def tick(cx):
        rt, rb, top, bot, o = aw * 0.32, aw * 0.13, 715, 505, []
        for i in range(13):
            a = math.pi * i / 12
            o.append((cx + rt * math.cos(a), top - rt + rt * math.sin(a)))
        o += [(cx - rb, bot), (cx + rb, bot)]
        if slant:
            o = [(x + slant * (y - TICK_MIDDLE), y) for x, y in o]
        return o
    tick_adv = round(aw * 0.64 + 2 * 70)
    tc = tick_adv / 2
    ys = [y for p in ap_polys for x, y in p]
    cx, cy = (min(axs) + max(axs)) / 2, (min(ys) + max(ys)) / 2
    turned = [[(2 * cx - x, 2 * cy - y) for x, y in p] for p in ap_polys]
    shifted = lambda polys: [[(x + dbl_gap, y) for x, y in p] for p in polys]
    return {
        "quotesingle": {"adv": tick_adv, "polys": [tick(tc)]},
        "quotedbl": {"adv": round(tick_adv + aw * 0.8), "polys": [tick(tc), tick(tc + aw * 0.8)]},
        "quotedblright": {"adv": round(ap_adv + dbl_gap), "polys": [[tuple(q) for q in p] for p in ap_polys] + shifted(ap_polys)},
        "quoteleft": {"adv": ap_adv, "polys": turned},
        "quotedblleft": {"adv": round(ap_adv + dbl_gap), "polys": turned + shifted(turned)},
    }


def signed_area(poly):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))


def master_outlines(M, which, italic_angle=0.0):
    """{glyph name: (advance, [contour, ...])} for one master; `which` is "polys" (decimated) or "raw"."""
    out = {".notdef": (500, [[(50, 0), (450, 0), (450, 700), (50, 700)]]), "space": (M["space"], [])}
    for k, g in M["glyphs"].items():
        out[gname(k)] = (g["adv"], [[tuple(q) for q in poly] for poly in g[which]])
    check("'" in M["glyphs"], "the generator must draw the apostrophe; the quote glyphs are derived from it")
    ap = M["glyphs"]["'"]
    for n, g in quote_glyphs(ap[which], ap["adv"], italic_angle).items():
        out[n] = (g["adv"], g["polys"])
    return out


def tt_glyph(contours):
    """A TrueType glyph with exactly the points given, rounded, all on-curve. Built directly rather
    than through TTGlyphPen, which drops a closing point that lands on the first one: adjacent
    samples on a small ring are ~1.4 units apart, so that happened in one master and not another
    (the inner ring of % in Bract's TextBold) and the masters stopped matching point for point.
    A zero-length closing segment is legal TrueType."""
    g = Glyph()
    pts, ends = [], []
    for c in contours:
        pts += [tuple(round(v) for v in q) for q in c]
        ends.append(len(pts) - 1)
    g.numberOfContours = len(contours)
    g.coordinates = GlyphCoordinates(pts)
    g.endPtsOfContours = ends
    g.flags = array.array("B", [flagOnCurve] * len(pts))
    g.program = ttProgram.Program()
    g.program.fromBytecode(b"")
    if pts:
        g.flags[0] |= flagOverlapSimple  # overlapping contours are deliberate; macOS reads this bit
    return g


def cmap_for(outlines, charset):
    """Code point -> glyph name. The two decisions font.json makes: NBSP draws the space glyph
    (nbsp_to_space), and the ASCII apostrophe draws the curly apostrophe with the straight tick left
    unmapped (ascii_apostrophe_curly), or the straight tick itself when that is false."""
    cmap = {0x20: "space", 0x2019: "quoteright", 0x2018: "quoteleft", 0x22: "quotedbl", 0x201C: "quotedblleft", 0x201D: "quotedblright"}
    cmap[0x27] = "quoteright" if charset["ascii_apostrophe_curly"] else "quotesingle"
    if charset["nbsp_to_space"]:
        cmap[0xA0] = "space"
    for n in outlines:
        for k, v in NAMES.items():
            if v == n and len(k) == 1 and ord(k) not in cmap:
                cmap[ord(k)] = n
        if len(n) == 1:
            cmap[ord(n)] = n
        elif n.startswith("uni") and len(n) == 7:
            cmap[int(n[3:], 16)] = n
        elif n in DIGITS:
            cmap[ord(str(DIGITS.index(n)))] = n
    return cmap


def name_records(cfg, group, style, full, ps, unique_suffix):
    names = cfg["names"]
    return {
        "familyName": cfg["family"], "styleName": style,
        "typographicFamily": cfg["family"], "typographicSubfamily": style,
        "uniqueFontIdentifier": f"{cfg['version']};{names['vendor_id'].strip()};{unique_suffix}",
        "fullName": full, "psName": ps,
        "version": f"Version {cfg['version']}",
        "copyright": names["copyright"], "manufacturer": names["manufacturer"], "designer": names["designer"],
        "description": names["description"],
        "vendorURL": names["vendor_url"], "designerURL": names.get("designer_url", names["vendor_url"]),
        "licenseDescription": names["licence"], "licenseInfoURL": names.get("licence_url", names["vendor_url"]),
    }


def vertical_spec(cfg, vmetrics):
    """The three vertical-metric sets the font carries, as (ascender, descender, line gap) with the descender
    negative. hhea and OS/2 typo are the same numbers with a line gap of 0, so macOS (hhea) and Windows or Chrome
    (typo, with USE_TYPO_METRICS) draw the same line height; they are font.json's `typo_metrics` when given, else
    the measured extent of every glyph of every master. OS/2 win is the clipping box and is always the measured
    extent, so no glyph is cut off on Windows. Returns {"hhea", "typo", "win": (ascent, descent as a positive number)}."""
    win_asc, win_desc = vmetrics
    typo = cfg.get("typo_metrics")
    asc, desc = (typo["ascender"], typo["descender"]) if typo else (win_asc, -win_desc)
    return {"hhea": (asc, desc, 0), "typo": (asc, desc, 0), "win": (win_asc, win_desc)}


def build_master(cfg, group, outlines, cmap, order, vmetrics, kerns, weight_class):
    """A static TrueType font for one master, with GPOS kern and GSUB liga from the same feature text.
    Italic groups get the italic metadata (review finding F004): style "Italic", fsSelection ITALIC
    with REGULAR clear, head.macStyle italic, post.italicAngle = -angle."""
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    glyphs, metrics = {}, {}
    for n in order:
        adv, contours = outlines[n]
        glyphs[n] = tt_glyph(contours)
        xs = [q[0] for c in contours for q in c]
        metrics[n] = (adv, round(min(xs)) if xs else 0)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    vs = vertical_spec(cfg, vmetrics)
    fb.setupHorizontalHeader(ascent=vs["hhea"][0], descent=vs["hhea"][1], lineGap=vs["hhea"][2])
    sn = style_names(cfg, group)
    fb.setupNameTable(name_records(cfg, group, sn["style"], sn["full"], sn["ps"], sn["file_stem"]), mac=False)
    fs = FS_USE_TYPO | (FS_ITALIC if group["italic"] else FS_REGULAR)
    # All masters carry the same vertical metrics so varLib has no vertical-metric deltas to put in
    # MVAR; the axes are what vary. The vendor id is padded to four characters as OS/2 requires.
    fb.setupOS2(version=4, sTypoAscender=vs["typo"][0], sTypoDescender=vs["typo"][1], sTypoLineGap=vs["typo"][2],
                usWinAscent=vs["win"][0], usWinDescent=vs["win"][1], sxHeight=500, sCapHeight=700, usWeightClass=weight_class,
                fsSelection=fs, achVendID=cfg["names"]["vendor_id"].ljust(4)[:4], fsType=cfg["names"]["fs_type"],
                ulCodePageRange1=CODE_PAGE_LATIN1)
    fb.setupPost(italicAngle=-group["_angle"] if group["italic"] else 0.0)
    # head.fontRevision is a 16.16 fixed number, so a three-part version keeps its first two parts
    fb.font["head"].fontRevision = float(".".join(cfg["version"].split(".")[:2]))
    fb.font["head"].macStyle = MAC_ITALIC if group["italic"] else 0
    fea = ["languagesystem DFLT dflt;", "languagesystem latn dflt;"]
    ligs = [(k, v) for k, v in (("ff", "f_f"), ("fi", "f_i"), ("fl", "f_l")) if v in outlines]
    if ligs:
        fea.append("feature liga { " + " ".join(f"sub {k[0]} {k[1]} by {v};" for k, v in ligs) + " } liga;")
    fea.append("feature kern {")
    for a, b, v in kerns:
        fea.append(f"  pos {gname(a)} {gname(b)} {v};")
    fea.append("} kern;")
    addOpenTypeFeaturesFromString(fb.font, "\n".join(fea))
    return fb.font


def axis_descriptors(group):
    """(DesignSpaceDocument with the group's axes, {tag: axis}) from font.json; avar comes from `map`."""
    doc = DesignSpaceDocument()
    by_tag = {}
    for a in group["axes"]:
        kw = dict(tag=a["tag"], name=a["name"], minimum=a["min"], default=a["default"], maximum=a["max"])
        if "map" in a:
            kw["map"] = [(u, d) for u, d in a["map"]]
        doc.addAxisDescriptor(**kw)
        by_tag[a["tag"]] = doc.axes[-1]
    return doc, by_tag


def design_location(by_tag, user_location):
    """A user-space location mapped forward through each axis's avar map, keyed by axis name."""
    return {by_tag[tag].name: by_tag[tag].map_forward(v) for tag, v in user_location.items()}


def default_weight_class(group):
    for a in group["axes"]:
        if a["tag"] == "wght":
            return round(a["default"])
    return 400


# What a weight value is called, restated for the self-check ONLY (not the writer's table below), so an edit to WEIGHT_NAMES
# alone is refused by the build: the CSS and OpenType usWeightClass names.
STANDARD_WEIGHT_NAMES = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}
WEIGHT_NAMES = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}
STAT_ELIDABLE = 0x0002  # STAT AxisValue flag: the name may be left out of a composed style name


def stat_axes(group):
    """The `axes` argument of buildStatTable: per axis, an axis value for every user-space value any named
    instance uses on it (so every fvar instance coordinate has one, which tools that read STAT to name
    instances look for) plus the axis default, which is marked elidable. A weight takes its standard name
    (400 Regular, 700 Bold); any other value is named by its number, which is accurate if plain."""
    axes = []
    for order, a in enumerate(group["axes"]):
        values = sorted({i["location"][a["tag"]] for i in group["instances"]} | {a["default"]})
        axes.append({"tag": a["tag"], "name": a["name"], "ordering": order, "values": [
            {"value": v, "name": WEIGHT_NAMES.get(round(v), f"{v:g}") if a["tag"] == "wght" and v == round(v) else f"{v:g}",
             **({"flags": STAT_ELIDABLE} if v == a["default"] else {})} for v in values]})
    return axes


def finish_tables(cfg, group, vf):
    """The tables a variable font needs beyond what varLib writes: STAT axis values for every named instance
    (varLib writes the axis records and no values), `gasp` and the smart-dropout `prep` program that pairs with
    it. Macintosh name records are never written (setupNameTable and buildStatTable are told so); the self-check
    reads the compiled font to prove none came from anywhere else."""
    buildStatTable(vf, stat_axes(group), elidedFallbackName=style_names(cfg, group)["style"], windowsNames=True, macNames=False)
    gasp = newTable("gasp")
    gasp.version, gasp.gaspRange = 1, {0xFFFF: 0x000F}  # grid-fit + grayscale + symmetric at every size
    vf["gasp"] = gasp
    prep = newTable("prep")
    prep.program = Program()
    prep.program.fromBytecode(PREP_SMART_DROPOUT)
    vf["prep"] = prep
    vf["maxp"].maxStackElements = max(vf["maxp"].maxStackElements, 1)  # the program pushes one value at a time; maxp counts prep's stack too


def build_variable(cfg, group, masters, vmetrics):
    """N static masters -> one variable font via varLib. Returns (vf, {name: static master})."""
    names = list(masters)
    order = list(master_outlines(masters[names[0]], "polys", group["_angle"]))
    cmap = cmap_for(order, cfg["charset"])
    doc, by_tag = axis_descriptors(group)
    statics = {}
    for n in names:
        font = build_master(cfg, group, master_outlines(masters[n], "polys", group["_angle"]), cmap, order, vmetrics,
                            masters[n]["kerns"], default_weight_class(group))
        statics[n] = font
        src = SourceDescriptor()
        src.font, src.name = font, n
        src.location = design_location(by_tag, group["masters"][n]["location"])
        doc.addSource(src)
    for inst in group["instances"]:
        d = InstanceDescriptor()
        d.familyName, d.styleName = cfg["family"], inst["name"]
        d.designLocation = design_location(by_tag, inst["location"])
        doc.addInstance(d)
    vf, _model, _ = varLib.build(doc, optimize=True)
    finish_tables(cfg, group, vf)
    return vf, statics


# --- self-checks ------------------------------------------------------------------------------------
def raster_font_file(outlines, path):
    """A throwaway TrueType font whose cmap maps U+E000+i to each glyph, so Pillow can render glyphs
    that have no character of their own (ligatures, the straight tick)."""
    order = list(outlines)
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({0xE000 + i: n for i, n in enumerate(order)})
    fb.setupGlyf({n: tt_glyph(c) for n, (adv, c) in outlines.items()})
    fb.setupHorizontalMetrics({n: (1000, 0) for n in order})
    fb.setupHorizontalHeader(ascent=1000, descent=-400)
    fb.setupNameTable({"familyName": "raster", "styleName": "Regular"})
    fb.setupOS2()
    fb.setupPost()
    # FreeType autohints any TrueType font that has no font program, and Pillow cannot turn that off;
    # the autohinter snaps whole glyphs by a pixel on tiny outline changes, which is exactly the noise
    # this comparison must not contain. One harmless instruction (SVTCA[0]) makes FreeType take the
    # bytecode path instead, and with no glyph instructions the outline is rendered as drawn.
    fpgm = newTable("fpgm")
    fpgm.program = Program()
    fpgm.program.fromBytecode(b"\x00")
    fb.font["fpgm"] = fpgm
    fb.save(str(path))
    return {n: 0xE000 + i for i, n in enumerate(order)}


def render_all(font_path, codes, size):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(str(font_path), size)
    out = {}
    for n, cp in codes.items():
        im = Image.new("L", (3 * size, 3 * size), 0)
        ImageDraw.Draw(im).text((size * 0.5, size * 2), chr(cp), font=font, fill=255, anchor="ls")
        out[n] = im
    return out


def max_diff(a, b):
    from PIL import ImageChops
    return ImageChops.difference(a, b).getextrema()[1]


def seam_diff(overlapping, unioned):
    """Max difference on pixels the union renders at full coverage: a seam, never an edge."""
    from PIL import ImageChops
    diff = ImageChops.difference(overlapping, unioned)
    full = unioned.point(lambda v: 255 if v == 255 else 0)
    return ImageChops.multiply(diff, full).getextrema()[1]


def union_outlines(outlines):
    from pathops import Path
    out = {}
    for n, (adv, contours) in outlines.items():
        p = Path()
        for c in contours:
            p.moveTo(*c[0])
            for q in c[1:]:
                p.lineTo(*q)
            p.close()
        p.simplify(fix_winding=True, keep_starting_points=False)
        rec = RecordingPen()
        p.draw(rec)
        cs, cur = [], []
        for op, pts in rec.value:
            if op == "moveTo":
                cur = [pts[0]]
            elif op == "lineTo":
                cur.append(pts[0])
            elif op in ("closePath", "endPath"):
                cs.append(cur)
                cur = []
            else:
                raise ValueError(op)
        out[n] = (adv, cs)
    return out


def self_checks(cfg, group, masters, vf, statics, woff2_bytes, tmp):
    """Every check that fails the build. Returns the measurements for the manifest."""
    report = {}
    names = list(masters)
    floors, raster, charset = group["hairline_floors"], cfg["raster"], cfg["charset"]
    label = group.get("_name", "group")
    # 1. masters structurally identical (export.js checked branch outcomes; this re-checks the shipped glyf)
    for n in names:
        for gn in statics[names[0]].getGlyphOrder():
            a, b = statics[names[0]]["glyf"][gn], statics[n]["glyf"][gn]
            check(a.numberOfContours == b.numberOfContours, f"{gn}: contour count differs in {n}")
            if a.numberOfContours > 0:
                check(list(a.endPtsOfContours) == list(b.endPtsOfContours), f"{gn}: point structure differs in {n}")
    ok(f"{label}: {len(statics[names[0]].getGlyphOrder())} glyphs structurally identical in {len(names)} masters")
    # 2. every contoured glyph varies: a gvar entry with a non-zero delta in every master's region
    gvar = vf["gvar"].variations
    # .notdef is the same box in every master on purpose, so it has nothing to vary
    missing = [gn for gn in vf.getGlyphOrder() if gn != ".notdef" and vf["glyf"][gn].numberOfContours > 0 and not gvar.get(gn)]
    check(not missing, f"glyphs without gvar variations: {missing}")
    report["gvar_glyphs"] = sum(1 for gn in vf.getGlyphOrder() if gvar.get(gn))
    ok(f"{label}: every contoured glyph varies ({report['gvar_glyphs']} gvar entries)")
    # 3. cmap: the two decisions font.json made
    cmap = vf.getBestCmap()
    if charset["nbsp_to_space"]:
        check(cmap.get(0xA0) == cmap[0x20] == "space", "NBSP must map to the space glyph")
    else:
        check(0xA0 not in cmap, "NBSP is mapped although charset.nbsp_to_space is false")
    check("quotesingle" in vf.getGlyphOrder(), "the straight tick must exist")
    if charset["ascii_apostrophe_curly"]:
        check(cmap[0x27] == cmap[0x2019] == "quoteright", "ASCII apostrophe must draw the curly apostrophe")
        check("quotesingle" not in cmap.values(), "the straight tick stays unmapped")
    else:
        check(cmap[0x27] == "quotesingle" and cmap[0x2019] == "quoteright", "ASCII apostrophe must draw the straight tick")
    for ch in charset["required"]:
        check(ord(ch) in cmap, f"required character {ch!r} U+{ord(ch):04X} is not in the cmap")
    ok(f"{label}: cmap maps {len(cmap)} code points, every charset.required character among them; NBSP and apostrophe as configured")
    # 4. hairlines: the floor is held against the exporter's figure AND the one load_masters() recomputed
    # from the polygons (review finding C7); the two already agree within 0.15 or the build was refused.
    report["min_stroke_width"] = {n: masters[n]["minStrokeWidth"] for n in names}
    report["min_stroke_at"] = {n: masters[n]["minStrokeAt"] for n in names}
    report["min_stroke_width_recomputed"] = {n: masters[n]["minStrokeWidthRecomputed"] for n in names}
    report["min_stroke_at_recomputed"] = {n: masters[n]["minStrokeAtRecomputed"] for n in names}
    for n in names:
        for figure, where in ((masters[n]["minStrokeWidth"], masters[n]["minStrokeAt"]), (masters[n]["minStrokeWidthRecomputed"], masters[n]["minStrokeAtRecomputed"])):
            check(figure >= floors[n], f"{n}: interior stroke {figure} below floor {floors[n]} at {where}")
        ok(f"{label} {n}: min interior stroke {masters[n]['minStrokeWidth']} (recomputed {masters[n]['minStrokeWidthRecomputed']}) clears floor {floors[n]}")
    # 4b. no stroke edge folds back on itself. load_masters() already recomputed the measure from the
    # polygons and refused any fold; this records the exporter's own figures beside it.
    report["folded_edges"] = {n: masters[n]["foldedEdges"] for n in names}
    report["max_backward_excursion"] = {n: {kind: [masters[n]["maxBackwardExcursion"][kind], masters[n]["worstFoldAt"][kind]]
                                            for kind in ("raw", "decimated")} for n in names}
    report["max_backward_excursion_recomputed"] = {n: masters[n]["maxBackwardExcursionRecomputed"] for n in names}
    for n in names:
        check(masters[n]["foldedEdges"] == 0,
              f"{n}: {masters[n]['foldedEdges']} stroke edge(s) fold back by more than {cfg['fold_units']} units, worst at {masters[n]['worstFoldAt']}")
    ok(f"{label}: no stroke edge folds back (exporter's count 0 in every master; recomputed in load_masters)")
    # 5. size
    report["woff2_bytes"] = len(woff2_bytes)
    check(len(woff2_bytes) <= cfg["size_budget_bytes"], f"woff2 is {len(woff2_bytes)} bytes, over the {cfg['size_budget_bytes']} budget")
    ok(f"{label}: woff2 {len(woff2_bytes)} bytes within the {cfg['size_budget_bytes']} budget")
    # 6. round trip, axis order, instancing at every named instance
    rt = TTFont(io.BytesIO(woff2_bytes))
    tags = [a["tag"] for a in group["axes"]]
    check([a.axisTag for a in rt["fvar"].axes] == tags, f"fvar axes {[a.axisTag for a in rt['fvar'].axes]} are not the configured {tags}")
    probe = next(gn for gn in vf.getGlyphOrder() if vf["glyf"][gn].numberOfContours > 0 and gn != ".notdef")
    for inst in group["instances"]:
        static = instancer.instantiateVariableFont(TTFont(io.BytesIO(woff2_bytes)), dict(inst["location"]), inplace=False)
        check("fvar" not in static and static["glyf"][probe].numberOfContours == vf["glyf"][probe].numberOfContours,
              f"instancing at {inst['name']} {inst['location']}")
    ok(f"{label}: woff2 round-trips, fvar axes {tags}, instancing works at {len(group['instances'])} named instances")
    # 7. the overlap flag survived compilation, on every contoured glyph
    bare = [gn for gn in rt.getGlyphOrder() if rt["glyf"][gn].numberOfContours > 0 and not rt["glyf"][gn].flags[0] & flagOverlapSimple]
    check(not bare, f"OVERLAP_SIMPLE flag lost on {bare[:8]}")
    ok(f"{label}: OVERLAP_SIMPLE set on every contoured glyph")
    # 8. style metadata (review finding F004)
    name = {r.nameID: r.toUnicode() for r in rt["name"].names if r.platformID == 3}
    sn = style_names(cfg, group)
    check(name.get(2) == sn["style"] and name.get(17) == sn["style"] and name.get(4) == sn["full"] and name.get(6) == sn["ps"],
          f"name table styles {name.get(2)!r}/{name.get(17)!r}/{name.get(4)!r}/{name.get(6)!r} are not {sn}")
    check(name.get(9) == cfg["names"]["designer"], f"name ID 9 (designer) is {name.get(9)!r}, font.json names.designer is {cfg['names']['designer']!r}")
    fs = rt["OS/2"].fsSelection
    check(bool(fs & FS_USE_TYPO), "USE_TYPO_METRICS must stay set")
    if group["italic"]:
        check(fs & FS_ITALIC and not fs & FS_REGULAR, f"italic group: fsSelection {fs:#x} must set ITALIC and clear REGULAR")
        check(rt["head"].macStyle & MAC_ITALIC, "italic group: head.macStyle italic bit")
        check(abs(rt["post"].italicAngle + group["_angle"]) < 1e-6, f"italic group: post.italicAngle {rt['post'].italicAngle} is not {-group['_angle']}")
    else:
        check(not fs & FS_ITALIC and fs & FS_REGULAR, f"roman group: fsSelection {fs:#x} must set REGULAR and clear ITALIC")
        check(not rt["head"].macStyle & MAC_ITALIC and rt["post"].italicAngle == 0, "roman group: italic metadata set")
    ok(f"{label}: name table {sn['full']!r}/{sn['ps']!r}, fsSelection {fs:#x}, macStyle and post.italicAngle match the group")
    # 8b. the font-table decisions: vertical metrics, fsType, code page, STAT, prep and gasp, no Mac names.
    # Read back from the compiled woff2. The metrics are printed because they decide `line-height: normal`.
    vs = vertical_spec(cfg, vertical_metrics(masters, group["_angle"]))
    hh, os2 = rt["hhea"], rt["OS/2"]
    got = {"hhea": (hh.ascent, hh.descent, hh.lineGap), "typo": (os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap), "win": (os2.usWinAscent, os2.usWinDescent)}
    check(got == vs, f"vertical metrics in the font {got} are not the ones this build decided {vs}")
    check(got["hhea"] == got["typo"] and got["hhea"][2] == 0, f"hhea {got['hhea']} and OS/2 typo {got['typo']} must be equal with a line gap of 0")
    check(bool(fs & FS_USE_TYPO), "USE_TYPO_METRICS must be set")
    report["vertical_metrics_written"] = {k: list(v) for k, v in got.items()}
    ok(f"{label}: vertical metrics written: hhea {got['hhea'][0]}/{got['hhea'][1]}/{got['hhea'][2]} = typo {got['typo'][0]}/{got['typo'][1]}/{got['typo'][2]}, "
       f"win {got['win'][0]}/{got['win'][1]} (every glyph's extent), USE_TYPO_METRICS set; line-height: normal is "
       f"{(got['hhea'][0] - got['hhea'][1] + got['hhea'][2]) / 1000:g} em wherever the platform reads hhea or typo (they agree); "
       "a platform that reads the win metrics is not covered")
    check(os2.fsType == cfg["names"]["fs_type"], f"OS/2 fsType {os2.fsType} is not font.json's names.fs_type {cfg['names']['fs_type']}")
    check(os2.ulCodePageRange1 & CODE_PAGE_LATIN1, f"OS/2 ulCodePageRange1 {os2.ulCodePageRange1:#x} lacks the Latin 1 bit")
    ok(f"{label}: OS/2 fsType {os2.fsType} (from font.json), ulCodePageRange1 {os2.ulCodePageRange1:#x} (Latin 1 set)")
    stat = rt["STAT"].table
    covered = {(stat.DesignAxisRecord.Axis[v.AxisIndex].AxisTag, v.Value) for v in (stat.AxisValueArray.AxisValue if stat.AxisValueArray else []) if v.Format in (1, 3)}
    uncovered = sorted((t, c) for i in rt["fvar"].instances for t, c in i.coordinates.items() if (t, c) not in covered)
    check(stat.AxisValueCount > 0 and not uncovered, f"STAT has {stat.AxisValueCount} axis values and none for the named-instance coordinates {uncovered}")
    stat_bad = []
    for v in (stat.AxisValueArray.AxisValue if stat.AxisValueArray else []):
        tag, value = stat.DesignAxisRecord.Axis[v.AxisIndex].AxisTag, v.Value
        want = STANDARD_WEIGHT_NAMES.get(int(value), f"{value:g}") if tag == "wght" and value == int(value) else f"{value:g}"
        default = next(a["default"] for a in group["axes"] if a["tag"] == tag)
        if rt["name"].getDebugName(v.ValueNameID) != want:
            stat_bad.append(f"{tag} {value:g} is named {rt['name'].getDebugName(v.ValueNameID)!r}, not {want!r}")
        if bool(v.Flags & STAT_ELIDABLE) != (value == default):
            stat_bad.append(f"{tag} {value:g} elidable flag is {bool(v.Flags & STAT_ELIDABLE)} (only the default {default:g} is elidable)")
    if rt["name"].getDebugName(stat.ElidedFallbackNameID) != sn["style"]:
        stat_bad.append(f"elided fallback name {rt['name'].getDebugName(stat.ElidedFallbackNameID)!r} is not {sn['style']!r}")
    check(not stat_bad, f"STAT value names: {stat_bad}")
    ok(f"{label}: STAT has {stat.AxisValueCount} axis values covering every coordinate of the {len(rt['fvar'].instances)} named instances, "
       f"standard weight names, only the default elidable, elided fallback {sn['style']!r}")
    check("prep" in rt and bytes(rt["prep"].program.getBytecode()) == PREP_SMART_DROPOUT, "prep must be the smart-dropout program")
    check("gasp" in rt and rt["gasp"].gaspRange == {0xFFFF: 0x000F}, f"gasp {getattr(rt.get('gasp'), 'gaspRange', None)} is not {{65535: 15}}")
    ok(f"{label}: prep holds the smart-dropout program ({len(PREP_SMART_DROPOUT)} bytes) and gasp is {{65535: 15}}")
    mac = sorted({r.nameID for r in rt["name"].names if r.platformID == 1})
    check(not mac, f"the name table carries Macintosh (platform 1) records for name IDs {mac[:8]}")
    ok(f"{label}: no Macintosh name records (Windows and Unicode platform names only)")
    # 9. decimation: signed-area sign per contour unchanged, and rasters before/after decimation
    for n in names:
        for k, g in masters[n]["glyphs"].items():
            for raw, dec in zip(g["raw"], g["polys"], strict=True):  # load_masters() refused unequal lists; strict so a bypass cannot skip a polygon
                check(math.copysign(1, signed_area(raw)) == math.copysign(1, signed_area(dec)) and len(dec) >= 3,
                      f"{n} {k}: decimation changed a contour's winding or left it degenerate")
    ok(f"{label}: decimation kept every contour's winding and left none degenerate")
    report["raster_max_diff"] = {"decimation": {}, "union": {}, "seam": {}}
    budget = raster["budget"]
    for n in names:
        dec = master_outlines(masters[n], "polys", group["_angle"])
        raw = master_outlines(masters[n], "raw", group["_angle"])
        uni = union_outlines(dec)
        codes = raster_font_file(dec, tmp / f"{n}-dec.ttf")
        raster_font_file(raw, tmp / f"{n}-raw.ttf")
        raster_font_file(uni, tmp / f"{n}-uni.ttf")
        for size in raster["sizes"]:
            d = render_all(tmp / f"{n}-dec.ttf", codes, size)
            r = render_all(tmp / f"{n}-raw.ttf", codes, size)
            u = render_all(tmp / f"{n}-uni.ttf", codes, size)
            worst_d = max((max_diff(d[g], r[g]), g) for g in codes)
            worst_u = max((max_diff(d[g], u[g]), g) for g in codes)
            worst_s = max((seam_diff(d[g], u[g]), g) for g in codes)
            report["raster_max_diff"]["decimation"][f"{n}@{size}"] = list(worst_d)
            report["raster_max_diff"]["union"][f"{n}@{size}"] = list(worst_u)
            report["raster_max_diff"]["seam"][f"{n}@{size}"] = list(worst_s)
            check(worst_d[0] <= budget["decimation"], f"{n}@{size}px: decimation changed {worst_d[1]} by {worst_d[0]} levels (budget {budget['decimation']})")
            check(worst_u[0] <= budget["union"],
                  f"{n}@{size}px: overlap rendering of {worst_u[1]} differs from its union by {worst_u[0]} levels (budget {budget['union']})")
            check(worst_s[0] <= budget["seam"], f"{n}@{size}px: {worst_s[1]} shows a seam of {worst_s[0]} levels inside a stroke (budget {budget['seam']})")
            ok(f"{label} {n}@{size}px: rasters within budget (decimation {worst_d[0]} at {worst_d[1]}, union {worst_u[0]} at {worst_u[1]}, "
               f"seam {worst_s[0]} at {worst_s[1]})")
    return report


# --- the fold guard, recomputed -----------------------------------------------------------------------
def fold_excursion(raw, runs, dec, kept):
    """The fold guard recomputed in Python from the loaded polygons, so a masters JSON handed to
    --masters cannot carry an exporter verdict this build did not check. Same walk as export.js:
    each edge of a stroke body, undecimated and decimated, every step measured against the raw
    centre line from one sample before the step to its end; the largest run of backward steps."""
    if len(runs) != 2:
        return {"raw": 0.0, "decimated": 0.0}
    (a0, a1), (b0, b1) = runs
    n = a1 - a0 + 1
    check(b1 - b0 + 1 == n, "edge runs of unequal length")
    C = [((raw[a0 + i][0] + raw[b1 - i][0]) / 2, (raw[a0 + i][1] + raw[b1 - i][1]) / 2) for i in range(n)]

    def walk(points, chords):
        worst = acc = 0.0
        for (x0, y0), (x1, y1), (tx, ty) in zip(points, points[1:], chords):
            tl = math.hypot(tx, ty) or 1
            c = ((x1 - x0) * tx + (y1 - y0) * ty) / tl
            if c < -1e-9:
                acc -= c
                worst = max(worst, acc)
            elif c > 1e-9:
                acc = 0.0
        return worst
    out = {"raw": 0.0, "decimated": 0.0}
    for lo, hi, pos in ((a0, a1, lambda i: i - a0), (b0, b1, lambda i: b1 - i)):
        def direction(i1, i2):
            p0, p1 = C[max(0, pos(i1) - 1)], C[pos(i2)]
            return (p1[0] - p0[0], p1[1] - p0[1])
        idx = list(range(lo, hi + 1))
        if pos(lo) > pos(hi):
            idx.reverse()
        out["raw"] = max(out["raw"], walk([raw[i] for i in idx], [direction(i1, i2) for i1, i2 in zip(idx, idx[1:])]))
        on_edge = sorted(((i, m) for m, i in enumerate(kept) if lo <= i <= hi), key=lambda t: pos(t[0]))
        out["decimated"] = max(out["decimated"], walk([dec[m] for i, m in on_edge], [direction(i1, i2) for (i1, _), (i2, _) in zip(on_edge, on_edge[1:])]))
    return out


STROKE_WIDTH_TOLERANCE = 0.15  # units; the raw coordinates are rounded to 0.1, see the module header


def body_interior_widths(raw, runs, W0):
    """(width, sample index) at every interior sample of one stroke body: the two edge runs paired as
    the fold guard pairs them, the centre line their midpoints, arc length along it, interior = at
    least 1.1 x W0 (the teardrop's reach; the taper's 0.9 x W0 is inside it) from either end. A point
    equal to its predecessor or successor on the same edge was moved by the generator's fold pin or
    end clip after the generator took its own measure, so it is not a sample of the drawn width."""
    (a0, a1), (b0, b1) = runs
    n = a1 - a0 + 1
    check(b1 - b0 + 1 == n, "edge runs of unequal length")
    L = [raw[a0 + i] for i in range(n)]
    R = [raw[b1 - i] for i in range(n)]
    C = [((p[0] + q[0]) / 2, (p[1] + q[1]) / 2) for p, q in zip(L, R)]
    s = [0.0]
    for i in range(1, n):
        s.append(s[-1] + math.hypot(C[i][0] - C[i - 1][0], C[i][1] - C[i - 1][1]))
    reach = 1.1 * W0
    for i in range(n):
        if s[i] < reach or s[-1] - s[i] < reach:
            continue
        if any(E[i] == E[j] for E in (L, R) for j in (i - 1, i + 1) if 0 <= j < n):
            continue
        yield math.hypot(L[i][0] - R[i][0], L[i][1] - R[i][1]), i


def min_interior_stroke_width(M, W0):
    """(minimum interior stroke width, "glyph poly P sample S") for one master, recomputed from its raw
    polygons (review finding C7): stroke bodies through body_interior_widths(); ring strokes as the
    distance between an inner ring's points and its outer ring's, where the inner ring is the only
    polygon the generator orients clockwise (negative area) and the outer is the polygon before it,
    the two paired by index i <-> n-1-i because exactly one of the pair was reversed. Every ring sample
    is interior, as in the generator. W0 is the concept's stroke width (W / mult), which the caller
    takes from gen.js, never from the masters JSON (re-review, code-a F002)."""
    best, at = math.inf, None
    for k, g in M["glyphs"].items():
        polys, runs = g["raw"], g["runs"]
        for pi, (raw, rs) in enumerate(zip(polys, runs, strict=True)):
            if len(rs) == 2:
                for w, i in body_interior_widths(raw, rs, W0):
                    if w < best:
                        best, at = w, f"{k} poly {pi} sample {i}"
            elif len(rs) == 1 and pi > 0 and len(runs[pi - 1]) == 1 and len(polys[pi - 1]) == len(raw) and signed_area(raw) < 0:
                outer, n = polys[pi - 1], len(raw)
                for i in range(n):
                    w = math.hypot(outer[i][0] - raw[n - 1 - i][0], outer[i][1] - raw[n - 1 - i][1])
                    if w < best:
                        best, at = w, f"{k} ring poly {pi - 1}/{pi} sample {i}"
    return best, at


def missing_required_characters(required, keys, charset):
    """The characters of a requirements file that no glyph key draws, by export.js's missingCharacters
    rule restated here for the --masters path (review finding C6): the space is the builder's own
    glyph; NBSP is the space when nbsp_to_space; both apostrophes and the four quotes are derived
    from the apostrophe key; ligatures are glyphs, not characters."""
    have = set(keys)
    out = []
    for ch in dict.fromkeys(required):
        if ch == " " or (ch == " " and charset["nbsp_to_space"]):
            continue
        if ch in ("’", "'", "‘", '"', "“", "”") and "'" in have:
            continue
        if ch not in have:
            out.append(ch)
    return out


PARAMS_JS = r"""
const m = require(process.argv[1]); const spec = JSON.parse(process.argv[2]);
const concepts = m.loadConcepts(spec.concepts); const out = {};
for (const [n, s] of Object.entries(spec.masters)) {
  const P = m.params(m.conceptById(concepts, s.concept), s.mult, spec.italic);
  out[n] = { concept: P.id, W: P.W, W0: P.W0, thin: P.thin, track: P.track };
}
process.stdout.write(JSON.stringify(out));
"""


def generator_params(cfg, group):
    """{master: {concept, W, W0, thin, track}} as gen.js params() computes them for the concept and
    multiplier font.json names, read back through node without drawing a glyph. The masters JSON must
    agree with these (load_masters), and the stroke-width recomputation uses this W0, so a JSON that
    overstated W could not move the interior region (re-review, code-a F002). Needs node, on the
    --masters path too: --masters saves the export, not the generator."""
    node = shutil.which("node")
    check(node, "node is not on PATH; the recorded master parameters (W, thin, track) cannot be checked against concepts.js without it")
    italic = group["_angle"] if group["italic"] else False
    spec = {"concepts": str(cfg["_concepts"]), "italic": italic,
            "masters": {n: {"concept": m["concept"], "mult": m["mult"]} for n, m in group["masters"].items()}}
    r = subprocess.run([node, "-e", PARAMS_JS, str(HERE / "gen.js"), json.dumps(spec)], cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    check(r.returncode == 0, f"gen.js params() failed for group {group['_name']}: {r.stderr.strip()[-300:]}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as exc:
        raise CheckFailed(f"gen.js params() printed no JSON for group {group['_name']}: {exc}") from exc


def load_requirements(path):
    try:
        req = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckFailed(f"cannot read the requirements file {path}: {exc}") from exc
    check(isinstance(req, dict), f"{path}: a requirements file is a JSON object")
    return req


def load_masters(path, cfg, group_name, requirements=None):
    """The exporter's JSON, re-checked here rather than trusted: the schema and group names, the
    master names equal to the group's, every glyph's branch record and point structure identical
    across masters, the fold units equal to font.json's, the fold measure recomputed from the
    polygons, the minimum interior stroke width recomputed from the polygons and held against the
    stated figure (C7), and, when a requirements file is given, every required character drawn (C6;
    on the export path export.js has already refused that, so this is the --masters path's check).
    The module header lists what is recomputed and what is still taken from the JSON."""
    group = cfg["groups"][group_name]
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CheckFailed(f"{path} is not valid JSON: {exc}") from exc
    check(data.get("schema") == EXPORT_SCHEMA, f"{path}: schema is {data.get('schema')!r}, expected {EXPORT_SCHEMA!r}")
    check(data.get("group") == group_name, f"{path}: export is for group {data.get('group')!r}, building {group_name!r}")
    check(data.get("family") == cfg["family"], f"{path}: export is for family {data.get('family')!r}, building {cfg['family']!r}")
    check(bool(data.get("italic")) == bool(group["italic"]), f"{path}: export italic={data.get('italic')} but the group says {group['italic']}")
    check(float(data.get("italicAngle", 0)) == group["_angle"], f"{path}: export italicAngle {data.get('italicAngle')} is not the group's {group['_angle']}")
    check(data.get("foldUnits") == cfg["fold_units"],
          f"export.js ({data.get('foldUnits')}) and font.json ({cfg['fold_units']}) disagree on the fold thresholds")
    # the skeleton override the export was drawn with must be the one font.json names, byte for byte (review F002): the
    # --masters path never runs export.js, so without this an export drawn before an edit of the override, or with none,
    # would be built and recorded under the current file's hash
    check(data.get("skeletons") == cfg.get("skeletons"),
          f"{path}: the export was drawn with skeletons {data.get('skeletons')!r} but font.json names {cfg.get('skeletons')!r}; "
          "export again (build without --masters)")
    if cfg.get("_skeletons"):
        now = sha256(cfg["_skeletons"])
        check(data.get("skeletonsSha256") == now,
              f"{path}: the export was drawn with {cfg['skeletons']} at sha256 {data.get('skeletonsSha256')} but the file's sha256 is {now} now; "
              "export again (build without --masters)")
    masters = data["masters"]
    check(list(masters) == list(group["masters"]), f"masters are {list(masters)}, expected {list(group['masters'])}")
    names = list(masters)
    for n in names:
        check(masters[n]["location"] == group["masters"][n]["location"],
              f"{n}: exported at {masters[n]['location']}, font.json says {group['masters'][n]['location']}")
        check(masters[n]["concept"] == group["masters"][n]["concept"] and masters[n]["mult"] == group["masters"][n]["mult"],
              f"{n}: exported concept/mult {masters[n]['concept']}/{masters[n]['mult']} differ from font.json")
    g_keys = set(masters[names[0]]["glyphs"])
    for n in names[1:]:
        check(set(masters[n]["glyphs"]) == g_keys, f"{n} draws a different glyph set from {names[0]}")
    if requirements is not None:
        missing = missing_required_characters(requirements.get("required_characters", ""), g_keys, cfg["charset"])
        check(not missing, f"{len(missing)} required character(s) have no glyph in {path}: "
                           + ", ".join(f"{c!r} U+{ord(c):04X}" for c in missing) + "; add a skeleton to gen.js or change the requirements")
        ok(f"{group_name}: every required character ({len(set(requirements.get('required_characters', '')))} distinct) has a glyph in the masters")
    for k, g0 in masters[names[0]]["glyphs"].items():
        # one record per polygon in each of the four lists, or a zip over them would stop at the shortest
        # list and the checks below would skip the polygons past it in silence (re-review, code-a F003)
        lengths = {key: len(g0[key]) for key in ("raw", "runs", "polys", "keptIdx")}
        check(len(set(lengths.values())) == 1, f"{k}: the per-polygon lists have unequal lengths {lengths}; every polygon needs a raw, "
                                                 f"runs, polys and keptIdx record, so this export is malformed")
        for n in names[1:]:
            g = masters[n]["glyphs"][k]
            check(g["sig"] == g0["sig"] and g["runs"] == g0["runs"] and [len(p) for p in g["polys"]] == [len(p) for p in g0["polys"]]
                  and [len(p) for p in g["raw"]] == [len(p) for p in g0["raw"]] and g["keptIdx"] == g0["keptIdx"],
                  f"{k}: branch record or point structure differs between {names[0]} and {n}")
    # the master parameters the JSON records, read back from gen.js for the concept and multiplier font.json
    # names: W (which sets the recomputation's interior reach), thin and track must equal the generator's
    gp = generator_params(cfg, group)
    for n in names:
        for key in ("concept", "W", "thin", "track"):
            check(masters[n].get(key) == gp[n].get(key),
                  f"{n}: the export records {key} = {masters[n].get(key)!r} but gen.js params() gives {gp[n].get(key)!r} for concept "
                  f"{group['masters'][n]['concept']!r} at mult {group['masters'][n]['mult']}; the recorded parameters are not trusted")
    ok(f"{group_name}: every master's concept, W, thin and track equal gen.js params() for the concept and multiplier font.json names")
    units = cfg["fold_units"]
    for n in names:
        folded, worst = 0, {"raw": (0.0, None), "decimated": (0.0, None)}
        for k, g in masters[n]["glyphs"].items():
            for pi, (raw, runs, dec, kept) in enumerate(zip(g["raw"], g["runs"], g["polys"], g["keptIdx"], strict=True)):
                e = fold_excursion(raw, runs, dec, kept)
                for kind in ("raw", "decimated"):
                    if e[kind] > units[kind]:
                        folded += 1
                    if e[kind] > worst[kind][0]:
                        worst[kind] = (round(e[kind], 2), f"{k} poly {pi}")
        check(folded == 0, f"{n}: {folded} stroke edge(s) fold back (recomputed here), worst {worst}")
        check(masters[n]["foldedEdges"] == 0, f"{n}: the exporter reported {masters[n]['foldedEdges']} folded edge(s)")
        masters[n]["foldedEdgesRecomputed"] = folded
        masters[n]["maxBackwardExcursionRecomputed"] = {kind: list(v) for kind, v in worst.items()}
        ok(f"{group_name} {n}: no stroke edge folds back, recomputed from the polygons (worst {worst})")
        # the stated minimum interior stroke width, against the polygons (review finding C7)
        recomputed, at = min_interior_stroke_width(masters[n], gp[n]["W0"])
        check(recomputed != math.inf, f"{n}: no stroke body or ring pair to measure a stroke width on")
        stated = masters[n]["minStrokeWidth"]
        check(abs(stated - recomputed) <= STROKE_WIDTH_TOLERANCE,
              f"{n}: the export states minStrokeWidth {stated} at {masters[n]['minStrokeAt']!r} but its polygons measure {recomputed:.2f} at {at!r}; "
              f"the stated figure is not trusted (tolerance {STROKE_WIDTH_TOLERANCE})")
        masters[n]["minStrokeWidthRecomputed"] = round(recomputed, 2)
        masters[n]["minStrokeAtRecomputed"] = at
        ok(f"{group_name} {n}: minStrokeWidth {stated} agrees with the polygons ({recomputed:.2f} at {at})")
    return data


def vertical_metrics(masters, italic_angle):
    """(ascent, descent) as positive integers covering every point of every glyph in every master
    (review finding F012 of Bract: constants copied from a precedent clipped accented capitals)."""
    top, bot = -1e9, 1e9
    for M in masters.values():
        for n, (adv, contours) in master_outlines(M, "polys", italic_angle).items():
            for c in contours:
                for x, y in c:
                    top, bot = max(top, y), min(bot, y)
    return math.ceil(top), math.ceil(-bot)


def run_export(cfg, group_name, out_json, eps, requirements_path=None):
    """export.js for one group. With a requirements path the exporter refuses a required character
    that has no skeleton before drawing anything (review finding C6: a build without the path skipped
    that check, so the normal build path now always carries it)."""
    node = shutil.which("node")
    check(node, "node is not on PATH; the generator needs it")
    cmd = [node, str(HERE / "export.js"), "--font", str(cfg["_path"]), "--group", group_name, "--eps", str(eps)]
    if requirements_path is not None:
        cmd += ["--requirements", str(requirements_path)]
    cmd.append(str(out_json))
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    sys.stderr.write(r.stderr)
    check(r.returncode == 0, f"export.js exited {r.returncode} for group {group_name}")
    if requirements_path is not None:
        ok(f"{group_name}: export.js found a skeleton for every required character in {requirements_path}")


# --- statics (--static DIR; review finding F012 of the skill plan) -------------------------------------
def static_file_stem(cfg, instance_name):
    return f"{family_token(cfg)}-{instance_name.replace(' ', '')}"


def instance_weight_class(group, location):
    return round(location["wght"]) if "wght" in location else default_weight_class(group)


def make_static(cfg, group, woff2_bytes, inst):
    """One named instance as a static TTFont: instancer at the user location with overlaps kept, then
    the names, weight class and italic bits this instance must carry (see the module header for why the
    names are written here)."""
    static = instancer.instantiateVariableFont(TTFont(io.BytesIO(woff2_bytes)), dict(inst["location"]), inplace=False,
                                               overlap=instancer.OverlapMode.KEEP_AND_SET_FLAGS)
    static.flavor = None
    # instancer keeps STAT, whose axis names and values point at name IDs 256 and up; this function replaces the
    # whole name table below, so those IDs would name nothing. A static says its weight in its own names.
    if "STAT" in static:
        del static["STAT"]
    style = inst["name"]
    stem = static_file_stem(cfg, style)
    static["name"] = newTable("name")
    static["name"].names = []
    fb = FontBuilder(font=static)
    fb.setupNameTable(name_records(cfg, group, style, f"{cfg['family']} {style}", stem, stem), mac=False)
    os2 = static["OS/2"]
    os2.usWeightClass = instance_weight_class(group, inst["location"])
    fs = os2.fsSelection & ~(FS_ITALIC | FS_REGULAR | FS_BOLD)
    fs |= FS_USE_TYPO | (FS_ITALIC if group["italic"] else 0)
    if not group["italic"] and style == "Regular":
        fs |= FS_REGULAR
    os2.fsSelection = fs
    static["head"].macStyle = MAC_ITALIC if group["italic"] else 0
    static["post"].italicAngle = -group["_angle"] if group["italic"] else 0.0
    return static


def check_static(cfg, group, inst, ttf_bytes, woff2_bytes, vf_woff2_bytes, tmp):
    """Every check a static must pass, read back from the bytes that will be written."""
    label = f"static {inst['name']}"
    st = TTFont(io.BytesIO(ttf_bytes))
    sw = TTFont(io.BytesIO(woff2_bytes))
    for t in ("fvar", "gvar", "avar", "STAT"):
        check(t not in st and t not in sw, f"{label}: {t} table left in the static")
    check(not any(r.platformID == 1 for r in st["name"].names), f"{label}: Macintosh name records in the static")
    check(st["OS/2"].fsType == cfg["names"]["fs_type"], f"{label}: OS/2 fsType {st['OS/2'].fsType} is not font.json's {cfg['names']['fs_type']}")
    check((st["hhea"].ascent, st["hhea"].descent, st["hhea"].lineGap) == (st["OS/2"].sTypoAscender, st["OS/2"].sTypoDescender, st["OS/2"].sTypoLineGap)
          and st["hhea"].lineGap == 0, f"{label}: hhea and OS/2 typo metrics differ, or the line gap is not 0")
    vf = TTFont(io.BytesIO(vf_woff2_bytes))
    check(st.getGlyphOrder() == vf.getGlyphOrder() == sw.getGlyphOrder(), f"{label}: glyph order differs from the variable font")
    # outlines and advances equal an independent instantiation at the same location, exactly
    ref = instancer.instantiateVariableFont(TTFont(io.BytesIO(vf_woff2_bytes)), dict(inst["location"]), inplace=False)
    for gn in st.getGlyphOrder():
        a, b, c = st["glyf"][gn], ref["glyf"][gn], sw["glyf"][gn]
        check(a.numberOfContours == b.numberOfContours == c.numberOfContours, f"{label} {gn}: contour count")
        if a.numberOfContours > 0:
            # instancer leaves float coordinates in memory; compiling rounds them (otRound), so the
            # reference is rounded the same way and the comparison is then exact
            ca, cb, cc = ([(otRound(x), otRound(y)) for x, y in g.getCoordinates(f["glyf"])[0]] for g, f in ((a, st), (b, ref), (c, sw)))
            check(ca == cb == cc, f"{label} {gn}: outline differs from an independent instantiation at {inst['location']}")
            check(a.flags[0] & flagOverlapSimple and c.flags[0] & flagOverlapSimple, f"{label} {gn}: OVERLAP_SIMPLE flag missing")
        check(st["hmtx"][gn] == tuple(otRound(v) for v in ref["hmtx"][gn]) == sw["hmtx"][gn],
              f"{label} {gn}: advance differs from an independent instantiation")
    name = {r.nameID: r.toUnicode() for r in st["name"].names if r.platformID == 3}
    stem = static_file_stem(cfg, inst["name"])
    check(name.get(1) == cfg["family"] and name.get(16) == cfg["family"], f"{label}: family name")
    check(name.get(9) == cfg["names"]["designer"], f"{label}: name ID 9 (designer) is {name.get(9)!r}, font.json names.designer is {cfg['names']['designer']!r}")
    check(name.get(2) == inst["name"] and name.get(17) == inst["name"], f"{label}: subfamily {name.get(2)!r}/{name.get(17)!r} is not {inst['name']!r}")
    check(name.get(4) == f"{cfg['family']} {inst['name']}" and name.get(6) == stem, f"{label}: full/PostScript name")
    check(st["OS/2"].usWeightClass == instance_weight_class(group, inst["location"]), f"{label}: usWeightClass {st['OS/2'].usWeightClass}")
    fs = st["OS/2"].fsSelection
    check(bool(fs & FS_ITALIC) == bool(group["italic"]) and bool(st["head"].macStyle & MAC_ITALIC) == bool(group["italic"]),
          f"{label}: italic bits (fsSelection {fs:#x}, macStyle {st['head'].macStyle:#x}) do not match the group")
    check(not fs & FS_REGULAR or (not group["italic"] and inst["name"] == "Regular"), f"{label}: REGULAR bit set on a non-regular static")
    check(bool(fs & FS_USE_TYPO), f"{label}: USE_TYPO_METRICS lost")
    want_angle = -group["_angle"] if group["italic"] else 0.0
    check(abs(st["post"].italicAngle - want_angle) < 1e-6, f"{label}: post.italicAngle {st['post'].italicAngle} is not {want_angle}")
    # the file loads in FreeType and draws something
    from PIL import Image, ImageDraw, ImageFont
    probe = tmp / f"{stem}-probe.ttf"
    probe.write_bytes(ttf_bytes)
    cmap = st.getBestCmap()
    ch = chr(next(cp for cp in sorted(cmap) if st["glyf"][cmap[cp]].numberOfContours > 0))
    im = Image.new("L", (120, 120), 0)
    ImageDraw.Draw(im).text((20, 90), ch, font=ImageFont.truetype(str(probe), 40), fill=255, anchor="ls")
    check(im.getextrema()[1] > 0, f"{label}: FreeType rendered nothing for {ch!r}")
    ok(f"{group.get('_name', 'group')} {label}: no variation tables, outlines and advances equal an independent instantiation, "
       f"overlap flag on, names/weight {st['OS/2'].usWeightClass}/italic bits right, renders in FreeType")


def build_statics(cfg, group, woff2_bytes, tmp):
    """{file name: bytes} for every named instance of a group, each checked before anything is written."""
    out = {}
    for inst in group["instances"]:
        static = make_static(cfg, group, woff2_bytes, inst)
        stem = static_file_stem(cfg, inst["name"])
        ttf, w2 = io.BytesIO(), io.BytesIO()
        static.save(ttf)
        static.flavor = "woff2"
        static.save(w2)
        check_static(cfg, group, inst, ttf.getvalue(), w2.getvalue(), woff2_bytes, tmp)
        out[f"{stem}.ttf"] = ttf.getvalue()
        out[f"{stem}.woff2"] = w2.getvalue()
    return out


# --- one group -----------------------------------------------------------------------------------------
def build_group(cfg, group_name, eps, masters_path, tmp, ttf_out=None, requirements_path=None, requirements=None, keep_masters=None):
    """Export (unless --masters), check, build and self-check one group. Returns (woff2 bytes, manifest entry, vf).
    `requirements_path` goes to export.js on the export path; `requirements` (the loaded file) is checked
    here on the --masters path. `keep_masters` copies the fresh export JSON to that path (W5)."""
    group = cfg["groups"][group_name]
    tmp = pathlib.Path(tmp)
    if masters_path is None:
        masters_path = tmp / f"{group_name}-masters.json"
        run_export(cfg, group_name, masters_path, eps, requirements_path)
        if keep_masters:
            keep = pathlib.Path(keep_masters)
            if len(cfg["groups"]) > 1 and keep.suffix == ".json":
                keep = keep.with_name(f"{keep.stem}-{group_name}{keep.suffix}")
            keep.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(masters_path, keep)
            log(f"build.py: kept the {group_name} export at {keep}")
        data = load_masters(masters_path, cfg, group_name)
    else:
        own_eps = json.loads(pathlib.Path(masters_path).read_text(encoding="utf-8")).get("eps")
        log(f"build.py: group {group_name}: reusing {masters_path} (re-checked; its own eps {own_eps} applies, not --eps)")
        data = load_masters(masters_path, cfg, group_name, requirements)
    masters = data["masters"]
    vmetrics = vertical_metrics(masters, group["_angle"])
    vf, statics = build_variable(cfg, group, masters, vmetrics)
    buf = io.BytesIO()
    vf.flavor = "woff2"
    vf.save(buf)
    woff2_bytes = buf.getvalue()
    report = self_checks(cfg, group, masters, vf, statics, woff2_bytes, tmp)
    if ttf_out:
        vf.flavor = None
        vf.save(str(ttf_out))
        vf.flavor = "woff2"
    gfile = group_file(cfg, group_name)
    # where the woff2 was WRITTEN: under --out-dir that is the override, not the configured out_dir (re-review,
    # code-a F009); relative to font.json's directory, with .. steps when it lies outside it, so the manifest is the
    # same in every clone; absolute only where no relative path exists (another drive on Windows)
    file_rec = relpath_posix(gfile, cfg["_dir"])
    entry = {
        "file": file_rec, "italic": bool(group["italic"]), "italic_angle": group["_angle"],
        "woff2_sha256": hashlib.sha256(woff2_bytes).hexdigest(), "woff2_bytes": len(woff2_bytes),
        "axes": [{k: v for k, v in a.items()} for a in group["axes"]],
        "instances": [{"name": i["name"], "location": i["location"]} for i in group["instances"]],
        "masters": {n: {"location": group["masters"][n]["location"], "concept": masters[n]["concept"], "mult": masters[n]["mult"],
                        "W": masters[n]["W"], "thin": masters[n]["thin"], "track": masters[n]["track"], "space": masters[n]["space"],
                        "points_raw": sum(len(p) for g in masters[n]["glyphs"].values() for p in g["raw"]),
                        "points": sum(len(p) for g in masters[n]["glyphs"].values() for p in g["polys"]),
                        "min_stroke_width": masters[n]["minStrokeWidth"], "min_stroke_at": masters[n]["minStrokeAt"],
                        "min_stroke_width_recomputed": masters[n]["minStrokeWidthRecomputed"], "min_stroke_at_recomputed": masters[n]["minStrokeAtRecomputed"],
                        "hairline_floor": group["hairline_floors"][n], "titles": masters[n]["titles"]} for n in masters},
        "decimation_eps": data["eps"],
        "glyphs": len(vf.getGlyphOrder()), "cmap_entries": len(vf.getBestCmap()),
        "kern_pairs": len(masters[list(masters)[0]]["kerns"]),
        "vertical_metrics": report.pop("vertical_metrics_written"),  # {"hhea": [asc, desc, gap], "typo": [...], "win": [asc, desc]}
        "fs_type": cfg["names"]["fs_type"],
        **report,
    }
    return woff2_bytes, entry, vf


def tool_versions():
    import brotli
    import pathops
    import PIL
    node = shutil.which("node")
    node_version = subprocess.run([node, "--version"], capture_output=True, text=True, encoding="utf-8").stdout.strip() if node else None
    if not node_version:
        log("build.py: could not read the node version for the manifest")
    return {"node": node_version, "fonttools": fonttools_version, "brotli": brotli.__version__,
            "skia-pathops": pathops.__version__, "pillow": PIL.__version__, "python": platform.python_version()}


def compose_manifest(cfg, entries, previous, requirements_path=None):
    """The manifest for this build: top-level facts plus one entry per group. A partial (--group) build
    keeps the previous manifest's entries for the groups it did not build, and says so. `requirements`
    records the requirements file the build ran with, relative to font.json's directory where it can
    be, or null for a --no-requirements build (review finding C6)."""
    groups = {}
    if previous is not None and set(entries) != set(cfg["groups"]):
        kept = [g for g in previous.get("groups", {}) if g not in entries and g in cfg["groups"]]
        if kept:
            log(f"build.py: manifest keeps the previous entries for {kept}; rebuild without --group to refresh them")
        groups.update({g: previous["groups"][g] for g in kept})
    groups.update(entries)
    sources = {s: sha256(HERE / s) for s in SCRIPT_SOURCES}
    sources["font.json"] = sha256(cfg["_path"])
    sources["concepts.js"] = sha256(cfg["_concepts"])
    if cfg.get("_skeletons"):
        sources[cfg["skeletons"]] = sha256(cfg["_skeletons"])
    if requirements_path is None:
        req_record = None
    else:
        rp = pathlib.Path(requirements_path).resolve()
        req_record = rp.relative_to(cfg["_dir"]).as_posix() if rp.is_relative_to(cfg["_dir"]) else rp.as_posix()
    # the override's name only when font.json names one: an unconditional "skeletons": null would move every project's manifest
    head = {"schema": MANIFEST_SCHEMA, "family": cfg["family"], "version": cfg["version"], "font_json": cfg["_path"].name, "concepts": cfg["concepts"]}
    if cfg.get("_skeletons"):
        head["skeletons"] = cfg["skeletons"]
    return {
        **head, "requirements": req_record,
        "sources_sha256": sources, "tools": tool_versions(),
        "source_date_epoch": int(os.environ["SOURCE_DATE_EPOCH"]),
        "size_budget_bytes": cfg["size_budget_bytes"], "raster_budget": cfg["raster"]["budget"], "raster_sizes": list(cfg["raster"]["sizes"]),
        "fold_units": cfg["fold_units"], "charset": cfg["charset"],
        "groups": {g: groups[g] for g in cfg["groups"] if g in groups},
    }


def read_previous_manifest(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CheckFailed(f"the existing manifest {path} is not valid JSON ({exc}); fix or remove it before building") from exc


def print_entry(group_name, entry):
    log(f"--- {group_name}: {entry['file']}")
    for k, v in entry.items():
        if k not in ("masters", "file", "axes", "instances"):
            log(f"  {k}: {json.dumps(v) if not isinstance(v, (int, str, float, bool)) else v}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--font", required=True, help="the project's font.json")
    ap.add_argument("--group", help="build this group only (default: every group in font.json)")
    ap.add_argument("--masters", help="reuse an export.js JSON for --group instead of running the export (re-checked, never trusted; "
                    "node still reads the master parameters back from gen.js)")
    ap.add_argument("--eps", type=float, help="decimation tolerance in font units (default: font.json decimation_eps)")
    ap.add_argument("--ttf", help="also write the variable TTF here (for inspection; never shipped); one group only")
    ap.add_argument("--check", action="store_true", help="rebuild to memory and compare with the shipped font(s) and manifest")
    ap.add_argument("--static", metavar="DIR", help="also write a static TTF and woff2 per named instance into DIR (relative to the working directory)")
    ap.add_argument("--out-dir", help="build elsewhere: the woff2s AND the manifest go into DIR (relative to the working directory; "
                    "the `manifest` key is ignored)")
    ap.add_argument("--requirements", metavar="PATH",
                    help="the reviewed requirements.json whose required_characters every build must draw (default: requirements.json beside font.json)")
    ap.add_argument("--no-requirements", action="store_true",
                    help="build without a requirements file; the required-character check is then not run, and the manifest says so")
    ap.add_argument("--keep-masters", metavar="PATH",
                    help="keep the fresh export JSON here (one group; with several, -<group> is added before .json); default: discarded with the temp dir")
    args = ap.parse_args(argv)
    try:
        cfg = load_config(args.font, args.out_dir)
        if args.requirements and args.no_requirements:
            raise CheckFailed("--requirements and --no-requirements contradict each other")
        if args.no_requirements:
            requirements_path, requirements = None, None
            log("build.py: --no-requirements: the required-character check is NOT run on this build")
        else:
            requirements_path = pathlib.Path(args.requirements).resolve() if args.requirements else cfg["_dir"] / "requirements.json"
            if not requirements_path.is_file():
                raise CheckFailed(f"no requirements file at {requirements_path}; pass --requirements PATH, or --no-requirements to build without the "
                                  "required-character check (the manifest then records requirements: null)")
            requirements = load_requirements(requirements_path)
    except CheckFailed as exc:
        log(f"build.py: {exc}")
        return 1
    # Reproducibility: fontTools stamps head.created/modified from SOURCE_DATE_EPOCH when it is set.
    # Assigned, not defaulted: a caller's value must not change the bytes (trap 14).
    os.environ["SOURCE_DATE_EPOCH"] = str(int(cfg["source_date_epoch"]))
    group_names = list(cfg["groups"])
    if args.group:
        if args.group not in cfg["groups"]:
            log(f"build.py: no group {args.group!r} in {cfg['_path']} (have {group_names})")
            return 1
        group_names = [args.group]
    if args.masters and len(group_names) != 1:
        log("build.py: --masters applies to one group; pass --group")
        return 1
    if args.ttf and len(group_names) != 1:
        log("build.py: --ttf writes one group's TTF; pass --group")
        return 1
    eps = args.eps if args.eps is not None else cfg["decimation_eps"]
    previous = read_previous_manifest(cfg["_manifest"]) if cfg["_manifest"].exists() else None
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        try:
            built, entries, statics = {}, {}, {}
            for g in group_names:
                woff2_bytes, entry, _vf = build_group(cfg, g, eps, args.masters, tmp, args.ttf, requirements_path, requirements, args.keep_masters)
                built[g], entries[g] = woff2_bytes, entry
                if args.static:
                    statics[g] = build_statics(cfg, cfg["groups"][g], woff2_bytes, tmp)
            manifest = compose_manifest(cfg, entries, previous, requirements_path)
        except CheckFailed as exc:
            log(f"build.py: SELF-CHECK FAILED: {exc}")
            return 1
    for g in group_names:
        print_entry(g, entries[g])
    if args.check:
        rc = 0
        manifest_disk = json.loads(json.dumps(manifest))  # tuples become lists on disk
        same_manifest = previous == manifest_disk
        for g in group_names:
            path = group_file(cfg, g)
            shipped = path.read_bytes() if path.exists() else b""
            same_font = shipped == built[g]
            log(f"build.py --check: {g}: font {'identical' if same_font else 'DIFFERS'}, manifest {'identical' if same_manifest else 'DIFFERS'}")
            if not same_font:
                rc = 1
        if not same_manifest:
            rc = 1
            old = previous or {}
            for k in sorted(set(old) | set(manifest_disk)):
                if old.get(k) != manifest_disk.get(k):
                    log(f"  manifest.{k}: shipped {json.dumps(old.get(k))[:200]} vs rebuilt {json.dumps(manifest_disk.get(k))[:200]}")
        return rc
    cfg["_out_dir"].mkdir(parents=True, exist_ok=True)
    for g in group_names:
        path = group_file(cfg, g)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(built[g])
        log(f"wrote {path} ({len(built[g])} bytes)")
    cfg["_manifest"].parent.mkdir(parents=True, exist_ok=True)
    cfg["_manifest"].write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    log(f"wrote {cfg['_manifest']}")
    if args.static:
        static_dir = resolve_arg(args.static)
        static_dir.mkdir(parents=True, exist_ok=True)
        for g in group_names:
            for fname, data in statics[g].items():
                (static_dir / fname).write_bytes(data)
            log(f"wrote {len(statics[g]) // 2} static instances of {g} to {static_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
