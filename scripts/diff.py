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
and the renderer, versions, layout engine and hinting line), `diff.md` (the changed renders, largest share first, then
how many are unchanged), and one PNG per CHANGED render named `<group>-<instance>-<size>px-<title>.png`: the before
render (black on white), the after render, and the diff (red where the after render has more ink, blue where it has
less, grey where both have ink and agree), stacked. Use a fresh OUT_DIR per round: a PNG left from an earlier run is
not removed. --before is a folder holding the previous build's group files under the names build.py writes (copy
`out/` to `work/round-N/` with `cp -R` before each build); --after defaults to font.json's `out_dir`. Exit 0 whether
or not anything changed; exit 2 when --before or --after lacks a group's file (each missing path is named) or a group of font.json has no `instances`; exit 1
when this Pillow lacks the raqm layout engine or a dependency is missing.

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
    """{group: (relative file name, before path, after path)}: where each group's woff2 lives under each folder. The relative
    name is build.py's own (`specimen.default_font_file`), so a group with a `file` key is found where build.py wrote it."""
    out_dir = pathlib.Path(font_json).parent / cfg.get("out_dir", "out")
    out = {}
    for name in cfg["groups"]:
        rel = specimen.default_font_file(cfg, font_json, name).relative_to(out_dir)
        out[name] = (rel, before / rel, after / rel)
    return out


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
    files = group_files(cfg, font_json, before, after)
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
    entries, layout, used = [], None, {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        for gname, group in cfg["groups"].items():
            rel, bpath, apath = files[gname]
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
    changed = sorted((e for e in entries if e["changed_px"] or e["advance_changed"]),
                     key=lambda e: (-e["share"], -abs(e["advance_after"] - e["advance_before"]), e["group"], e["instance"], e["size"], e["title"]))
    result = {"tool": "diff.py", "before": str(before), "after": str(after), "scale": scale, "threshold": THRESHOLD, "advance_tolerance": ADVANCE_TOL, "gap": GAP,
              "layout": layout, "hinting": HINTING,
              "renderer": {"pillow": PIL.__version__, "freetype": features.version("freetype2"), "fonttools": tt.version, "raqm": features.version("raqm")},
              "renders": len(entries), "changed": len(changed), "entries": entries}
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
    lines += [f"{m - n} of {m} renders unchanged.", "",
              f"Renderer: Pillow {result['renderer']['pillow']}, FreeType {result['renderer']['freetype']}, fontTools {result['renderer']['fonttools']}, "
              f"layout engine {result['layout']}, at {result['scale']}x; {result['hinting']}.",
              "What this proves: what FreeType drew on this machine from the two files, unhinted, at these sizes and instances. "
              "It is not CoreText, not Chrome and not the page's CSS."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", help="the folder to write diff.json, diff.md and the PNGs into (use a fresh one per round)")
    ap.add_argument("--font", required=True, help="the project's font.json")
    ap.add_argument("--before", required=True, help="a folder holding the previous build's group files by build.py's names")
    ap.add_argument("--after", help="a folder holding the current build's group files (default: font.json's out_dir)")
    ap.add_argument("--sizes", nargs="+", type=float, metavar="PX", help="CSS px sizes to render (default: review.sizes)")
    ap.add_argument("--scale", type=int, default=2, help="render at size x SCALE pixels (default 2)")
    args = ap.parse_args(argv)
    if args.scale < 1:
        ap.error("--scale must be at least 1")
    require_raqm()
    try:
        cfg = json.loads(pathlib.Path(args.font).read_text(encoding="utf-8"))
        after = pathlib.Path(args.after) if args.after else pathlib.Path(args.font).parent / cfg.get("out_dir", "out")
        result = run(cfg, args.font, pathlib.Path(args.before), after, pathlib.Path(args.out), args.sizes, args.scale)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        sys.exit(f"diff.py: {type(exc).__name__}: {exc}")
    print(f"diff.py: {result['changed']} of {result['renders']} renders changed; wrote {pathlib.Path(args.out) / 'diff.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
